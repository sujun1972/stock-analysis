"""
个股多维度数据收集服务

拆分为子模块：
- collectors.py     — 基础盘面/资金/股东/财报/风险/九转数据收集
- technical.py      — 技术指标收集 + 跨指标共振分析
- text_formatter.py — Markdown 报告格式化
- formatters.py     — 纯函数格式化工具
"""

from datetime import datetime
from typing import Dict, Any

import asyncio
from loguru import logger

from . import collectors
from .technical import get_technical_indicators
from .text_formatter import format_as_text


class StockDataCollectionService:
    """个股多维度数据收集服务"""

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------

    async def collect(self, ts_code: str, stock_name: str) -> Dict[str, Any]:
        """收集指定股票的全维度数据，返回结构化字典。"""
        pure_code = ts_code.split('.')[0] if '.' in ts_code else ts_code

        results = await asyncio.gather(
            self._get_basic_market(ts_code, pure_code),
            self._get_capital_flow(ts_code, pure_code),
            self._get_shareholder_info(ts_code),
            self._get_technical_indicators(ts_code),
            self._get_financial_reports(ts_code),
            self._get_risk_alerts(ts_code),
            self._get_nine_turn(ts_code),
            self._get_auction(ts_code),
            self._get_smart_money(ts_code),
            self._get_limit_ecology(ts_code),
            self._get_limit_history(ts_code),
            self._get_auction_baseline(ts_code),
            self._get_dividend_context(ts_code),
            self._get_analyst_consensus(ts_code),
            self._get_recent_announcements(ts_code),
            self._get_recent_news(ts_code),
            return_exceptions=True,
        )

        labels = [
            'basic', 'capital', 'shareholder', 'technical', 'financial',
            'risk', 'nine_turn', 'auction', 'smart_money',
            'limit_ecology', 'limit_history', 'auction_baseline', 'dividend',
            'analyst_consensus', 'recent_announcements', 'recent_news',
        ]
        (basic, capital, shareholder, technical, financial, risk, nine_turn,
         auction, smart_money, limit_ecology, limit_history, auction_baseline,
         dividend, analyst_consensus, recent_announcements, recent_news) = [
            self._unwrap(v, label) for v, label in zip(results, labels)
        ]

        return {
            "ts_code": ts_code,
            "stock_name": stock_name,
            "collected_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "basic_market": basic,
            "capital_flow": capital,
            "shareholder": shareholder,
            "technical": technical,
            "financial": financial,
            "risk": risk,
            "nine_turn": nine_turn,
            "auction": auction,
            "smart_money": smart_money,
            "limit_ecology": limit_ecology,
            "limit_history": limit_history,
            "auction_baseline": auction_baseline,
            "dividend": dividend,
            "analyst_consensus": analyst_consensus,
            "recent_announcements": recent_announcements,
            "recent_news": recent_news,
        }

    async def collect_and_format(self, ts_code: str, stock_name: str) -> tuple:
        """收集数据并格式化为 Markdown 结构化文本。

        Returns:
            (formatted_text, trade_date) — trade_date 为 YYYYMMDD 格式，
            来自最新交易日行情数据；无行情数据时为 None。
        """
        data = await self.collect(ts_code, stock_name)
        text = format_as_text(data)
        raw_date = data.get("basic_market", {}).get("trade_date")
        trade_date = raw_date.replace("-", "") if raw_date else None
        return text, trade_date

    @staticmethod
    def _unwrap(val: Any, label: str) -> Dict:
        if isinstance(val, Exception):
            logger.warning(f"数据收集子模块[{label}]异常: {type(val).__name__}: {val}")
            return {}
        return val

    # ------------------------------------------------------------------
    # 数据收集委托（保持方法签名不变，供 langchain_tools 调用）
    # ------------------------------------------------------------------

    async def _get_basic_market(self, ts_code: str, pure_code: str) -> Dict:
        return await collectors.get_basic_market(ts_code, pure_code)

    async def _get_capital_flow(self, ts_code: str, pure_code: str) -> Dict:
        return await collectors.get_capital_flow(ts_code, pure_code)

    async def _get_shareholder_info(self, ts_code: str) -> Dict:
        return await collectors.get_shareholder_info(ts_code)

    async def _get_technical_indicators(self, ts_code: str) -> Dict:
        return await get_technical_indicators(ts_code)

    async def _get_financial_reports(self, ts_code: str) -> Dict:
        return await collectors.get_financial_reports(ts_code)

    async def _get_smart_money(self, ts_code: str) -> Dict:
        return await collectors.get_smart_money(ts_code)

    async def _get_risk_alerts(self, ts_code: str) -> Dict:
        return await collectors.get_risk_alerts(ts_code)

    async def _get_nine_turn(self, ts_code: str) -> Dict:
        return await collectors.get_nine_turn(ts_code)

    async def _get_auction(self, ts_code: str) -> Dict:
        return await collectors.get_auction(ts_code)

    async def _get_limit_ecology(self, ts_code: str) -> Dict:
        return await collectors.get_limit_ecology(ts_code)

    async def _get_limit_history(self, ts_code: str) -> Dict:
        return await collectors.get_limit_history(ts_code)

    async def _get_auction_baseline(self, ts_code: str) -> Dict:
        return await collectors.get_auction_baseline(ts_code)

    async def _get_dividend_context(self, ts_code: str) -> Dict:
        return await collectors.get_dividend_context(ts_code)

    async def _get_analyst_consensus(self, ts_code: str) -> Dict:
        return await collectors.get_analyst_consensus(ts_code)

    async def _get_recent_announcements(self, ts_code: str, days: int = 30, limit: int = 20) -> Dict:
        """近 N 天公司公告（来源：stock_anns 表，AkShare 同步）。"""
        return await collectors.get_recent_announcements(ts_code, days=days, limit=limit)

    async def _get_recent_news(self, ts_code: str, days: int = 7, limit: int = 30) -> Dict:
        """近 N 天与该股关联的财经快讯（来源：news_flash 表，AkShare Phase 2）。"""
        return await collectors.get_recent_news(ts_code, days=days, limit=limit)
