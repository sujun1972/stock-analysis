"""
个股多维度数据收集服务

从本地数据库收集股票分析所需的全维度数据，包括：
- 基础盘面：收盘价、涨跌幅、成交额、换手率、PE-TTM、行业位置、筹码获利比
- 资金流向：主力净流入(1/5/10日)、北向资金持股、股东人数、大股东减持、解禁预告
- 技术指标：MA5/10/20/60/120、RSI多周期分析(7/14/21)、MACD(12,26,9)、量价异动
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
        # 取约3年日线数据（~900日历天），满足月线 MACD 稳定性需要
        start_dash = (today - timedelta(days=900)).strftime('%Y-%m-%d')
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

        # ---- 均线多周期结构分析 ----
        from app.services.ma_analysis_service import MaAnalysisService
        last_close = self._safe_float(close.iloc[-1]) if len(close) > 0 else None
        result['ma_analysis'] = MaAnalysisService.analyze(mas, last_close)

        # ---- RSI 多周期分析 ----
        from app.services.rsi_analysis_service import RsiAnalysisService
        result['rsi_analysis'] = RsiAnalysisService.analyze(df)

        # ---- 多级别 MACD 分析 ----
        from app.services.macd_analysis_service import MacdAnalysisService
        result['macd_multi'] = MacdAnalysisService.analyze_multi_level(df)

        # ---- 布林线多级别分析 ----
        from app.services.boll_analysis_service import BollAnalysisService
        result['boll_multi'] = BollAnalysisService.analyze_multi_level(df)

        # ---- K 线形态识别 ----
        from app.services.candlestick_analysis_service import CandlestickAnalysisService
        result['candlestick'] = CandlestickAnalysisService.analyze(df)

        # ---- ATR 波动率 ----
        result['atr'] = self._compute_atr(df)

        # ---- 量价动能分析 ----
        from app.services.volume_price_analysis_service import VolumePriceAnalysisService
        ma_trend = (result.get('ma_analysis') or {}).get('structure', {}).get('trend', '')
        result['volume_price'] = VolumePriceAnalysisService.analyze(df, trend_context=ma_trend)

        # ---- 近20日价格空间定位 ----
        if len(df) >= 20:
            recent_20 = df.tail(20)
            high_20 = float(recent_20['high'].max())
            low_20 = float(recent_20['low'].min())
            last_close = float(close.iloc[-1])
            price_range = high_20 - low_20
            percentile_20d = round((last_close - low_20) / price_range * 100) if price_range > 0 else 50
            # 阻力距离（距20日高点）和支撑距离（距20日低点）
            resist_pct = round((high_20 - last_close) / last_close * 100, 1) if last_close > 0 else 0
            support_pct = round((last_close - low_20) / last_close * 100, 1) if last_close > 0 else 0
            result['price_position'] = {
                'high_20d': round(high_20, 2),
                'low_20d': round(low_20, 2),
                'percentile_20d': percentile_20d,
                'close': round(last_close, 2),
                'resist_pct': resist_pct,
                'support_pct': support_pct,
            }

        # ---- 跨指标冲突与共振验证 ----
        result['cross_verification'] = self._build_cross_verification(result)

        return result

    @staticmethod
    def _compute_atr(df: pd.DataFrame, period: int = 14) -> Optional[Dict[str, Any]]:
        """计算 ATR（平均真实波幅）及其历史分位数。"""
        if len(df) < period + 20:
            return None

        high = df['high'].astype(float)
        low = df['low'].astype(float)
        close = df['close'].astype(float)

        # True Range
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)

        atr = tr.rolling(period).mean()
        last_atr = float(atr.iloc[-1])
        last_close = float(close.iloc[-1])

        # ATR 占价格的百分比
        atr_pct = round(last_atr / last_close * 100, 2) if last_close > 0 else 0

        # 历史分位数（近 120 日 ATR 的百分位）
        n = min(120, len(atr.dropna()))
        atr_history = atr.dropna().iloc[-n:]
        percentile = round(float((atr_history < last_atr).sum() / len(atr_history) * 100))

        # 定性
        if percentile >= 80:
            desc = f'波动率处于历史高位（{percentile}%分位），市场情绪剧烈，注意设宽止损'
        elif percentile >= 60:
            desc = f'波动率偏高（{percentile}%分位），波动活跃'
        elif percentile <= 20:
            desc = f'波动率处于历史低位（{percentile}%分位），市场交投清淡，可能酝酿变盘'
        elif percentile <= 40:
            desc = f'波动率偏低（{percentile}%分位），波动收敛'
        else:
            desc = f'波动率处于正常水平（{percentile}%分位）'

        return {
            'atr': round(last_atr, 2),
            'atr_pct': atr_pct,
            'percentile': percentile,
            'desc': desc,
        }


    @staticmethod
    def _build_cross_verification(technical: Dict) -> Optional[Dict[str, Any]]:
        """综合各技术指标，提取跨指标矛盾点、共振确认和风险因素。"""
        ma_analysis = technical.get('ma_analysis')
        rsi_analysis = technical.get('rsi_analysis')
        macd_multi = technical.get('macd_multi')
        boll_multi = technical.get('boll_multi')
        vp = technical.get('volume_price')
        candle = technical.get('candlestick')
        atr = technical.get('atr')

        if not any([ma_analysis, macd_multi, boll_multi]):
            return None

        conflicts = []
        confirmations = []
        risks = []

        # 提取各指标方向判断
        ma_trend = (ma_analysis or {}).get('structure', {}).get('trend', '')
        ma_bullish = '多头' in ma_trend
        ma_bearish = '空头' in ma_trend

        # MACD 日线方向（区分大势和短期方向，避免"零轴上方但黏合偏空"被标记为看多）
        daily_macd = (macd_multi or {}).get('daily', {})
        macd_zero_bullish = '上方' in daily_macd.get('zero_axis', '')
        macd_cross_bearish = '死叉' in daily_macd.get('cross_state', '') or '偏空' in daily_macd.get('cross_state', '')
        macd_bullish = macd_zero_bullish and not macd_cross_bearish
        macd_bearish = '下方' in daily_macd.get('zero_axis', '') or macd_cross_bearish
        macd_diverging = macd_zero_bullish and macd_cross_bearish

        # MACD 周线方向
        weekly_macd = (macd_multi or {}).get('weekly', {})
        weekly_macd_bearish = '下方' in weekly_macd.get('zero_axis', '')
        weekly_macd_bullish = '上方' in weekly_macd.get('zero_axis', '')

        # Boll 日线方向
        daily_boll = (boll_multi or {}).get('daily', {})
        boll_bullish = daily_boll.get('percent_b', 0.5) > 0.6
        boll_bearish = daily_boll.get('percent_b', 0.5) < 0.4

        # RSI 短线
        rsi_slices = (rsi_analysis or {}).get('slices', [])
        rsi_short = next((s for s in rsi_slices if s.get('period') == 7), {})
        rsi_overbought = rsi_short.get('rsi_value', 50) > 70
        rsi_oversold = rsi_short.get('rsi_value', 50) < 30

        # ---- 矛盾点 ----
        # 周线强势 + 日线 MACD 高位偏空分化
        if weekly_macd_bullish and macd_diverging:
            cross_desc = daily_macd.get('cross_state', '').split('（')[0]
            conflicts.append(
                f"周线 MACD 处于零轴上方强势区，但日线 MACD {cross_desc}，"
                f"长短周期出现分化，需关注日线动能是否进一步衰减"
            )

        # 日线看多 vs 周线看空
        if macd_bullish and weekly_macd_bearish:
            conflicts.append(
                f"日线 MACD {daily_macd.get('cross_state', '').split('（')[0]}（偏多），"
                f"但周线 MACD 仍处于零轴下方（弱势），短线反弹可能受长线趋势压制"
            )

        # Boll 贴上轨 + RSI 超买
        if boll_bullish and rsi_overbought:
            rsi_val = rsi_short.get('rsi_value', 0)
            conflicts.append(
                f"价格贴近布林上轨且 RSI7={rsi_val:.0f} 进入超买区，"
                f"属于「加速上涨」还是「诱多衰竭」需量价验证"
            )

        # 均线空头 + 短线看多信号
        if ma_bearish and (macd_bullish or boll_bullish):
            conflicts.append(
                '均线系统处于空头排列，但短线指标出现看多信号，'
                '可能是下跌中继反弹而非趋势反转'
            )

        # ---- 共振确认（区分周线大势和日线短线方向） ----
        bullish_signals = sum([ma_bullish, macd_bullish, boll_bullish])
        bearish_signals = sum([ma_bearish, macd_bearish, boll_bearish])

        if bullish_signals >= 3:
            confirmations.append('均线、MACD、布林线多维共振看多，趋势信号较强')
        elif bearish_signals >= 3:
            confirmations.append('均线、MACD、布林线多维共振看空，趋势信号较强')
        elif ma_bullish and boll_bullish and macd_diverging:
            # 大势看多但 MACD 日线出现偏空分化 — 精确描述而非笼统说"共振看多"
            confirmations.append(
                '周线级别（均线、布林线）大势看多；但日线 MACD 高位黏合偏空，长短周期出现分化'
            )

        if macd_bullish and boll_bullish and not rsi_overbought:
            confirmations.append('MACD 看多 + 布林上半通道 + RSI 未超买，上涨空间尚可')
        elif macd_diverging and boll_bullish and not rsi_overbought:
            # MACD 偏空但布林和 RSI 尚好 — 不能说"上涨空间尚可"，而应标注分化
            confirmations.append('布林上半通道 + RSI 未超买，但日线 MACD 动能减弱，上行需量能配合')

        # 量价确认
        if vp:
            daily_detail = vp.get('daily_detail', [])
            if daily_detail:
                last_d = daily_detail[-1]
                vol_ratio = last_d.get('vol_ratio', 1)
                pct = last_d.get('pct_change', 0)
                if pct > 1 and vol_ratio >= 1.3:
                    confirmations.append(f"最近一日放量上涨（量比 {vol_ratio}x），资金进场确认")
                elif pct < -1 and vol_ratio >= 1.3:
                    risks.append(f"最近一日放量下跌（量比 {vol_ratio}x），资金出逃信号")

        # ---- 风险因素 ----
        # MA120 压制
        if ma_analysis:
            battle = (ma_analysis.get('structure') or {}).get('battle_point', '')
            if 'MA120' in battle and '阻力' in battle:
                risks.append(f"MA120 形成上方阻力，{battle.split('；')[0]}")

        # 周线级别空头
        if weekly_macd_bearish:
            risks.append(f"周线 MACD 处于零轴下方（{weekly_macd.get('zero_axis', '')}），中线趋势偏空")

        # RSI 超买风险
        if rsi_overbought:
            risks.append(f"RSI7 进入超买区（{rsi_short.get('rsi_value', 0):.0f}），短线存在回调压力")

        # 布林收口
        if '收窄' in daily_boll.get('channel_width', '') or '收口' in daily_boll.get('pattern', ''):
            risks.append('日线布林通道收口，波动率即将放大，需关注变盘方向')

        # ATR 异常
        if atr and atr.get('percentile', 50) >= 80:
            risks.append(f"波动率处于历史高位（{atr['percentile']}%分位），注意设宽止损")

        # ---- 支撑/阻力阶梯 ----
        price_pos = technical.get('price_position', {})
        current_price = price_pos.get('close')
        support_ladder = []
        resistance_ladder = []
        if current_price and current_price > 0:
            # 收集所有关键价位
            key_levels = []
            # MA 均线
            ma = technical.get('ma', {})
            for name, val in [('MA5', ma.get('ma5')), ('MA10', ma.get('ma10')),
                              ('MA20', ma.get('ma20')), ('MA60', ma.get('ma60')),
                              ('MA120', ma.get('ma120'))]:
                if val:
                    key_levels.append((name, float(val)))
            # 布林带
            if boll_multi:
                d_boll = boll_multi.get('daily', {})
                for name, val in [('布林上轨', d_boll.get('upper')),
                                  ('布林中轨', d_boll.get('middle')),
                                  ('布林下轨', d_boll.get('lower'))]:
                    if val:
                        key_levels.append((name, float(val)))
            # 20日高低点
            if price_pos.get('high_20d'):
                key_levels.append(('20日高点', float(price_pos['high_20d'])))
            if price_pos.get('low_20d'):
                key_levels.append(('20日低点', float(price_pos['low_20d'])))

            for name, val in key_levels:
                pct = round((val - current_price) / current_price * 100, 1)
                if val >= current_price:
                    resistance_ladder.append((name, val, pct))
                else:
                    support_ladder.append((name, val, pct))
            # 支撑从近到远（价格从高到低），阻力从近到远（价格从低到高）
            support_ladder.sort(key=lambda x: x[1], reverse=True)
            resistance_ladder.sort(key=lambda x: x[1])

        if not conflicts and not confirmations and not risks:
            return None

        # ---- 综合推理任务（统一替代各子模块散落的分析提示） ----
        prompt_parts = ['请作为资深策略分析师，基于上述全部技术指标数据，完成以下交叉验证推理：']
        task_num = 1

        if conflicts:
            prompt_parts.append(f'{task_num}. 处理上述指标矛盾点：判断哪个信号的权重更高，给出依据')
            task_num += 1

        # RSI/MACD 背离信号验证（严格匹配"顶背离"或"底背离"，排除"数据不足无法判断背离"等干扰）
        has_divergence = False
        for s in rsi_slices:
            div_text = s.get('divergence', '')
            if '顶背离' in div_text or '底背离' in div_text:
                has_divergence = True
                break
        if not has_divergence:
            macd_div = daily_macd.get('divergence', '')
            if '顶背离' in macd_div or '底背离' in macd_div:
                has_divergence = True
            # 周线背离也检查
            weekly_div = weekly_macd.get('divergence', '')
            if '顶背离' in weekly_div or '底背离' in weekly_div:
                has_divergence = True
        if has_divergence:
            prompt_parts.append(
                f'{task_num}. 评估背离信号的有效性：结合提供的历史锚点（前次极值价格 vs 当前极值价格），'
                f'判断背离是否可靠、反转概率多大'
            )
            task_num += 1
        else:
            # 无背离时，引导 AI 分析动能延续性而非寻找不存在的背离
            prompt_parts.append(
                f'{task_num}. 当前各指标均未检测到背离信号，请分析当前趋势动能的延续概率和潜在衰竭迹象'
            )
            task_num += 1

        if bullish_signals >= 2 and bearish_signals >= 1:
            prompt_parts.append(f'{task_num}. 判断当前看多/看空的确定性（1-10 分），说明核心理由')
            task_num += 1

        if risks:
            prompt_parts.append(f'{task_num}. 评估各风险因素的实际威胁程度和触发条件')
            task_num += 1

        # K线形态与阻力位联动提示（高位出现见顶形态时自动引导）
        if candle and resistance_ladder and price_pos.get('percentile_20d', 0) >= 70:
            nearest_resist = resistance_ladder[0] if resistance_ladder else None
            candle_patterns = candle.get('daily_patterns', [])
            combo_patterns = candle.get('combo_patterns', [])
            # 检查是否有高位危险形态
            danger_keywords = ['墓碑', '长上影', '看跌吞没', '高位孕线', '高位看跌']
            has_danger_pattern = False
            for p in candle_patterns:
                if any(kw in p.get('pattern', '') for kw in danger_keywords):
                    has_danger_pattern = True
                    break
            if not has_danger_pattern:
                for c_pat in (combo_patterns or []):
                    if any(kw in c_pat for kw in danger_keywords):
                        has_danger_pattern = True
                        break
            if has_danger_pattern and nearest_resist:
                prompt_parts.append(
                    f'{task_num}. 形态与空间共振：结合近期 K 线高位见顶形态与距离上方阻力位'
                    f'（{nearest_resist[0]} {nearest_resist[1]:.2f}，仅 +{abs(nearest_resist[2]):.1f}%）'
                    f'的距离，评估短线见顶回调的实际威胁程度'
                )
                task_num += 1

        # 盈亏比计算指令（乖离率较大时自动生成）
        convergence = (ma_analysis or {}).get('convergence', {})
        bias_val = convergence.get('bias20')
        if (bias_val is not None and abs(bias_val) >= 5
                and resistance_ladder and support_ladder):
            nearest_r = resistance_ladder[0]
            nearest_s = support_ladder[0]
            prompt_parts.append(
                f'{task_num}. 风盈比计算：当前乖离率 {bias_val:+.1f}%，'
                f'上方阻力空间 +{abs(nearest_r[2]):.1f}%（{nearest_r[0]}），'
                f'下方支撑空间 {nearest_s[2]:.1f}%（{nearest_s[0]}），'
                f'请结合此风盈比评估当前追高/加仓的合理性，并给出仓位建议'
            )
            task_num += 1

        prompt_parts.append(
            f'{task_num}. 给出明确的综合操作建议：'
            f'包含具体的止损价位（跌破哪里应离场）和加仓条件（突破哪里可加仓）'
        )

        prompt = '\n'.join(prompt_parts)

        return {
            'conflicts': conflicts,
            'confirmations': confirmations,
            'risks': risks,
            'support_ladder': support_ladder,
            'resistance_ladder': resistance_ladder,
            'prompt': prompt,
        }

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

        # ================================================================
        # 一、基础盘面
        # ================================================================
        basic = data.get('basic_market', {})
        lines.append("## 一、基础盘面与行业位置")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 交易日期 | {basic.get('trade_date', 'N/A')} |")
        lines.append(f"| 收盘价 | {self._fmt(basic.get('close'))} 元 |")
        lines.append(f"| 涨跌幅 | {self._fmt(basic.get('pct_change'))}% |")
        lines.append(f"| 成交额 | {self._fmt_amount(basic.get('amount'))} |")
        lines.append(f"| 换手率 | {self._fmt(basic.get('turnover_rate'))}% |")
        lines.append(f"| PE-TTM | {self._fmt_pe(basic.get('pe_ttm'))} |")
        lines.append(f"| PB | {self._fmt(basic.get('pb'))} |")
        lines.append(f"| 总市值 | {self._fmt_wan(basic.get('total_mv'))} |")
        lines.append(f"| 行业(Tushare) | {basic.get('industry') or 'N/A'} |")
        lines.append(f"| 地区 | {basic.get('area') or 'N/A'} |")

        board_name = basic.get('industry_board_name', '')
        if board_name:
            lines.append(f"| 东财行业板块 | {board_name} |")

        chip = basic.get('chip', {})
        if chip:
            lines.append(f"| 筹码获利比 | {self._fmt(chip.get('winner_rate'))}% |")
            lines.append(
                f"| 成本分布 (15%/50%/85%) | "
                f"{self._fmt(chip.get('cost_15pct'))} / "
                f"{self._fmt(chip.get('cost_50pct'))} / "
                f"{self._fmt(chip.get('cost_85pct'))} 元 |"
            )
            lines.append(f"| 加权平均成本 | {self._fmt(chip.get('weight_avg'))} 元 |")

        # 行业板块近5日涨跌幅
        ind_5d = basic.get('industry_5d', [])
        if ind_5d:
            lines.append("")
            lines.append("**行业板块近5日涨跌幅：**")
            lines.append("")
            lines.append("| 日期 | 涨跌幅 |")
            lines.append("|------|--------|")
            for r in ind_5d:
                lines.append(f"| {r.get('trade_date', '')} | {self._fmt(r.get('pct_change'))}% |")
        lines.append("")

        # ================================================================
        # 二、资金流向
        # ================================================================
        capital = data.get('capital_flow', {})
        lines.append("## 二、资金流向与筹码变动")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 主力净流入 近1日 | {self._fmt_flow(capital.get('net_1d'))} |")
        lines.append(f"| 主力净流入 近5日 | {self._fmt_flow(capital.get('net_5d'))} |")
        lines.append(f"| 主力净流入 近10日 | {self._fmt_flow(capital.get('net_10d'))} |")

        hk = capital.get('hk_hold', {})
        if hk:
            lines.append(
                f"| 北向持股({hk.get('trade_date', '')}) | "
                f"{self._fmt(hk.get('vol'), 0)} 股，占流通 {self._fmt(hk.get('ratio'))}% |"
            )
            if hk.get('vol_change_pct') is not None:
                lines.append(f"| 北向较历史变动 | {self._fmt(hk.get('vol_change_pct'))}% |")
        else:
            lines.append("| 北向资金 | 本地无持股数据 |")

        flow_detail = capital.get('flow_detail', [])
        if flow_detail:
            lines.append("")
            lines.append("**近5日资金流向明细：**")
            lines.append("")
            lines.append("| 日期 | 净流入 | 涨跌幅 |")
            lines.append("|------|--------|--------|")
            for r in flow_detail:
                lines.append(
                    f"| {r.get('trade_date', '')} "
                    f"| {self._fmt_flow(r.get('net_amount'))} "
                    f"| {self._fmt(r.get('pct_change'))}% |"
                )
        lines.append("")

        # ================================================================
        # 股东变化
        # ================================================================
        shareholder = data.get('shareholder', {})
        lines.append("## 三、股东变化")
        lines.append("")

        holder_nums = shareholder.get('holder_nums', [])
        if holder_nums:
            lines.append("**股东人数（近4季，最新在前）：**")
            lines.append("")
            lines.append("| 报告期 | 股东人数 | 环比变化 |")
            lines.append("|--------|---------|---------|")
            for r in holder_nums:
                qoq = f"{r['qoq_pct']}%" if r.get('qoq_pct') is not None else '-'
                lines.append(f"| {r.get('end_date', '')} | {r.get('holder_num', 'N/A')} 户 | {qoq} |")
        else:
            lines.append("股东人数：暂无数据")

        reductions = shareholder.get('reductions', [])
        if reductions:
            lines.append("")
            lines.append("**近3个月大股东减持明细：**")
            lines.append("")
            lines.append("| 公告日 | 股东名称 | 减持股数 | 变动比例 | 均价 |")
            lines.append("|--------|---------|---------|---------|------|")
            for r in reductions:
                lines.append(
                    f"| {r.get('ann_date', '')} | {r.get('holder_name', '')} "
                    f"| {self._fmt(r.get('change_vol'), 0)} 股 "
                    f"| {self._fmt(r.get('change_ratio'))}% "
                    f"| {self._fmt(r.get('avg_price'))} 元 |"
                )
        else:
            lines.append("")
            lines.append("近3个月：无大股东减持公告")

        upcoming = shareholder.get('upcoming_floats', [])
        if upcoming:
            lines.append("")
            lines.append("**未来1个月解禁预告：**")
            lines.append("")
            lines.append("| 解禁日期 | 解禁股数 | 股份类型 | 占比 |")
            lines.append("|---------|---------|---------|------|")
            for r in upcoming:
                lines.append(
                    f"| {r.get('float_date', '')} "
                    f"| {self._fmt(r.get('float_share'), 0)} 万股 "
                    f"| {r.get('share_type', '')} "
                    f"| {self._fmt(r.get('float_ratio'))}% |"
                )
        else:
            lines.append("")
            lines.append("未来1个月：无解禁计划")
        lines.append("")

        # ================================================================
        # 四、技术指标（YAML 格式，便于 LLM 结构化解析）
        # ================================================================
        technical = data.get('technical', {})
        lines.append("## 四、技术指标详情")
        lines.append("")
        lines.append("```yaml")

        pp = technical.get('price_position')
        atr = technical.get('atr')
        ma_analysis = technical.get('ma_analysis')
        rsi_analysis = technical.get('rsi_analysis')
        macd_multi = technical.get('macd_multi')
        boll_multi = technical.get('boll_multi')
        candle = technical.get('candlestick')
        vp = technical.get('volume_price')
        cross_verification = technical.get('cross_verification')
        nine_turn = data.get('nine_turn', {})

        # --- 价格行为观测 ---
        if pp:
            lines.append("价格行为观测:")
            lines.append(f"  当前价: {self._fmt(pp.get('close'))}")
            lines.append(f"  20日波动区间: [{self._fmt(pp.get('low_20d'))}, {self._fmt(pp.get('high_20d'))}]")
            lines.append(f"  区间分位: {pp.get('percentile_20d')}%")
            lines.append(f"  距上方阻力: +{self._fmt(pp.get('resist_pct', 0), 1)}% ({self._fmt(pp.get('high_20d'))})")
            lines.append(f"  距下方支撑: -{self._fmt(pp.get('support_pct', 0), 1)}% ({self._fmt(pp.get('low_20d'))})")
            if atr:
                lines.append(f"  波动率:")
                lines.append(f"    ATR14: {self._fmt(atr.get('atr'), 2)}")
                lines.append(f"    占股价: {self._fmt(atr.get('atr_pct'), 2)}%")
                lines.append(f"    历史分位: {atr.get('percentile')}%")
                lines.append(f"    定性: {atr.get('desc', '')}")

        # --- 均线系统 ---
        if ma_analysis:
            lines.append("")
            lines.append("均线系统:")
            lines.append(f"  最新收盘价: {self._fmt(ma_analysis.get('close'))}")
            lines.append("  各周期状态:")
            for s in ma_analysis.get('slices', []):
                lines.append(f"    - 级别: {s['level']}")
                lines.append(f"      均线: {s['names']}")
                lines.append(f"      排列: {s['arrangement']}")
                lines.append(f"      价格位置: {s['position']}")
                lines.append(f"      数值: {s['values']}")
            structure = ma_analysis.get('structure', {})
            if structure:
                lines.append("  核心结构:")
                lines.append(f"    整体趋势: {structure.get('trend', '')}")
                if structure.get('short_signal'):
                    lines.append(f"    短期异动: {structure['short_signal']}")
                if structure.get('battle_point'):
                    lines.append(f"    核心博弈点: {structure['battle_point']}")
            convergence = ma_analysis.get('convergence', {})
            if convergence:
                if convergence.get('convergence_desc'):
                    lines.append(f"  收敛度: {convergence['convergence_desc']}")
                if convergence.get('bias_desc'):
                    lines.append(f"  乖离率: {convergence['bias_desc']}")

        # --- RSI ---
        if rsi_analysis:
            lines.append("")
            lines.append("RSI多周期分析:")
            lines.append("  各周期状态:")
            for s in rsi_analysis.get('slices', []):
                div_text = s['divergence'] if '背离' in s['divergence'] else '无'
                lines.append(f"    - 周期: RSI{s['period']} ({s['label']})")
                lines.append(f"      值: {self._fmt(s['rsi_value'], 1)}")
                lines.append(f"      区间: {s['zone']}")
                lines.append(f"      趋势: {s['trend']}")
                lines.append(f"      背离: {div_text}")
            cross = rsi_analysis.get('cross_period', {})
            if cross:
                lines.append("  跨周期逻辑:")
                lines.append(f"    多周期共振: {cross.get('resonance', '')}")
                if cross.get('divergence_analysis'):
                    lines.append(f"    长短分歧: {cross['divergence_analysis']}")
                if cross.get('extreme_warning'):
                    lines.append(f"    极值预警: {cross['extreme_warning']}")
                if cross.get('divergence_signals'):
                    lines.append(f"    背离汇总: {cross['divergence_signals']}")

        # --- MACD ---
        if macd_multi:
            lines.append("")
            lines.append("MACD多级别分析:")
            lines.append("  各级别状态:")
            for key in ['monthly', 'weekly', 'daily']:
                lv = macd_multi.get(key)
                if not lv:
                    continue
                div_text = lv['divergence'] if '背离' in lv['divergence'] else '无背离信号'
                lines.append(f"    - 级别: {lv['level']}")
                lines.append(f"      零轴: {lv['zero_axis']}")
                lines.append(f"      交叉: {lv['cross_state']}")
                lines.append(f"      动能: {lv['bar_momentum']}")
                lines.append(f"      背离: {div_text}")
                lines.append(f"      DIF: {self._fmt(lv.get('dif'), 2)}")
                lines.append(f"      DEA: {self._fmt(lv.get('dea'), 2)}")
            cross = macd_multi.get('cross_level', {})
            if cross:
                lines.append("  跨级别逻辑:")
                lines.append(f"    共振状态: {cross.get('resonance_state', '')}")
                if cross.get('battle_analysis'):
                    lines.append(f"    长短博弈: {cross['battle_analysis']}")

        # --- 布林线 ---
        if boll_multi:
            lines.append("")
            lines.append("布林线多级别分析:")
            lines.append("  各级别状态:")
            for key in ['monthly', 'weekly', 'daily']:
                lv = boll_multi.get(key)
                if not lv:
                    continue
                lines.append(f"    - 级别: {lv['level']}")
                lines.append(f"      通道宽度: {lv['channel_width']} (BW={self._fmt(lv.get('bandwidth'), 1)}%)")
                lines.append(f"      价格位置: {lv['price_position']} (%B={self._fmt(lv.get('percent_b'), 2)})")
                lines.append(f"      中轨方向: {lv['mid_direction']}")
                lines.append(f"      信号: {lv['signal']}")
                lines.append(f"      形态: {lv['pattern']}")
                lines.append(f"      上轨: {self._fmt(lv.get('upper'), 2)}")
                lines.append(f"      中轨: {self._fmt(lv.get('middle'), 2)}")
                lines.append(f"      下轨: {self._fmt(lv.get('lower'), 2)}")
            cross = boll_multi.get('cross_level', {})
            if cross:
                lines.append("  跨级别逻辑:")
                lines.append(f"    共振状态: {cross.get('resonance_state', '')}")
                if cross.get('battle_analysis'):
                    lines.append(f"    长短博弈: {cross['battle_analysis']}")

        # --- K 线形态 ---
        if candle:
            lines.append("")
            lines.append("K线形态:")
            daily_p = candle.get('daily_patterns', [])
            if daily_p:
                lines.append("  逐日形态:")
                for d in daily_p:
                    lines.append(f"    - 日期: {d['date']}")
                    lines.append(f"      涨跌幅: {self._fmt(d['pct_change'])}%")
                    lines.append(f"      形态: {d['pattern']}")
            combo = candle.get('combo_patterns', [])
            if combo and combo != ['无显著组合形态']:
                lines.append("  组合形态:")
                for c in combo:
                    lines.append(f"    - {c}")
            gravity = candle.get('gravity_trend', '')
            if gravity:
                lines.append(f"  重心趋势: {gravity}")

        # --- ATR（若未在价格行为观测中展示） ---
        if not pp and atr:
            lines.append("")
            lines.append("波动率:")
            lines.append(f"  ATR14: {self._fmt(atr.get('atr'), 2)}")
            lines.append(f"  占股价: {self._fmt(atr.get('atr_pct'), 2)}%")
            lines.append(f"  定性: {atr.get('desc', '')}")

        # --- 量价动能 ---
        if vp:
            lines.append("")
            lines.append("量价动能分析:")
            turnover = vp.get('turnover')
            vol_mean = vp.get('vol_5d_mean')
            if turnover is not None:
                lines.append(f"  换手率: {self._fmt(turnover)}%")
            if vol_mean is not None:
                lines.append(f"  5日均量: {self._fmt_vol(vol_mean)}")
            daily = vp.get('daily_detail', [])
            if daily:
                lines.append("  近5日量价推演:")
                for d in daily:
                    lines.append(f"    - 日期: {d['date']}")
                    lines.append(f"      涨跌幅: {self._fmt(d['pct_change'])}%")
                    lines.append(f"      成交量: {self._fmt_vol(d['volume'])}")
                    lines.append(f"      量比: {d['vol_desc']}")
                    lines.append(f"      形态: {d['pattern']}")
            vp_ratio_desc = vp.get('vp_ratio_desc')
            if vp_ratio_desc:
                lines.append(f"  量价背离系数: {vp_ratio_desc}")
            mid_long = vp.get('mid_long', {})
            if mid_long:
                lines.append("  中长线结构:")
                if mid_long.get('mid_structure'):
                    lines.append(f"    中线(60日): {mid_long['mid_structure']}")
                if mid_long.get('volume_pressure'):
                    lines.append(f"    长线压力: {mid_long['volume_pressure']}")
                anomalies = mid_long.get('key_anomalies', [])
                if anomalies:
                    lines.append(f"    异动: {'; '.join(anomalies)}")

        # --- 多维指标交叉验证 ---
        if cross_verification:
            lines.append("")
            lines.append("多维指标交叉验证:")
            conflicts = cross_verification.get('conflicts', [])
            if conflicts:
                lines.append("  矛盾点:")
                for c in conflicts:
                    lines.append(f"    - {c}")
            confirmations = cross_verification.get('confirmations', [])
            if confirmations:
                lines.append("  共振确认:")
                for c in confirmations:
                    lines.append(f"    - {c}")
            risks = cross_verification.get('risks', [])
            if risks:
                lines.append("  风险因素:")
                for r in risks:
                    lines.append(f"    - {r}")
            support_ladder = cross_verification.get('support_ladder', [])
            resistance_ladder = cross_verification.get('resistance_ladder', [])
            if resistance_ladder:
                lines.append("  阻力位阶梯:")
                for name, val, pct in resistance_ladder[:3]:
                    lines.append(f"    - {name}: {val:.2f} (+{abs(pct):.1f}%)")
            if support_ladder:
                lines.append("  支撑位阶梯:")
                for name, val, pct in support_ladder[:4]:
                    lines.append(f"    - {name}: {val:.2f} ({pct:.1f}%)")

        # --- 神奇九转 ---
        if nine_turn:
            lines.append("")
            lines.append("神奇九转:")
            lines.append(f"  日期: {nine_turn.get('latest_date', '')}")
            up_c = nine_turn.get('up_count')
            down_c = nine_turn.get('down_count')
            up_signal = nine_turn.get('nine_up_turn')
            down_signal = nine_turn.get('nine_down_turn')
            for cnt_val, signal_val, direction, signal_label in [
                (up_c, up_signal, '上涨', '见顶'),
                (down_c, down_signal, '下跌', '见底'),
            ]:
                if cnt_val is not None and cnt_val > 0:
                    count = int(cnt_val)
                    triggered = (signal_val == '+9') if direction == '上涨' else (signal_val == '-9')
                    if triggered:
                        qualifier = f"已触发九转{signal_label}信号，日线级别存在短线反转风险"
                    elif count >= 7:
                        qualifier = f"接近九转阈值，关注后续1-2日是否触发{signal_label}信号"
                    elif count >= 4:
                        qualifier = f"处于{direction}序列中段，序列延续中"
                    else:
                        qualifier = f"处于{direction}序列初期，未触发极值反转信号"
                    lines.append(f"  {direction}计数: {count}")
                    lines.append(f"  {direction}状态: {qualifier}")
            signals = nine_turn.get('recent_signals', [])
            if signals:
                lines.append("  近期信号:")
                for s in signals:
                    lines.append(f"    - 日期: {s.get('date', '')}")
                    lines.append(f"      类型: {s.get('type', '')}")
            if not up_c and not down_c:
                lines.append("  状态: 无连续计数（多空交替频繁，暂无趋势性信号）")

        lines.append("```")
        lines.append("")

        # ---- 综合推理任务（YAML 代码块之外，作为自然语言指令） ----
        if cross_verification:
            verify_prompt = cross_verification.get('prompt', '')
            if verify_prompt:
                lines.append("**【综合推理任务】**")
                lines.append("")
                for prompt_line in verify_prompt.split('\n'):
                    lines.append(f"> {prompt_line}")
                lines.append("")

        # ================================================================
        # 五、财报与公告
        # ================================================================
        financial = data.get('financial', {})
        lines.append("## 五、财报与敏感公告")
        lines.append("")

        disclosures = financial.get('disclosures', [])
        if disclosures:
            lines.append("**财报预约披露日期：**")
            lines.append("")
            lines.append("| 报告期 | 预约披露日 |")
            lines.append("|--------|----------|")
            for r in disclosures:
                actual = r.get('actual_date', '')
                pre = r.get('pre_date', '')
                date_str = actual if (actual and actual not in ('None', '')) else pre
                lines.append(f"| {r.get('end_date', '')} | {date_str} |")
        else:
            lines.append("暂无近期财报披露计划")

        risk = data.get('risk', {})
        alerts = risk.get('alerts', [])
        if alerts:
            lines.append("")
            lines.append("**风险警示：**")
            lines.append("")
            lines.append("| 起始日期 | 结束日期 | 类型 |")
            lines.append("|---------|---------|------|")
            for r in alerts:
                lines.append(f"| {r.get('start_date', '')} | {r.get('end_date', '')} | {r.get('type', '')} |")
        else:
            lines.append("")
            lines.append("近期无风险警示公告")

        pledge = risk.get('pledge', {})
        if pledge:
            lines.append("")
            lines.append(f"**质押情况（{pledge.get('end_date', '')}）：**")
            lines.append("")
            lines.append("| 指标 | 数值 |")
            lines.append("|------|------|")
            lines.append(f"| 质押笔数 | {pledge.get('pledge_count', 'N/A')} 笔 |")
            lines.append(f"| 质押比例 | {self._fmt(pledge.get('pledge_ratio'))}% |")
            lines.append(f"| 未解押股份 | {self._fmt(pledge.get('unrest_pledge'), 0)} 万股 |")

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

    @staticmethod
    def _fmt_vol(val) -> str:
        """格式化成交量（输入为股数），自动换算万股/亿股。"""
        if val is None:
            return 'N/A'
        try:
            v = float(val)
            if math.isnan(v):
                return 'N/A'
        except (TypeError, ValueError):
            return 'N/A'
        if v >= 1e8:
            return f"{v / 1e8:.2f}亿股"
        if v >= 1e4:
            return f"{v / 1e4:.0f}万股"
        return f"{v:.0f}股"
