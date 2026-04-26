"""批量 AI 分析 Celery 任务

前端提交一组 ts_code，该任务以 STOCK_CONCURRENCY 并发调用 run_multi_expert_for_stock()，
每只完成后把明细和分桶计数回写 celery_task_history（供前端 3 秒轮询渲染进度）。
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from celery.exceptions import SoftTimeLimitExceeded
from loguru import logger

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery


# 股票层面默认并发数；端点可通过 concurrency 参数覆盖（每只内部还有 3-4 个 LLM 并行）
DEFAULT_STOCK_CONCURRENCY = 4

# 单批最大股票数。超过应在端点拒绝；这里作为最后兜底
MAX_BATCH_SIZE = 200

# 写入 celery_task_history.task_type 的常量，endpoint 查询"活跃批量任务"时用
TASK_TYPE = "batch_ai_analysis"

# 单只一键分析复用同一个 Celery 任务（ts_codes 长度=1, concurrency=1），
# 但用独立 task_type 让 active 端点和监控可按子类型区分。两者的 metadata.items 结构一致。
SINGLE_TASK_TYPE = "single_ai_analysis"


@celery_app.task(
    bind=True,
    name="tasks.batch_ai_analysis",
    max_retries=0,
    soft_time_limit=7200,   # 2 小时（200 只 × ~30s 中位耗时 / 4 并发 ≈ 25 分钟，留充足裕度）
    time_limit=7500,
)
def batch_ai_analysis_task(
    self,
    ts_codes: List[str],
    stock_names: Dict[str, str],
    analysis_types: List[str],
    include_cio: bool,
    user_id: int,
    concurrency: Optional[int] = None,
    reuse_existing_experts: bool = True,
):
    """批量为多只股票生成 AI 分析。

    Args:
        ts_codes: 股票 ts_code 列表（端点已限制 ≤ MAX_BATCH_SIZE）
        stock_names: ts_code -> 股票名称 映射（端点通过 StockQuoteCache 预填）
        analysis_types: 分析类型列表（不含 cio_directive，由 include_cio 控制）
        include_cio: 是否追加 CIO 综合决策
        user_id: 发起任务的用户 ID
        concurrency: 股票层面并发数；None 时用 DEFAULT_STOCK_CONCURRENCY；端点可覆盖（1~8）
        reuse_existing_experts: 同一交易日已有合法专家报告时复用（默认 True）
    """
    celery_task_id = self.request.id
    effective_concurrency = max(1, min(concurrency or DEFAULT_STOCK_CONCURRENCY, 8))
    logger.info(
        f"[batch_ai_analysis] 任务启动 task_id={celery_task_id[:8]} "
        f"user_id={user_id} total={len(ts_codes)} concurrency={effective_concurrency} "
        f"reuse_existing_experts={reuse_existing_experts}"
    )

    return run_async_in_celery(
        _batch_run,
        celery_task_id=celery_task_id,
        ts_codes=ts_codes,
        stock_names=stock_names or {},
        analysis_types=analysis_types,
        include_cio=include_cio,
        user_id=user_id,
        concurrency=effective_concurrency,
        reuse_existing_experts=reuse_existing_experts,
    )


async def _batch_run(
    *,
    celery_task_id: str,
    ts_codes: List[str],
    stock_names: Dict[str, str],
    analysis_types: List[str],
    include_cio: bool,
    user_id: int,
    concurrency: int,
    reuse_existing_experts: bool = True,
) -> Dict:
    """异步编排：初始化明细 → Semaphore 并发执行 → 每只完成后回写进度。

    SoftTimeLimitExceeded 由 Celery soft_time_limit 触发；此时把所有 pending/running
    状态的条目标记为 timeout_skipped，并返回部分成功结果（task_success 信号会写
    status='success'，前端 metadata.items 仍可看到完整明细）。
    """
    from app.repositories.celery_task_history_repository import CeleryTaskHistoryRepository
    from app.services.batch_ai_analysis_service import run_multi_expert_for_stock

    repo = CeleryTaskHistoryRepository()

    # 明细项列表：前端轮询时通过 metadata.items 渲染每只股票的状态/耗时/错误
    items: List[Dict] = [
        {
            "ts_code": ts,
            "stock_name": stock_names.get(ts, ""),
            "status": "pending",
            "error": None,
            "duration_sec": None,
            "expert_count": 0,
        }
        for ts in ts_codes
    ]
    total = len(items)
    state_lock = asyncio.Lock()   # 保护 items[] 和 counters 的并发写入
    counters = {"completed": 0, "success": 0, "failed": 0, "timeout_skipped": 0}

    async def _flush_progress():
        await asyncio.to_thread(
            repo.update_batch_progress,
            celery_task_id,
            completed_items=counters["completed"],
            success_items=counters["success"],
            failed_items=counters["failed"] + counters["timeout_skipped"],
            progress=int(counters["completed"] * 100 / total) if total else 100,
            metadata={"items": items, "concurrency": concurrency},
        )

    # 初始化进度快照（提交端点生成 task_id 后已 INSERT 记录，这里 UPDATE 首次快照）
    await asyncio.to_thread(
        repo.update_batch_progress,
        celery_task_id,
        total_items=total,
        completed_items=0,
        success_items=0,
        failed_items=0,
        progress=0,
        metadata={"items": items, "concurrency": concurrency},
    )

    sem = asyncio.Semaphore(concurrency)

    async def _process_one(item: Dict):
        async with sem:
            started_at = datetime.now()
            async with state_lock:
                item["status"] = "running"
            # running 状态先落库一次，让前端看到"分析中"
            await asyncio.to_thread(
                repo.update_batch_progress,
                celery_task_id,
                metadata={"items": items, "concurrency": concurrency},
            )

            ts_code = item["ts_code"]
            stock_code = ts_code.split(".")[0] if "." in ts_code else ts_code
            stock_name = item["stock_name"] or stock_code

            try:
                result = await run_multi_expert_for_stock(
                    ts_code=ts_code,
                    stock_name=stock_name,
                    stock_code=stock_code,
                    analysis_types=list(analysis_types),
                    include_cio=include_cio,
                    user_id=user_id,
                    db=None,   # Service 内部自管 Session（Celery 无请求作用域）
                    reuse_existing_experts=reuse_existing_experts,
                )
                errors = result.get("errors") or []
                expert_count = result.get("expert_count", 0)
                # 判定：全部专家都失败才算整只失败，部分失败仍视为成功
                is_failure = expert_count == 0
                async with state_lock:
                    item["status"] = "error" if is_failure else "success"
                    item["expert_count"] = expert_count
                    item["error"] = (
                        "; ".join(e.get("error", "") for e in errors) if is_failure and errors
                        else (f"{len(errors)} 个专家失败" if errors else None)
                    )
                    item["duration_sec"] = round(
                        (datetime.now() - started_at).total_seconds(), 1
                    )
                    counters["completed"] += 1
                    if is_failure:
                        counters["failed"] += 1
                    else:
                        counters["success"] += 1
            except SoftTimeLimitExceeded:
                # 任务级超时；标记当前条目为超时并冒泡到外层 except 统一收尾
                async with state_lock:
                    item["status"] = "timeout_skipped"
                    item["error"] = "任务总超时被中断"
                    item["duration_sec"] = round(
                        (datetime.now() - started_at).total_seconds(), 1
                    )
                raise
            except Exception as e:  # noqa: BLE001
                logger.error(f"[batch_ai_analysis] {ts_code} 失败: {e}", exc_info=True)
                async with state_lock:
                    item["status"] = "error"
                    item["error"] = str(e)[:500]
                    item["duration_sec"] = round(
                        (datetime.now() - started_at).total_seconds(), 1
                    )
                    counters["completed"] += 1
                    counters["failed"] += 1

            # 每只完成后回写分桶计数 + 整体 progress
            await _flush_progress()

    try:
        await asyncio.gather(*[_process_one(item) for item in items])
        timed_out = False
    except SoftTimeLimitExceeded:
        # 把所有还未完成的条目标记为 timeout_skipped；保留已 success/error 的不变
        async with state_lock:
            for it in items:
                if it["status"] in ("pending", "running"):
                    it["status"] = "timeout_skipped"
                    it["error"] = it["error"] or "任务总超时被中断"
                    counters["timeout_skipped"] += 1
        await _flush_progress()
        timed_out = True
        logger.warning(
            f"[batch_ai_analysis] 任务超时中断 task_id={celery_task_id[:8]} "
            f"completed={counters['completed']}/{total} timeout_skipped={counters['timeout_skipped']}"
        )

    logger.info(
        f"[batch_ai_analysis] 任务结束 task_id={celery_task_id[:8]} "
        f"total={total} success={counters['success']} failed={counters['failed']} "
        f"timeout_skipped={counters['timeout_skipped']} timed_out={timed_out}"
    )

    return {
        "total": total,
        "success": counters["success"],
        "failed": counters["failed"],
        "timeout_skipped": counters["timeout_skipped"],
        "timed_out": timed_out,
    }
