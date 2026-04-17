"""
均线系统（MA）多周期结构与趋势分析服务

提供短期（MA5/MA10）、中期（MA20/MA60）、长期（MA120）三个层级的均线状态分析：
- 各周期均线排列形态（多头/空头/交叉）
- 价格相对位置（支撑/阻力判定）
- 跨周期空间结构提取（整体趋势 + 短期异动 + 核心博弈点）
- 动态分析提示

从 StockDataCollectionService 提取，供技术指标收集和 LangChain Tool 使用。
"""

from typing import Dict, Any, Optional, List


class MaAnalysisService:
    """均线系统多周期分析服务（纯计算，无 IO）。"""

    # 三组均线定义：(组名, 级别标签, 包含的均线周期)
    _GROUPS = [
        ('short', '短期', [5, 10]),
        ('mid', '中期', [20, 60]),
        ('long', '长期', [120]),
    ]

    # 各周期级别的排列形态描述词
    _LEVEL_DESC = {
        '短期': {'bullish': '短线反弹', 'bearish': '短线走弱'},
        '中期': {'bullish': '中线走强', 'bearish': '中线弱势'},
        '长期': {'bullish': '长线多头确认', 'bearish': '长线空头格局'},
    }

    @classmethod
    def analyze(cls, ma_values: Dict[str, Optional[float]],
                last_close: Optional[float]) -> Optional[Dict[str, Any]]:
        """对均线数据进行多周期结构分析。

        Args:
            ma_values: {'ma5': float, 'ma10': float, ...}，值可为 None。
            last_close: 最新收盘价。

        Returns:
            分析结果字典，数据不足时返回 None。
        """
        if last_close is None:
            return None

        # 至少需要 MA5 和 MA20 才有意义
        if ma_values.get('ma5') is None or ma_values.get('ma20') is None:
            return None

        close = float(last_close)
        result: Dict[str, Any] = {'close': round(close, 2)}

        # ---- 各周期状态切片 ----
        slices = []
        for group_key, level_label, periods in cls._GROUPS:
            vals = {p: ma_values.get(f'ma{p}') for p in periods}
            # 跳过全部无数据的组
            if all(v is None for v in vals.values()):
                continue
            slices.append(cls._compute_group_status(level_label, periods, vals, close))
        result['slices'] = slices

        # ---- 跨周期空间结构 ----
        result['structure'] = cls._analyze_structure(ma_values, close)

        # ---- 均线收敛度与乖离率 ----
        result['convergence'] = cls._analyze_convergence(ma_values, close)

        return result

    # ------------------------------------------------------------------
    # 单组均线状态
    # ------------------------------------------------------------------

    @classmethod
    def _compute_group_status(cls, level: str, periods: List[int],
                              vals: Dict[int, Optional[float]],
                              close: float) -> Dict[str, Any]:
        """计算一组均线的排列形态和价格相对位置。"""
        names = ', '.join(f'MA{p}' for p in periods)
        valid = {p: v for p, v in vals.items() if v is not None}

        # 排列形态
        arrangement = cls._detect_arrangement(periods, vals, close, level)

        # 价格相对位置
        position = cls._detect_position(periods, vals, close)

        # 关键数值
        value_str = ', '.join(
            f'MA{p}={round(v, 2)}' for p, v in sorted(valid.items())
        )

        return {
            'level': level,
            'names': names,
            'arrangement': arrangement,
            'position': position,
            'values': value_str,
        }

    @staticmethod
    def _detect_arrangement(periods: List[int], vals: Dict[int, Optional[float]],
                            close: float, level: str = '短期') -> str:
        """检测均线排列形态。"""
        valid = [(p, vals[p]) for p in periods if vals.get(p) is not None]
        if not valid:
            return '数据不足'

        if len(valid) == 1:
            p, v = valid[0]
            if close > v:
                return f'价格站上 MA{p}（偏多）'
            else:
                return f'价格低于 MA{p}（偏空）'

        desc = MaAnalysisService._LEVEL_DESC.get(level, MaAnalysisService._LEVEL_DESC['短期'])

        # 两条均线的情况
        p1, v1 = valid[0]  # 短周期
        p2, v2 = valid[1]  # 长周期

        if v1 > v2:
            return f'金叉向上（{desc["bullish"]}）' if close > v1 else '金叉但价格未站稳'
        elif v1 < v2:
            return f'空头排列（{desc["bearish"]}）' if close < v1 else '死叉但价格尚在上方'
        else:
            return '均线黏合（方向待选择）'

    @staticmethod
    def _detect_position(periods: List[int], vals: Dict[int, Optional[float]],
                         close: float) -> str:
        """检测价格相对均线的支撑/阻力关系。"""
        valid = [(p, vals[p]) for p in periods if vals.get(p) is not None]
        if not valid:
            return '数据不足'

        above = [p for p, v in valid if close > v]
        below = [p for p, v in valid if close <= v]

        if above and not below:
            names = ' 与 '.join(f'MA{p}' for p in above)
            return f'价格站上 {names}（受均线支撑）'
        elif below and not above:
            names = ' 与 '.join(f'MA{p}' for p in below)
            return f'价格低于 {names}（受均线压制）'
        else:
            above_names = '/'.join(f'MA{p}' for p in above)
            below_names = '/'.join(f'MA{p}' for p in below)
            return f'站上 {above_names}，受压于 {below_names}'

    # ------------------------------------------------------------------
    # 跨周期空间结构
    # ------------------------------------------------------------------

    @classmethod
    def _analyze_structure(cls, ma_vals: Dict[str, Optional[float]],
                           close: float) -> Dict[str, Any]:
        """提取均线的整体趋势、短期异动、核心博弈点、动态分析提示。"""

        ma5 = ma_vals.get('ma5')
        ma10 = ma_vals.get('ma10')
        ma20 = ma_vals.get('ma20')
        ma60 = ma_vals.get('ma60')
        ma120 = ma_vals.get('ma120')

        # ---- 整体趋势 ----
        trend = cls._detect_overall_trend(ma5, ma10, ma20, ma60, ma120)

        # ---- 短期异动 ----
        short_signal = cls._detect_short_signal(close, ma5, ma10, ma20)

        # ---- 核心博弈点（最近的阻力/支撑） ----
        battle_point = cls._detect_battle_point(close, ma_vals)

        # ---- 动态分析提示 ----
        analysis_prompt = cls._generate_prompt(trend, short_signal, battle_point, close, ma_vals)

        return {
            'trend': trend,
            'short_signal': short_signal,
            'battle_point': battle_point,
            'analysis_prompt': analysis_prompt,
        }

    @staticmethod
    def _detect_overall_trend(ma5, ma10, ma20, ma60, ma120) -> str:
        """判断均线系统的整体趋势。"""
        # 收集有效的长周期均线（MA20/60/120）判断大方向
        long_mas = []
        if ma20 is not None:
            long_mas.append(('MA20', ma20))
        if ma60 is not None:
            long_mas.append(('MA60', ma60))
        if ma120 is not None:
            long_mas.append(('MA120', ma120))

        if len(long_mas) < 2:
            return '长周期均线数据不足，无法判断整体趋势'

        # 检查是否多头排列（短均线 > 长均线）
        values = [v for _, v in long_mas]
        is_bullish = all(values[i] >= values[i + 1] for i in range(len(values) - 1))
        is_bearish = all(values[i] <= values[i + 1] for i in range(len(values) - 1))

        if is_bullish:
            names = ' > '.join(n for n, _ in long_mas)
            return f'大级别处于多头趋势中（{names}）'
        elif is_bearish:
            names = ' < '.join(n for n, _ in long_mas)
            return f'大级别处于空头趋势中（{names}）'
        else:
            return '中长期均线交织，趋势不明朗'

    @staticmethod
    def _detect_short_signal(close, ma5, ma10, ma20) -> str:
        """检测短期均线异动信号。"""
        if ma5 is None or ma10 is None:
            return '短期均线数据不足'

        signals = []

        # MA5 上穿 MA10
        if ma5 > ma10:
            if close > ma5:
                signals.append('短期均线金叉向上，价格站上 MA5/MA10')
            else:
                signals.append('短期均线金叉，但价格尚未站稳')
        elif ma5 < ma10:
            if close < ma5:
                signals.append('短期均线死叉向下，价格跌破 MA5/MA10')
            else:
                signals.append('短期均线死叉，但价格仍在上方')
        else:
            signals.append('MA5 与 MA10 黏合，短线方向待选择')

        # 与 MA20 的关系
        if ma20 is not None:
            if ma5 > ma10 and close < ma20:
                signals.append('短线回暖但受 MA20 压制')
            elif ma5 < ma10 and close > ma20:
                signals.append('短线走弱但 MA20 仍有支撑')

        return '；'.join(signals) if signals else '短期均线无明显异动'

    @classmethod
    def _detect_battle_point(cls, close: float,
                             ma_vals: Dict[str, Optional[float]]) -> str:
        """找出当前价格最近的阻力位和支撑位。"""
        resistances = []  # 价格上方的均线（阻力）
        supports = []     # 价格下方的均线（支撑）

        for period in [5, 10, 20, 60, 120]:
            v = ma_vals.get(f'ma{period}')
            if v is None:
                continue
            if v > close:
                resistances.append((f'MA{period}', round(v, 2)))
            elif v < close:
                supports.append((f'MA{period}', round(v, 2)))
            # v == close 视为支撑

        parts = []

        if resistances:
            # 最近的阻力（价格最接近的）
            nearest_r = min(resistances, key=lambda x: x[1] - close)
            pct = round((nearest_r[1] - close) / close * 100, 1)
            parts.append(f'上方最近阻力位: {nearest_r[0]}({nearest_r[1]})，距当前价 +{pct}%')

        if supports:
            # 最近的支撑（价格最接近的）
            nearest_s = max(supports, key=lambda x: x[1])
            pct = round((close - nearest_s[1]) / close * 100, 1)
            parts.append(f'下方最近支撑位: {nearest_s[0]}({nearest_s[1]})，距当前价 -{pct}%')

        if not resistances and supports:
            parts.append('价格已突破所有均线阻力，处于多头发散状态')
        elif not supports and resistances:
            parts.append('价格跌破所有均线支撑，处于空头发散状态')

        return '；'.join(parts) if parts else '均线数据不足，无法判断支撑/阻力'

    @staticmethod
    def _generate_prompt(trend: str, short_signal: str,
                         battle_point: str, close: float,
                         ma_vals: Dict[str, Optional[float]]) -> str:
        """根据均线状态动态生成分析提示。"""
        is_bearish_trend = '空头' in trend
        is_bullish_trend = '多头' in trend
        short_bullish = '金叉' in short_signal or '站上' in short_signal
        short_bearish = '死叉' in short_signal or '跌破' in short_signal

        if is_bullish_trend and short_bullish:
            return (
                '请结合上述均线多头排列结构，评估当前多头趋势的延续性，'
                '关注短期均线是否出现走平或拐头迹象，并给出操作建议（持股待涨、逢回调加仓等）。'
            )
        elif is_bullish_trend and short_bearish:
            ma20 = ma_vals.get('ma20')
            ref = f'MA20({round(ma20, 2)})' if ma20 else 'MA20'
            return (
                f'请结合上述均线结构，评估短期死叉是否只是上升趋势中的正常回调。'
                f'重点关注 {ref} 的支撑有效性，给出操作建议（逢低加仓、破位止损等）。'
            )
        elif is_bearish_trend and short_bullish:
            # 找最近阻力
            nearest = None
            for p in [20, 60, 120]:
                v = ma_vals.get(f'ma{p}')
                if v is not None and v > close:
                    nearest = f'MA{p}({round(v, 2)})'
                    break
            ref = nearest or 'MA20'
            return (
                f'请结合上述均线的多空排列结构，评估当前价格站上短期均线的有效性。'
                f'这是一次短线的诱多反抽，还是具备向上挑战 {ref} 潜力的底部结构？'
            )
        elif is_bearish_trend and short_bearish:
            return (
                '请结合上述均线全面空头排列，评估下跌趋势是否有减速迹象，'
                '并给出操作建议（空仓观望、关注超跌反弹信号等）。'
            )
        else:
            return (
                '请结合上述均线结构，分析当前趋势方向的明确程度，'
                '并给出操作建议（区间操作、等待方向选择后再介入等）。'
            )

    # ------------------------------------------------------------------
    # 均线收敛度与乖离率
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_convergence(ma_vals: Dict[str, Optional[float]],
                             close: float) -> Dict[str, Any]:
        """分析短中期均线收敛程度和价格乖离率。

        收敛度 = MA5/MA10/MA20 三条均线的极差 / MA20，衡量均线是否高度纠缠。
        乖离率 = (close - MA20) / MA20 * 100，衡量价格偏离均线的程度。
        """
        result: Dict[str, Any] = {}

        ma5 = ma_vals.get('ma5')
        ma10 = ma_vals.get('ma10')
        ma20 = ma_vals.get('ma20')

        # 乖离率（BIAS20）
        if ma20 is not None and ma20 != 0:
            bias20 = round((close - ma20) / ma20 * 100, 2)
            result['bias20'] = bias20
            if bias20 > 8:
                result['bias_desc'] = f'价格大幅偏离 MA20（乖离率 +{bias20}%），存在技术性回调需求'
            elif bias20 > 4:
                result['bias_desc'] = f'价格偏离 MA20 较多（乖离率 +{bias20}%），关注回踩风险'
            elif bias20 < -8:
                result['bias_desc'] = f'价格大幅偏离 MA20（乖离率 {bias20}%），存在超跌反弹需求'
            elif bias20 < -4:
                result['bias_desc'] = f'价格偏离 MA20 较多（乖离率 {bias20}%），关注反弹机会'
            else:
                result['bias_desc'] = f'价格围绕 MA20 运行（乖离率 {bias20}%），处于正常水平'

        # 收敛度
        if all(v is not None for v in [ma5, ma10, ma20]):
            ma_max = max(ma5, ma10, ma20)
            ma_min = min(ma5, ma10, ma20)
            spread = ma_max - ma_min
            convergence = round(spread / ma20 * 100, 2) if ma20 != 0 else 0
            result['convergence_pct'] = convergence
            if convergence < 1.0:
                result['convergence_desc'] = (
                    f'MA5/MA10/MA20 高度黏合（极差仅 {convergence}%），均线纠缠蓄势，'
                    f'一旦放量突破将引发大级别方向选择'
                )
            elif convergence < 2.5:
                result['convergence_desc'] = f'MA5/MA10/MA20 较为收敛（极差 {convergence}%），方向待选择'
            elif convergence > 8:
                result['convergence_desc'] = f'MA5/MA10/MA20 大幅发散（极差 {convergence}%），趋势强烈运行中'
            elif convergence > 5:
                result['convergence_desc'] = f'MA5/MA10/MA20 明显发散（极差 {convergence}%），趋势明确'
            else:
                result['convergence_desc'] = f'MA5/MA10/MA20 正常展开（极差 {convergence}%）'

        return result
