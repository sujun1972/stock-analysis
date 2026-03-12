"""
市场情绪数据Celery任务

定时任务：每日17:30（北京时间）采集市场情绪数据
"""

import asyncio
import pytz
from datetime import datetime
from celery import Task

from loguru import logger

from app.celery_app import celery_app
from app.services.sentiment_service import MarketSentimentService
from app.core.redis_lock import redis_lock


class SentimentSyncTask(Task):
    """情绪数据同步任务基类"""
    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = 300  # 5分钟后重试
    retry_jitter = True


@celery_app.task(
    base=SentimentSyncTask,
    name="sentiment.daily_sync_17_30",
    bind=True
)
def daily_sentiment_sync_task(self):
    """
    每日情绪数据同步任务

    触发时间: 17:30 Beijing Time (UTC 9:30)
    Cron表达式: 30 9 * * 1-5

    流程:
    1. 检查是否交易日
    2. 抓取大盘数据
    3. 抓取涨停板池
    4. 抓取龙虎榜
    5. 记录执行日志
    """
    try:
        # 获取北京时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        date_str = now.strftime('%Y-%m-%d')

        logger.info(f"========== [Celery] 开始执行17:30情绪数据同步任务: {date_str} ==========")

        # 使用分布式锁防止并发执行（手动同步和自动同步不会冲突）
        lock_key = f"sentiment_sync:{date_str}"

        with redis_lock.acquire(lock_key, timeout=600, blocking=False) if redis_lock else _dummy_context() as acquired:
            if not acquired and redis_lock:
                logger.warning(f"⚠️  {date_str} 情绪数据同步任务已在执行中，跳过本次调度")
                return {
                    "status": "skipped",
                    "reason": "任务正在执行中（分布式锁）",
                    "date": date_str
                }

            # 创建服务实例
            service = MarketSentimentService()

            # 运行异步任务
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(
                service.sync_daily_sentiment(date=date_str)
            )

        # 判断结果
        if not result.get('is_trading_day'):
            logger.info(f"[Celery] {date_str} 非交易日，跳过同步")
            return {
                "status": "skipped",
                "reason": "非交易日",
                "date": date_str
            }

        if result.get('success'):
            logger.success(f"[Celery] 情绪数据同步成功: {date_str}")
            logger.info(f"[Celery] 同步详情: {result.get('details', {})}")

            # 记录到scheduled_tasks执行历史（可选）
            _log_task_execution(date_str, 'success', result)

            return {
                "status": "success",
                "date": date_str,
                "data": result
            }
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"[Celery] 情绪数据同步失败: {error_msg}")

            # 记录失败日志
            _log_task_execution(date_str, 'failed', result)

            # 抛出异常触发重试
            raise Exception(error_msg)

    except Exception as e:
        logger.error(f"[Celery] 任务执行异常: {e}")

        # 记录异常
        try:
            _log_task_execution(
                date_str if 'date_str' in locals() else 'unknown',
                'error',
                {'error': str(e)}
            )
        except:
            pass

        # 重试
        raise self.retry(exc=e)


@celery_app.task(
    base=SentimentSyncTask,
    name="sentiment.manual_sync",
    bind=True
)
def manual_sentiment_sync_task(self, date: str = None):
    """
    手动触发的情绪数据同步任务（Admin界面使用）

    Args:
        date: 日期字符串 (YYYY-MM-DD)，默认为今天

    Returns:
        同步结果
    """
    try:
        if not date:
            beijing_tz = pytz.timezone('Asia/Shanghai')
            now = datetime.now(beijing_tz)
            date = now.strftime('%Y-%m-%d')

        logger.info(f"========== [手动同步] 开始执行情绪数据同步: {date} ==========")

        # 使用分布式锁防止并发
        lock_key = f"sentiment_sync:{date}"

        with redis_lock.acquire(lock_key, timeout=600, blocking=False) if redis_lock else _dummy_context() as acquired:
            if not acquired and redis_lock:
                logger.warning(f"⚠️  {date} 情绪数据同步任务已在执行中")
                return {
                    "status": "locked",  # 特殊状态：锁被占用
                    "reason": "数据同步任务正在执行中，请稍后再试",
                    "date": date,
                    "message": "已有同步任务正在进行，请等待其完成"
                }

            # 创建服务实例
            service = MarketSentimentService()

            # 运行异步任务
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    service.sync_daily_sentiment(date=date)
                )
            finally:
                loop.close()

            # 判断结果
            if not result.get('is_trading_day'):
                logger.info(f"[手动同步] {date} 非交易日")
                return {
                    "status": "skipped",
                    "reason": "非交易日",
                    "date": date,
                    "is_trading_day": False
                }

            if result.get('success'):
                logger.success(f"[手动同步] {date} 情绪数据同步成功")
                _log_task_execution(date, 'success', result)

                return {
                    "status": "success",
                    "date": date,
                    "data": result,
                    "is_trading_day": True
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"[手动同步] {date} 同步失败: {error_msg}")
                _log_task_execution(date, 'failed', result)

                raise Exception(error_msg)

    except Exception as e:
        logger.error(f"[手动同步] 任务执行异常: {e}")
        _log_task_execution(date or 'unknown', 'error', {'error': str(e)})
        raise self.retry(exc=e)


@celery_app.task(name="sentiment.calendar_sync")
def sync_trading_calendar_task(years: list):
    """
    同步交易日历任务（按需手动触发）

    Args:
        years: 年份列表

    Returns:
        同步结果
    """
    try:
        logger.info(f"[Celery] 开始同步交易日历: {years}")

        service = MarketSentimentService()

        loop = asyncio.get_event_loop()
        count = loop.run_until_complete(
            service.sync_trading_calendar_batch(years)
        )

        logger.success(f"[Celery] 交易日历同步完成，共{count}条记录")

        return {
            "status": "success",
            "years": years,
            "count": count
        }

    except Exception as e:
        logger.error(f"[Celery] 交易日历同步失败: {e}")
        raise


from contextlib import contextmanager

@contextmanager
def _dummy_context():
    """空上下文管理器（当 Redis 不可用时使用）"""
    yield True


def _log_task_execution(date: str, status: str, result: dict):
    """
    记录任务执行历史到数据库

    Args:
        date: 执行日期
        status: 执行状态 (success/failed/error)
        result: 执行结果
    """
    try:
        import os
        from src.database.connection_pool_manager import ConnectionPoolManager

        db_config = {
            'host': os.getenv('DATABASE_HOST', 'timescaledb'),
            'port': int(os.getenv('DATABASE_PORT', '5432')),
            'database': os.getenv('DATABASE_NAME', 'stock_analysis'),
            'user': os.getenv('DATABASE_USER', 'stock_user'),
            'password': os.getenv('DATABASE_PASSWORD', 'stock_password_123')
        }
        pool_manager = ConnectionPoolManager(db_config)
        conn = pool_manager.get_connection()
        cursor = conn.cursor()

        # 查找任务ID
        cursor.execute("""
            SELECT id FROM scheduled_tasks WHERE task_name = 'daily_sentiment_sync'
        """)
        task_row = cursor.fetchone()

        if task_row:
            task_id = task_row[0]

            # 插入执行历史（补充必要的 task_name 和 module 字段）
            cursor.execute("""
                INSERT INTO task_execution_history (
                    task_id, task_name, module, status, started_at, result_summary
                ) VALUES (%s, %s, %s, %s, NOW(), %s)
            """, (
                task_id,
                'daily_sentiment_sync',
                'sentiment',
                status,
                str(result)[:500]  # 截断过长的结果
            ))

            conn.commit()

        cursor.close()
        pool_manager.release_connection(conn)
        pool_manager.close_all()

    except Exception as e:
        logger.warning(f"记录任务执行历史失败: {e}")


# 任务注册到Celery Beat定时调度
# 在celery_app.py中配置：
"""
celery_app.conf.beat_schedule = {
    'daily-sentiment-sync-17-30': {
        'task': 'sentiment.daily_sync_17_30',
        'schedule': crontab(
            hour=9,      # UTC 9点 = 北京时间17点
            minute=30,
            day_of_week='1-5'  # 周一到周五
        ),
        'options': {
            'expires': 3600,  # 1小时后过期
        }
    },
}
"""
