"""
布林线多级别通道与趋势分析服务

提供月线、周线、日线三个级别的布林线状态分析，包括：
- 通道宽度（波动率状态）
- 价格位置（%B 相对通道位置）
- 中轨方向（趋势方向）
- 轨道突破/回踩信号
- 布林线形态（开口/收口/沿轨运行）
- 跨级别共振 / 长短博弈分析

从 StockDataCollectionService 提取，供技术指标收集和 LangChain Tool 使用。
"""

from typing import Dict, Any, Optional, List

import pandas as pd


class BollAnalysisService:
    """布林线多级别分析服务（纯计算，无 IO）。"""

    @classmethod
    def analyze_multi_level(cls, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """对日线 DataFrame 进行多级别布林线分析。

        Args:
            df: 日线 OHLCV DataFrame，index 为日期，需含 open/high/low/close/volume/pct_change。

        Returns:
            多级别布林线分析结果字典，数据不足时返回 None。
        """
        from app.services.macd_analysis_service import MacdAnalysisService

        boll_multi: Dict[str, Any] = {}

        # 日线布林线（需 >= 26 根 K 线，确保 20 周期 + 足够历史）
        if len(df) >= 26:
            boll_multi['daily'] = cls._compute_boll_status(df, '日线')

        # 周线布林线（日线重采样）
        weekly_df = MacdAnalysisService._resample_ohlcv(df, 'W')
        if weekly_df is not None and len(weekly_df) >= 26:
            boll_multi['weekly'] = cls._compute_boll_status(weekly_df, '周线')

        # 月线布林线（日线重采样）
        monthly_df = MacdAnalysisService._resample_ohlcv(df, 'ME')
        if monthly_df is not None and len(monthly_df) >= 26:
            boll_multi['monthly'] = cls._compute_boll_status(monthly_df, '月线')

        # 跨级别共振分析
        if boll_multi:
            boll_multi['cross_level'] = cls._analyze_cross_level(boll_multi)

        return boll_multi if boll_multi else None

    # ------------------------------------------------------------------
    # 单级别布林线状态
    # ------------------------------------------------------------------

    @classmethod
    def _compute_boll_status(cls, df: pd.DataFrame, level_name: str,
                              period: int = 20, std_dev: int = 2) -> Dict[str, Any]:
        """计算单个时间级别的布林线完整状态。"""
        close = df['close'].astype(float)
        high = df['high'].astype(float)
        low = df['low'].astype(float)

        # 布林线计算
        middle = close.rolling(period).mean()
        std = close.rolling(period).std()
        upper = middle + std_dev * std
        lower = middle - std_dev * std

        last_close = float(close.iloc[-1])
        last_upper = float(upper.iloc[-1])
        last_middle = float(middle.iloc[-1])
        last_lower = float(lower.iloc[-1])

        # 带宽与 %B
        bandwidth = (last_upper - last_lower) / last_middle * 100 if last_middle != 0 else 0
        percent_b = ((last_close - last_lower) / (last_upper - last_lower)
                     if (last_upper - last_lower) != 0 else 0.5)

        # 带宽均值（用于定性）
        bw_series = (upper - lower) / middle * 100
        bw_ma = float(bw_series.rolling(period).mean().iloc[-1]) if len(bw_series) >= period else bandwidth

        # 1. 通道宽度定性
        channel_width = cls._classify_channel_width(bandwidth, bw_ma)

        # 2. 价格位置定性
        price_position = cls._classify_price_position(percent_b)

        # 3. 中轨方向定性
        mid_direction = cls._classify_mid_direction(middle)

        # 4. 轨道突破/回踩信号
        signal = cls._detect_signal(close, high, low, upper, middle, lower)

        # 5. 布林线形态
        pattern = cls._classify_pattern(bandwidth, bw_ma, mid_direction, percent_b,
                                         close, upper, lower, middle)

        return {
            'level': level_name,
            'upper': round(last_upper, 2),
            'middle': round(last_middle, 2),
            'lower': round(last_lower, 2),
            'bandwidth': round(bandwidth, 2),
            'percent_b': round(percent_b, 3),
            'channel_width': channel_width,
            'price_position': price_position,
            'mid_direction': mid_direction,
            'signal': signal,
            'pattern': pattern,
        }

    # ------------------------------------------------------------------
    # 维度 1：通道宽度（波动率状态）
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_channel_width(bandwidth: float, bw_ma: float) -> str:
        if bw_ma <= 0:
            return '通道宽度正常'
        ratio = bandwidth / bw_ma
        if ratio > 1.5:
            return '通道极度扩张（趋势剧烈运动中）'
        if ratio > 1.2:
            return '通道扩张（趋势运行中）'
        if ratio < 0.6:
            return '通道极度收窄（变盘临界，即将选择方向）'
        if ratio < 0.8:
            return '通道收窄（波动率降低，蓄势待变）'
        return '通道宽度正常'

    # ------------------------------------------------------------------
    # 维度 2：价格位置（%B）
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_price_position(percent_b: float) -> str:
        if percent_b > 1.0:
            return '价格突破上轨（超强势/可能超买）'
        if percent_b > 0.8:
            return '价格贴近上轨运行（强势）'
        if 0.4 <= percent_b <= 0.6:
            return '价格围绕中轨震荡（方向不明）'
        if percent_b < 0:
            return '价格跌破下轨（超弱势/可能超卖）'
        if percent_b < 0.2:
            return '价格贴近下轨运行（弱势）'
        if percent_b > 0.6:
            return '上半通道运行'
        return '下半通道运行'

    # ------------------------------------------------------------------
    # 维度 3：中轨方向（趋势方向）
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_mid_direction(middle: pd.Series) -> str:
        if len(middle) < 5:
            return '数据不足'

        # 取最近 5 根 K 线的中轨值（用于检测拐头）
        m = middle.iloc[-5:].values
        last_mid = m[-1]
        # 相对化阈值：中轨值的 0.1%
        threshold = abs(last_mid) * 0.001 if last_mid != 0 else 0.01

        # 最近 3 根的斜率
        slope_1 = m[-1] - m[-2]
        slope_2 = m[-2] - m[-3]
        slope_3 = m[-3] - m[-4]

        # 连续 3 根上升且斜率显著
        if slope_1 > threshold and slope_2 > threshold and slope_3 > threshold:
            return '中轨持续上行'
        # 连续 3 根下降且斜率显著
        if slope_1 < -threshold and slope_2 < -threshold and slope_3 < -threshold:
            return '中轨持续下行'

        # 拐头检测：前面下行，最近上行
        if slope_1 > threshold and slope_2 > 0 and slope_3 < -threshold:
            return '中轨拐头向上'
        if slope_1 > threshold and (slope_3 < -threshold or slope_2 < -threshold * 0.5):
            return '中轨拐头向上'

        # 拐头检测：前面上行，最近下行
        if slope_1 < -threshold and slope_2 < 0 and slope_3 > threshold:
            return '中轨拐头向下'
        if slope_1 < -threshold and (slope_3 > threshold or slope_2 > threshold * 0.5):
            return '中轨拐头向下'

        # 走平
        if abs(slope_1) <= threshold and abs(slope_2) <= threshold:
            return '中轨走平'

        # 微幅变化但不够显著
        if slope_1 > 0:
            return '中轨微幅上行'
        if slope_1 < 0:
            return '中轨微幅下行'
        return '中轨走平'

    # ------------------------------------------------------------------
    # 维度 4：轨道突破/回踩信号
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_signal(close: pd.Series, high: pd.Series, low: pd.Series,
                       upper: pd.Series, middle: pd.Series, lower: pd.Series) -> str:
        n = min(5, len(close) - 1)
        if n < 2:
            return '数据不足'

        signals = []
        for i in range(-n, 0):
            c_now = float(close.iloc[i])
            c_prev = float(close.iloc[i - 1])
            u_now = float(upper.iloc[i])
            u_prev = float(upper.iloc[i - 1])
            l_now = float(lower.iloc[i])
            l_prev = float(lower.iloc[i - 1])

            # 上轨突破
            if c_now > u_now and c_prev <= u_prev:
                signals.append('上轨突破')
            # 上轨回落
            if c_now <= u_now and c_prev > u_prev:
                signals.append('上轨回落')
            # 下轨跌破
            if c_now < l_now and c_prev >= l_prev:
                signals.append('下轨跌破')
            # 下轨企稳
            if c_now >= l_now and c_prev < l_prev:
                signals.append('下轨企稳')

        # 中轨支撑：近 3 日 low 触及中轨但 close 在中轨上方
        if len(close) >= 4:
            mid_support = True
            for i in range(-3, 0):
                lo = float(low.iloc[i])
                cl = float(close.iloc[i])
                mi = float(middle.iloc[i])
                # low 在中轨附近（误差 1%）且 close 在中轨上方
                if not (lo <= mi * 1.01 and cl > mi):
                    mid_support = False
                    break
            if mid_support:
                signals.append('中轨支撑')

        # 中轨失守：近 3 日从中轨上方跌到下方
        if len(close) >= 4:
            c_3ago = float(close.iloc[-4])
            m_3ago = float(middle.iloc[-4])
            c_last = float(close.iloc[-1])
            m_last = float(middle.iloc[-1])
            if c_3ago > m_3ago and c_last < m_last:
                signals.append('中轨失守')

        if signals:
            return '、'.join(dict.fromkeys(signals))
        return '无显著突破/回踩信号'

    # ------------------------------------------------------------------
    # 维度 5：布林线形态
    # ------------------------------------------------------------------

    @classmethod
    def _classify_pattern(cls, bandwidth: float, bw_ma: float,
                          mid_direction: str, percent_b: float,
                          close: pd.Series, upper: pd.Series,
                          lower: pd.Series, middle: pd.Series) -> str:
        is_expanding = bandwidth > bw_ma * 1.1 if bw_ma > 0 else False
        is_narrowing = bandwidth < bw_ma * 0.85 if bw_ma > 0 else False
        is_up = '上行' in mid_direction and '拐头' not in mid_direction
        is_down = '下行' in mid_direction and '拐头' not in mid_direction
        is_flat = '走平' in mid_direction

        # 沿上轨运行：%B > 0.8 连续 3 日以上
        if len(close) >= 4:
            upper_run = all(
                cls._calc_percent_b(float(close.iloc[i]),
                                     float(upper.iloc[i]),
                                     float(lower.iloc[i])) > 0.8
                for i in range(-3, 0)
            )
            lower_run = all(
                cls._calc_percent_b(float(close.iloc[i]),
                                     float(upper.iloc[i]),
                                     float(lower.iloc[i])) < 0.2
                for i in range(-3, 0)
            )
        else:
            upper_run = percent_b > 0.8
            lower_run = percent_b < 0.2

        # 开口扩张上行
        if is_expanding and is_up and percent_b > 0.7:
            return '布林开口上行（加速上涨）'
        # 开口扩张下行
        if is_expanding and is_down and percent_b < 0.3:
            return '布林开口下行（加速下跌）'
        # 收口蓄势
        if is_narrowing and (is_flat or (not is_up and not is_down)):
            return '布林收口（变盘临界）'
        # 沿上轨强势运行
        if upper_run:
            return '沿上轨强势运行'
        # 沿下轨弱势运行
        if lower_run:
            return '沿下轨弱势运行'
        # 向中轨回归：价格从极端位置回归
        if len(close) >= 3:
            prev_pb = cls._calc_percent_b(float(close.iloc[-3]),
                                           float(upper.iloc[-3]),
                                           float(lower.iloc[-3]))
            if (prev_pb > 0.85 and percent_b < 0.7) or (prev_pb < 0.15 and percent_b > 0.3):
                return '向中轨回归'
        return '常规运行'

    @staticmethod
    def _calc_percent_b(close: float, upper: float, lower: float) -> float:
        span = upper - lower
        return (close - lower) / span if span != 0 else 0.5

    # ------------------------------------------------------------------
    # 跨级别共振分析
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_cross_level(boll_multi: Dict) -> Dict[str, Any]:
        """分析多级别布林线跨级别共振，输出共振状态 + 长短博弈 + 动态分析提示。"""
        levels: List[Dict] = []
        for key in ['monthly', 'weekly', 'daily']:
            if key in boll_multi:
                levels.append(boll_multi[key])

        if not levels:
            return {'resonance_state': '数据不足', 'battle_analysis': '', 'analysis_prompt': ''}

        # ---- 共振状态 ----
        all_mid_up = all('上行' in lv['mid_direction'] and '拐头' not in lv['mid_direction'] for lv in levels)
        all_mid_down = all('下行' in lv['mid_direction'] and '拐头' not in lv['mid_direction'] for lv in levels)
        all_narrowing = all('收窄' in lv['channel_width'] for lv in levels)
        all_upper_half = all(lv['percent_b'] > 0.5 for lv in levels)
        all_lower_half = all(lv['percent_b'] < 0.5 for lv in levels)

        if all_mid_up and all_upper_half:
            resonance_state = '所有级别中轨上行且价格在上半通道'
        elif all_mid_down and all_lower_half:
            resonance_state = '所有级别中轨下行且价格在下半通道'
        elif all_narrowing:
            resonance_state = '多级别通道同步收窄，大变盘临界'
        else:
            parts = []
            for lv in levels:
                dir_short = lv['mid_direction'].split('（')[0]
                pos_short = lv['price_position'].split('（')[0]
                parts.append(f"{lv['level']}{dir_short}+{pos_short}")
            resonance_state = f"各级别方向分歧（{'、'.join(parts)}）"

        # ---- 长短博弈 ----
        long_key = 'monthly' if 'monthly' in boll_multi else ('weekly' if 'weekly' in boll_multi else None)
        short_key = 'daily' if 'daily' in boll_multi else None

        battle_analysis = '各级别通道无显著矛盾'

        if long_key and short_key:
            long_lv = boll_multi[long_key]
            short_lv = boll_multi[short_key]
            long_pattern = long_lv['pattern']
            short_pattern = short_lv['pattern']

            long_up = '开口上行' in long_pattern or '沿上轨' in long_pattern
            long_down = '开口下行' in long_pattern or '沿下轨' in long_pattern
            long_squeeze = '收口' in long_pattern
            short_up = '开口上行' in short_pattern or '沿上轨' in short_pattern
            short_down = '开口下行' in short_pattern or '沿下轨' in short_pattern
            short_squeeze = '收口' in short_pattern or '回归' in short_pattern

            if long_up and short_up:
                battle_analysis = '长短共振上行，趋势加速'
            elif long_up and short_squeeze:
                battle_analysis = (
                    f"大趋势向好（{long_lv['level']}{long_pattern}），"
                    f"短线进入整理（{short_lv['level']}{short_pattern}），关注中轨支撑"
                )
            elif long_up and short_down:
                battle_analysis = (
                    f"长短分化：{long_lv['level']}开口上行（{long_pattern}），"
                    f"{short_lv['level']}开口下行（{short_pattern}）"
                )
            elif long_squeeze and short_up:
                battle_analysis = (
                    f"短线率先选择方向向上（{short_lv['level']}{short_pattern}），"
                    f"关注能否带动{long_lv['level']}共振突破"
                )
            elif long_squeeze and short_squeeze:
                battle_analysis = '多级别蓄势，即将迎来方向选择'
            elif long_down and short_up:
                battle_analysis = (
                    f"{long_lv['level']}开口下行（{long_pattern}），"
                    f"{short_lv['level']}开口上行（{short_pattern}）"
                )
            elif long_down and short_down:
                battle_analysis = f"长短共振下行"
            elif long_down and short_squeeze:
                battle_analysis = (
                    f"大趋势偏空（{long_lv['level']}{long_pattern}），"
                    f"短线波动收窄（{short_lv['level']}{short_pattern}），关注变盘方向"
                )
            else:
                battle_analysis = (
                    f"{long_lv['level']}：{long_pattern}；"
                    f"{short_lv['level']}：{short_pattern}，方向待明确"
                )

        # ---- 动态分析提示 ----
        if all_mid_up and all_upper_half:
            analysis_prompt = (
                "请评估布林通道多级别上行的持续性，"
                "关注上轨压力和通道是否有收窄迹象。"
            )
        elif all_mid_down and all_lower_half:
            analysis_prompt = (
                "请评估布林通道多级别下行的动能变化，"
                "关注下轨支撑和通道宽度变化。"
            )
        elif all_narrowing:
            analysis_prompt = (
                "布林通道多级别同步收窄，请结合量价分析变盘方向的概率。"
            )
        else:
            analysis_prompt = (
                "请分析长线与短线布林通道方向分歧的含义。"
            )

        return {
            'resonance_state': resonance_state,
            'battle_analysis': battle_analysis,
            'analysis_prompt': analysis_prompt,
        }
