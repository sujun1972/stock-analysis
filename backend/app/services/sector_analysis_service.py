"""板块行情分析服务

聚合 dc_index / dc_daily / moneyflow_ind_dc / limit_cpt_list 四张表，
输出市场板块层面的四个视图：

- top_gainers_5d         近5交易日板块涨幅榜
- top_capital_inflow     当日主力净流入榜
- strongest_by_limits    涨停数最多的板块榜
- capital_vs_price_divergence  量价背离板块（涨幅/资金排名错位）

数据源均为同步表，本服务只读不写。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.repositories.dc_daily_repository import DcDailyRepository
from app.repositories.dc_index_repository import DcIndexRepository
from app.repositories.limit_cpt_repository import LimitCptRepository
from app.repositories.moneyflow_ind_dc_repository import MoneyflowIndDcRepository


class SectorAnalysisService:
    """板块行情聚合服务。"""

    def __init__(self) -> None:
        self.dc_daily_repo = DcDailyRepository()
        self.dc_index_repo = DcIndexRepository()
        self.moneyflow_ind_repo = MoneyflowIndDcRepository()
        self.limit_cpt_repo = LimitCptRepository()

    async def analyze_board(self, trade_date: Optional[str] = None) -> Dict[str, Any]:
        """生成指定交易日的板块行情聚合视图。

        Args:
            trade_date: YYYY-MM-DD 或 YYYYMMDD；None 时取板块数据最新日期。
        """
        trade_date_fmt = await self._normalize_trade_date(trade_date)
        if not trade_date_fmt:
            return {
                "trade_date": None,
                "generated_at": datetime.now().isoformat(timespec='seconds'),
                "error": "无可用板块交易日期",
            }

        today = datetime.strptime(trade_date_fmt, '%Y%m%d')
        start_5d = (today - timedelta(days=14)).strftime('%Y%m%d')

        (
            top_gainers_5d,
            top_capital_inflow,
            strongest_by_limits,
            all_inflow_today,
        ) = await asyncio.gather(
            asyncio.to_thread(self._compute_top_gainers_5d, start_5d, trade_date_fmt, 10),
            asyncio.to_thread(
                self.moneyflow_ind_repo.get_top_by_net_amount,
                trade_date_fmt, None, 10,
            ),
            asyncio.to_thread(self.limit_cpt_repo.get_by_trade_date, trade_date_fmt, 10),
            asyncio.to_thread(
                self.moneyflow_ind_repo.get_by_date_range,
                start_date=trade_date_fmt, end_date=trade_date_fmt, limit=500,
            ),
        )

        divergence = self._compute_capital_vs_price_divergence(
            top_gainers_5d_all=self._compute_full_rank_by_5d_pct(start_5d, trade_date_fmt),
            inflow_today=all_inflow_today,
        )

        return {
            "trade_date": f"{trade_date_fmt[:4]}-{trade_date_fmt[4:6]}-{trade_date_fmt[6:8]}",
            "generated_at": datetime.now().isoformat(timespec='seconds'),
            "top_gainers_5d": top_gainers_5d,
            "top_capital_inflow": top_capital_inflow,
            "strongest_by_limits": strongest_by_limits,
            "capital_vs_price_divergence": divergence,
        }

    async def _normalize_trade_date(self, trade_date: Optional[str]) -> Optional[str]:
        if not trade_date:
            return await asyncio.to_thread(self.dc_daily_repo.get_latest_trade_date) \
                if hasattr(self.dc_daily_repo, 'get_latest_trade_date') \
                else await asyncio.to_thread(self.dc_index_repo.get_latest_trade_date)
        s = trade_date.replace('-', '')
        return s if len(s) == 8 and s.isdigit() else None

    def _compute_top_gainers_5d(self, start: str, end: str, top_n: int) -> List[Dict]:
        """计算 5 个交易日窗口内板块累计涨跌幅 TOP-N。

        Tushare dc_daily.pct_change 已是百分比；累计近似用算术求和（小涨幅下与复利差异 <1%）。
        """
        rows = self.dc_daily_repo.get_by_date_range(
            start_date=start, end_date=end, ts_code=None, limit=10000, offset=0,
        )
        if not rows:
            return []
        name_map = self.dc_index_repo.get_board_name_map()

        agg: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            tc = r.get('ts_code')
            if not tc:
                continue
            a = agg.setdefault(tc, {
                "ts_code": tc,
                "name": name_map.get(tc, ''),
                "cum_pct_5d": 0.0,
                "days": 0,
                "latest_close": None,
                "latest_date": '',
            })
            a["cum_pct_5d"] += float(r.get('pct_change') or 0)
            a["days"] += 1
            td = str(r.get('trade_date') or '')
            if td >= a["latest_date"]:
                a["latest_date"] = td
                a["latest_close"] = float(r.get('close') or 0)

        # 过滤无名称的条目（非常规板块），按累计涨幅降序
        ranked = sorted(
            [a for a in agg.values() if a["name"]],
            key=lambda x: x["cum_pct_5d"],
            reverse=True,
        )
        return ranked[:top_n]

    def _compute_full_rank_by_5d_pct(self, start: str, end: str) -> List[Dict]:
        """辅助：为背离分析提供全量板块 5 日涨幅排名。"""
        return self._compute_top_gainers_5d(start, end, top_n=500)

    def _compute_capital_vs_price_divergence(
        self,
        top_gainers_5d_all: List[Dict],
        inflow_today: List[Dict],
    ) -> List[Dict]:
        """识别涨幅排名与资金排名错位 >20 档的板块（按 name 连接）。"""
        if not top_gainers_5d_all or not inflow_today:
            return []

        price_rank: Dict[str, int] = {
            row["name"]: i + 1 for i, row in enumerate(top_gainers_5d_all) if row.get("name")
        }
        inflow_sorted = sorted(inflow_today, key=lambda x: x.get('net_amount') or 0, reverse=True)
        inflow_rank: Dict[str, int] = {
            row.get("name"): i + 1 for i, row in enumerate(inflow_sorted) if row.get("name")
        }

        results = []
        for name, pr in price_rank.items():
            ir = inflow_rank.get(name)
            if ir is None:
                continue
            diff = abs(pr - ir)
            if diff <= 20:
                continue
            results.append({
                "name": name,
                "price_rank_5d": pr,
                "inflow_rank_today": ir,
                "rank_diff": diff,
                "divergence": "价强资弱" if ir > pr else "资强价弱",
            })

        results.sort(key=lambda x: x["rank_diff"], reverse=True)
        return results[:10]
