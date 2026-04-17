"""
RSI 多周期超买超卖与背离分析服务

提供三个层级的 RSI 分析：
- 各周期 RSI 状态切片（超买超卖区间、趋势方向、背离信号）
- 跨周期核心逻辑提取（多周期共振、长短分歧、极值位置）
- 动态分析提示

从 StockDataCollectionService 提取，供技术指标收集和 LangChain Tool 使用。
"""

from typing import Dict, Any, Optional, List

import pandas as pd


class RsiAnalysisService:
    """RSI 多周期分析服务（纯计算，无 IO）。"""

    _PERIODS = [
        (7, '短线'),
        (14, '中线'),
        (21, '长线'),
    ]

    @classmethod
    def analyze(cls, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """对日线 DataFrame 进行多周期 RSI 分析。

        Args:
            df: 日线 DataFrame，需含 close 列，index 为日期，按时间升序排列。

        Returns:
            RSI 分析结果字典，数据不足时返回 None。
        """
        if df is None or df.empty or len(df) < 30:
            return None

        try:
            close = df['close'].astype(float)
        except (KeyError, ValueError):
            return None

        # 计算各周期 RSI 序列
        rsi_series: Dict[int, pd.Series] = {}
        for period, _ in cls._PERIODS:
            s = cls._calc_rsi_series(close, period)
            if s is not None:
                rsi_series[period] = s

        if not rsi_series:
            return None

        # ---- 各周期状态切片 ----
        slices = []
        for period, label in cls._PERIODS:
            if period not in rsi_series:
                continue
            slices.append(cls._compute_period_status(
                close, rsi_series[period], period, label
            ))

        if not slices:
            return None

        result: Dict[str, Any] = {'slices': slices}

        # ---- 跨周期核心逻辑提取 ----
        result['cross_period'] = cls._analyze_cross_period(slices)

        # ---- 动态分析提示 ----
        result['analysis_prompt'] = cls._generate_prompt(slices, result['cross_period'])

        return result

    # ------------------------------------------------------------------
    # RSI 序列计算
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_rsi_series(close: pd.Series, period: int) -> Optional[pd.Series]:
        """计算完整的 RSI 时间序列。"""
        if len(close) < period + 1:
            return None
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, float('nan'))
        rsi = 100 - 100 / (1 + rs)
        # loss 为 0 时 RSI = 100
        rsi = rsi.fillna(100.0)
        return rsi

    # ------------------------------------------------------------------
    # 单周期状态
    # ------------------------------------------------------------------

    @classmethod
    def _compute_period_status(cls, close: pd.Series, rsi: pd.Series,
                                period: int, label: str) -> Dict[str, Any]:
        """计算单个周期的 RSI 完整状态。"""
        last_rsi = float(rsi.iloc[-1])

        # 1. 超买超卖区间定性
        zone = cls._classify_zone(last_rsi)

        # 2. 趋势方向
        trend = cls._detect_trend(rsi)

        # 3. 背离信号
        divergence = cls._detect_divergence(close, rsi, last_rsi)

        return {
            'period': period,
            'label': label,
            'rsi_value': round(last_rsi, 1),
            'zone': zone,
            'trend': trend,
            'divergence': divergence,
        }

    @staticmethod
    def _classify_zone(rsi: float) -> str:
        """RSI 超买超卖区间定性。"""
        if rsi > 80:
            return '超买'
        if rsi > 60:
            return '偏强'
        if rsi > 40:
            return '中性'
        if rsi > 20:
            return '弱势'
        return '超卖'

    @staticmethod
    def _detect_trend(rsi: pd.Series) -> str:
        """检测 RSI 近期趋势方向。"""
        if len(rsi) < 5:
            return '数据不足'

        recent = rsi.iloc[-5:]
        valid = recent.dropna()
        if len(valid) < 3:
            return '数据不足'

        # 计算近期斜率：比较最近3个值的走向
        v1, v2, v3 = float(valid.iloc[-3]), float(valid.iloc[-2]), float(valid.iloc[-1])

        up_count = int(v2 > v1) + int(v3 > v2)
        down_count = int(v2 < v1) + int(v3 < v2)

        if up_count == 2:
            # 连续上行
            diff = v3 - v1
            if diff > 5:
                return 'RSI 快速上行'
            return 'RSI 连续上行'
        if down_count == 2:
            diff = v1 - v3
            if diff > 5:
                return 'RSI 快速下行'
            return 'RSI 连续下行'
        return 'RSI 走平'

    @classmethod
    def _detect_divergence(cls, close: pd.Series, rsi: pd.Series,
                           last_rsi: float) -> str:
        """检测 RSI 顶背离/底背离信号。

        约束：
        - 顶背离仅在 RSI > 40 时检测（弱势区不可能出现有效顶背离）
        - 底背离仅在 RSI < 60 时检测（强势区不可能出现有效底背离）
        - 两个极值点间距 >= 5 根 K 线
        - 价格变化幅度 >= 1%
        """
        if len(close) < 60 or len(rsi) < 60:
            return '无'

        check_top = last_rsi > 40
        check_bottom = last_rsi < 60

        if not check_top and not check_bottom:
            return '无'

        c = close.iloc[-60:].values
        r = rsi.iloc[-60:].values

        min_gap = 5
        min_pct = 0.01

        # 顶背离：价格创新高但 RSI 未创新高
        if check_top:
            highs = []
            for i in range(2, len(c) - 2):
                if (c[i] > c[i - 1] and c[i] > c[i - 2]
                        and c[i] > c[i + 1] and c[i] > c[i + 2]):
                    highs.append(i)

            if len(highs) >= 2:
                for j in range(len(highs) - 1, 0, -1):
                    h2 = highs[j]
                    h1 = highs[j - 1]
                    if h2 - h1 < min_gap:
                        continue
                    if c[h1] > 0 and abs(c[h2] - c[h1]) / c[h1] < min_pct:
                        continue
                    r1, r2 = float(r[h1]), float(r[h2])
                    if pd.isna(r1) or pd.isna(r2):
                        continue
                    if c[h2] > c[h1] and r2 < r1:
                        return '顶背离（价格新高但 RSI 走低）'
                    break

        # 底背离：价格创新低但 RSI 未创新低
        if check_bottom:
            lows = []
            for i in range(2, len(c) - 2):
                if (c[i] < c[i - 1] and c[i] < c[i - 2]
                        and c[i] < c[i + 1] and c[i] < c[i + 2]):
                    lows.append(i)

            if len(lows) >= 2:
                for j in range(len(lows) - 1, 0, -1):
                    l2 = lows[j]
                    l1 = lows[j - 1]
                    if l2 - l1 < min_gap:
                        continue
                    if c[l1] > 0 and abs(c[l2] - c[l1]) / c[l1] < min_pct:
                        continue
                    r1, r2 = float(r[l1]), float(r[l2])
                    if pd.isna(r1) or pd.isna(r2):
                        continue
                    if c[l2] < c[l1] and r2 > r1:
                        return '底背离（价格新低但 RSI 走高）'
                    break

        return '无'

    # ------------------------------------------------------------------
    # 跨周期核心逻辑提取
    # ------------------------------------------------------------------

    @classmethod
    def _analyze_cross_period(cls, slices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析跨周期 RSI 共振、长短分歧、极值位置。"""
        result: Dict[str, Any] = {}

        zones = [s['zone'] for s in slices]
        rsi_values = [s['rsi_value'] for s in slices]

        # ---- 多周期共振 ----
        all_overbought = all(z in ('超买', '偏强') for z in zones)
        all_oversold = all(z in ('超卖', '弱势') for z in zones)
        all_extreme_ob = all(z == '超买' for z in zones)
        all_extreme_os = all(z == '超卖' for z in zones)

        if all_extreme_ob:
            resonance = '多周期同步超买（RSI 均>80），强烈见顶预警'
        elif all_extreme_os:
            resonance = '多周期同步超卖（RSI 均<20），强烈见底信号'
        elif all_overbought:
            resonance = '多周期共振偏强（RSI 均>60），多头格局延续'
        elif all_oversold:
            resonance = '多周期共振偏弱（RSI 均<40），空头格局延续'
        else:
            # 检查是否有单个周期处于极端值
            any_extreme_ob = any(s['rsi_value'] > 80 for s in slices)
            any_extreme_os = any(s['rsi_value'] < 20 for s in slices)
            if any_extreme_ob:
                extreme_items = [f"RSI{s['period']}({s['rsi_value']})" for s in slices if s['rsi_value'] > 80]
                resonance = (
                    f"各周期 RSI 方向分歧，多空博弈中。"
                    f"⚠️ 短线风险提示：{'/'.join(extreme_items)} 已进入超买区，短线有技术性回调诉求"
                )
            elif any_extreme_os:
                extreme_items = [f"RSI{s['period']}({s['rsi_value']})" for s in slices if s['rsi_value'] < 20]
                resonance = (
                    f"各周期 RSI 方向分歧，多空博弈中。"
                    f"短线机会提示：{'/'.join(extreme_items)} 已进入超卖区，短线存在技术性反弹需求"
                )
            else:
                resonance = '各周期 RSI 方向分歧，多空博弈中'
        result['resonance'] = resonance

        # ---- 长短分歧 ----
        if len(slices) >= 2:
            short_s = slices[0]  # RSI7
            long_s = slices[-1]  # RSI21
            short_zone = short_s['zone']
            long_zone = long_s['zone']

            if long_zone in ('弱势', '超卖') and short_zone in ('偏强', '超买', '中性'):
                if short_s['rsi_value'] > long_s['rsi_value'] + 10:
                    result['divergence_analysis'] = (
                        f"长线弱势(RSI{long_s['period']}={long_s['rsi_value']})但短线回暖"
                        f"(RSI{short_s['period']}={short_s['rsi_value']})，"
                        f"属于超跌反弹结构，反弹高度可能受限"
                    )
            elif long_zone in ('偏强', '超买') and short_zone in ('弱势', '超卖', '中性'):
                if long_s['rsi_value'] > short_s['rsi_value'] + 10:
                    result['divergence_analysis'] = (
                        f"长线偏强(RSI{long_s['period']}={long_s['rsi_value']})但短线回落"
                        f"(RSI{short_s['period']}={short_s['rsi_value']})，"
                        f"属于强势回调，回调后有望延续上行"
                    )

        # ---- 极值位置 ----
        extreme_parts = []
        for s in slices:
            if s['rsi_value'] > 85:
                extreme_parts.append(
                    f"⚠️ RSI{s['period']}({s['rsi_value']}) 进入极端超买区(>85)，"
                    f"短线有强烈的技术性回调诉求"
                )
            elif s['rsi_value'] > 80:
                extreme_parts.append(
                    f"⚠️ RSI{s['period']}({s['rsi_value']}) 已进入超买区(>80)，"
                    f"短线面临技术性回调压力"
                )
            elif s['rsi_value'] < 15:
                extreme_parts.append(
                    f"RSI{s['period']}({s['rsi_value']}) 进入极端超卖区(<15)，"
                    f"历史上反弹概率极高"
                )
            elif s['rsi_value'] < 20:
                extreme_parts.append(
                    f"RSI{s['period']}({s['rsi_value']}) 已进入超卖区(<20)，"
                    f"短线存在技术性反弹需求"
                )
        if extreme_parts:
            result['extreme_warning'] = '；'.join(extreme_parts)

        # ---- 背离汇总 ----
        div_parts = []
        for s in slices:
            if '背离' in s['divergence']:
                div_parts.append(f"⚠ RSI{s['period']}{s['divergence']}")
        if div_parts:
            result['divergence_signals'] = '；'.join(div_parts)

        return result

    # ------------------------------------------------------------------
    # 动态分析提示
    # ------------------------------------------------------------------

    @classmethod
    def _generate_prompt(cls, slices: List[Dict[str, Any]],
                         cross_period: Dict[str, Any]) -> str:
        """根据 RSI 状态动态生成分析提示。"""
        resonance = cross_period.get('resonance', '')
        has_divergence = any('背离' in s['divergence'] for s in slices)
        has_extreme = 'extreme_warning' in cross_period

        if '同步超买' in resonance:
            return (
                '请结合上述 RSI 多周期同步超买状态，评估当前是否面临短期回调风险，'
                '分析在强趋势中 RSI 钝化的可能性，并给出操作建议（减仓、止盈、等待 RSI 拐头确认等）。'
            )
        if '同步超卖' in resonance:
            return (
                '请结合上述 RSI 多周期同步超卖状态，评估当前是否已接近底部区域，'
                '并给出操作建议（分批建仓、等待 RSI 拐头、观察量能配合等）。'
            )
        if has_extreme:
            return (
                '请结合上述 RSI 极端值预警，分析当前极端超买/超卖状态的持续性，'
                '评估 RSI 回归均值的时间窗口，并给出操作建议。'
            )
        if has_divergence:
            return (
                '请结合上述 RSI 背离信号，评估背离的有效性和可靠程度，'
                '分析价格是否可能出现反转，并给出操作建议。'
            )
        if '分歧' in resonance:
            divergence_analysis = cross_period.get('divergence_analysis', '')
            if '超跌反弹' in divergence_analysis:
                return (
                    '请结合上述 RSI 长短分歧（长线弱势但短线回暖），'
                    '评估当前反弹的力度和持续性，并给出操作建议（轻仓试探、设置止损等）。'
                )
            if '强势回调' in divergence_analysis:
                return (
                    '请结合上述 RSI 长短分歧（长线偏强但短线回落），'
                    '评估回调的深度和支撑位，并给出操作建议（逢低加仓、等待 RSI 企稳等）。'
                )
            return (
                '请结合上述各周期 RSI 状态，分析多空博弈的方向选择概率，'
                '并给出操作建议（观望、区间操作、等待方向明确等）。'
            )
        if '偏强' in resonance:
            return (
                '请结合上述 RSI 多周期共振偏强状态，评估多头趋势的延续性，'
                '关注是否有动能衰减或超买风险，并给出操作建议。'
            )
        if '偏弱' in resonance:
            return (
                '请结合上述 RSI 多周期共振偏弱状态，评估空头趋势是否有见底迹象，'
                '并给出操作建议（空仓观望、等待超卖信号等）。'
            )
        return (
            '请结合上述 RSI 各周期状态，分析当前超买超卖程度和趋势方向，'
            '并给出操作建议。'
        )
