"""
量价动能与筹码结构分析服务

提供三个层级的量价分析：
- 量价基础参考系（换手率、5日均量基准）
- 短线视角：近5日逐日量价动态推演（量比、形态定性）
- 中长线视角：60日量价结构特征、历史天量压力、核心异动标记
- 动态分析提示

从 StockDataCollectionService 提取，供技术指标收集和 LangChain Tool 使用。
"""

from typing import Dict, Any, Optional, List

import pandas as pd


class VolumePriceAnalysisService:
    """量价动能分析服务（纯计算，无 IO）。"""

    @classmethod
    def analyze(cls, df: pd.DataFrame, trend_context: str = '',
                limit_map: Optional[Dict[str, Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        """对日线 DataFrame 进行量价结构分析。

        Args:
            df: 日线 DataFrame，需含 close/volume/pct_change/turnover/high/low，
                index 为日期，按时间升序排列。
            trend_context: MA 趋势上下文（如"多头趋势"），用于动态调整分析提示话术。
            limit_map: 涨跌停标记字典，key 为 'YYYY-MM-DD'，value 为
                {'limit_type': 'U'/'D'/'Z', 'limit_times': int, 'open_times': int, 'fd_amount': float}。
                涨停/跌停/炸板日的 K 线语义与普通量价完全不同，需单独标注，避免被误读为
                "温和放量长阳/长阴"。

        Returns:
            量价分析结果字典，数据不足时返回 None。
        """
        if df is None or df.empty or len(df) < 10:
            return None

        try:
            close = df['close'].astype(float)
            volume = df['volume'].astype(float)
            pct_change = df['pct_change'].astype(float)
        except (KeyError, ValueError):
            return None

        # 换手率可能不存在
        has_turnover = 'turnover' in df.columns
        turnover = df['turnover'].astype(float) if has_turnover else None

        result: Dict[str, Any] = {}

        # ---- 基础参考系 ----
        # turnover 字段在部分数据源中可能为 0 或空值，需取最近有效值
        last_turnover = None
        if turnover is not None and len(turnover) > 0:
            # 从最新一天往前找第一个有效值（> 0 才算有效）
            for i in range(len(turnover) - 1, max(len(turnover) - 10, -1), -1):
                val = float(turnover.iloc[i])
                if not pd.isna(val) and val > 0:
                    last_turnover = round(val, 2)
                    break
        result['turnover'] = last_turnover

        vol_5d_mean = float(volume.iloc[-5:].mean())
        result['vol_5d_mean'] = round(vol_5d_mean) if vol_5d_mean > 0 else None

        # ---- 短线视角：近5日量价推演 ----
        daily_detail = cls._build_daily_detail(df, vol_5d_mean, limit_map=limit_map)
        result['daily_detail'] = daily_detail

        # ---- 近5日量价背离系数 ----
        recent_5 = df.tail(5)
        up_vol = 0.0
        down_vol = 0.0
        for _, row in recent_5.iterrows():
            pct_val = float(row.get('pct_change', 0) or 0)
            vol_val = float(row.get('volume', 0) or 0)
            if pct_val > 0.3:
                up_vol += vol_val
            elif pct_val < -0.3:
                down_vol += vol_val
        if down_vol > 0:
            vp_ratio = round(up_vol / down_vol, 2)
            vp_ratio_desc = f'近5日上涨日总量/下跌日总量 = {vp_ratio}'
        elif up_vol > 0:
            vp_ratio_desc = '近5日仅有上涨日成交，无下跌日'
        else:
            vp_ratio_desc = None
        result['vp_ratio_desc'] = vp_ratio_desc

        # ---- 中长线视角 ----
        mid_long = cls._analyze_mid_long(df, vol_5d_mean, limit_map=limit_map)
        result['mid_long'] = mid_long

        # ---- 动态分析提示 ----
        result['analysis_prompt'] = cls._generate_prompt(daily_detail, mid_long, trend_context)

        return result

    # ------------------------------------------------------------------
    # 短线：逐日量价推演
    # ------------------------------------------------------------------

    @classmethod
    def _build_daily_detail(cls, df: pd.DataFrame,
                            vol_5d_mean: float,
                            limit_map: Optional[Dict[str, Dict[str, Any]]] = None
                            ) -> List[Dict[str, Any]]:
        """构建近5日逐日量价数据，含量比和形态定性。"""
        recent = df.tail(5)
        details = []

        for idx, row in recent.iterrows():
            date_str = str(idx)[:10]
            vol = float(row.get('volume', 0) or 0)
            pct = float(row.get('pct_change', 0) or 0)

            # 量比
            vol_ratio = round(vol / vol_5d_mean, 1) if vol_5d_mean > 0 else None

            # 量价相对表现（文字描述）
            vol_desc = cls._describe_vol_ratio(vol_ratio)

            # 形态定性（涨停/跌停/炸板优先）
            limit_info = (limit_map or {}).get(date_str)
            pattern = cls._classify_pattern(pct, vol_ratio, limit_info=limit_info)

            details.append({
                'date': date_str,
                'pct_change': round(pct, 2),
                'volume': round(vol),
                'vol_ratio': vol_ratio,
                'vol_desc': vol_desc,
                'pattern': pattern,
            })

        return details

    @staticmethod
    def _describe_vol_ratio(ratio: Optional[float]) -> str:
        """量比相对 5 日均量的中性档位描述。"""
        if ratio is None:
            return 'N/A'
        if ratio >= 2.0:
            return f'≥2.0x ({ratio}x)'
        if ratio >= 1.5:
            return f'1.5~2.0x ({ratio}x)'
        if ratio >= 1.1:
            return f'1.1~1.5x ({ratio}x)'
        if ratio >= 0.8:
            return f'0.8~1.1x ({ratio}x)'
        if ratio >= 0.5:
            return f'0.5~0.8x ({ratio}x)'
        return f'<0.5x ({ratio}x)'

    @staticmethod
    def _classify_pattern(pct: float, vol_ratio: Optional[float],
                          limit_info: Optional[Dict[str, Any]] = None) -> str:
        """根据涨跌幅和量比进行量价形态定性。

        使用涨跌幅分档 + 量比分档的组合，输出精确的复合标签。
        涨停/跌停/炸板日有专属语义（量能受封板限制，不能套用普通量价逻辑）。
        """
        if vol_ratio is None:
            return '数据不足'

        # ---- 涨跌停优先识别 ----
        # 涨停日量能"低"是因封板后无卖单可成交，普通"温和放量长阳"标签会严重误导。
        # 炸板日（Z）则相反：开板后剧烈分歧 → 量能必然放大。
        if limit_info:
            ltype = limit_info.get('limit_type')
            ltimes = limit_info.get('limit_times')
            otimes = limit_info.get('open_times')
            ltimes_int = int(ltimes) if ltimes is not None else None
            otimes_int = int(otimes) if otimes is not None else 0

            if ltype == 'U':  # 涨停封板
                board_label = (
                    f'{ltimes_int}连板' if ltimes_int and ltimes_int >= 2
                    else '首板'
                )
                if otimes_int == 0:
                    return f'涨停（{board_label}，开板0次，全天封板，量比{vol_ratio}x）'
                return (
                    f'涨停（{board_label}，开板{otimes_int}次后封板，量比{vol_ratio}x）'
                )
            if ltype == 'D':  # 跌停
                if otimes_int == 0:
                    return f'跌停（开板0次，全天封板，量比{vol_ratio}x）'
                return f'跌停（开板{otimes_int}次后封板，量比{vol_ratio}x）'
            if ltype == 'Z':  # 炸板（盘中触及涨停后回落）
                return (
                    f'盘中触及涨停后回落（炸板，pct{pct:+.1f}%，量比{vol_ratio}x）'
                )

        # 涨跌幅分档
        big_up = pct > 5
        mid_up = 2 < pct <= 5
        small_up = 0.3 < pct <= 2
        small_down = -2 <= pct < -0.3
        mid_down = -5 <= pct < -2
        big_down = pct < -5
        flat = -0.3 <= pct <= 0.3

        # 量比分档
        heavy = vol_ratio >= 1.5
        light = vol_ratio < 0.7
        normal = not heavy and not light

        # 形态标签：仅做"涨跌幅档位 + 量能档位"的组合事实描述，不下结论性词语
        if big_up:
            if heavy:
                return f'大涨放量（涨{pct:.1f}%，量比{vol_ratio}x）'
            if normal:
                return f'大涨常量（涨{pct:.1f}%，量比{vol_ratio}x）'
            return f'大涨缩量（涨{pct:.1f}%，量比{vol_ratio}x）'
        if mid_up:
            if heavy:
                return f'中涨放量（涨{pct:.1f}%，量比{vol_ratio}x）'
            if normal:
                return f'中涨常量（涨{pct:.1f}%，量比{vol_ratio}x）'
            return f'中涨缩量（涨{pct:.1f}%，量比{vol_ratio}x）'
        if small_up:
            if heavy:
                return f'小涨放量（涨{pct:.1f}%，量比{vol_ratio}x）'
            if light:
                return f'小涨缩量（涨{pct:.1f}%，量比{vol_ratio}x）'
            return f'小涨常量（涨{pct:.1f}%，量比{vol_ratio}x）'
        if big_down:
            if heavy:
                return f'大跌放量（跌{pct:.1f}%，量比{vol_ratio}x）'
            if normal:
                return f'大跌常量（跌{pct:.1f}%，量比{vol_ratio}x）'
            return f'大跌缩量（跌{pct:.1f}%，量比{vol_ratio}x）'
        if mid_down:
            if heavy:
                return f'中跌放量（跌{pct:.1f}%，量比{vol_ratio}x）'
            if normal:
                return f'中跌常量（跌{pct:.1f}%，量比{vol_ratio}x）'
            return f'中跌缩量（跌{pct:.1f}%，量比{vol_ratio}x）'
        if small_down:
            if heavy:
                return f'小跌放量（跌{pct:.1f}%，量比{vol_ratio}x）'
            if light:
                return f'小跌缩量（跌{pct:.1f}%，量比{vol_ratio}x）'
            return f'小跌常量（跌{pct:.1f}%，量比{vol_ratio}x）'
        if flat:
            if heavy:
                return f'平盘放量（pct{pct:+.1f}%，量比{vol_ratio}x）'
            if light:
                return f'平盘缩量（pct{pct:+.1f}%，量比{vol_ratio}x）'
            return f'平盘常量（pct{pct:+.1f}%，量比{vol_ratio}x）'
        return f'平盘常量（pct{pct:+.1f}%，量比{vol_ratio}x）'

    # ------------------------------------------------------------------
    # 中长线：全局筹码与资金行为结构
    # ------------------------------------------------------------------

    @classmethod
    def _analyze_mid_long(cls, df: pd.DataFrame,
                          vol_5d_mean: float,
                          limit_map: Optional[Dict[str, Dict[str, Any]]] = None
                          ) -> Dict[str, Any]:
        """分析60日量价结构特征。"""
        result: Dict[str, Any] = {}

        # 取最近60日（或全部可用数据）
        n = min(len(df), 60)
        recent_60 = df.iloc[-n:]
        close_60 = recent_60['close'].astype(float)
        volume_60 = recent_60['volume'].astype(float)
        pct_60 = recent_60['pct_change'].astype(float)

        # ---- 中线结构 ----
        result['mid_structure'] = cls._detect_mid_structure(pct_60, volume_60, n)

        # ---- 历史天量压力 ----
        result['volume_pressure'] = cls._detect_volume_pressure(df, close_60, volume_60)

        # ---- 核心量价异动 ----
        result['key_anomalies'] = cls._detect_key_anomalies(
            recent_60, vol_5d_mean, limit_map=limit_map
        )

        return result

    @staticmethod
    def _detect_mid_structure(pct: pd.Series, volume: pd.Series, n: int) -> str:
        """检测中线量价结构特征。"""
        if n < 20:
            return '数据不足，无法判断中线结构'

        # 将交易日分为上涨日和下跌日
        up_mask = pct > 0.3
        down_mask = pct < -0.3

        up_vol = float(volume[up_mask].mean()) if up_mask.any() else 0
        down_vol = float(volume[down_mask].mean()) if down_mask.any() else 0

        up_days = int(up_mask.sum())
        down_days = int(down_mask.sum())

        if up_vol == 0 and down_vol == 0:
            return f'涨跌幅均在 ±0.3% 内，无明显涨跌（涨{up_days}日/跌{down_days}日）'

        if up_vol > 0 and down_vol > 0:
            ratio = up_vol / down_vol
            return (
                f'上涨日均量/下跌日均量={ratio:.2f}x，'
                f'涨{up_days}日/跌{down_days}日'
            )
        if up_vol > 0:
            return f'仅有上涨日成交（涨{up_days}日，无下跌日）'
        return f'仅有下跌日成交（跌{down_days}日，无上涨日）'

    @staticmethod
    def _detect_volume_pressure(df: pd.DataFrame,
                                close_60: pd.Series,
                                volume_60: pd.Series) -> str:
        """检测历史天量密集区带来的压力。"""
        current_close = float(close_60.iloc[-1])

        # 找最近60日最大成交量及对应价格
        max_vol_idx = volume_60.idxmax()
        max_vol = float(volume_60.loc[max_vol_idx])
        max_vol_close = float(close_60.loc[max_vol_idx])

        avg_vol = float(volume_60.mean())

        if max_vol > avg_vol * 2.5:
            date_str = str(max_vol_idx)[:10]
            ratio_to_avg = round(max_vol / avg_vol, 1)
            if max_vol_close > current_close:
                pct_away = round((max_vol_close - current_close) / current_close * 100, 1)
                return (
                    f'60日最大成交量={ratio_to_avg}x 日均量，对应日={date_str}，'
                    f'当日收盘={round(max_vol_close, 2)}（高于当前价 +{pct_away}%）'
                )
            else:
                pct_away = round((current_close - max_vol_close) / current_close * 100, 1)
                return (
                    f'60日最大成交量={ratio_to_avg}x 日均量，对应日={date_str}，'
                    f'当日收盘={round(max_vol_close, 2)}（低于当前价 -{pct_away}%）'
                )
        else:
            return f'60日最大成交量 ≤ 2.5x 日均量，无显著天量柱'

    @classmethod
    def _detect_key_anomalies(cls, recent_60: pd.DataFrame,
                              vol_5d_mean: float,
                              limit_map: Optional[Dict[str, Dict[str, Any]]] = None
                              ) -> List[str]:
        """检测核心量价异动事件（含涨停/跌停/炸板事件）。"""
        anomalies = []

        if vol_5d_mean <= 0:
            return anomalies

        volume = recent_60['volume'].astype(float)

        # 检测近10日内的显著量价事件
        recent_10 = recent_60.tail(10)
        for idx, row in recent_10.iterrows():
            vol = float(row.get('volume', 0) or 0)
            p = float(row.get('pct_change', 0) or 0)
            ratio = vol / vol_5d_mean
            date_str = str(idx)[:10]

            # 涨停/跌停/炸板事件优先标注
            linfo = (limit_map or {}).get(date_str)
            if linfo:
                ltype = linfo.get('limit_type')
                ltimes = linfo.get('limit_times')
                otimes = int(linfo.get('open_times') or 0)
                ltimes_int = int(ltimes) if ltimes is not None else None
                if ltype == 'U':
                    board_label = f'{ltimes_int}连板' if ltimes_int and ltimes_int >= 2 else '首板'
                    suffix = '一字/秒板' if otimes == 0 else (f'开板{otimes}次后封板')
                    anomalies.append(f'{date_str} 涨停（{board_label}，{suffix}，量比{ratio:.1f}x）')
                    continue
                if ltype == 'D':
                    suffix = '一字/秒板' if otimes == 0 else (f'开板{otimes}次后封死')
                    anomalies.append(f'{date_str} 跌停（{suffix}，量比{ratio:.1f}x）')
                    continue
                if ltype == 'Z':
                    anomalies.append(
                        f'{date_str} 炸板（盘中触及涨停未封住，pct{p:+.1f}%，量比{ratio:.1f}x）'
                    )
                    continue

            if ratio >= 2.0 and p > 2:
                anomalies.append(f'{date_str} 倍量阳线（量比{ratio:.1f}x, +{p:.1f}%）')
            elif ratio >= 2.0 and p < -2:
                anomalies.append(f'{date_str} 倍量阴线（量比{ratio:.1f}x, {p:.1f}%）')
            elif ratio >= 2.0 and abs(p) <= 2:
                anomalies.append(f'{date_str} 放巨量但涨跌幅有限（量比{ratio:.1f}x），多空剧烈换手')

        # 检测缩量到极致（近5日量能 < 60日均量的50%）
        vol_60_mean = float(volume.mean())
        if vol_60_mean > 0 and vol_5d_mean < vol_60_mean * 0.5:
            anomalies.append('近5日量能萎缩至60日均量的50%以下')

        return anomalies

    # ------------------------------------------------------------------
    # 动态分析提示
    # ------------------------------------------------------------------

    @classmethod
    def _generate_prompt(cls, daily_detail: List[Dict[str, Any]],
                         mid_long: Dict[str, Any],
                         trend_context: str = '') -> str:
        """根据量价特征动态生成分析提示。"""
        if not daily_detail:
            return '请结合量价数据，分析当前资金动向。'

        # 判断 MA 趋势环境
        is_bullish = '多头' in trend_context
        is_bearish = '空头' in trend_context

        # 找近5日中最显著的事件（量比最大的那天）
        notable = sorted(daily_detail, key=lambda d: d.get('vol_ratio') or 0, reverse=True)
        top1 = notable[0] if notable else None

        prompt_parts = []

        # 如果有显著放量日，构建博弈分析引导
        if top1 and top1.get('vol_ratio', 0) >= 1.3:
            last = daily_detail[-1]
            # 检查最显著放量日与最新一天是否构成对比
            top1_up = top1['pct_change'] > 0.3
            last_down = last['pct_change'] < -0.3
            top1_down = top1['pct_change'] < -0.3
            last_up = last['pct_change'] > 0.3

            top1_label = top1["pattern"].split("（")[0]
            last_label = last["pattern"].split("（")[0]

            if top1_up and last_down and top1['date'] != last['date']:
                prompt_parts.append(
                    f'请分析 {top1["date"]} 的"{top1_label}"与 {last["date"]} 的"{last_label}"之间的量价关系。'
                )
            elif top1_down and last_up and top1['date'] != last['date']:
                prompt_parts.append(
                    f'请分析 {top1["date"]} 的"{top1_label}"与 {last["date"]} 的"{last_label}"之间的量价关系。'
                )
            elif top1_up:
                prompt_parts.append(
                    f'请评估 {top1["date"]} 的放量上涨（量比{top1["vol_ratio"]}x）后的量能变化趋势。'
                )
            elif top1_down:
                prompt_parts.append(
                    f'请评估 {top1["date"]} 的放量下跌（量比{top1["vol_ratio"]}x）后的量能变化趋势。'
                )
        else:
            prompt_parts.append(
                '近5日量能整体平淡，请分析当前缩量状态的量能级别。'
            )

        # 补充中长线视角的关键信息
        anomalies = mid_long.get('key_anomalies', [])
        if anomalies:
            prompt_parts.append(
                '结合当前处于均线和 MACD 的整体环境，'
                '判断上述核心量价异动对后市的影响。'
            )
        else:
            mid_str = mid_long.get('mid_structure', '')
            if '吸筹' in mid_str:
                prompt_parts.append('结合中线"上涨放量、下跌缩量"的吸筹特征，评估建仓完成度。')
            elif '出逃' in mid_str:
                prompt_parts.append('结合中线"上涨缩量、下跌放量"的出逃特征，评估风险释放程度。')

        return ''.join(prompt_parts)
