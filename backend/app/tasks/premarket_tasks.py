"""
盘前预期管理定时任务

每日早8:00自动执行:
1. 判断是否为交易日
2. 抓取隔夜外盘数据
3. 抓取盘前核心新闻
4. 生成AI碰撞分析

作者: AI Strategy Team
创建日期: 2026-03-11
"""

from celery import Task
from datetime import datetime
from loguru import logger
import os

from app.celery_app import celery_app
from src.premarket.fetcher import PremarketDataFetcher
from src.database.connection_pool_manager import ConnectionPoolManager
from app.services.premarket_analysis_service import premarket_analysis_service


class PremarketTask(Task):
    """盘前任务基类"""

    def __init__(self):
        self._pool_manager = None

    @property
    def pool_manager(self):
        if self._pool_manager is None:
            db_config = {
                'host': os.getenv('DATABASE_HOST', 'timescaledb'),
                'port': int(os.getenv('DATABASE_PORT', '5432')),
                'database': os.getenv('DATABASE_NAME', 'stock_analysis'),
                'user': os.getenv('DATABASE_USER', 'stock_user'),
                'password': os.getenv('DATABASE_PASSWORD', 'stock_password_123')
            }
            self._pool_manager = ConnectionPoolManager(db_config)
        return self._pool_manager


@celery_app.task(bind=True, base=PremarketTask, name="premarket.full_workflow_8_00")
def premarket_full_workflow_task(self):
    """
    盘前完整工作流（每日8:00）

    执行步骤:
    1. 校验交易日
    2. 同步外盘数据
    3. 同步盘前新闻
    4. 生成碰撞分析

    返回:
        {
            "success": True/False,
            "message": "执行结果消息",
            "trade_date": "2026-03-11",
            "action_command": "行动指令",
            "tokens_used": 1500,
            "generation_time": 5.2
        }
    """
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"========== 开始执行盘前工作流: {today} ==========")

        # 步骤1: 判断交易日
        fetcher = PremarketDataFetcher(self.pool_manager)
        is_trading = fetcher.is_trading_day(today)

        if not is_trading:
            logger.info(f"{today} 非交易日，跳过盘前工作流")
            return {
                "success": True,
                "message": "非交易日，已跳过",
                "trade_date": today,
                "is_trading_day": False
            }

        # 步骤2+3: 同步盘前数据（外盘 + 新闻）
        logger.info("步骤1/2: 同步盘前数据...")
        sync_result = fetcher.sync_premarket_data(today)

        if not sync_result.success:
            logger.error(f"盘前数据同步失败: {sync_result.error}")
            return {
                "success": False,
                "message": f"数据同步失败: {sync_result.error}",
                "trade_date": today
            }

        logger.success(f"盘前数据同步成功: {sync_result.synced_tables}")
        logger.info(f"外盘数据: A50变动{sync_result.details.get('overnight_data', {}).get('a50_change', 0)}%")
        logger.info(f"盘前新闻: {sync_result.details.get('news', {}).get('count', 0)}条")

        # 步骤4: 生成碰撞分析
        logger.info("步骤2/2: 生成AI碰撞分析...")

        # 异步调用转同步（在Celery任务中）
        import asyncio
        analysis_result = asyncio.run(
            premarket_analysis_service.generate_collision_analysis(
                trade_date=today,
                provider="deepseek",  # 使用默认提供商
                model=None
            )
        )

        if not analysis_result.get("success"):
            logger.error(f"碰撞分析生成失败: {analysis_result.get('error')}")
            return {
                "success": False,
                "message": f"碰撞分析失败: {analysis_result.get('error')}",
                "trade_date": today,
                "data_synced": True  # 数据已同步成功
            }

        logger.success(f"========== 盘前工作流执行成功: {today} ==========")
        logger.info(f"【行动指令】\n{analysis_result.get('action_command')}")
        logger.info(f"AI消耗: {analysis_result.get('tokens_used')} tokens, 耗时 {analysis_result.get('generation_time')}s")

        return {
            "success": True,
            "message": "盘前工作流执行成功",
            "trade_date": today,
            "is_trading_day": True,
            "action_command": analysis_result.get('action_command'),
            "ai_provider": analysis_result.get('ai_provider'),
            "tokens_used": analysis_result.get('tokens_used'),
            "generation_time": analysis_result.get('generation_time')
        }

    except Exception as e:
        logger.error(f"盘前工作流执行失败: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"执行失败: {str(e)}",
            "trade_date": today if 'today' in locals() else None
        }


@celery_app.task(name="premarket.sync_data_only")
def sync_premarket_data_task(date: str = None):
    """
    仅同步盘前数据（手动触发）

    用途: 当自动同步失败或需要补充历史数据时使用

    Args:
        date: 交易日期，None表示今天

    Returns:
        {
            "success": True/False,
            "message": "同步结果",
            "trade_date": "2026-03-11",
            "synced_tables": ["overnight_market_data", "premarket_news_flash"],
            "details": {...}
        }
    """
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"手动同步盘前数据: {date}")

        db_config = {
            'host': os.getenv('DATABASE_HOST', 'timescaledb'),
            'port': int(os.getenv('DATABASE_PORT', '5432')),
            'database': os.getenv('DATABASE_NAME', 'stock_analysis'),
            'user': os.getenv('DATABASE_USER', 'stock_user'),
            'password': os.getenv('DATABASE_PASSWORD', 'stock_password_123')
        }
        pool_manager = ConnectionPoolManager(db_config)

        fetcher = PremarketDataFetcher(pool_manager)
        result = fetcher.sync_premarket_data(date)

        return {
            "success": result.success,
            "message": "同步成功" if result.success else result.error,
            "trade_date": result.trade_date,
            "is_trading_day": result.is_trading_day,
            "synced_tables": result.synced_tables,
            "details": result.details
        }

    except Exception as e:
        logger.error(f"同步盘前数据失败: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


@celery_app.task(name="premarket.generate_analysis_only")
def generate_analysis_task(date: str = None, provider: str = "deepseek"):
    """
    仅生成碰撞分析（手动触发）

    用途: 当自动分析失败或需要重新生成分析时使用

    Args:
        date: 交易日期，None表示今天
        provider: AI提供商（deepseek/gemini/openai）

    Returns:
        {
            "success": True/False,
            "trade_date": "2026-03-11",
            "analysis_result": {...},
            "action_command": "行动指令",
            "tokens_used": 1500,
            "generation_time": 5.2
        }
    """
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"手动生成碰撞分析: {date}, provider={provider}")

        import asyncio
        result = asyncio.run(
            premarket_analysis_service.generate_collision_analysis(
                trade_date=date,
                provider=provider,
                model=None
            )
        )

        return result

    except Exception as e:
        logger.error(f"生成碰撞分析失败: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }
