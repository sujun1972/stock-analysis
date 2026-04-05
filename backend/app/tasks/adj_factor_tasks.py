"""
复权因子数据同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from datetime import datetime
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.adj_factor_service import AdjFactorService
from app.tasks.extended_sync_tasks import run_async_in_celery

# 全量同步进度 Redis key（Set，存储已完成的 ts_code，支持中断续继）
ADJ_FULL_HISTORY_PROGRESS_KEY = "sync:adj_factor:full_history:progress"


@celery_app.task(bind=True, name="tasks.sync_adj_factor")
def sync_adj_factor_task(
    self,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    同步复权因子数据

    Args:
        ts_code: 股票代码（可选）
        trade_date: 交易日期 YYYYMMDD（可选）
        start_date: 开始日期 YYYYMMDD（可选）
        end_date: 结束日期 YYYYMMDD（可选）

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行复权因子同步任务: ts_code={ts_code}, trade_date={trade_date}, "
                   f"start_date={start_date}, end_date={end_date}")

        service = AdjFactorService()
        result = run_async_in_celery(
            service.sync_adj_factor,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

        if result["status"] == "success":
            logger.info(f"复权因子同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"复权因子同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行复权因子同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_adj_factor_full_history",
    max_retries=0,
    soft_time_limit=28800,
    time_limit=32400,
    acks_late=False,  # 支持续继，worker 重启后不自动重新入队
)
def sync_adj_factor_full_history_task(self, start_date: Optional[str] = None, concurrency: int = 8):
    """
    逐只股票全量同步复权因子历史数据

    每只股票单独请求 Tushare，8 并发执行，支持 Redis 中断续继。
    进度存储：Redis Set key = sync:adj_factor:full_history:progress

    Args:
        start_date: 开始日期 YYYYMMDD（可选，默认 20210101）
    """
    from app.core.redis_lock import redis_client
    from app.repositories.stock_basic_repository import StockBasicRepository

    effective_start = start_date or "20210101"
    today = datetime.now().strftime("%Y%m%d")

    logger.info(f"========== [Celery] 开始复权因子全量历史同步任务 start_date={effective_start} ==========")

    if redis_client is None:
        logger.error("Redis 不可用，无法执行全量同步任务")
        return {"status": "error", "message": "Redis 不可用"}

    # 获取全部上市股票
    repo = StockBasicRepository()
    all_ts_codes = repo.get_listed_ts_codes(status='L')
    total = len(all_ts_codes)
    logger.info(f"共 {total} 只上市股票需要同步")

    if total == 0:
        return {"status": "success", "message": "无上市股票", "count": 0}

    # 读取已完成的进度
    completed_set = redis_client.smembers(ADJ_FULL_HISTORY_PROGRESS_KEY)
    logger.info(f"已完成 {len(completed_set)} 只，剩余 {total - len(completed_set)} 只")

    pending_codes = [c for c in all_ts_codes if c not in completed_set]

    service = AdjFactorService()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    success_count = 0
    skip_count = len(completed_set)
    error_count = 0

    CONCURRENCY = max(1, concurrency)
    BATCH_SIZE = 50

    async def sync_one(ts_code: str, sem: asyncio.Semaphore):
        async with sem:
            try:
                result = await service.sync_adj_factor(
                    ts_code=ts_code,
                    start_date=effective_start,
                    end_date=today
                )
                if result.get("status") == "error":
                    return ts_code, False, result.get("error", "未知错误")
                return ts_code, True, None
            except Exception as e:
                return ts_code, False, str(e)

    async def run_concurrent():
        nonlocal success_count, error_count
        sem = asyncio.Semaphore(CONCURRENCY)

        for batch_start in range(0, len(pending_codes), BATCH_SIZE):
            batch = pending_codes[batch_start:batch_start + BATCH_SIZE]
            results = await asyncio.gather(*[sync_one(c, sem) for c in batch])

            for ts_code, ok, err in results:
                if ok:
                    redis_client.sadd(ADJ_FULL_HISTORY_PROGRESS_KEY, ts_code)
                    success_count += 1
                else:
                    error_count += 1
                    if err:
                        logger.error(f"同步 {ts_code} 失败（下次续继）: {err}")

            done = skip_count + success_count
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': done,
                    'total': total,
                    'percent': round(done / total * 100, 1),
                    'success': success_count,
                    'errors': error_count
                }
            )
            logger.info(
                f"进度: {done}/{total} ({round(done / total * 100, 1)}%) "
                f"| 本次成功={success_count} 失败={error_count}"
            )

    try:
        loop.run_until_complete(run_concurrent())
    finally:
        loop.close()

    final_done = len(redis_client.smembers(ADJ_FULL_HISTORY_PROGRESS_KEY))
    if final_done >= total:
        redis_client.delete(ADJ_FULL_HISTORY_PROGRESS_KEY)
        logger.info("✅ 复权因子全量历史同步完成，进度已清除")

    logger.info(
        f"========== [Celery] 复权因子全量同步结束: "
        f"本次成功={success_count}, 跳过={skip_count}, 失败={error_count} =========="
    )
    return {
        "status": "success",
        "total": total,
        "success": success_count,
        "skipped": skip_count,
        "errors": error_count,
        "message": f"同步完成 {success_count} 只，跳过 {skip_count} 只，失败 {error_count} 只"
    }
