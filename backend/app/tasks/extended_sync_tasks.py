"""
Celery异步任务 - 扩展数据同步
用于定时同步Tushare扩展数据（资金流向、每日指标、北向资金等）
"""

from datetime import datetime
import asyncio
from typing import Optional

from app.celery_app import celery_app
from app.services.extended_sync_service import ExtendedDataSyncService
from loguru import logger


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
        loop = asyncio.get_event_loop()

        result = loop.run_until_complete(
            service.sync_daily_basic(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )
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
        loop = asyncio.get_event_loop()

        result = loop.run_until_complete(
            service.sync_moneyflow(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                stock_list=stock_list
            )
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
        loop = asyncio.get_event_loop()

        result = loop.run_until_complete(
            service.sync_hk_hold(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )
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
        loop = asyncio.get_event_loop()

        result = loop.run_until_complete(
            service.sync_margin_detail(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )
        )

        logger.info(f"[Celery] 融资融券同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"[Celery] 融资融券同步任务失败: {str(e)}")
        self.retry(countdown=60, exc=e)


@celery_app.task(name="extended.sync_stk_limit",
             bind=True,
             max_retries=3,
             soft_time_limit=300,
             time_limit=600)
def sync_stk_limit_task(self,
                       trade_date: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None):
    """
    同步涨跌停价格任务
    积分消耗：120
    建议执行时间：每日9:00
    """
    try:
        logger.info(f"[Celery] 开始执行涨跌停价格同步任务: trade_date={trade_date}")

        service = ExtendedDataSyncService()
        loop = asyncio.get_event_loop()

        result = loop.run_until_complete(
            service.sync_stk_limit(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )
        )

        logger.info(f"[Celery] 涨跌停价格同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"[Celery] 涨跌停价格同步任务失败: {str(e)}")
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
        loop = asyncio.get_event_loop()

        result = loop.run_until_complete(
            service.sync_adj_factor(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
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
        loop = asyncio.get_event_loop()

        result = loop.run_until_complete(
            service.sync_block_trade(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )
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
        loop = asyncio.get_event_loop()

        result = loop.run_until_complete(
            service.sync_suspend(
                ts_code=ts_code,
                suspend_date=suspend_date,
                resume_date=resume_date
            )
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

        # 涨跌停价格（120分）
        try:
            results['stk_limit'] = sync_stk_limit_task.apply_async(
                kwargs={'trade_date': trade_date}
            ).get(timeout=300)
        except Exception as e:
            logger.error(f"涨跌停价格同步失败: {e}")
            results['stk_limit'] = {"status": "error", "error": str(e)}

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
    'sync-stk-limit': {
        'task': 'extended.sync_stk_limit',
        'schedule': '0 9 * * *',  # 每日9:00
        'description': '同步涨跌停价格数据',
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
    }
}