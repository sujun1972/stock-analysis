"""
Celery异步任务 - 扩展数据同步
用于定时同步Tushare扩展数据（资金流向、每日指标、北向资金等）
"""

from datetime import datetime
import asyncio
from typing import Optional, Callable, Any

from app.celery_app import celery_app
from app.services.extended_sync_service import ExtendedDataSyncService
from app.services.margin_secs_service import MarginSecsService
from app.core.database import reset_async_engine
from loguru import logger


def run_async_in_celery(async_func: Callable, *args, **kwargs) -> Any:
    """
    在 Celery fork pool worker 中安全地运行异步函数

    解决 "attached to a different loop" 错误：
    当 Celery 使用 fork pool 时，全局的 async_engine 会绑定到父进程的事件循环。
    子进程必须创建新的事件循环并重新初始化数据库引擎。

    Args:
        async_func: 要运行的异步函数
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        异步函数的返回值

    Raises:
        传递异步函数抛出的所有异常
    """
    # 关闭继承的旧事件循环
    try:
        old_loop = asyncio.get_event_loop()
        if old_loop and not old_loop.is_closed():
            old_loop.close()
    except RuntimeError:
        # 如果没有运行中的循环，忽略错误
        pass

    # 创建新的事件循环并设置为当前循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # 重新初始化数据库引擎（绑定到新循环）
        reset_async_engine()

        # 运行异步函数
        return loop.run_until_complete(async_func(*args, **kwargs))
    finally:
        # 清理资源
        loop.close()


@celery_app.task(name="extended.sync_daily_basic",
             bind=True,
             max_retries=3,
             soft_time_limit=600,
             time_limit=900)
def sync_daily_basic_task(self,
                         trade_date: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None):
    """
    同步每日指标任务
    积分消耗：120
    建议执行时间：每日17:00
    """
    try:
        logger.info(f"[Celery] 开始执行每日指标同步任务: trade_date={trade_date}")

        service = ExtendedDataSyncService()
        result = run_async_in_celery(
            service.sync_daily_basic,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

        logger.info(f"[Celery] 每日指标同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"[Celery] 每日指标同步任务失败: {str(e)}")
        # 重试任务，延迟60秒
        self.retry(countdown=60, exc=e)


@celery_app.task(name="extended.sync_moneyflow",
             bind=True,
             max_retries=2,
             soft_time_limit=1200,
             time_limit=1500)
def sync_moneyflow_task(self,
                       trade_date: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       stock_list: Optional[list] = None):
    """
    同步资金流向任务（高积分消耗，谨慎使用）
    积分消耗：2000
    建议执行时间：每日17:30
    注意：默认只同步活跃股票TOP100
    """
    try:
        logger.info(f"[Celery] 开始执行资金流向同步任务: trade_date={trade_date}")

        service = ExtendedDataSyncService()
        result = run_async_in_celery(
            service.sync_moneyflow,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list
        )

        logger.info(f"[Celery] 资金流向同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"[Celery] 资金流向同步任务失败: {str(e)}")
        # 由于积分消耗高，重试延迟更长
        self.retry(countdown=300, exc=e)


@celery_app.task(name="extended.sync_hk_hold",
             bind=True,
             max_retries=3,
             soft_time_limit=600,
             time_limit=900)
def sync_hk_hold_task(self,
                     trade_date: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None):
    """
    同步北向资金任务
    积分消耗：300
    建议执行时间：每日18:00
    """
    try:
        logger.info(f"[Celery] 开始执行北向资金同步任务: trade_date={trade_date}")

        service = ExtendedDataSyncService()
        result = run_async_in_celery(
            service.sync_hk_hold,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

        logger.info(f"[Celery] 北向资金同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"[Celery] 北向资金同步任务失败: {str(e)}")
        self.retry(countdown=60, exc=e)


@celery_app.task(name="extended.sync_margin",
             bind=True,
             max_retries=3,
             soft_time_limit=600,
             time_limit=900)
def sync_margin_task(self,
                    trade_date: Optional[str] = None,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None):
    """
    同步融资融券任务
    积分消耗：300
    建议执行时间：每日18:30
    """
    try:
        logger.info(f"[Celery] 开始执行融资融券同步任务: trade_date={trade_date}")

        service = ExtendedDataSyncService()
        result = run_async_in_celery(
            service.sync_margin_detail,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

        logger.info(f"[Celery] 融资融券同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"[Celery] 融资融券同步任务失败: {str(e)}")
        self.retry(countdown=60, exc=e)


@celery_app.task(name="extended.sync_adj_factor",
             bind=True,
             max_retries=3,
             soft_time_limit=600,
             time_limit=900)
def sync_adj_factor_task(self,
                        ts_code: Optional[str] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None):
    """
    同步复权因子任务
    积分消耗：120
    建议执行时间：每周一2:00
    """
    try:
        logger.info(f"[Celery] 开始执行复权因子同步任务: ts_code={ts_code}")

        service = ExtendedDataSyncService()
        result = run_async_in_celery(
            service.sync_adj_factor,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

        logger.info(f"[Celery] 复权因子同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"[Celery] 复权因子同步任务失败: {str(e)}")
        self.retry(countdown=60, exc=e)


@celery_app.task(name="extended.sync_block_trade",
             bind=True,
             max_retries=3,
             soft_time_limit=600,
             time_limit=900)
def sync_block_trade_task(self,
                         trade_date: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None):
    """
    同步大宗交易任务
    积分消耗：300
    建议执行时间：每日19:00
    """
    try:
        logger.info(f"[Celery] 开始执行大宗交易同步任务: trade_date={trade_date}")

        service = ExtendedDataSyncService()
        result = run_async_in_celery(
            service.sync_block_trade,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

        logger.info(f"[Celery] 大宗交易同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"[Celery] 大宗交易同步任务失败: {str(e)}")
        self.retry(countdown=60, exc=e)


@celery_app.task(name="extended.sync_suspend",
             bind=True,
             max_retries=3,
             soft_time_limit=300,
             time_limit=600)
def sync_suspend_task(self,
                     ts_code: Optional[str] = None,
                     suspend_date: Optional[str] = None,
                     resume_date: Optional[str] = None):
    """
    同步停复牌信息任务
    积分消耗：120
    建议执行时间：每日
    """
    try:
        logger.info(f"[Celery] 开始执行停复牌信息同步任务")

        service = ExtendedDataSyncService()
        result = run_async_in_celery(
            service.sync_suspend,
            ts_code=ts_code,
            suspend_date=suspend_date,
            resume_date=resume_date
        )

        logger.info(f"[Celery] 停复牌信息同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"[Celery] 停复牌信息同步任务失败: {str(e)}")
        self.retry(countdown=60, exc=e)


@celery_app.task(name="extended.sync_all",
             bind=True,
             max_retries=1,
             soft_time_limit=3600,
             time_limit=4800)
def sync_all_extended_data_task(self, trade_date: Optional[str] = None):
    """
    同步所有扩展数据（慎用）
    该任务会同步所有类型的扩展数据
    总积分消耗：约3500分
    建议：分开执行各个任务，避免一次性消耗过多积分
    """
    try:
        if not trade_date:
            trade_date = datetime.now().strftime("%Y%m%d")

        logger.info(f"[Celery] 开始同步所有扩展数据: trade_date={trade_date}")

        results = {}

        # 每日指标（120分）
        try:
            results['daily_basic'] = sync_daily_basic_task.apply_async(
                kwargs={'trade_date': trade_date}
            ).get(timeout=600)
        except Exception as e:
            logger.error(f"每日指标同步失败: {e}")
            results['daily_basic'] = {"status": "error", "error": str(e)}

        # 北向资金（300分）
        try:
            results['hk_hold'] = sync_hk_hold_task.apply_async(
                kwargs={'trade_date': trade_date}
            ).get(timeout=600)
        except Exception as e:
            logger.error(f"北向资金同步失败: {e}")
            results['hk_hold'] = {"status": "error", "error": str(e)}

        # 融资融券（300分）
        try:
            results['margin'] = sync_margin_task.apply_async(
                kwargs={'trade_date': trade_date}
            ).get(timeout=600)
        except Exception as e:
            logger.error(f"融资融券同步失败: {e}")
            results['margin'] = {"status": "error", "error": str(e)}

        # 资金流向（2000分）- 默认不执行，需要显式开启
        # results['moneyflow'] = sync_moneyflow_task.apply_async(
        #     kwargs={'trade_date': trade_date}
        # ).get(timeout=1200)

        logger.info(f"[Celery] 所有扩展数据同步完成: {results}")
        return results

    except Exception as e:
        logger.error(f"[Celery] 批量同步扩展数据失败: {str(e)}")
        raise


# 注册任务到Celery beat schedule
# 这些配置可以在Admin界面的定时任务管理中动态调整
EXTENDED_SYNC_SCHEDULES = {
    'sync-daily-basic': {
        'task': 'extended.sync_daily_basic',
        'schedule': '0 17 * * *',  # 每日17:00
        'description': '同步每日指标数据（换手率、PE等）',
        'points_consumption': 120,
        'enabled': True
    },
    'sync-hk-hold': {
        'task': 'extended.sync_hk_hold',
        'schedule': '0 18 * * *',  # 每日18:00
        'description': '同步北向资金持股数据',
        'points_consumption': 300,
        'enabled': True
    },
    'sync-margin': {
        'task': 'extended.sync_margin',
        'schedule': '30 18 * * *',  # 每日18:30
        'description': '同步融资融券数据',
        'points_consumption': 300,
        'enabled': True
    },
    'sync-moneyflow': {
        'task': 'extended.sync_moneyflow',
        'schedule': '30 17 * * *',  # 每日17:30
        'description': '同步资金流向数据（高积分消耗）',
        'points_consumption': 2000,
        'enabled': False  # 默认关闭，因为积分消耗高
    },
    'sync-adj-factor': {
        'task': 'extended.sync_adj_factor',
        'schedule': '0 2 * * 1',  # 每周一2:00
        'description': '同步复权因子',
        'points_consumption': 120,
        'enabled': True
    },
    'sync-block-trade': {
        'task': 'extended.sync_block_trade',
        'schedule': '0 19 * * *',  # 每日19:00
        'description': '同步大宗交易数据',
        'points_consumption': 300,
        'enabled': False  # 默认关闭
    },
    'sync-margin-secs': {
        'task': 'extended.sync_margin_secs',
        'schedule': '0 8 * * *',  # 每日8:00（盘前更新）
        'description': '同步融资融券标的（盘前更新）',
        'points_consumption': 2000,
        'enabled': False  # 默认关闭，高积分消耗
    }
}


@celery_app.task(name="extended.sync_margin_secs",
             bind=True,
             max_retries=3,
             soft_time_limit=600,
             time_limit=900)
def sync_margin_secs_task(self,
                         trade_date: Optional[str] = None,
                         exchange: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None):
    """
    同步融资融券标的任务

    无参数调用时使用 sync_incremental（从 sync_configs 读取回看天数）。
    有参数时使用原始 sync_margin_secs（直接传参给 Tushare）。
    """
    try:
        logger.info(f"[Celery] 开始执行融资融券标的同步任务: trade_date={trade_date}, exchange={exchange}, "
                   f"start_date={start_date}, end_date={end_date}")

        service = MarginSecsService()

        if not trade_date and not exchange and not start_date and not end_date:
            result = run_async_in_celery(service.sync_incremental)
        else:
            result = run_async_in_celery(
                service.sync_margin_secs,
                trade_date=trade_date,
                exchange=exchange,
                start_date=start_date,
                end_date=end_date
            )

        if result.get("status") == "success":
            logger.info(f"[Celery] 融资融券标的同步成功: {result.get('records', 0)} 条")
            return result
        else:
            error_msg = result.get('error') or result.get('message', '未知错误')
            logger.warning(f"[Celery] 融资融券标的同步失败: {result}")
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"[Celery] 融资融券标的同步任务失败: {str(e)}")
        raise


@celery_app.task(
    name="tasks.sync_margin_secs_full_history",
    bind=True,
    max_retries=0,
    soft_time_limit=7200,
    time_limit=10800,
    acks_late=False,
)
def sync_margin_secs_full_history_task(
    self,
    start_date: Optional[str] = None,
    concurrency: int = 5,
    **kwargs
):
    """按自然月切片全量同步融资融券标的历史数据（支持中断续继）"""
    import asyncio
    from app.core.redis_lock import redis_client, redis_lock
    from app.tasks.sync_tasks import _DummyContext

    LOCK_KEY = "sync:margin_secs:full_history:lock"
    logger.info(f"[Celery] 开始融资融券标的全量历史同步 start_date={start_date} concurrency={concurrency}")

    if redis_client is None:
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(LOCK_KEY, timeout=7200, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = MarginSecsService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.sync_full_history(
                    redis_client=redis_client,
                    start_date=start_date,
                    concurrency=concurrency,
                    update_state_fn=self.update_state
                )
            )
        finally:
            loop.close()

    logger.info(f"[Celery] 融资融券标的全量历史同步结束: 成功={result.get('success')}, 跳过={result.get('skipped')}, 失败={result.get('errors')}")
    return result
