"""
市场情绪数据Celery任务

定时任务：每日17:30（北京时间）采集市场情绪数据
"""

import pytz
from datetime import datetime
from celery import Task

from loguru import logger

from app.celery_app import celery_app
from app.services.sentiment_service import MarketSentimentService
from app.core.redis_lock import redis_lock
from app.tasks.extended_sync_tasks import run_async_in_celery


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

            # 创建服务实例并运行异步任务
            service = MarketSentimentService()
            result = run_async_in_celery(
                service.sync_daily_sentiment,
                date=date_str
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

        # 更新任务状态为开始
        self.update_state(
            state='PROGRESS',
            meta={
                'message': f'开始同步 {date} 的情绪数据',
                'progress': 0,
                'current': 0,
                'total': 3,  # 3个步骤：大盘数据、涨停板池、龙虎榜
                'date': date
            }
        )

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

            # 更新进度：检查交易日
            self.update_state(
                state='PROGRESS',
                meta={
                    'message': f'检查 {date} 是否为交易日',
                    'progress': 10,
                    'current': 0,
                    'total': 3,
                    'date': date
                }
            )

            # 创建服务实例
            service = MarketSentimentService()

            # 运行异步任务
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # 由于无法在 fetcher 内部直接更新 Celery 状态，
                # 我们在每个步骤前后更新进度

                # 步骤1: 同步大盘数据
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'message': f'正在抓取大盘数据 (1/3)',
                        'progress': 25,
                        'current': 1,
                        'total': 3,
                        'date': date
                    }
                )

                # 执行完整同步
                result = loop.run_until_complete(
                    service.sync_daily_sentiment(date=date)
                )

                # 根据同步的表来判断进度
                synced_count = len(result.get('synced_tables', []))

                # 步骤2: 涨停板池
                if synced_count >= 1:
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'message': f'正在抓取涨停板池 (2/3)',
                            'progress': 50,
                            'current': 2,
                            'total': 3,
                            'date': date
                        }
                    )

                # 步骤3: 龙虎榜
                if synced_count >= 2:
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'message': f'正在抓取龙虎榜 (3/3)',
                            'progress': 75,
                            'current': 3,
                            'total': 3,
                            'date': date
                        }
                    )

            finally:
                loop.close()

            # 判断结果
            if not result.get('is_trading_day'):
                logger.info(f"[手动同步] {date} 非交易日，尝试查找最近一个交易日")

                # 查找最近一个交易日
                from datetime import datetime, timedelta
                target_date = datetime.strptime(date, '%Y-%m-%d')
                attempts = 0
                max_attempts = 10  # 最多向前查找10天

                while attempts < max_attempts:
                    target_date -= timedelta(days=1)
                    date_str = target_date.strftime('%Y-%m-%d')
                    attempts += 1

                    logger.info(f"[手动同步] 尝试同步最近交易日: {date_str} (尝试 {attempts}/{max_attempts})")

                    # 更新进度提示
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'message': f'{date} 非交易日，正在同步最近交易日 {date_str}',
                            'progress': 15,
                            'current': 0,
                            'total': 3,
                            'date': date_str
                        }
                    )

                    # 尝试同步该日期
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            service.sync_daily_sentiment(date=date_str)
                        )
                    finally:
                        loop.close()

                    # 如果是交易日，退出循环
                    if result.get('is_trading_day'):
                        logger.success(f"[手动同步] 找到最近交易日: {date_str}")
                        date = date_str  # 更新为实际同步的日期
                        break
                    else:
                        logger.debug(f"[手动同步] {date_str} 也非交易日，继续查找")
                else:
                    # 超过最大尝试次数仍未找到交易日
                    logger.warning(f"[手动同步] 未能在最近{max_attempts}天内找到交易日")
                    return {
                        "status": "skipped",
                        "reason": f"最近{max_attempts}天内无交易日",
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


@celery_app.task(
    base=SentimentSyncTask,
    name="sentiment.batch_sync",
    bind=True
)
def batch_sentiment_sync_task(self, start_date: str, end_date: str):
    """
    批量同步情绪数据任务（支持日期范围）

    Args:
        start_date: 起始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        批量同步结果
    """
    try:
        logger.info(f"========== [批量同步] 开始执行情绪数据批量同步: {start_date} ~ {end_date} ==========")

        # 生成日期列表
        from datetime import datetime, timedelta
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        date_list = []
        current_dt = start_dt
        while current_dt <= end_dt:
            date_list.append(current_dt.strftime('%Y-%m-%d'))
            current_dt += timedelta(days=1)

        total_dates = len(date_list)
        logger.info(f"[批量同步] 共需同步 {total_dates} 个日期")

        # 初始化进度
        self.update_state(
            state='PROGRESS',
            meta={
                'message': f'开始批量同步 {start_date} ~ {end_date}',
                'progress': 0,
                'current': 0,
                'total': total_dates,
                'start_date': start_date,
                'end_date': end_date,
                'details': {
                    'success_count': 0,
                    'failed_count': 0,
                    'skipped_count': 0
                }
            }
        )

        # 创建服务实例
        service = MarketSentimentService()

        # 统计结果
        success_count = 0
        failed_count = 0
        skipped_count = 0
        failed_dates = []

        # 逐个同步
        for idx, date in enumerate(date_list, start=1):
            try:
                # 更新进度
                progress = int((idx / total_dates) * 100)
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'message': f'正在同步 {date} ({idx}/{total_dates})',
                        'progress': progress,
                        'current': idx,
                        'total': total_dates,
                        'start_date': start_date,
                        'end_date': end_date,
                        'current_date': date,
                        'details': {
                            'success_count': success_count,
                            'failed_count': failed_count,
                            'skipped_count': skipped_count
                        }
                    }
                )

                logger.info(f"[批量同步] 正在同步 {date} ({idx}/{total_dates})")

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
                    skipped_count += 1
                    logger.info(f"[批量同步] {date} 非交易日，跳过")
                elif result.get('success'):
                    success_count += 1
                    logger.success(f"[批量同步] {date} 同步成功")
                else:
                    failed_count += 1
                    failed_dates.append(date)
                    logger.error(f"[批量同步] {date} 同步失败: {result.get('error')}")

                # 添加延迟，避免API限流
                import time
                time.sleep(1)

            except Exception as e:
                failed_count += 1
                failed_dates.append(date)
                logger.error(f"[批量同步] {date} 同步异常: {e}")

        # 返回最终结果
        logger.success(f"========== [批量同步] 完成 ==========")
        logger.info(f"成功: {success_count}, 失败: {failed_count}, 跳过: {skipped_count}")

        return {
            "status": "success",
            "start_date": start_date,
            "end_date": end_date,
            "total": total_dates,
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "failed_dates": failed_dates
        }

    except Exception as e:
        logger.error(f"[批量同步] 任务执行异常: {e}")
        raise


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
        count = run_async_in_celery(
            service.sync_trading_calendar_batch,
            years
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
