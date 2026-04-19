"""市场情绪 AI 分析 - 数据聚合模块

从打板专题表（top_list / limit_list_d / limit_step / limit_cpt_list）及
资金面相关表（moneyflow_mkt_dc / moneyflow_hsgt / top_inst）读取当日数据。
"""

from typing import Dict, Any, Optional, List
from loguru import logger


class SentimentDataCollector:
    """打板专题数据聚合器"""

    def fetch_data(self, trade_date: str) -> Optional[Dict[str, Any]]:
        """从打板专题及资金面相关表读取数据

        Args:
            trade_date: 交易日期（YYYY-MM-DD）

        Returns:
            聚合数据字典，无打板数据返回 None。
        """
        try:
            from app.repositories.top_list_repository import TopListRepository
            from app.repositories.limit_list_repository import LimitListRepository
            from app.repositories.limit_step_repository import LimitStepRepository
            from app.repositories.limit_cpt_repository import LimitCptRepository
            from app.repositories.moneyflow_mkt_dc_repository import MoneyflowMktDcRepository
            from app.repositories.moneyflow_hsgt_repository import MoneyflowHsgtRepository
            from app.repositories.top_inst_repository import TopInstRepository

            trade_date_fmt = trade_date.replace('-', '')

            top_list_data = TopListRepository().get_by_trade_date(trade_date_fmt)
            limit_list_data = LimitListRepository().get_by_date_range(
                start_date=trade_date_fmt, end_date=trade_date_fmt, page=1, page_size=200
            )
            limit_step_data = LimitStepRepository().get_by_trade_date(trade_date_fmt)
            limit_cpt_data = LimitCptRepository().get_by_trade_date(trade_date_fmt, limit=20)
            mkt_flow = MoneyflowMktDcRepository().get_by_trade_date(trade_date_fmt)
            hsgt_flow = MoneyflowHsgtRepository().get_by_trade_date(trade_date_fmt)
            top_inst_data = TopInstRepository().get_by_trade_date(trade_date_fmt)

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
                "mkt_flow": mkt_flow,
                "hsgt_flow": hsgt_flow,
                "top_inst_data": top_inst_data,
                "top_inst_summary": self._summarize_top_inst(top_inst_data),
            }

        except Exception as e:
            logger.error(f"读取情绪数据失败: {str(e)}")
            return None

    @staticmethod
    def _summarize_top_inst(rows: List[Dict]) -> Dict[str, Any]:
        """按席位聚合龙虎榜机构明细：区分游资/机构，并按净买入绝对值排出 TOP5。"""
        if not rows:
            return {"institution_count": 0, "hot_money_count": 0, "top_seats": []}

        seat_agg: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            exalter = (r.get('exalter') or '').strip()
            if not exalter:
                continue
            is_inst = '机构专用' in exalter
            agg = seat_agg.setdefault(exalter, {
                "exalter": exalter,
                "is_institution": is_inst,
                "buy": 0.0,
                "sell": 0.0,
                "net_buy": 0.0,
                "stock_count": 0,
            })
            agg["buy"] += float(r.get('buy') or 0)
            agg["sell"] += float(r.get('sell') or 0)
            agg["net_buy"] += float(r.get('net_buy') or 0)
            agg["stock_count"] += 1

        institution_seats = [s for s in seat_agg.values() if s["is_institution"]]
        hot_money_seats = [s for s in seat_agg.values() if not s["is_institution"]]

        top_seats = sorted(seat_agg.values(), key=lambda x: abs(x["net_buy"]), reverse=True)[:5]

        return {
            "institution_count": len(institution_seats),
            "hot_money_count": len(hot_money_seats),
            "top_seats": top_seats,
        }


sentiment_data_collector = SentimentDataCollector()
