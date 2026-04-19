"""
技术指标收集与跨指标分析

包含：MA/RSI/MACD/布林/K线/量价动能的数据收集，
ATR 波动率计算，以及跨指标共振/矛盾/推理任务生成。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import pandas as pd

from .formatters import is_nan, safe_float


async def get_technical_indicators(ts_code: str) -> Dict:
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
    result: Dict[str, Any] = {}

    # MA 均线
    mas = {}
    for n in [5, 10, 20, 60, 120]:
        if len(close) >= n:
            val = close.rolling(n).mean().iloc[-1]
            mas[f'ma{n}'] = round(float(val), 3) if not is_nan(val) else None
        else:
            mas[f'ma{n}'] = None
    result['ma'] = mas

    # ---- 均线多周期结构分析 ----
    from app.services.ma_analysis_service import MaAnalysisService
    last_close = safe_float(close.iloc[-1]) if len(close) > 0 else None
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
    result['atr'] = compute_atr(df)

    # ---- 量价动能分析 ----
    from app.services.volume_price_analysis_service import VolumePriceAnalysisService
    ma_trend = (result.get('ma_analysis') or {}).get('structure', {}).get('trend', '')
    # 拉近 60 日涨跌停事实（U/D/Z），让涨停/跌停/炸板日的 K 线获得专属语义。
    # stock_daily 表无"是否涨停"列，且 A 股涨幅规则复杂（±10/±20/±5），不能仅靠 pct_change 推断。
    limit_map = await _fetch_recent_limit_map(ts_code, lookback_days=70)
    result['volume_price'] = VolumePriceAnalysisService.analyze(
        df, trend_context=ma_trend, limit_map=limit_map,
    )

    # ---- 近20日价格空间定位 ----
    if len(df) >= 20:
        recent_20 = df.tail(20)
        high_20 = float(recent_20['high'].max())
        low_20 = float(recent_20['low'].min())
        last_close = float(close.iloc[-1])
        price_range = high_20 - low_20
        percentile_20d = round((last_close - low_20) / price_range * 100) if price_range > 0 else 50
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
    # 传入 close 序列，让其能推演"明日布林上轨"动态位置（避免把静态 1.8% 误判为天花板）
    result['cross_verification'] = build_cross_verification(result, close_series=close)

    return result


async def _fetch_recent_limit_map(ts_code: str, lookback_days: int = 70) -> Dict[str, Dict[str, Any]]:
    """从 limit_list_d 拉取近 N 日涨跌停事实，返回 {date_str: {limit_type, limit_times, open_times, fd_amount}}。

    stock_daily 表无"是否涨停"列；A 股涨幅规则随板块/股票类型不同（±10/±20/±5），
    仅靠 pct_change ≈ 9.99 判断涨停会漏判创业板（±20%）和 ST 股（±5%），且无法区分
    一字板/反复炸板/普通封板。limit_list_d 是涨跌停事实的权威来源。
    """
    from app.repositories.limit_list_repository import LimitListRepository

    today = datetime.now()
    start_yyyymmdd = (today - timedelta(days=lookback_days)).strftime('%Y%m%d')
    end_yyyymmdd = today.strftime('%Y%m%d')

    try:
        rows = await asyncio.to_thread(
            LimitListRepository().get_by_date_range,
            start_date=start_yyyymmdd,
            end_date=end_yyyymmdd,
            ts_code=ts_code,
            page=1,
            page_size=200,
        )
    except Exception:
        return {}

    # key 统一成 'YYYY-MM-DD'，与 stock_daily DataFrame 的 index 字符串对齐
    from .formatters import format_date_dashed
    limit_map: Dict[str, Dict[str, Any]] = {}
    for r in rows or []:
        date_key = format_date_dashed(r.get('trade_date'))
        if not date_key:
            continue
        limit_map[date_key] = {
            'limit_type': r.get('limit_type'),
            'limit_times': r.get('limit_times'),
            'open_times': r.get('open_times'),
            'fd_amount': r.get('fd_amount'),
        }
    return limit_map


def compute_atr(df: pd.DataFrame, period: int = 14) -> Optional[Dict[str, Any]]:
    """计算 ATR（平均真实波幅）及其历史分位数。"""
    if len(df) < period + 20:
        return None

    high = df['high'].astype(float)
    low = df['low'].astype(float)
    close = df['close'].astype(float)

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()
    last_atr = float(atr.iloc[-1])
    last_close = float(close.iloc[-1])

    atr_pct = round(last_atr / last_close * 100, 2) if last_close > 0 else 0

    n = min(120, len(atr.dropna()))
    atr_history = atr.dropna().iloc[-n:]
    percentile = round(float((atr_history < last_atr).sum() / len(atr_history) * 100))

    if percentile >= 80:
        desc = f'波动率处于历史高位（{percentile}%分位），市场情绪剧烈'
    elif percentile >= 60:
        desc = f'波动率偏高（{percentile}%分位），波动活跃'
    elif percentile <= 20:
        desc = f'波动率处于历史低位（{percentile}%分位），市场交投清淡'
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


def _project_next_day_boll_upper(close_series: pd.Series,
                                  scenarios: Optional[list] = None
                                  ) -> Optional[Dict[str, Any]]:
    """推演"明日布林上轨"在多种次日收盘情景下的位置。

    布林上轨 = 20日 mean + 2*pstdev，是滚动窗口的动态产物：当新值进入窗口、20日前
    的旧值滚出后，mean 和 std 都会变化 → 上轨被动上移/下移。仅看"当前上轨距今日 +1.8%"
    会得出"上涨空间只有 1.8%"的静态错觉。

    Args:
        close_series: 收盘价 Series（按时间升序），至少 20 条。
        scenarios: [(label, ratio)] 列表，默认覆盖平开/+5%/涨停+10%/-5%。

    Returns:
        {
            'today_upper': float,
            'today_close': float,
            'projections': [{'label', 'next_close', 'projected_upper',
                             'gain_to_upper_pct', 'upper_shift_pct'}, ...]
        }
        数据不足返回 None。
    """
    if close_series is None or len(close_series) < 20:
        return None

    closes = close_series.astype(float)
    today_close = float(closes.iloc[-1])
    last20 = closes.iloc[-20:]
    today_mean = float(last20.mean())
    # 与 BollAnalysisService 保持一致：使用总体标准差（pstdev）
    today_std = float(last20.std(ddof=0))
    today_upper = round(today_mean + 2 * today_std, 2)

    # 滚动窗口：保留最近 19 条 + 1 个明日假设值
    base_window = list(closes.iloc[-19:].astype(float))

    if scenarios is None:
        scenarios = [
            ('平开持平', 1.00),
            ('+3%', 1.03),
            ('涨停 +10%', 1.10),
            ('-3%', 0.97),
        ]

    projections = []
    for label, ratio in scenarios:
        next_close = round(today_close * ratio, 2)
        new_window = pd.Series(base_window + [next_close])
        new_upper = round(float(new_window.mean()) + 2 * float(new_window.std(ddof=0)), 2)
        gain = round((new_upper - next_close) / next_close * 100, 1) if next_close > 0 else None
        shift = round((new_upper - today_upper) / today_upper * 100, 1) if today_upper > 0 else None
        # 位置语义标签：当次日收盘突破新上轨（gain<0），意味着"股价突破 +2σ 通道"→ 加速上涨，
        # 而不是"距离上轨仅 -2.4% 的阻力"。前者是强势延续信号，后者是静态误读。
        if gain is None:
            location = ''
        elif gain < 0:
            location = '收盘突破新上轨（+2σ 通道外，加速上涨形态）'
        elif gain < 2:
            location = '收盘贴近新上轨（强势运行）'
        else:
            location = '收盘仍在新上轨下方（通道内）'
        projections.append({
            'label': label,
            'next_close': next_close,
            'projected_upper': new_upper,
            'gain_to_upper_pct': gain,
            'upper_shift_pct': shift,
            'location': location,
        })

    return {
        'today_close': round(today_close, 2),
        'today_upper': today_upper,
        'projections': projections,
    }


def build_cross_verification(technical: Dict,
                              close_series: Optional[pd.Series] = None
                              ) -> Optional[Dict[str, Any]]:
    """综合各技术指标，提取跨指标矛盾点、共振确认和风险因素。

    Args:
        technical: 技术指标聚合结果。
        close_series: 收盘价序列（升序），用于推演"明日布林上轨"动态位置；
            没有则跳过动态推演。
    """
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

    # MACD 日线方向
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

    # ---- 矛盾点 ----
    if weekly_macd_bullish and macd_diverging:
        cross_desc = daily_macd.get('cross_state', '').split('（')[0]
        conflicts.append(
            f"周线 MACD 处于零轴上方强势区，但日线 MACD {cross_desc}，"
            f"长短周期出现分化，需关注日线动能是否进一步衰减"
        )

    if macd_bullish and weekly_macd_bearish:
        conflicts.append(
            f"日线 MACD {daily_macd.get('cross_state', '').split('（')[0]}（偏多），"
            f"但周线 MACD 仍处于零轴下方��弱势），短线反弹可能受长线趋势压制"
        )

    if boll_bullish and rsi_overbought:
        rsi_val = rsi_short.get('rsi_value', 0)
        conflicts.append(
            f"价格贴近布林上轨且 RSI7={rsi_val:.0f} 进入超买区（>70）"
        )

    if ma_bearish and (macd_bullish or boll_bullish):
        conflicts.append(
            '均线系统处于空头排列，但短线指标（MACD/布林）出现偏多信号'
        )

    # ---- 共振确认 ----
    bullish_signals = sum([ma_bullish, macd_bullish, boll_bullish])
    bearish_signals = sum([ma_bearish, macd_bearish, boll_bearish])

    if bullish_signals >= 3:
        confirmations.append('均线、MACD、布林线三指标方向一致偏多')
    elif bearish_signals >= 3:
        confirmations.append('均线、MACD、布林线三指标方向一致偏空')
    elif ma_bullish and boll_bullish and macd_diverging:
        confirmations.append(
            '均线、布林线方向偏多；日线 MACD 高位黏合偏空，长短周期出现分化'
        )

    if macd_bullish and boll_bullish and not rsi_overbought:
        confirmations.append('MACD 零轴上方 + 布林上半通道 + RSI 未超买')
    elif macd_diverging and boll_bullish and not rsi_overbought:
        confirmations.append('布林上半通道 + RSI 未超买，但日线 MACD 动能减弱')

    # 量价确认
    if vp:
        daily_detail = vp.get('daily_detail', [])
        if daily_detail:
            last_d = daily_detail[-1]
            vol_ratio = last_d.get('vol_ratio', 1)
            pct = last_d.get('pct_change', 0)
            if pct > 1 and vol_ratio >= 1.3:
                confirmations.append(f"最近一日放量上涨（量比 {vol_ratio}x）")
            elif pct < -1 and vol_ratio >= 1.3:
                risks.append(f"最近一日放量下跌（量比 {vol_ratio}x）")

    # ---- 风险因素 ----
    if ma_analysis:
        battle = (ma_analysis.get('structure') or {}).get('battle_point', '')
        if 'MA120' in battle and '阻力' in battle:
            risks.append(f"MA120 形成上方阻力，{battle.split('；')[0]}")

    if weekly_macd_bearish:
        risks.append(f"周线 MACD 处于零轴下方（{weekly_macd.get('zero_axis', '')}），中线趋势偏空")

    if rsi_overbought:
        risks.append(f"RSI7 进入超买区（{rsi_short.get('rsi_value', 0):.0f}，>70）")

    if '收窄' in daily_boll.get('channel_width', '') or '收口' in daily_boll.get('pattern', ''):
        risks.append('日线布林通道收口，波动率收窄')

    if atr and atr.get('percentile', 50) >= 80:
        risks.append(f"波动率处于历史高位（{atr['percentile']}%分位）")

    # ---- 支撑/阻力阶梯 ----
    price_pos = technical.get('price_position', {})
    current_price = price_pos.get('close')
    support_ladder = []
    resistance_ladder = []
    if current_price and current_price > 0:
        key_levels = []
        ma = technical.get('ma', {})
        for name, val in [('MA5', ma.get('ma5')), ('MA10', ma.get('ma10')),
                          ('MA20', ma.get('ma20')), ('MA60', ma.get('ma60')),
                          ('MA120', ma.get('ma120'))]:
            if val:
                key_levels.append((name, float(val)))
        if boll_multi:
            d_boll = boll_multi.get('daily', {})
            for name, val in [('布林上轨', d_boll.get('upper')),
                              ('布林中轨', d_boll.get('middle')),
                              ('布林下轨', d_boll.get('lower'))]:
                if val:
                    key_levels.append((name, float(val)))
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
        support_ladder.sort(key=lambda x: x[1], reverse=True)
        resistance_ladder.sort(key=lambda x: x[1])

    if not conflicts and not confirmations and not risks:
        return None

    # ---- 综合推理任务 ----
    prompt_parts = ['基于上述全部技术指标数据，完成以下交叉验证推理：']
    task_num = 1

    if conflicts:
        prompt_parts.append(f'{task_num}. 处理上述指标矛盾点：判断哪个信号的权重更高，给出依据')
        task_num += 1

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
        prompt_parts.append(
            f'{task_num}. 当前各指标均未检测到背离信号，请分析当前趋势动能的延续概率和潜在衰竭迹象'
        )
        task_num += 1

    if bullish_signals >= 2 and bearish_signals >= 1:
        prompt_parts.append(f'{task_num}. 判断当前看多/看空的确定性（1-10 分），说明核心理由')
        task_num += 1

    if risks:
        prompt_parts.append(f'{task_num}. 请逐项评估上述风险因素的实际影响程度与触发条件')
        task_num += 1

    if candle and resistance_ladder and price_pos.get('percentile_20d', 0) >= 70:
        nearest_resist = resistance_ladder[0] if resistance_ladder else None
        candle_patterns = candle.get('daily_patterns', [])
        combo_patterns = candle.get('combo_patterns', [])
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
                f'{task_num}. 请评估近期 K 线形态（含上述 K 线分析中检测到的关键形态）'
                f'与最近上方阻力位（{nearest_resist[0]} {nearest_resist[1]:.2f}，'
                f'+{abs(nearest_resist[2]):.1f}%）的距离关系，并给出你的判断'
            )
            task_num += 1

    convergence = (ma_analysis or {}).get('convergence', {})
    bias_val = convergence.get('bias20')
    # 推演明日布林上轨（仅当最近阻力是布林上轨时才有意义）
    boll_projection = None
    nearest_r_for_proj = resistance_ladder[0] if resistance_ladder else None
    if (close_series is not None and nearest_r_for_proj
            and nearest_r_for_proj[0] == '布林上轨'):
        boll_projection = _project_next_day_boll_upper(close_series)

    if (bias_val is not None and abs(bias_val) >= 5
            and resistance_ladder and support_ladder):
        nearest_r = resistance_ladder[0]
        nearest_s = support_ladder[0]
        prompt_lines = [
            f'{task_num}. 盈亏比计算：当前乖离率 {bias_val:+.1f}%，'
            f'上方阻力空间 +{abs(nearest_r[2]):.1f}%（{nearest_r[0]}），'
            f'下方支撑空间 {nearest_s[2]:.1f}%（{nearest_s[0]}），'
            f'请计算盈亏比并评估当前价格位置的性价比。'
        ]
        # 阻力是布林上轨时，必须提示其动态特性（窗口滚动 → 上轨被动上移）
        # 并且对每种场景明确标注"收盘突破/贴近/未破"上轨，避免把"涨停后上轨仍在 -2.4%"误读为"涨停遇阻"
        if boll_projection and nearest_r[0] == '布林上轨':
            projs = boll_projection.get('projections', [])
            today_upper = boll_projection.get('today_upper')
            scenario_descs = [
                f"{p['label']}收于{p['next_close']:.2f} → 新上轨≈{p['projected_upper']:.2f}"
                f"（上轨较今日{p['upper_shift_pct']:+.1f}%；"
                f"{p.get('location', '')}）"
                for p in projs
            ]
            prompt_lines.append(
                f'   说明：布林上轨为滚动 20 日 mean+2σ 的动态值，'
                f'今日上轨 {today_upper}；下面列出不同次日收盘情景下重新计算的明日上轨数值——'
                f'注意：次日收盘突破上轨并不意味着"遇阻"，反而是 +2σ 通道被突破的加速上涨信号。'
                + '；'.join(scenario_descs) + '。'
            )
        prompt_parts.append('\n'.join(prompt_lines))
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
        'boll_projection': boll_projection,
        'prompt': prompt,
    }
