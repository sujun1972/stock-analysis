"""
MACD 多级别动能与趋势分析服务

提供月线、周线、日线三个级别的 MACD 状态分析，包括：
- 零轴位置（定多空）
- 交叉状态（定买卖）
- 柱体动能（定力度）
- 结构形态 / 背离信号（定反转）
- 跨级别共振 / 冲突分析

从 StockDataCollectionService 提取，供技术指标收集和 LangChain Tool 使用。
"""

from typing import Dict, Any, Optional

import pandas as pd
from loguru import logger


class MacdAnalysisService:
    """MACD 多级别分析服务（纯计算，无 IO）。"""

    @classmethod
    def analyze_multi_level(cls, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """对日线 DataFrame 进行多级别 MACD 分析。

        Args:
            df: 日线 OHLCV DataFrame，index 为日期，需含 open/high/low/close/volume/pct_change。

        Returns:
            多级别 MACD 分析结果字典，数据不足时返回 None。
        """
        close = df['close'].astype(float)
        macd_multi: Dict[str, Any] = {}

        # 日线 MACD
        if len(close) >= 35:
            macd_multi['daily'] = cls._compute_macd_status(df, '日线')

        # 周线 MACD（日线重采样）
        weekly_df = cls._resample_ohlcv(df, 'W')
        if weekly_df is not None and len(weekly_df) >= 35:
            macd_multi['weekly'] = cls._compute_macd_status(weekly_df, '周线')

        # 月线 MACD（日线重采样）
        monthly_df = cls._resample_ohlcv(df, 'ME')
        if monthly_df is not None and len(monthly_df) >= 35:
            macd_multi['monthly'] = cls._compute_macd_status(monthly_df, '月线')

        # 跨级别共振分析
        if macd_multi:
            macd_multi['cross_level'] = cls._analyze_cross_level_resonance(macd_multi)

        return macd_multi if macd_multi else None

    # ------------------------------------------------------------------
    # 重采样
    # ------------------------------------------------------------------

    @staticmethod
    def _resample_ohlcv(df: pd.DataFrame, freq: str) -> Optional[pd.DataFrame]:
        """将日线 OHLCV DataFrame 重采样为周线/月线。"""
        try:
            ohlcv = df[['open', 'high', 'low', 'close', 'volume', 'pct_change']].copy()
            ohlcv.index = pd.to_datetime(ohlcv.index)
            resampled = ohlcv.resample(freq).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
                'pct_change': 'sum',
            }).dropna(subset=['close'])
            return resampled if len(resampled) >= 5 else None
        except Exception as e:
            logger.warning(f"OHLCV 重采样失败({freq}): {e}")
            return None

    # ------------------------------------------------------------------
    # 单级别 MACD 状态
    # ------------------------------------------------------------------

    @classmethod
    def _compute_macd_status(cls, df: pd.DataFrame, level_name: str) -> Dict[str, Any]:
        """计算单个时间级别的 MACD 完整状态（零轴位置、交叉状态、柱体动能、背离信号）。"""
        close = df['close'].astype(float)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd_bar = (dif - dea) * 2

        last_dif = float(dif.iloc[-1])
        last_dea = float(dea.iloc[-1])
        last_bar = float(macd_bar.iloc[-1])

        # 1. 零轴位置
        threshold = max(abs(last_dif), abs(last_dea)) * 0.1 + 0.01
        if last_dif > threshold and last_dea > threshold:
            zero_axis = '零轴上方（强势）'
        elif last_dif < -threshold and last_dea < -threshold:
            zero_axis = '零轴下方（弱势）'
        else:
            zero_axis = '零轴附近（变盘期）'

        # 2. 交叉状态
        cross_state = cls._detect_cross_state(dif, dea)

        # 3. 柱体动能
        bar_momentum = cls._detect_bar_momentum(macd_bar)

        # 4. 背离信号（结合零轴位置过滤不合理的背离）
        divergence = cls._detect_divergence(close, dif, macd_bar, zero_axis)

        return {
            'level': level_name,
            'dif': round(last_dif, 3),
            'dea': round(last_dea, 3),
            'macd_bar': round(last_bar, 3),
            'zero_axis': zero_axis,
            'cross_state': cross_state,
            'bar_momentum': bar_momentum,
            'divergence': divergence,
        }

    # ------------------------------------------------------------------
    # 交叉状态检测
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_cross_state(dif: pd.Series, dea: pd.Series) -> str:
        """检测 MACD 交叉状态：金叉/死叉/趋于黏合/拒绝死叉/拒绝金叉。"""
        if len(dif) < 5:
            return '数据不足'

        diff = dif - dea
        last_diff = float(diff.iloc[-1])
        prev_diff = float(diff.iloc[-2])

        # 金叉：DIF 从下穿上 DEA
        if last_diff > 0 and prev_diff <= 0:
            return '金叉（DIF 上穿 DEA）'
        # 死叉：DIF 从上穿下 DEA
        if last_diff < 0 and prev_diff >= 0:
            return '死叉（DIF 下穿 DEA）'

        # 检查近5根K线是否趋于黏合（DIF 与 DEA 差值极小）
        recent_diffs = [abs(float(diff.iloc[i])) for i in range(-5, 0)]
        avg_abs_diff = sum(recent_diffs) / len(recent_diffs)
        abs_dif_mean = max(abs(float(dif.iloc[-5:].mean())), 0.01)
        if avg_abs_diff < abs_dif_mean * 0.15:
            # 黏合状态需标注当前 DIF/DEA 的实际多空关系，避免与数值矛盾
            if last_diff > 0:
                return '高位黏合偏多（DIF 略高于 DEA，方向待选择）'
            elif last_diff < 0:
                return '高位黏合偏空（DIF 略低于 DEA，方向待选择）'
            return '趋于黏合（DIF≈DEA，方向不明）'

        # 拒绝死叉（老鸭头）：DIF 向下接近 DEA 但未穿越后重新发散向上
        recent_8 = diff.iloc[-8:]
        if len(recent_8) >= 8 and last_diff > 0:
            min_diff = float(recent_8.min())
            if min_diff > 0 and min_diff < float(recent_8.iloc[0]) * 0.3:
                if float(diff.iloc[-1]) > float(diff.iloc[-2]) > float(diff.iloc[-3]):
                    return '拒绝死叉（老鸭头形态）'

        # 拒绝金叉：DIF 向上接近 DEA 但未穿越后重新下行
        if last_diff < 0:
            max_diff = float(recent_8.max())
            if max_diff < 0 and abs(max_diff) < abs(float(recent_8.iloc[0])) * 0.3:
                if float(diff.iloc[-1]) < float(diff.iloc[-2]) < float(diff.iloc[-3]):
                    return '拒绝金叉（空头延续）'

        # 维持金叉发散 / 维持死叉发散
        if last_diff > 0:
            if float(diff.iloc[-1]) > float(diff.iloc[-2]):
                return '金叉发散中（DIF-DEA 差值扩大）'
            return '维持金叉（DIF>DEA）'
        else:
            if float(diff.iloc[-1]) < float(diff.iloc[-2]):
                return '死叉发散中（DIF-DEA 差值扩大）'
            return '维持死叉（DIF<DEA）'

    # ------------------------------------------------------------------
    # 柱体动能检测
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_bar_momentum(macd_bar: pd.Series) -> str:
        """检测 MACD 柱体动能状态。"""
        if len(macd_bar) < 3:
            return '数据不足'

        last = float(macd_bar.iloc[-1])
        prev = float(macd_bar.iloc[-2])
        prev2 = float(macd_bar.iloc[-3])

        if last > 0:
            if last > prev > prev2:
                return '红柱持续放大'
            elif last > prev:
                return '红柱放大'
            elif last < prev:
                return '红柱缩短'
            else:
                return '红柱持平'
        elif last < 0:
            if last < prev < prev2:
                return '绿柱持续放大'
            elif last < prev:
                return '绿柱放大'
            elif last > prev:
                return '绿柱缩短'
            else:
                return '绿柱持平'
        else:
            return '柱体归零'

    # ------------------------------------------------------------------
    # 背离检测
    # ------------------------------------------------------------------

    @classmethod
    def _detect_divergence(cls, close: pd.Series, dif: pd.Series,
                           macd_bar: pd.Series, zero_axis: str = '') -> str:
        """检测 MACD 顶背离/底背离信号。

        原理：比较最近两个价格极值与对应的 DIF 极值，
        价格创新高但 DIF 未创新高 → 顶背离；
        价格创新低但 DIF 未创新低 → 底背离。

        关键约束（避免误判）：
        - 顶背离只在零轴上方或附近检测（DIF 深度负值时不可能价格创真正新高）
        - 底背离只在零轴下方或附近检测
        - 两个极值点间距 >= 5 根 K 线（过滤噪声）
        - 价格变化幅度 >= 1%（过滤微小波动）
        """
        if len(close) < 60:
            return '数据不足，无法判断背离'

        # 零轴位置过滤：零轴下方深水区不可能出现有效顶背离，反之亦然
        check_top = '下方' not in zero_axis  # 零轴上方或附近才检测顶背离
        check_bottom = '上方' not in zero_axis  # 零轴下方或附近才检测底背离

        if not check_top and not check_bottom:
            return '无背离信号'

        # 使用最近 60 根 K 线检测
        c = close.iloc[-60:].values
        d = dif.iloc[-60:].values

        min_gap = 5  # 两个极值点最小间距（K 线数）
        min_pct = 0.01  # 价格变化最小幅度（1%）

        # 日期索引，用于输出历史锚点
        dates = close.iloc[-60:].index

        # 顶背离检测
        if check_top:
            # 寻找局部极大值（价格高点）
            highs = []
            for i in range(2, len(c) - 2):
                if c[i] > c[i - 1] and c[i] > c[i - 2] and c[i] > c[i + 1] and c[i] > c[i + 2]:
                    highs.append(i)

            if len(highs) >= 2:
                # 从后向前找满足间距条件的两个高点
                for j in range(len(highs) - 1, 0, -1):
                    h2 = highs[j]
                    h1 = highs[j - 1]
                    if h2 - h1 < min_gap:
                        continue
                    # 价格变化需有一定幅度
                    if c[h1] > 0 and abs(c[h2] - c[h1]) / c[h1] < min_pct:
                        continue
                    if c[h2] > c[h1] and d[h2] < d[h1]:
                        d1_date = str(dates[h1])[:10]
                        d2_date = str(dates[h2])[:10]
                        gap = h2 - h1
                        return (
                            f'顶背离（前高 {d1_date} 价格{c[h1]:.2f}/DIF{d[h1]:.3f} → '
                            f'近高 {d2_date} 价格{c[h2]:.2f}/DIF{d[h2]:.3f}，'
                            f'间隔{gap}日，价格新高但 DIF 走低）'
                        )
                    break  # 只检查最近一组有效高点

        # 底背离检测
        if check_bottom:
            # 寻找局部极小值（价格低点）
            lows = []
            for i in range(2, len(c) - 2):
                if c[i] < c[i - 1] and c[i] < c[i - 2] and c[i] < c[i + 1] and c[i] < c[i + 2]:
                    lows.append(i)

            if len(lows) >= 2:
                for j in range(len(lows) - 1, 0, -1):
                    l2 = lows[j]
                    l1 = lows[j - 1]
                    if l2 - l1 < min_gap:
                        continue
                    if c[l1] > 0 and abs(c[l2] - c[l1]) / c[l1] < min_pct:
                        continue
                    if c[l2] < c[l1] and d[l2] > d[l1]:
                        d1_date = str(dates[l1])[:10]
                        d2_date = str(dates[l2])[:10]
                        gap = l2 - l1
                        return (
                            f'底背离（前低 {d1_date} 价格{c[l1]:.2f}/DIF{d[l1]:.3f} → '
                            f'近低 {d2_date} 价格{c[l2]:.2f}/DIF{d[l2]:.3f}，'
                            f'间隔{gap}日，价格新低但 DIF 走高）'
                        )
                    break

        return '无背离信号'

    # ------------------------------------------------------------------
    # 跨级别共振分析
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_cross_level_resonance(macd_multi: Dict) -> Dict[str, Any]:
        """分析多级别 MACD 跨级别共振，输出共振状态 + 长短博弈 + 动态分析提示。"""
        levels = []
        for key in ['monthly', 'weekly', 'daily']:
            if key in macd_multi:
                levels.append(macd_multi[key])

        if not levels:
            return {'resonance_state': '数据不足', 'battle_analysis': '', 'analysis_prompt': ''}

        # 判断各级别多空方向
        directions = {}
        for lv in levels:
            name = lv['level']
            if '上方' in lv['zero_axis']:
                directions[name] = 'bullish'
            elif '下方' in lv['zero_axis']:
                directions[name] = 'bearish'
            else:
                directions[name] = 'neutral'

        dir_values = list(directions.values())
        all_bullish = all(d == 'bullish' for d in dir_values)
        all_bearish = all(d == 'bearish' for d in dir_values)

        # ---- 共振状态（一句话定性） ----
        resonance_state = ''
        if all_bullish:
            resonance_state = '所有级别均处于零轴上方'
        elif all_bearish:
            resonance_state = '所有级别均处于零轴下方'
        else:
            parts = []
            for lv in levels:
                d = directions[lv['level']]
                tag = {'bullish': '多头', 'bearish': '空头', 'neutral': '震荡'}[d]
                parts.append(f"{lv['level']}{tag}")
            resonance_state = f"各级别方向分歧（{'、'.join(parts)}）"

        # 叠加金叉/死叉共振
        if 'weekly' in macd_multi and 'daily' in macd_multi:
            w = macd_multi['weekly']
            d_lv = macd_multi['daily']
            if '金叉' in w['cross_state'] and '金叉' in d_lv['cross_state']:
                resonance_state += '，叠加周线+日线金叉共振'
            elif '死叉' in w['cross_state'] and '死叉' in d_lv['cross_state']:
                resonance_state += '，叠加周线+日线死叉共振'

        # ---- 长短博弈（描述各级别动能的矛盾或协同） ----
        battle_parts = []

        # 找长线级别（月线优先，无则周线）和短线级别（日线）
        long_key = 'monthly' if 'monthly' in macd_multi else ('weekly' if 'weekly' in macd_multi else None)
        short_key = 'daily' if 'daily' in macd_multi else None
        mid_key = 'weekly' if 'weekly' in macd_multi and long_key == 'monthly' else None

        if long_key and short_key:
            long_lv = macd_multi[long_key]
            short_lv = macd_multi[short_key]
            long_dir = directions[long_lv['level']]
            short_dir = directions[short_lv['level']]

            # 取柱体动能的简短描述（去掉括号内的解释，避免嵌套）
            long_bar = long_lv['bar_momentum'].split('（')[0]
            short_bar = short_lv['bar_momentum'].split('（')[0]
            long_bar_full = long_lv['bar_momentum']
            short_bar_full = short_lv['bar_momentum']

            if long_dir == short_dir == 'bullish':
                long_weakening = '缩短' in long_bar_full or '衰减' in long_bar_full
                short_strengthening = '放大' in short_bar_full or '增强' in short_bar_full
                if long_weakening and short_strengthening:
                    battle_parts.append(
                        f"长短分化：{long_lv['level']}动能衰减（{long_bar}），"
                        f"{short_lv['level']}动能放大（{short_bar}）"
                    )
                elif long_weakening:
                    battle_parts.append(
                        f"{long_lv['level']}动能衰减（{long_bar}），"
                        f"{short_lv['level']}暂未有效接力"
                    )
                elif short_strengthening:
                    battle_parts.append(f"{long_lv['level']}与{short_lv['level']}同步放大")
                else:
                    battle_parts.append(f"零轴上方运行，{short_lv['level']}动能有衰减迹象")
            elif long_dir == short_dir == 'bearish':
                long_weakening = '缩短' in long_bar_full
                short_strengthening = '红柱' in short_bar_full or '缩短' in short_bar_full
                if long_weakening and short_strengthening:
                    battle_parts.append(
                        f"{long_lv['level']}绿柱缩短（{long_bar}），"
                        f"{short_lv['level']}出现红柱（{short_bar}）"
                    )
                elif long_weakening:
                    battle_parts.append(f"{long_lv['level']}绿柱缩短（{long_bar}）")
                else:
                    battle_parts.append(f"零轴下方运行，{long_lv['level']}和{short_lv['level']}均偏空")
            elif long_dir == 'bullish' and short_dir == 'bearish':
                battle_parts.append(f"{long_lv['level']}零轴上方，{short_lv['level']}处于回调周期（{short_lv['cross_state']}）")
            elif long_dir == 'bearish' and short_dir == 'bullish':
                battle_parts.append(f"{long_lv['level']}零轴下方，{short_lv['level']}短线转多（{short_lv['cross_state']}）")
            else:
                battle_parts.append(f"{long_lv['level']}与{short_lv['level']}方向不一致，盘面震荡为主")

        # 中线补充（同样取简短版）
        if mid_key:
            mid_lv = macd_multi[mid_key]
            mid_bar = mid_lv['bar_momentum'].split('（')[0]
            mid_cross = mid_lv['cross_state'].split('（')[0]
            battle_parts.append(f"{mid_lv['level']}：{mid_cross}，{mid_bar}")

        # 背离补充：只提取有实际背离信号的级别（跳过"无背离信号"等无效提示）
        for lv in levels:
            div = lv.get('divergence', '')
            if '顶背离' in div or '底背离' in div:
                battle_parts.append(f"⚠ {lv['level']}{div}")

        battle_analysis = '；'.join(battle_parts) if battle_parts else '各级别动能无显著矛盾'

        # ---- 动态分析提示（根据实际盘面状态生成） ----
        if all_bullish:
            analysis_prompt = (
                "请结合上述多级别 MACD 状态，评估当前趋势的持续性，"
                "关注是否有动能衰减或背离迹象。"
            )
        elif all_bearish:
            has_rebound = any('红柱' in lv.get('bar_momentum', '') for lv in levels)
            if has_rebound:
                analysis_prompt = (
                    "请结合上述多级别 MACD 状态，分析短线红柱放大在零轴下方的含义，"
                    "评估动能变化的方向和力度。"
                )
            else:
                analysis_prompt = (
                    "请结合上述多级别 MACD 状态，评估当前空头动能的变化趋势。"
                )
        else:
            analysis_prompt = (
                "请结合上述多级别 MACD 状态，分析各级别方向分歧的含义。"
            )

        return {
            'resonance_state': resonance_state,
            'battle_analysis': battle_analysis,
            'analysis_prompt': analysis_prompt,
        }
