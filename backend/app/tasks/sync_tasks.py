"""
数据同步 Celery 任务

包含：
- 股票列表同步
- 批量日线数据同步
- 新股列表同步
- 退市股票同步
- 概念数据同步
"""

import asyncio
from datetime import datetime
from typing import Optional
from celery import Task
from loguru import logger

from app.celery_app import celery_app
from app.services.stock_list_sync_service import StockListSyncService
from app.core.redis_lock import redis_lock


class SyncTask(Task):
    """同步任务基类"""
    autoretry_for = (Exception,)
    max_retries = 2
    retry_backoff = 180  # 3分钟后重试
    retry_jitter = True


class _DummyContext:
    """占位上下文管理器"""
    def __enter__(self):
        return True
    def __exit__(self, *args):
        pass


@celery_app.task(
    base=SyncTask,
    name="sync.stock_list",
    bind=True
)
def sync_stock_list_task(self: Task):
    """
    异步同步股票列表

    Returns:
        {
            "status": "success|locked",
            "total": 总数,
            "success": 成功数,
            "failed": 失败数
        }
    """
    try:
        logger.info("========== [Celery] 开始执行股票列表同步任务 ==========")

        # 使用分布式锁防止并发执行
        lock_key = "sync:stock_list"

        with redis_lock.acquire(lock_key, timeout=600, blocking=False) if redis_lock else _DummyContext() as acquired:
            if not acquired and redis_lock:
                logger.warning("⚠️  股票列表同步任务已在执行中，跳过本次执行")
                return {
                    "status": "locked",
                    "message": "已有同步任务正在进行"
                }

            # 创建服务实例
            service = StockListSyncService()

            # 运行异步任务
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(service.sync_stock_list())
            finally:
                loop.close()

        logger.info(f"[Celery] 股票列表同步完成: {result}")

        return {
            "status": "success",
            "total": result.get("total", 0),
            "success": result.get("success", 0),
            "failed": result.get("failed", 0),
            "data_source": result.get("data_source", "")
        }

    except Exception as e:
        logger.error(f"[Celery] 股票列表同步失败: {str(e)}", exc_info=True)
        raise


@celery_app.task(
    base=SyncTask,
    name="sync.daily_batch",
    bind=True
)
def sync_daily_batch_task(self: Task, start_date: str = None, end_date: str = None, years: int = None):
    """
    异步批量同步日线数据

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        years: 或者指定年数（向前推算）

    Returns:
        {
            "status": "success|locked",
            "date_range": "日期范围",
            "success": 成功数,
            "failed": 失败数,
            "skipped": 跳过数,
            "total": 总数
        }
    """
    try:
        logger.info(f"========== [Celery] 开始执行日线数据批量同步任务 ==========")
        logger.info(f"参数: start_date={start_date}, end_date={end_date}, years={years}")

        # 使用分布式锁防止并发执行
        lock_key = "sync:daily_batch"

        with redis_lock.acquire(lock_key, timeout=3600, blocking=False) if redis_lock else _DummyContext() as acquired:
            if not acquired and redis_lock:
                logger.warning("⚠️  日线数据批量同步任务已在执行中，跳过本次执行")
                return {
                    "status": "locked",
                    "message": "已有同步任务正在进行"
                }

            # 导入服务（延迟导入避免循环依赖）
            from app.services.data_service import DataDownloadService
            from app.services.config_service import ConfigService

            # 创建服务实例
            data_service = DataDownloadService()
            config_service = ConfigService()

            # 获取数据源配置
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                config = loop.run_until_complete(config_service.get_data_source_config())

                # 获取所有正常股票列表（使用中文状态值）
                stock_list = data_service.db.get_stock_list(status='正常')

                if stock_list.empty:
                    logger.warning("没有可同步的股票（stock_list 为空）")
                    return {
                        "status": "success",
                        "date_range": f"{start_date} ~ {end_date}" if start_date else f"最近{years}年",
                        "success": 0,
                        "failed": 0,
                        "skipped": 0,
                        "total": 0,
                        "message": "股票列表为空，请先同步股票列表"
                    }

                codes = stock_list['code'].tolist()
                total = len(codes)
                success_count = 0
                failed_count = 0
                skipped_count = 0

                logger.info(f"共需同步 {total} 只股票")

                # 更新任务进度
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': 0,
                        'total': total,
                        'percent': 0,
                        'status': '准备中...'
                    }
                )

                # 逐个同步股票
                for i, code in enumerate(codes):
                    try:
                        # 计算年数（如果提供了日期范围，转换为年数）
                        if years:
                            sync_years = years
                        else:
                            # 简单估算：从start_date到end_date的天数除以365
                            from datetime import datetime
                            start = datetime.strptime(start_date, '%Y-%m-%d')
                            end = datetime.strptime(end_date, '%Y-%m-%d')
                            days = (end - start).days
                            sync_years = max(1, int(days / 365) + 1)

                        # 异步调用 download_single_stock
                        result = loop.run_until_complete(
                            data_service.download_single_stock(code, years=sync_years)
                        )

                        if result is not None:
                            success_count += 1
                        else:
                            skipped_count += 1

                    except Exception as e:
                        logger.error(f"同步 {code} 失败: {str(e)}")
                        failed_count += 1

                    # 每10只股票更新一次进度
                    if (i + 1) % 10 == 0 or (i + 1) == total:
                        percent = int((i + 1) / total * 100)
                        self.update_state(
                            state='PROGRESS',
                            meta={
                                'current': i + 1,
                                'total': total,
                                'percent': percent,
                                'success': success_count,
                                'failed': failed_count,
                                'status': f'同步中... ({i + 1}/{total})'
                            }
                        )
                        logger.info(f"进度: {i + 1}/{total} ({percent}%) - 成功: {success_count}, 失败: {failed_count}")

            finally:
                loop.close()

        date_range_str = f"{start_date} ~ {end_date}" if start_date else f"最近{years}年"
        logger.info(f"[Celery] 日线数据批量同步完成: 成功={success_count}, 失败={failed_count}, 总计={total}")

        return {
            "status": "success",
            "date_range": date_range_str,
            "success": success_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "total": total
        }

    except Exception as e:
        logger.error(f"[Celery] 日线数据批量同步失败: {str(e)}", exc_info=True)
        raise


@celery_app.task(
    base=SyncTask,
    name="sync.new_stocks",
    bind=True
)
def sync_new_stocks_task(self: Task, days: int = 30):
    """
    异步同步新股列表

    Args:
        days: 最近多少天的新股

    Returns:
        同步结果
    """
    try:
        logger.info(f"========== [Celery] 开始执行新股列表同步任务 (最近{days}天) ==========")

        # 使用分布式锁
        lock_key = "sync:new_stocks"

        with redis_lock.acquire(lock_key, timeout=300, blocking=False) if redis_lock else _DummyContext() as acquired:
            if not acquired and redis_lock:
                logger.warning("⚠️  新股列表同步任务已在执行中，跳过本次执行")
                return {
                    "status": "locked",
                    "message": "已有同步任务正在进行"
                }

            service = StockListSyncService()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(service.sync_new_stocks(days=days))
            finally:
                loop.close()

        logger.info(f"[Celery] 新股列表同步完成: {result}")

        return {
            "status": "success",
            "total": result.get("total", 0),
            "days": days
        }

    except Exception as e:
        logger.error(f"[Celery] 新股列表同步失败: {str(e)}", exc_info=True)
        raise


@celery_app.task(
    base=SyncTask,
    name="sync.delisted_stocks",
    bind=True
)
def sync_delisted_stocks_task(self: Task):
    """
    异步同步退市股票列表

    Returns:
        同步结果
    """
    try:
        logger.info("========== [Celery] 开始执行退市股票列表同步任务 ==========")

        # 使用分布式锁
        lock_key = "sync:delisted_stocks"

        with redis_lock.acquire(lock_key, timeout=300, blocking=False) if redis_lock else _DummyContext() as acquired:
            if not acquired and redis_lock:
                logger.warning("⚠️  退市股票列表同步任务已在执行中，跳过本次执行")
                return {
                    "status": "locked",
                    "message": "已有同步任务正在进行"
                }

            service = StockListSyncService()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(service.sync_delisted_stocks())
            finally:
                loop.close()

        logger.info(f"[Celery] 退市股票列表同步完成: {result}")

        return {
            "status": "success",
            "total": result.get("total", 0)
        }

    except Exception as e:
        logger.error(f"[Celery] 退市股票列表同步失败: {str(e)}", exc_info=True)
        raise


@celery_app.task(
    base=SyncTask,
    name="sync.concept",
    bind=True
)
def sync_concept_task(self: Task, source: Optional[str] = None):
    """
    异步同步概念数据

    Args:
        source: 数据源（None=使用配置，em=东方财富，tushare=Tushare）

    Returns:
        {
            "status": "success|locked",
            "concepts_count": 概念数量,
            "relationships_count": 股票关系数量,
            "data_source": 数据源
        }
    """
    try:
        logger.info("========== [Celery] 开始执行概念数据同步任务 ==========")

        # 使用分布式锁防止并发执行
        lock_key = "sync:concept"

        with redis_lock.acquire(lock_key, timeout=1800, blocking=False) if redis_lock else _DummyContext() as acquired:
            if not acquired and redis_lock:
                logger.warning("⚠️  概念数据同步任务已在执行中，跳过本次执行")
                return {
                    "status": "locked",
                    "message": "已有同步任务正在进行"
                }

            # 创建服务实例
            from app.services.concept_sync_service import ConceptSyncService
            service = ConceptSyncService()

            # 运行异步任务
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    service.sync_concepts(source=source, task_id=self.request.id)
                )
            finally:
                loop.close()

        logger.info(f"[Celery] 概念数据同步完成: {result}")

        return {
            "status": "success",
            "concepts_count": result.get("concepts_count", 0),
            "relationships_count": result.get("relationships_count", 0),
            "data_source": result.get("data_source", "")
        }

    except Exception as e:
        logger.error(f"[Celery] 概念数据同步失败: {str(e)}", exc_info=True)
        raise
