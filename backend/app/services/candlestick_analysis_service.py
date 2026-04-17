"""
K 线形态识别服务

识别近 5 日 K 线的经典形态（Price Action），包括：
- 单根 K 线形态（长上影、长下影、十字星、大阳线、大阴线）
- 组合 K 线形态（吞没、孕线、穿头破脚）
- K 线重心变化趋势

纯计算服务，无 IO，无数据库访问。
供技术指标收集和 LangChain Tool 使用。
"""

from typing import Dict, Any, Optional, List

import pandas as pd


class CandlestickAnalysisService:
    """K 线形态识别服务（纯计算，无 IO）。"""

    @classmethod
    def analyze(cls, df: pd.DataFrame, n: int = 5) -> Optional[Dict[str, Any]]:
        """分析最近 n 日 K 线形态。

        Args:
            df: 日线 OHLCV DataFrame，index 为日期，需含 open/high/low/close。
            n: 分析最近几根 K 线，默认 5。

        Returns:
            K 线形态分析结果字典，数据不足时返回 None。
        """
        if df is None or len(df) < max(n + 1, 3):
            return None

        recent = df.tail(n)
        result: Dict[str, Any] = {}

        # 逐日 K 线形态描述
        patterns = []
        for i, (idx, row) in enumerate(recent.iterrows()):
            o = float(row['open'])
            h = float(row['high'])
            l = float(row['low'])
            c = float(row['close'])
            pct = float(row.get('pct_change', 0) or 0)
            date_str = str(idx)[:10]

            body = abs(c - o)
            total = h - l
            if total == 0:
                total = 0.001  # 防除零

            upper_shadow = h - max(o, c)
            lower_shadow = min(o, c) - l

            pattern = cls._classify_single(o, h, l, c, body, total,
                                           upper_shadow, lower_shadow, pct)
            patterns.append({
                'date': date_str,
                'pct_change': round(pct, 2),
                'pattern': pattern,
            })

        result['daily_patterns'] = patterns

        # 计算当前价在近20日的分位数（用于组合形态的高低位语境）
        price_percentile = None
        if len(df) >= 20:
            recent_20 = df.tail(20)
            h20 = float(recent_20['high'].max())
            l20 = float(recent_20['low'].min())
            last_c = float(df.iloc[-1]['close'])
            rng = h20 - l20
            if rng > 0:
                price_percentile = round((last_c - l20) / rng * 100)

        # 组合形态检测（近 2-3 日）
        combo = cls._detect_combo_patterns(df.tail(n + 1), price_percentile)
        result['combo_patterns'] = combo

        # K 线重心趋势
        result['gravity_trend'] = cls._analyze_gravity(recent)

        return result

    # ------------------------------------------------------------------
    # 单根 K 线形态分类
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_single(o: float, h: float, l: float, c: float,
                         body: float, total: float,
                         upper_shadow: float, lower_shadow: float,
                         pct_change: float = 0) -> str:
        body_ratio = body / total
        # 使用真实涨跌幅（前收→收盘），而非仅实体（开盘→收盘），避免跳空缺口导致标签偏差
        pct_abs = round(abs(pct_change), 1) if pct_change != 0 else (
            round(body / o * 100, 1) if o > 0 else 0
        )

        # 十字星：实体极小
        if body_ratio < 0.1:
            if upper_shadow > total * 0.3 and lower_shadow > total * 0.3:
                return '十字星（多空激烈交锋，方向待选择）'
            if upper_shadow > total * 0.6:
                return '墓碑十字（上方抛压沉重）'
            if lower_shadow > total * 0.6:
                return '蜻蜓十字（下方买盘托举）'
            return '小十字星（犹豫整理）'

        # 长上影线：上影 > 实体 2 倍
        if upper_shadow > body * 2 and upper_shadow > total * 0.4:
            if c > o:
                return '长上影阳线（冲高受阻，上方压力显著）'
            return '长上影阴线（冲高回落，抛压沉重）'

        # 长下影线：下影 > 实体 2 倍
        if lower_shadow > body * 2 and lower_shadow > total * 0.4:
            if c > o:
                return '长下影阳线（探底回升，下方有支撑）'
            return '长下影阴线（下方有买盘但多头力度不足）'

        # 基于实体占比和涨跌幅综合判断K线大小
        # 优先级：涨跌幅 > 实体占比（解决有影线但振幅大的K线被误标为"小阳/阴线"的问题）
        if c > o:
            if pct_abs > 5 or (body_ratio > 0.7 and pct_abs > 3):
                return f'大阳线（涨幅 {pct_abs}%，多头强势进攻）'
            if pct_abs > 2 or body_ratio > 0.7:
                return f'中阳线（涨幅 {pct_abs}%，多头占优）'
            return '小阳线（温和上涨）'
        elif c < o:
            if pct_abs > 5 or (body_ratio > 0.7 and pct_abs > 3):
                return f'大阴线（跌幅 {pct_abs}%，空头强势打压）'
            if pct_abs > 2 or body_ratio > 0.7:
                return f'中阴线（跌幅 {pct_abs}%，空头占优）'
            return '小阴线（温和下跌）'
        return '平盘线'

    # ------------------------------------------------------------------
    # 组合 K 线形态
    # ------------------------------------------------------------------

    @classmethod
    def _detect_combo_patterns(cls, df: pd.DataFrame,
                               price_percentile: Optional[int] = None) -> List[str]:
        """检测近 2-3 日的组合 K 线形态，并标注高低位语境。

        Args:
            df: 近 n+1 日 OHLCV DataFrame。
            price_percentile: 当前价在近20日区间的百分位（0-100），
                              用于区分高位/低位形态的不同含义。
        """
        if len(df) < 2:
            return []

        # 高低位判断
        at_high = price_percentile is not None and price_percentile >= 70
        at_low = price_percentile is not None and price_percentile <= 30
        pos_tag = '高位' if at_high else ('低位' if at_low else '中位')

        combos = []
        rows = list(df.iterrows())

        for i in range(1, len(rows)):
            _, prev = rows[i - 1]
            _, curr = rows[i]

            po, pc = float(prev['open']), float(prev['close'])
            co, cc = float(curr['open']), float(curr['close'])

            prev_body = abs(pc - po)
            curr_body = abs(cc - co)
            prev_bullish = pc > po
            curr_bullish = cc > co

            # 看涨吞没：前阴后阳，阳线实体包含阴线实体
            if not prev_bullish and curr_bullish:
                if co <= pc and cc >= po and curr_body > prev_body:
                    if at_low:
                        combos.append(f'{pos_tag}看涨吞没（底部强反转信号，多头强势反包）')
                    elif at_high:
                        combos.append(f'{pos_tag}看涨吞没（多头反包，但高位追涨风险较大）')
                    else:
                        combos.append('看涨吞没（多头强势反包，可能反转上行）')

            # 看跌吞没：前阳后阴，阴线实体包含阳线实体
            if prev_bullish and not curr_bullish:
                if co >= pc and cc <= po and curr_body > prev_body:
                    if at_high:
                        combos.append(f'{pos_tag}看跌吞没（强烈见顶信号，空头强势反包）')
                    elif at_low:
                        combos.append(f'{pos_tag}看跌吞没（空头反包，但低位杀跌动能可能有限）')
                    else:
                        combos.append('看跌吞没（空头强势反包，可能反转下行）')

            # 孕线（母子线）：当日 K 线实体完全在前一日实体内
            if curr_body < prev_body * 0.5:
                curr_high_body = max(co, cc)
                curr_low_body = min(co, cc)
                prev_high_body = max(po, pc)
                prev_low_body = min(po, pc)
                if curr_high_body <= prev_high_body and curr_low_body >= prev_low_body:
                    if prev_bullish:
                        if at_high:
                            combos.append(f'{pos_tag}孕线（上涨动能衰竭，高位犹豫是危险信号，关注见顶回落）')
                        else:
                            combos.append('孕线（上涨后出现犹豫，关注变盘方向）')
                    else:
                        if at_low:
                            combos.append(f'{pos_tag}孕线（下跌动能衰竭，低位犹豫可能酝酿反弹）')
                        else:
                            combos.append('孕线（下跌后出现犹豫，关注反转可能）')

        # 去重
        return list(dict.fromkeys(combos)) if combos else ['无显著组合形态']

    # ------------------------------------------------------------------
    # K 线重心趋势
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_gravity(recent: pd.DataFrame) -> str:
        """分析近 N 日 K 线重心（高低点中心）的移动趋势。"""
        if len(recent) < 3:
            return '数据不足'

        # 重心 = (high + low + close) / 3
        gravities = []
        for _, row in recent.iterrows():
            g = (float(row['high']) + float(row['low']) + float(row['close'])) / 3
            gravities.append(g)

        # 判断重心趋势
        rising = 0
        falling = 0
        for i in range(1, len(gravities)):
            if gravities[i] > gravities[i - 1]:
                rising += 1
            elif gravities[i] < gravities[i - 1]:
                falling += 1

        total = len(gravities) - 1
        if rising >= total * 0.7:
            return 'K 线重心持续上移（多头控盘）'
        if falling >= total * 0.7:
            return 'K 线重心持续下移（空头主导）'
        if rising > falling:
            return 'K 线重心缓慢上移'
        if falling > rising:
            return 'K 线重心缓慢下移'
        return 'K 线重心横向整理'
