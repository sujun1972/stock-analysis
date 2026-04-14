"""
同步任务管理仪表盘 API

提供：
1. GET  /sync-dashboard/overview          - 所有表的同步状态快照（配置 + 最近任务历史 + Redis进度）
2. GET  /sync-dashboard/{table_key}/progress - 查询单表的 Redis 全量同步进度
3. GET  /sync-dashboard/configs           - 获取所有同步配置（可编辑）
4. PUT  /sync-dashboard/configs/{table_key} - 更新单条同步配置
5. POST /sync-dashboard/{table_key}/clear-progress - 清除 Redis 进度（重置全量同步）
"""

import asyncio
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from loguru import logger
from pydantic import BaseModel

from app.api.error_handler import handle_api_errors
from app.core.dependencies import require_admin
from app.models.api_response import ApiResponse
from app.models.user import User
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.celery_task_history_repository import CeleryTaskHistoryRepository
from app.repositories.scheduled_task_repository import ScheduledTaskRepository
from app.repositories.sync_history_repository import SyncHistoryRepository

router = APIRouter()

# Redis 全量同步进度 key 的命名规则映射
# key = table_key, value = Redis set key 前缀
FULL_SYNC_REDIS_KEYS: Dict[str, str] = {
    "stock_daily":      "sync:daily:full_history:progress",
    "adj_factor":       "sync:adj_factor:full_history:progress",
    "daily_basic":      "sync:daily_basic:full_history:progress",
    "stk_limit_d":      "sync:stk_limit_d:full_history:progress",
    "suspend":          "sync:suspend:full_history:progress",
    "hsgt_top10":       "sync:hsgt_top10:full_history:progress",
    "ggt_top10":        "sync:ggt_top10:full_history:progress",
    "ggt_daily":        "sync:ggt_daily:full_history:progress",
    "ggt_monthly":      "sync:ggt_monthly:full_history:progress",
    "income":           "sync:income:full_history:progress",
    "balancesheet":     "sync:balancesheet:full_history:progress",
    "cashflow":         "sync:cashflow:full_history:progress",
    "forecast":         "sync:forecast:full_history:progress",
    "express":          "sync:express:full_history:progress",
    "dividend":         "sync:dividend:full_history:progress",
    "fina_indicator":   "sync:fina_indicator:full_history:progress",
    "fina_mainbz":      "sync:fina_mainbz:full_history:progress",
    "fina_audit":       "sync:fina_audit:full_history:progress",
    "disclosure_date":  "sync:disclosure_date:full_history:progress",
    "pledge_stat":      "sync:pledge_stat:full_history:progress",
    "repurchase":       "sync:repurchase:full_history:progress",
    "share_float":      "sync:share_float:full_history:progress",
    "stk_holdernumber": "sync:stk_holdernumber:full_history:progress",
    "block_trade":      "sync:block_trade:full_history:progress",
    "stk_holdertrade":  "sync:stk_holdertrade:full_history:progress",
    # 基础数据
    "stock_st":         "sync:stock_st:full_history:progress",
    # 两融及转融通
    "margin":                "sync:margin:full_history:progress",
    "margin_detail":         "sync:margin_detail:full_history:progress",
    "margin_secs":           "sync:margin_secs:full_history:progress",
    "slb_len":               "sync:slb_len:full_history:progress",
    "moneyflow":             "sync:moneyflow:full_history:progress",
    "moneyflow_hsgt":        "sync:moneyflow_hsgt:full_history:progress",
    "moneyflow_mkt_dc":      "sync:moneyflow_mkt_dc:full_history:progress",
    "moneyflow_ind_dc":      "sync:moneyflow_ind_dc:full_history:progress",
    "moneyflow_stock_dc":    "sync:moneyflow_stock_dc:full_history:progress",
    # 特色数据
    "report_rc":             "sync:report_rc:full_history:progress",
    "cyq_perf":              "sync:cyq_perf:full_history:progress",
    "cyq_chips":             "sync:cyq_chips:full_history:progress",
    "ccass_hold":            "sync:ccass_hold:full_history:progress",
    "ccass_hold_detail":     "sync:ccass_hold_detail:full_history:progress",
    "hk_hold":               "sync:hk_hold:full_history:progress",
    "stk_auction_o":         "sync:stk_auction_o:full_history:progress",
    "stk_auction_c":         "sync:stk_auction_c:full_history:progress",
    "stk_nineturn":          "sync:stk_nineturn:full_history:progress",
    "stk_ah_comparison":     "sync:stk_ah_comparison:full_history:progress",
    "stk_surv":              "sync:stk_surv:full_history:progress",
    "broker_recommend":      "sync:broker_recommend:full_history:progress",
    # 参考数据（异常波动类）
    "stk_shock":             "sync:stk_shock:full_history:progress",
    "stk_high_shock":        "sync:stk_high_shock:full_history:progress",
    "stk_alert":             "sync:stk_alert:full_history:progress",
    # 打板专题
    "top_list":              "sync:top_list:full_history:progress",
    "top_inst":              "sync:top_inst:full_history:progress",
    "limit_list":            "sync:limit_list:full_history:progress",
    "limit_step":            "sync:limit_step:full_history:progress",
    "limit_cpt":             "sync:limit_cpt:full_history:progress",
    # dc_index 按板块类型分 key，此处列出默认类型（概念板块）
    "dc_index":              "sync:dc_index:full_history:progress:概念板块",
    "dc_index_industry":     "sync:dc_index:full_history:progress:行业板块",
    "dc_index_region":       "sync:dc_index:full_history:progress:地域板块",
    "dc_member":             "sync:dc_member:full_history:progress",
    "dc_daily":              "sync:dc_daily:full_history:progress",
}


def _get_redis():
    """获取 Redis 客户端（懒加载）"""
    try:
        import redis as redis_lib
        from app.core.config import settings
        return redis_lib.Redis(
            host=getattr(settings, 'REDIS_HOST', 'redis'),
            port=int(getattr(settings, 'REDIS_PORT', 6379)),
            db=0,
            decode_responses=True,
            socket_connect_timeout=2,
        )
    except Exception:
        return None


def release_stale_lock(table_key: str) -> bool:
    """
    检查全量同步 lock key 是否为残留锁（锁存在但数据库中没有对应的 running 任务），
    若是则删除并返回 True；锁不存在或任务真实在跑返回 False。

    供各全量同步 API 端点在提交新任务前调用，实现无感知自动解锁。
    """
    lock_key = f"sync:{table_key}:full_history:lock"
    r = _get_redis()
    if not r:
        return False
    try:
        if not r.exists(lock_key):
            return False  # 锁不存在，无需处理
        # 锁存在，检查数据库里是否有真实 running 的全量任务
        repo = CeleryTaskHistoryRepository()
        rows = repo.execute_query(
            """
            SELECT id FROM celery_task_history
            WHERE task_name LIKE %s
              AND status = 'running'
              AND started_at > NOW() - INTERVAL '4 hours'
            LIMIT 1
            """,
            (f"tasks.sync_{table_key.replace('-', '_')}_full_history%",),
        )
        if rows:
            return False  # 任务确实在跑，不清锁
        # 没有活跃任务，锁是残留的
        r.delete(lock_key)
        logger.warning(f"[release_stale_lock] 检测到 {table_key} 残留锁，已自动释放（无对应活跃任务）")
        return True
    except Exception as e:
        logger.error(f"[release_stale_lock] 检查 {table_key} 锁失败: {e}")
        return False


def _get_redis_progress(table_key: str) -> Optional[Dict]:
    """查询单表的 Redis 全量同步进度"""
    redis_key = FULL_SYNC_REDIS_KEYS.get(table_key)
    if not redis_key:
        return None
    r = _get_redis()
    if not r:
        return None
    try:
        count = r.scard(redis_key)
        if count == 0:
            return None
        return {
            "redis_key": redis_key,
            "completed_count": count,
        }
    except Exception:
        return None


def _get_last_task(task_name: str, repo: CeleryTaskHistoryRepository) -> Optional[Dict]:
    """查询某 Celery 任务名的最近一次执行记录"""
    if not task_name:
        return None
    try:
        rows = repo.execute_query(
            """
            SELECT celery_task_id, status, started_at, completed_at, duration_ms, error
            FROM celery_task_history
            WHERE task_name = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (task_name,),
        )
        if not rows:
            return None
        r = rows[0]
        return {
            "celery_task_id": r[0],
            "status": r[1],
            "started_at": r[2].isoformat() + 'Z' if r[2] else None,
            "completed_at": r[3].isoformat() + 'Z' if r[3] else None,
            "duration_ms": r[4],
            "error": r[5],
        }
    except Exception:
        return None


# ==================== Pydantic ====================

class SyncConfigUpdate(BaseModel):
    incremental_default_days: Optional[int] = None
    incremental_sync_strategy: Optional[str] = None  # 增量同步策略
    full_sync_strategy: Optional[str] = None
    full_sync_concurrency: Optional[int] = None
    passive_sync_enabled: Optional[bool] = None
    passive_sync_task_name: Optional[str] = None
    notes: Optional[str] = None
    api_name: Optional[str] = None
    description: Optional[str] = None
    doc_url: Optional[str] = None
    data_source: Optional[str] = None  # 'tushare' 或 'akshare'，None 表示不修改
    api_limit: Optional[int] = None    # 接口单次请求上限（超出则分页继续）
    max_requests_per_minute: Optional[int] = None  # 每分钟最大请求数（None=不修改，0=不限速，正整数=覆盖全局）
    api_params: Optional[dict] = None  # 接口参数约束（JSONB）


class ScheduleUpdate(BaseModel):
    enabled: Optional[bool] = None
    cron_expression: Optional[str] = None


# ==================== 路由 ====================

@router.get("/overview")
@handle_api_errors
async def get_overview(
    category: Optional[str] = Query(None, description="按分类筛选"),
    current_user: User = Depends(require_admin),
):
    """
    获取所有数据表的同步状态快照。

    每条记录包含：
    - 同步配置（策略、并发数、积分消耗等）
    - 增量任务的最近执行记录
    - 全量任务的最近执行记录
    - Redis 全量进度（如果有中断续继进度）
    """
    config_repo = SyncConfigRepository()
    task_repo = CeleryTaskHistoryRepository()
    schedule_repo = ScheduledTaskRepository()

    configs = await asyncio.to_thread(config_repo.get_all)
    if category:
        configs = [c for c in configs if c['category'] == category]

    # 收集所有需要查询的任务名（去重）
    all_task_names = set()
    for cfg in configs:
        if cfg['incremental_task_name']:
            all_task_names.add(cfg['incremental_task_name'])
        if cfg['full_sync_task_name']:
            all_task_names.add(cfg['full_sync_task_name'])

    # 批量查询各任务最近一次执行记录
    async def _batch_last_tasks():
        if not all_task_names:
            return {}
        result = {}
        for task_name in all_task_names:
            record = await asyncio.to_thread(_get_last_task, task_name, task_repo)
            if record:
                result[task_name] = record
        return result

    # 批量查询增量任务的定时调度配置
    async def _batch_schedules():
        incr_names = [cfg['incremental_task_name'] for cfg in configs if cfg['incremental_task_name']]
        if not incr_names:
            return {}
        result = {}
        all_tasks = await asyncio.to_thread(schedule_repo.get_all_tasks)
        for t in all_tasks:
            if t['task_name'] in incr_names:
                result[t['task_name']] = {
                    'schedule_id': t['id'],
                    'cron_expression': t['cron_expression'],
                    'enabled': t['enabled'],
                }
        return result

    # 批量查询各表最近一次成功同步的数据截止日期
    async def _batch_last_data_dates():
        sync_hist_repo = SyncHistoryRepository()
        table_keys = [cfg['table_key'] for cfg in configs]
        if not table_keys:
            return {}
        try:
            placeholders = ','.join(['%s'] * len(table_keys))
            rows = await asyncio.to_thread(
                sync_hist_repo.execute_query,
                f"""
                SELECT DISTINCT ON (table_key) table_key, data_end_date
                FROM sync_history
                WHERE table_key IN ({placeholders})
                  AND status = 'success'
                  AND data_end_date IS NOT NULL
                ORDER BY table_key, started_at DESC
                """,
                tuple(table_keys),
            )
            return {r[0]: r[1] for r in rows} if rows else {}
        except Exception:
            return {}

    last_tasks, schedules, last_data_dates = await asyncio.gather(
        _batch_last_tasks(), _batch_schedules(), _batch_last_data_dates()
    )

    # 组合结果
    items = []
    for cfg in configs:
        item = dict(cfg)
        item['last_incremental'] = last_tasks.get(cfg['incremental_task_name'])
        item['last_full_sync'] = last_tasks.get(cfg['full_sync_task_name'])
        item['redis_progress'] = _get_redis_progress(cfg['table_key'])
        item['incremental_schedule'] = schedules.get(cfg['incremental_task_name'])
        item['last_data_date'] = last_data_dates.get(cfg['table_key'])
        items.append(item)

    # 分类汇总
    categories = {}
    for item in items:
        cat = item['category']
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1

    return ApiResponse.success(data={
        "items": items,
        "total": len(items),
        "categories": [{"name": k, "count": v} for k, v in categories.items()],
    })


@router.get("/configs")
@handle_api_errors
async def get_configs(
    category: Optional[str] = Query(None),
    current_user: User = Depends(require_admin),
):
    """获取所有同步配置（用于配置管理页面）"""
    repo = SyncConfigRepository()
    configs = await asyncio.to_thread(repo.get_all)
    if category:
        configs = [c for c in configs if c['category'] == category]
    return ApiResponse.success(data={"items": configs, "total": len(configs)})


@router.put("/configs/{table_key}")
@handle_api_errors
async def update_config(
    table_key: str,
    body: SyncConfigUpdate,
    current_user: User = Depends(require_admin),
):
    """更新单条同步配置（可编辑的字段：并发数、回看天数、被动同步开关、备注、数据源）"""
    repo = SyncConfigRepository()
    # 使用 exclude_unset=True：只包含客户端显式传入的字段（含显式传 null 的字段），
    # 未传入的字段不会覆盖数据库现有值。
    data = body.model_dump(exclude_unset=True)
    updated = await asyncio.to_thread(repo.update, table_key, data)
    if not updated:
        return ApiResponse.error(message=f"配置 {table_key} 不存在或无可更新字段", code=400)
    cfg = await asyncio.to_thread(repo.get_by_table_key, table_key)
    return ApiResponse.success(data=cfg, message="配置已更新")


@router.put("/configs/{table_key}/schedule")
@handle_api_errors
async def update_schedule(
    table_key: str,
    body: ScheduleUpdate,
    current_user: User = Depends(require_admin),
):
    """更新增量同步任务的定时调度配置（启用/禁用、Cron 表达式）"""
    config_repo = SyncConfigRepository()
    cfg = await asyncio.to_thread(config_repo.get_by_table_key, table_key)
    if not cfg or not cfg.get('incremental_task_name'):
        return ApiResponse.error(message=f"表 {table_key} 不存在或无增量同步任务", code=400)

    task_name = cfg['incremental_task_name']
    schedule_repo = ScheduledTaskRepository()
    task = await asyncio.to_thread(schedule_repo.get_by_task_name, task_name)
    if not task:
        return ApiResponse.error(message=f"定时任务 {task_name} 不存在于 scheduled_tasks 表", code=404)

    await asyncio.to_thread(
        schedule_repo.update_task_config,
        task_name,
        body.cron_expression,
        body.enabled,
    )
    updated = await asyncio.to_thread(schedule_repo.get_by_task_name, task_name)
    return ApiResponse.success(data={
        'schedule_id': updated['id'],
        'task_name': task_name,
        'cron_expression': updated['cron_expression'],
        'enabled': updated['enabled'],
    }, message="调度配置已更新")


@router.get("/{table_key}/progress")
@handle_api_errors
async def get_table_progress(
    table_key: str,
    current_user: User = Depends(require_admin),
):
    """查询单表 Redis 全量同步进度"""
    progress = _get_redis_progress(table_key)
    if progress is None:
        return ApiResponse.success(data={"table_key": table_key, "has_progress": False})
    return ApiResponse.success(data={
        "table_key": table_key,
        "has_progress": True,
        **progress,
    })


@router.post("/{table_key}/clear-progress")
@handle_api_errors
async def clear_progress(
    table_key: str,
    current_user: User = Depends(require_admin),
):
    """
    清除 Redis 全量同步进度（同时释放残留锁）。

    清除后下次触发全量同步时将从头开始，而不是续继。
    适用于：数据库已清空后重新全量同步的场景，或任务异常中断后锁未释放的场景。
    """
    redis_key = FULL_SYNC_REDIS_KEYS.get(table_key)
    if not redis_key:
        return ApiResponse.error(message=f"表 {table_key} 没有 Redis 进度记录", code=400)
    r = _get_redis()
    if not r:
        return ApiResponse.error(message="Redis 连接失败", code=500)
    try:
        lock_key = f"sync:{table_key}:full_history:lock"
        deleted_progress = r.delete(redis_key)
        deleted_lock = r.delete(lock_key)
        return ApiResponse.success(data={
            "table_key": table_key,
            "redis_key": redis_key,
            "deleted": deleted_progress > 0,
            "lock_released": deleted_lock > 0,
        }, message="进度已清除，锁已释放，下次全量同步将从头开始")
    except Exception as e:
        return ApiResponse.error(message=f"清除失败: {e}", code=500)
