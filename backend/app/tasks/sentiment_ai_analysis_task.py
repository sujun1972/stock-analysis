"""
市场情绪AI分析定时任务

每日18:00（北京时间）执行，调用LLM生成盘后情绪分析报告。

作者: AI Strategy Team
创建日期: 2026-03-10
"""

import asyncio
from datetime import datetime
import pytz
from celery import Task
from loguru import logger

from app.celery_app import celery_app
from app.services.sentiment_ai_analysis_service import sentiment_ai_analysis_service


class SentimentAIAnalysisTask(Task):
    """情绪AI分析任务基类"""

    autoretry_for = (Exception,)
    max_retries = 2  # 最多重试2次（AI调用成本较高）
    retry_backoff = 600  # 10分钟后重试
    retry_jitter = True


@celery_app.task(
    base=SentimentAIAnalysisTask,
    name="sentiment.ai_analysis_18_00",
    bind=True
)
def daily_sentiment_ai_analysis_task(self, date: str = None, provider: str = "deepseek"):
    """
    每日18:00执行市场情绪AI分析任务

    Args:
        date: 分析日期（可选，默认为当天）
        provider: AI提供商（deepseek/gemini/openai）

    Returns:
        分析结果字典
    """
    try:
        # 获取北京时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)

        # 使用指定日期或当天
        if not date:
            date = now.strftime('%Y-%m-%d')

        logger.info(f"开始执行18:00情绪AI分析任务: {date}, AI提供商: {provider}")

        # 创建事件循环并运行异步任务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                sentiment_ai_analysis_service.generate_ai_analysis(
                    trade_date=date,
                    provider=provider
                )
            )
        finally:
            loop.close()

        # 判断结果
        if result.get('success'):
            logger.success(
                f"情绪AI分析成功 | 日期: {date} | "
                f"AI: {result.get('ai_provider')} | "
                f"Tokens: {result.get('tokens_used')} | "
                f"耗时: {result.get('generation_time')}s"
            )

            # 记录任务执行历史
            _log_task_execution(date, 'success', result)

            return {
                "status": "success",
                "date": date,
                "ai_provider": result.get('ai_provider'),
                "tokens_used": result.get('tokens_used'),
                "generation_time": result.get('generation_time')
            }
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"情绪AI分析失败: {error_msg}")

            # 记录失败
            _log_task_execution(date, 'failed', result)

            # 如果是数据缺失，不重试
            if "无情绪数据" in error_msg:
                logger.warning(f"{date} 情绪数据缺失，跳过AI分析")
                return {"status": "skipped", "reason": error_msg}

            # 其他错误，抛出异常触发重试
            raise Exception(error_msg)

    except Exception as e:
        logger.error(f"任务执行异常: {str(e)}", exc_info=True)
        _log_task_execution(date or 'unknown', 'error', {'error': str(e)})
        raise self.retry(exc=e)


def _log_task_execution(date: str, status: str, result: dict):
    """
    记录任务执行历史到数据库

    Args:
        date: 执行日期
        status: 执行状态（success/failed/error）
        result: 结果摘要
    """
    try:
        import json
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

        # 查找情绪AI分析任务ID
        cursor.execute("""
            SELECT id FROM scheduled_tasks
            WHERE task_name = 'sentiment.ai_analysis_18_00'
            LIMIT 1
        """)

        task_row = cursor.fetchone()
        if not task_row:
            logger.warning("未找到情绪AI分析任务记录")
            cursor.close()
            conn.close()
            return

        task_id = task_row[0]

        # 记录执行历史
        result_summary = json.dumps(result, ensure_ascii=False)[:500]  # 截断到500字节

        cursor.execute("""
            INSERT INTO task_execution_history (
                task_id, executed_at, status, result_summary
            )
            VALUES (%s, NOW(), %s, %s)
        """, (task_id, status, result_summary))

        conn.commit()
        cursor.close()
        pool_manager.release_connection(conn)

        logger.info(f"任务执行历史已记录: {date} - {status}")

    except Exception as e:
        logger.error(f"记录任务执行历史失败: {str(e)}")


# 手动触发任务的辅助函数
def trigger_ai_analysis_manually(date: str = None, provider: str = "deepseek"):
    """
    手动触发AI分析任务（用于测试或补数据）

    Args:
        date: 分析日期（默认今天）
        provider: AI提供商

    Returns:
        Celery AsyncResult对象
    """
    logger.info(f"手动触发AI分析任务: {date}, 提供商: {provider}")
    return daily_sentiment_ai_analysis_task.apply_async(
        args=[date, provider],
        countdown=0  # 立即执行
    )
