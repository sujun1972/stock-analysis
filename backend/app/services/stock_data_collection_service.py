"""
个股多维度数据收集服务

从本地数据库收集股票分析所需的全维度数据，包括：
- 基础盘面：收盘价、涨跌幅、成交额、换手率、PE-TTM、行业位置、筹码获利比
- 资金流向：主力净流入(1/5/10日)、北向资金持股、股东人数、大股东减持、解禁预告
- 技术指标：MA5/10/20/60/120、RSI7/14/21、MACD(12,26,9)、量价异动
- 神奇九转：上涨/下跌连续计数、见顶/见底信号（来源 stk_nineturn 表）
- 财报公告：披露日期、风险警示、质押冻结

数据库表格式说明：
  - stock_daily.code 存 ts_code 格式（000002.SZ），日期列为 DATE 类型（YYYY-MM-DD）
  - stock_basic.code 存纯6位代码（000002），ts_code 存完整格式
  - moneyflow_stock_dc.net_amount 单位为万元
  - stk_holdernumber 同一季报可能有多条记录（end_date 日期不同），按 YYYYMM 去重
"""

import asyncio
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import pandas as pd
from loguru import logger


class StockDataCollectionService:
    """个股多维度数据收集服务"""

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------

    async def collect(self, ts_code: str, stock_name: str) -> Dict[str, Any]:
        """
        收集指定股票的全维度数据。

        Returns:
            结构化数据字典，供 AI 提示词填充使用。
        """
        # stock_basic 用纯6位代码，其余表用 ts_code 格式
        pure_code = ts_code.split('.')[0] if '.' in ts_code else ts_code

        results = await asyncio.gather(
            self._get_basic_market(ts_code, pure_code),
            self._get_capital_flow(ts_code, pure_code),
            self._get_shareholder_info(ts_code),
            self._get_technical_indicators(ts_code),
            self._get_financial_reports(ts_code),
            self._get_risk_alerts(ts_code),
            self._get_nine_turn(ts_code),
            return_exceptions=True,
        )

        labels = ['basic', 'capital', 'shareholder', 'technical', 'financial', 'risk', 'nine_turn']
        basic, capital, shareholder, technical, financial, risk, nine_turn = [
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
        }

    async def collect_and_format(self, ts_code: str, stock_name: str) -> tuple:
        """收集数据并格式化为 Markdown 结构化文本。

        Returns:
            (formatted_text, trade_date) — trade_date 为 YYYYMMDD 格式，
            来自最新交易日行情数据；无行情数据时为 None。
        """
        data = await self.collect(ts_code, stock_name)
        text = self._format_as_text(data)
        # basic_market.trade_date 格式为 YYYY-MM-DD，转为 YYYYMMDD
        raw_date = data.get("basic_market", {}).get("trade_date")
        trade_date = raw_date.replace("-", "") if raw_date else None
        return text, trade_date

    @staticmethod
    def _unwrap(val: Any, label: str) -> Dict:
        """将 asyncio.gather return_exceptions 的结果解包为安全字典。"""
        if isinstance(val, Exception):
            logger.warning(f"数据收集子模块[{label}]异常: {type(val).__name__}: {val}")
            return {}
        return val

    # ------------------------------------------------------------------
    # 一、基础盘面与行业位置
    # ------------------------------------------------------------------

    async def _get_basic_market(self, ts_code: str, pure_code: str) -> Dict:
        from app.repositories.stock_daily_repository import StockDailyRepository
        from app.repositories.daily_basic_repository import DailyBasicRepository
        from app.repositories.stock_basic_repository import StockBasicRepository
        from app.repositories.cyq_perf_repository import CyqPerfRepository

        daily_repo = StockDailyRepository()
        basic_repo = DailyBasicRepository()
        stock_repo = StockBasicRepository()
        cyq_repo = CyqPerfRepository()

        today = datetime.now()
        # stock_daily.date 是 DATE 类型，Repository 接受 YYYY-MM-DD
        start_dash = (today - timedelta(days=14)).strftime('%Y-%m-%d')
        end_dash = today.strftime('%Y-%m-%d')
        # daily_basic/cyq_perf 日期字段接受 YYYYMMDD
        start_yyyymmdd = (today - timedelta(days=14)).strftime('%Y%m%d')
        end_yyyymmdd = today.strftime('%Y%m%d')

        daily_df, basic_data, stock_info, cyq_data = await asyncio.gather(
            asyncio.to_thread(daily_repo.get_by_code_and_date_range, ts_code, start_dash, end_dash),
            asyncio.to_thread(basic_repo.get_by_code_and_date_range, ts_code, start_yyyymmdd, end_yyyymmdd, 5),
            asyncio.to_thread(stock_repo.get_by_code, pure_code),
            asyncio.to_thread(cyq_repo.get_by_date_range, start_yyyymmdd, end_yyyymmdd, ts_code, 1, 1),
        )

        result: Dict[str, Any] = {}

        if daily_df is not None and not daily_df.empty:
            latest = daily_df.iloc[-1]
            result['close'] = self._safe_float(latest.get('close'))
            result['pct_change'] = self._safe_float(latest.get('pct_change'))
            result['volume'] = self._safe_float(latest.get('volume'))
            result['amount'] = self._safe_float(latest.get('amount'))
            result['trade_date'] = str(daily_df.index[-1])[:10]
            result['recent_5d'] = [
                {
                    'date': str(idx)[:10],
                    'close': self._safe_float(row.get('close')),
                    'pct_change': self._safe_float(row.get('pct_change')),
                    'volume': self._safe_float(row.get('volume')),
                }
                for idx, row in daily_df.tail(5).iterrows()
            ]

        if basic_data:
            b = basic_data[0]
            result['pe_ttm'] = self._safe_float(b.get('pe_ttm'))
            result['pb'] = self._safe_float(b.get('pb'))
            result['turnover_rate'] = self._safe_float(b.get('turnover_rate'))
            result['total_mv'] = self._safe_float(b.get('total_mv'))
            result['circ_mv'] = self._safe_float(b.get('circ_mv'))

        if stock_info:
            result['industry'] = stock_info.get('industry') or ''
            result['area'] = stock_info.get('area') or ''

        # 东财行业板块及近5交易日涨跌幅
        industry_bk = await self._get_industry_board(ts_code)
        if industry_bk:
            result['industry_board_name'] = industry_bk.get('name', '')
            result['industry_5d'] = await self._get_board_pct_5d(industry_bk['ts_code'])

        if cyq_data:
            c = cyq_data[0]
            result['chip'] = {
                'winner_rate': self._safe_float(c.get('winner_rate')),
                'cost_50pct': self._safe_float(c.get('cost_50pct')),
                'cost_15pct': self._safe_float(c.get('cost_15pct')),
                'cost_85pct': self._safe_float(c.get('cost_85pct')),
                'weight_avg': self._safe_float(c.get('weight_avg')),
            }

        return result

    async def _get_industry_board(self, ts_code: str) -> Optional[Dict]:
        """通过 dc_member JOIN dc_index 查找股票所属行业板块（idx_type='行业板块'）。"""
        try:
            from app.repositories.dc_member_repository import DcMemberRepository
            return await asyncio.to_thread(
                DcMemberRepository().get_industry_board_by_con_code, ts_code
            )
        except Exception as e:
            logger.warning(f"查询行业板块失败: {e}")
            return None

    async def _get_board_pct_5d(self, board_ts_code: str) -> list:
        """从 dc_daily 获取板块近5个交易日涨跌幅。"""
        try:
            from app.repositories.dc_daily_repository import DcDailyRepository
            today = datetime.now()
            start = (today - timedelta(days=14)).strftime('%Y%m%d')
            end = today.strftime('%Y%m%d')
            data = await asyncio.to_thread(
                DcDailyRepository().get_by_date_range, start, end, board_ts_code, 5
            )
            return [
                {
                    'trade_date': str(r.get('trade_date', ''))[:8],
                    'pct_change': self._safe_float(r.get('pct_change')),
                }
                for r in (data or [])
            ]
        except Exception as e:
            logger.warning(f"查询板块近5日涨跌幅失败: {e}")
            return []

    # ------------------------------------------------------------------
    # 二、资金流向
    # ------------------------------------------------------------------

    async def _get_capital_flow(self, ts_code: str, pure_code: str) -> Dict:
        from app.repositories.moneyflow_stock_dc_repository import MoneyflowStockDcRepository
        from app.repositories.hk_hold_repository import HkHoldRepository

        today = datetime.now()
        start_10d = (today - timedelta(days=20)).strftime('%Y%m%d')
        end_today = today.strftime('%Y%m%d')

        # hk_hold.code 是港交所原始代码（如 90000），不是 A 股代码；用 ts_code 查询
        flow_data, hk_data = await asyncio.gather(
            asyncio.to_thread(MoneyflowStockDcRepository().get_by_date_range, start_10d, end_today, ts_code, 10),
            asyncio.to_thread(HkHoldRepository().get_paged, None, ts_code, None, None, 'trade_date', 'desc', 1, 10),
        )

        result: Dict[str, Any] = {}

        if flow_data:
            # net_amount 单位为万元
            net_amounts = [self._safe_float(r.get('net_amount')) or 0 for r in flow_data]
            result['net_1d'] = net_amounts[0] if net_amounts else None
            result['net_5d'] = sum(net_amounts[:5])
            result['net_10d'] = sum(net_amounts[:10])
            result['flow_detail'] = [
                {
                    'trade_date': str(r.get('trade_date', ''))[:8],
                    'net_amount': self._safe_float(r.get('net_amount')) or 0,
                    'pct_change': self._safe_float(r.get('pct_change')) or 0,
                }
                for r in flow_data[:5]
            ]

        if hk_data:
            latest_hk = hk_data[0]
            result['hk_hold'] = {
                'trade_date': str(latest_hk.get('trade_date', ''))[:10],
                'vol': latest_hk.get('vol'),
                'ratio': self._safe_float(latest_hk.get('ratio')),
            }
            if len(hk_data) > 1:
                prev_vol = self._safe_float(hk_data[-1].get('vol')) or 0
                curr_vol = self._safe_float(latest_hk.get('vol')) or 0
                result['hk_hold']['prev_vol'] = prev_vol
                result['hk_hold']['vol_change_pct'] = (
                    round((curr_vol - prev_vol) / prev_vol * 100, 2) if prev_vol else None
                )

        return result

    # ------------------------------------------------------------------
    # 股东信息
    # ------------------------------------------------------------------

    async def _get_shareholder_info(self, ts_code: str) -> Dict:
        from app.repositories.stk_holdernumber_repository import StkHolderNumberRepository
        from app.repositories.stk_holdertrade_repository import StkHoldertradeRepository
        from app.repositories.share_float_repository import ShareFloatRepository

        today = datetime.now()
        three_months_ago = (today - timedelta(days=90)).strftime('%Y%m%d')
        one_month_later = (today + timedelta(days=30)).strftime('%Y%m%d')
        today_str = today.strftime('%Y%m%d')

        holder_nums, reductions, floats = await asyncio.gather(
            asyncio.to_thread(StkHolderNumberRepository().get_latest_by_code, ts_code, 5),
            asyncio.to_thread(
                StkHoldertradeRepository().get_by_date_range,
                three_months_ago, today_str, ts_code, None, 'DE', 20
            ),
            # share_float.get_by_date_range 签名: (start, end, ts_code, ann_date, float_date, limit, offset)
            asyncio.to_thread(
                ShareFloatRepository().get_by_date_range, today_str, one_month_later, ts_code, None, None, 20
            ),
        )

        result: Dict[str, Any] = {}

        if holder_nums:
            # stk_holdernumber 同一季报可能有多条（end_date 精确日期不同），按 YYYYMM 取最先出现的一条
            seen: Dict[str, Any] = {}
            for r in holder_nums:
                quarter_key = str(r.get('end_date', ''))[:6]  # YYYYMM
                if quarter_key not in seen:
                    seen[quarter_key] = r
            deduped = list(seen.values())[:4]
            nums_list = [
                {
                    'ann_date': str(r.get('ann_date', '')),
                    'end_date': str(r.get('end_date', '')),
                    'holder_num': int(r.get('holder_num') or 0),
                }
                for r in deduped
            ]
            for i in range(len(nums_list) - 1):
                curr = nums_list[i]['holder_num']
                prev = nums_list[i + 1]['holder_num']
                nums_list[i]['qoq_pct'] = round((curr - prev) / prev * 100, 2) if prev else None
            result['holder_nums'] = nums_list

        if reductions:
            result['reductions'] = [
                {
                    'ann_date': str(r.get('ann_date', '')),
                    'holder_name': r.get('holder_name', ''),
                    'change_vol': r.get('change_vol'),
                    'change_ratio': r.get('change_ratio'),
                    'avg_price': r.get('avg_price'),
                    'begin_date': str(r.get('begin_date', '')),
                    'close_date': str(r.get('close_date', '')),
                }
                for r in reductions
            ]

        if floats:
            result['upcoming_floats'] = [
                {
                    'float_date': str(r.get('float_date', '')),
                    'float_share': r.get('float_share'),
                    'float_ratio': r.get('float_ratio'),
                    'share_type': r.get('share_type', ''),
                }
                for r in floats
            ]

        return result

    # ------------------------------------------------------------------
    # 三、技术指标（基于 stock_daily 计算）
    # ------------------------------------------------------------------

    async def _get_technical_indicators(self, ts_code: str) -> Dict:
        from app.repositories.stock_daily_repository import StockDailyRepository

        today = datetime.now()
        # 取约150个交易日（~210日历天），满足 MA120 计算需要
        start_dash = (today - timedelta(days=210)).strftime('%Y-%m-%d')
        end_dash = today.strftime('%Y-%m-%d')

        df = await asyncio.to_thread(
            StockDailyRepository().get_by_code_and_date_range, ts_code, start_dash, end_dash
        )

        if df is None or df.empty or len(df) < 5:
            return {}

        close = df['close'].astype(float)
        volume = df['volume'].astype(float)
        result: Dict[str, Any] = {}

        # MA 均线
        mas = {}
        for n in [5, 10, 20, 60, 120]:
            if len(close) >= n:
                val = close.rolling(n).mean().iloc[-1]
                mas[f'ma{n}'] = round(float(val), 3) if not self._is_nan(val) else None
            else:
                mas[f'ma{n}'] = None
        result['ma'] = mas

        # RSI
        result['rsi'] = {
            f'rsi{n}': self._calc_rsi(close, n)
            for n in [7, 14, 21]
        }

        # MACD（12, 26, 9）— 需至少 26+9=35 根 K 线
        if len(close) >= 35:
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            macd_bar = (dif - dea) * 2

            def _round_last(series):
                v = series.iloc[-1]
                return round(float(v), 3) if not self._is_nan(v) else None

            result['macd'] = {
                'dif': _round_last(dif),
                'dea': _round_last(dea),
                'macd': _round_last(macd_bar),
            }
        else:
            result['macd'] = None

        # 量价异动（近5日 vs 前5日均量对比）
        if len(df) >= 10:
            recent5 = df.tail(5)
            prev_vol_mean = float(volume.iloc[-10:-5].mean())
            recent_vol_avg = float(recent5['volume'].mean())
            recent_pct_avg = abs(float(recent5['pct_change'].mean()))

            anomaly = []
            if prev_vol_mean > 0:
                if recent_vol_avg > prev_vol_mean * 1.5 and recent_pct_avg < 0.8:
                    anomaly.append('放量滞涨')
                if recent_vol_avg < prev_vol_mean * 0.6:
                    close_list = recent5['close'].tolist()
                    if len(close_list) >= 2 and close_list[-1] < close_list[0]:
                        anomaly.append('缩量回调')
            result['anomaly'] = anomaly if anomaly else ['无明显量价异动']

            result['recent_5d_vol'] = [
                {
                    'date': str(idx)[:10],
                    'volume': float(row.get('volume', 0) or 0),
                    'pct_change': float(row.get('pct_change', 0) or 0),
                }
                for idx, row in recent5.iterrows()
            ]

        return result

    @staticmethod
    def _calc_rsi(close: pd.Series, period: int) -> Optional[float]:
        if len(close) < period + 1:
            return None
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        last_loss = float(loss.iloc[-1]) if not StockDataCollectionService._is_nan(loss.iloc[-1]) else 0
        last_gain = float(gain.iloc[-1]) if not StockDataCollectionService._is_nan(gain.iloc[-1]) else 0
        if last_loss == 0:
            return 100.0
        return round(100 - 100 / (1 + last_gain / last_loss), 2)

    # ------------------------------------------------------------------
    # 神奇九转指标（基于 stk_nineturn 表）
    # ------------------------------------------------------------------

    async def _get_nine_turn(self, ts_code: str) -> Dict:
        from app.repositories.stk_nineturn_repository import StkNineturnRepository

        today = datetime.now()
        start_dash = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        end_dash = today.strftime('%Y-%m-%d')

        rows = await asyncio.to_thread(
            StkNineturnRepository().get_by_date_range,
            start_date=start_dash,
            end_date=end_dash,
            ts_code=ts_code,
            sort_by='trade_date',
            sort_order='desc',
            limit=10,
        )

        if not rows:
            return {}

        result: Dict[str, Any] = {}

        # 最新一条的计数
        latest = rows[0]
        result['latest_date'] = latest.get('trade_date', '')[:10]
        result['up_count'] = latest.get('up_count')
        result['down_count'] = latest.get('down_count')
        result['nine_up_turn'] = latest.get('nine_up_turn')
        result['nine_down_turn'] = latest.get('nine_down_turn')

        # 近期出现的信号（+9 或 -9）
        signals = [
            r for r in rows
            if r.get('nine_up_turn') == '+9' or r.get('nine_down_turn') == '-9'
        ]
        result['recent_signals'] = [
            {
                'date': r.get('trade_date', '')[:10],
                'type': '九转见顶' if r.get('nine_up_turn') == '+9' else '九转见底',
            }
            for r in signals
        ]

        return result

    # ------------------------------------------------------------------
    # 四、财报与敏感公告
    # ------------------------------------------------------------------

    async def _get_financial_reports(self, ts_code: str) -> Dict:
        from app.repositories.disclosure_date_repository import DisclosureDateRepository

        # get_by_ts_code 只接受 (ts_code, limit)，无日期范围参数
        disclosures = await asyncio.to_thread(
            DisclosureDateRepository().get_by_ts_code, ts_code, 8
        )

        result: Dict[str, Any] = {}
        if disclosures:
            cutoff = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            filtered = [r for r in disclosures if str(r.get('end_date', '')) >= cutoff][:5]
            result['disclosures'] = [
                {
                    'end_date': str(r.get('end_date', '')),
                    'pre_date': str(r.get('pre_date', '')),
                    'actual_date': str(r.get('actual_date', '') or ''),
                    'modify_date': str(r.get('modify_date', '') or ''),
                }
                for r in filtered
            ]

        return result

    # ------------------------------------------------------------------
    # 风险警示
    # ------------------------------------------------------------------

    async def _get_risk_alerts(self, ts_code: str) -> Dict:
        from app.repositories.stk_alert_repository import StkAlertRepository
        from app.repositories.pledge_stat_repository import PledgeStatRepository

        alerts, pledge_data = await asyncio.gather(
            asyncio.to_thread(StkAlertRepository().get_by_stock, ts_code),
            asyncio.to_thread(PledgeStatRepository().get_by_stock, ts_code),
        )

        result: Dict[str, Any] = {}

        if alerts:
            result['alerts'] = [
                {
                    'start_date': str(r.get('start_date', '')),
                    'end_date': str(r.get('end_date', '')),
                    'type': r.get('type', ''),
                }
                for r in alerts[:5]
            ]

        if pledge_data:
            p = pledge_data[0]
            result['pledge'] = {
                'end_date': str(p.get('end_date', '')),
                'pledge_count': p.get('pledge_count'),
                'pledge_ratio': self._safe_float(p.get('pledge_ratio')),
                'unrest_pledge': self._safe_float(p.get('unrest_pledge')),
            }

        return result

    # ------------------------------------------------------------------
    # 格式化输出
    # ------------------------------------------------------------------

    def _format_as_text(self, data: Dict) -> str:
        lines = []
        lines.append(f"# 个股数据收集报告：{data.get('stock_name', '')}（{data.get('ts_code', '')}）")
        lines.append(f"数据收集时间：{data.get('collected_at', '')}")
        lines.append("")

        # 一、基础盘面
        basic = data.get('basic_market', {})
        lines.append("## 一、基础盘面与行业位置")
        lines.append(f"- 交易日期：{basic.get('trade_date', 'N/A')}")
        lines.append(f"- 收盘价：{self._fmt(basic.get('close'))} 元")
        lines.append(f"- 涨跌幅：{self._fmt(basic.get('pct_change'))} %")
        lines.append(f"- 成交额：{self._fmt_amount(basic.get('amount'))}")
        lines.append(f"- 换手率：{self._fmt(basic.get('turnover_rate'))} %")
        lines.append(f"- PE-TTM：{self._fmt_pe(basic.get('pe_ttm'))}")
        lines.append(f"- PB：{self._fmt(basic.get('pb'))}")
        lines.append(f"- 总市值：{self._fmt_wan(basic.get('total_mv'))}")
        lines.append(f"- 所属行业（Tushare）：{basic.get('industry') or 'N/A'} / 地区：{basic.get('area') or 'N/A'}")

        board_name = basic.get('industry_board_name', '')
        ind_5d = basic.get('industry_5d', [])
        if board_name:
            lines.append(f"- 东财行业板块：{board_name}")
        if ind_5d:
            lines.append("- 行业板块近5交易日涨跌幅：")
            for r in ind_5d:
                lines.append(f"  {r.get('trade_date', '')}  {self._fmt(r.get('pct_change'))}%")
        elif board_name:
            lines.append("- 行业板块近期数据：暂无")

        chip = basic.get('chip', {})
        if chip:
            lines.append(f"- 筹码获利比（winner_rate）：{self._fmt(chip.get('winner_rate'))} %")
            lines.append(
                f"  成本分布：15%={self._fmt(chip.get('cost_15pct'))} /"
                f" 50%={self._fmt(chip.get('cost_50pct'))} /"
                f" 85%={self._fmt(chip.get('cost_85pct'))} 元"
            )
            lines.append(f"  加权平均成本：{self._fmt(chip.get('weight_avg'))} 元")
        else:
            lines.append("- 筹码数据：暂无")
        lines.append("")

        # 二、资金流向
        capital = data.get('capital_flow', {})
        lines.append("## 二、资金流向与筹码变动")
        lines.append(f"- 主力净流入 近1日：{self._fmt_flow(capital.get('net_1d'))}")
        lines.append(f"- 主力净流入 近5日：{self._fmt_flow(capital.get('net_5d'))}")
        lines.append(f"- 主力净流入 近10日：{self._fmt_flow(capital.get('net_10d'))}")

        flow_detail = capital.get('flow_detail', [])
        if flow_detail:
            lines.append("- 近5日资金流向明细：")
            for r in flow_detail:
                lines.append(
                    f"  {r.get('trade_date', '')}  净流入 {self._fmt_flow(r.get('net_amount'))}"
                    f"  涨跌 {self._fmt(r.get('pct_change'))}%"
                )

        hk = capital.get('hk_hold', {})
        if hk:
            lines.append(
                f"- 北向资金持股（{hk.get('trade_date', '')}）："
                f"{self._fmt(hk.get('vol'), 0)} 股，占流通 {self._fmt(hk.get('ratio'))}%"
            )
            if hk.get('vol_change_pct') is not None:
                lines.append(f"  较历史变动：{self._fmt(hk.get('vol_change_pct'))}%")
        else:
            lines.append("- 北向资金：本地无持股数据")
        lines.append("")

        # 股东信息
        shareholder = data.get('shareholder', {})
        lines.append("## 股东变化")
        holder_nums = shareholder.get('holder_nums', [])
        if holder_nums:
            lines.append("- 股东人数（近4季，最新在前）：")
            for r in holder_nums:
                qoq = f"  环比 {r['qoq_pct']}%" if r.get('qoq_pct') is not None else ''
                lines.append(f"  报告期 {r.get('end_date', '')}：{r.get('holder_num', 'N/A')} 户{qoq}")
        else:
            lines.append("- 股东人数：暂无数据")

        reductions = shareholder.get('reductions', [])
        if reductions:
            lines.append("- 近3个月大股东减持明细：")
            for r in reductions:
                lines.append(
                    f"  {r.get('ann_date', '')} {r.get('holder_name', '')} "
                    f"减持 {self._fmt(r.get('change_vol'), 0)} 股"
                    f"（{self._fmt(r.get('change_ratio'))}%），均价 {self._fmt(r.get('avg_price'))} 元"
                )
        else:
            lines.append("- 近3个月：无大股东减持公告")

        upcoming = shareholder.get('upcoming_floats', [])
        if upcoming:
            lines.append("- 未来1个月解禁预告：")
            for r in upcoming:
                lines.append(
                    f"  {r.get('float_date', '')} 解禁 {self._fmt(r.get('float_share'), 0)} 万股"
                    f"（{r.get('share_type', '')}），占比 {self._fmt(r.get('float_ratio'))}%"
                )
        else:
            lines.append("- 未来1个月：无解禁计划")
        lines.append("")

        # 三、技术指标
        technical = data.get('technical', {})
        lines.append("## 三、技术指标详情")
        ma = technical.get('ma', {})
        if ma:
            lines.append(
                f"- 均线：MA5={self._fmt(ma.get('ma5'))}"
                f"  MA10={self._fmt(ma.get('ma10'))}"
                f"  MA20={self._fmt(ma.get('ma20'))}"
                f"  MA60={self._fmt(ma.get('ma60'))}"
                f"  MA120={self._fmt(ma.get('ma120'))}"
            )
        else:
            lines.append("- 均线：暂无数据")

        rsi = technical.get('rsi', {})
        if rsi:
            lines.append(
                f"- RSI：RSI7={self._fmt(rsi.get('rsi7'))}"
                f"  RSI14={self._fmt(rsi.get('rsi14'))}"
                f"  RSI21={self._fmt(rsi.get('rsi21'))}"
            )

        macd = technical.get('macd')
        if macd:
            lines.append(
                f"- MACD：DIF={self._fmt(macd.get('dif'), 3)}"
                f"  DEA={self._fmt(macd.get('dea'), 3)}"
                f"  MACD柱={self._fmt(macd.get('macd'), 3)}"
            )

        anomaly = technical.get('anomaly', [])
        if anomaly:
            lines.append(f"- 量价异动：{'、'.join(anomaly)}")

        vol_5d = technical.get('recent_5d_vol', [])
        if vol_5d:
            lines.append("- 近5日量价：")
            for r in vol_5d:
                lines.append(
                    f"  {r.get('date', '')}  量 {self._fmt(r.get('volume'), 0)} 股"
                    f"  涨跌 {self._fmt(r.get('pct_change'))}%"
                )

        # 神奇九转指标
        nine_turn = data.get('nine_turn', {})
        if nine_turn:
            lines.append(f"- 神奇九转（{nine_turn.get('latest_date', '')}）：")
            up_c = nine_turn.get('up_count')
            down_c = nine_turn.get('down_count')
            up_signal = nine_turn.get('nine_up_turn')
            down_signal = nine_turn.get('nine_down_turn')
            parts = []
            if up_c is not None and up_c > 0:
                s = f"上涨计数={int(up_c)}"
                if up_signal == '+9':
                    s += "（已触发九转见顶信号）"
                parts.append(s)
            if down_c is not None and down_c > 0:
                s = f"下跌计数={int(down_c)}"
                if down_signal == '-9':
                    s += "（已触发九转见底信号）"
                parts.append(s)
            if parts:
                lines.append(f"  当前状态：{'，'.join(parts)}")
            else:
                lines.append("  当前状态：无连续计数")

            signals = nine_turn.get('recent_signals', [])
            if signals:
                lines.append("  近30日信号：")
                for s in signals:
                    lines.append(f"    {s.get('date', '')}  {s.get('type', '')}")
        else:
            lines.append("- 神奇九转：暂无数据")
        lines.append("")

        # 四、财报与公告
        financial = data.get('financial', {})
        lines.append("## 四、财报与敏感公告")
        disclosures = financial.get('disclosures', [])
        if disclosures:
            lines.append("- 财报预约披露日期：")
            for r in disclosures:
                actual = r.get('actual_date', '')
                pre = r.get('pre_date', '')
                date_str = actual if (actual and actual not in ('None', '')) else pre
                lines.append(f"  报告期 {r.get('end_date', '')}：预约披露 {date_str}")
        else:
            lines.append("- 暂无近期财报披露计划")

        risk = data.get('risk', {})
        alerts = risk.get('alerts', [])
        if alerts:
            lines.append("- 风险警示：")
            for r in alerts:
                lines.append(f"  {r.get('start_date', '')} ~ {r.get('end_date', '')}  {r.get('type', '')}")
        else:
            lines.append("- 近期无风险警示公告")

        pledge = risk.get('pledge', {})
        if pledge:
            lines.append(
                f"- 质押情况（{pledge.get('end_date', '')}）："
                f"质押笔数 {pledge.get('pledge_count', 'N/A')} 笔，"
                f"质押比例 {self._fmt(pledge.get('pledge_ratio'))}%，"
                f"未解押股份 {self._fmt(pledge.get('unrest_pledge'), 0)} 万股"
            )
        else:
            lines.append("- 暂无质押数据")

        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _is_nan(val) -> bool:
        try:
            return math.isnan(float(val))
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _safe_float(val) -> Optional[float]:
        if val is None:
            return None
        try:
            f = float(val)
            return None if math.isnan(f) or math.isinf(f) else f
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _fmt(val, decimals: int = 2) -> str:
        if val is None:
            return 'N/A'
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return 'N/A'
            return f"{f:.{decimals}f}"
        except (TypeError, ValueError):
            return str(val)

    @staticmethod
    def _fmt_pe(val) -> str:
        """PE-TTM 专用：亏损时 Tushare 返回 NaN，显示为"亏损/负值"。"""
        if val is None:
            return 'N/A'
        try:
            f = float(val)
            if math.isnan(f):
                return '亏损/负值'
            if math.isinf(f):
                return 'N/A'
            return f"{f:.2f}"
        except (TypeError, ValueError):
            return str(val)

    @staticmethod
    def _fmt_amount(val) -> str:
        """格式化成交额（单位：元），自动换算万元/亿元。"""
        if val is None:
            return 'N/A'
        try:
            v = float(val)
            if math.isnan(v):
                return 'N/A'
        except (TypeError, ValueError):
            return 'N/A'
        if v >= 1e8:
            return f"{v / 1e8:.2f} 亿元"
        if v >= 1e4:
            return f"{v / 1e4:.2f} 万元"
        return f"{v:.2f} 元"

    @staticmethod
    def _fmt_wan(val) -> str:
        """格式化万元单位的数值（市值等），自动换算亿元。"""
        if val is None:
            return 'N/A'
        try:
            v = float(val)
            if math.isnan(v):
                return 'N/A'
        except (TypeError, ValueError):
            return 'N/A'
        if v >= 1e4:
            return f"{v / 1e4:.2f} 亿元"
        return f"{v:,.0f} 万元"

    @staticmethod
    def _fmt_flow(val) -> str:
        """格式化资金流向金额，输入单位为万元（moneyflow_stock_dc.net_amount）。"""
        if val is None:
            return 'N/A'
        try:
            v = float(val)
            if math.isnan(v):
                return 'N/A'
        except (TypeError, ValueError):
            return 'N/A'
        sign = '+' if v >= 0 else ''
        if abs(v) >= 10000:
            return f"{sign}{v / 10000:.2f} 亿元"
        return f"{sign}{v:.2f} 万元"
