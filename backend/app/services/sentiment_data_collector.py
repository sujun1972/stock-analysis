"""市场情绪 AI 分析 - 数据聚合模块

从打板专题表（top_list / limit_list_d / limit_step / limit_cpt_list）读取当日数据。
"""

from typing import Dict, Any, Optional
from loguru import logger


class SentimentDataCollector:
    """打板专题数据聚合器"""

    def fetch_data(self, trade_date: str) -> Optional[Dict[str, Any]]:
        """从打板专题表读取数据

        Args:
            trade_date: 交易日期（YYYY-MM-DD）

        Returns:
            {
                "trade_date": "2026-03-10",
                "trade_date_fmt": "20260310",
                "top_list_data": [...],
                "limit_list_data": [...],
                "limit_step_data": [...],
                "limit_cpt_data": [...],
            }
            无数据返回 None。
        """
        try:
            from app.repositories.top_list_repository import TopListRepository
            from app.repositories.limit_list_repository import LimitListRepository
            from app.repositories.limit_step_repository import LimitStepRepository
            from app.repositories.limit_cpt_repository import LimitCptRepository

            trade_date_fmt = trade_date.replace('-', '')

            top_list_repo = TopListRepository()
            limit_list_repo = LimitListRepository()
            limit_step_repo = LimitStepRepository()
            limit_cpt_repo = LimitCptRepository()

            top_list_data = top_list_repo.get_by_trade_date(trade_date_fmt)
            limit_list_data = limit_list_repo.get_by_date_range(
                start_date=trade_date_fmt, end_date=trade_date_fmt, limit=200
            )
            limit_step_data = limit_step_repo.get_by_trade_date(trade_date_fmt)
            limit_cpt_data = limit_cpt_repo.get_by_trade_date(trade_date_fmt, limit=20)

            if not limit_list_data and not limit_step_data and not top_list_data:
                logger.warning(f"{trade_date} 打板专题数据为空，请先同步数据")
                return None

            return {
                "trade_date": trade_date,
                "trade_date_fmt": trade_date_fmt,
                "top_list_data": top_list_data,
                "limit_list_data": limit_list_data,
                "limit_step_data": limit_step_data,
                "limit_cpt_data": limit_cpt_data,
            }

        except Exception as e:
            logger.error(f"读取情绪数据失败: {str(e)}")
            return None


sentiment_data_collector = SentimentDataCollector()
