"""
LangChain Tool 定义 — 将 StockDataCollectionService 的 7 个子方法注册为可被 Agent 调用的 Tool。

每个 Tool 接受 ts_code 参数，内部调用对应的数据收集方法，返回格式化文本。
Agent（如 CIO）可根据分析需要自主决定调用哪些 Tool。

作者: AI Strategy Team
创建日期: 2026-04-16
"""

import math

from langchain_core.tools import tool
from loguru import logger


# ------------------------------------------------------------------
# 辅助：格式化数据为简洁文本
# ------------------------------------------------------------------

def _safe_fmt(val, decimals: int = 2) -> str:
    if val is None:
        return "N/A"
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return "N/A"
        return f"{f:.{decimals}f}"
    except (TypeError, ValueError):
        return str(val)


def _fmt_wan(val) -> str:
    """格式化万元单位的数值（市值等），自动换算亿元。"""
    if val is None:
        return "N/A"
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return "N/A"
    except (TypeError, ValueError):
        return "N/A"
    if v >= 1e4:
        return f"{v / 1e4:.2f} 亿元"
    return f"{v:,.0f} 万元"


def _fmt_vol(val) -> str:
    """格式化成交量（输入为股数），自动换算万股/亿股。"""
    if val is None:
        return "N/A"
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return "N/A"
    except (TypeError, ValueError):
        return "N/A"
    if v >= 1e8:
        return f"{v / 1e8:.2f}亿股"
    if v >= 1e4:
        return f"{v / 1e4:.0f}万股"
    return f"{v:.0f}股"


def _fmt_flow(val) -> str:
    if val is None:
        return "N/A"
    try:
        v = float(val)
        if math.isnan(v):
            return "N/A"
    except (TypeError, ValueError):
        return "N/A"
    sign = "+" if v >= 0 else ""
    if abs(v) >= 10000:
        return f"{sign}{v / 10000:.2f} 亿元"
    return f"{sign}{v:.2f} 万元"


# ------------------------------------------------------------------
# Tool 定义
# ------------------------------------------------------------------

@tool
async def get_basic_market(ts_code: str) -> str:
    """获取股票基础盘面数据：最新收盘价、涨跌幅、成交额、换手率、PE-TTM（含近3年估值分位）、PB、总市值、
    所属行业、交易所属性（涨跌幅限制）、最新财报指标（营收/净利润同比、ROE、毛利率）、
    东财行业板块近5日涨跌幅、筹码获利比及成本分布。
    适用场景：了解股票当前估值水平、基本面质量、市场活跃度和行业位置。"""
    from app.services.stock_data_collection_service import StockDataCollectionService

    svc = StockDataCollectionService()
    pure_code = ts_code.split(".")[0] if "." in ts_code else ts_code
    try:
        data = await svc._get_basic_market(ts_code, pure_code)
    except Exception as e:
        logger.warning(f"[tool:get_basic_market] {ts_code} 异常: {e}")
        return f"获取基础盘面失败: {e}"

    if not data:
        return "暂无基础盘面数据"

    lines = [
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 交易日期 | {data.get('trade_date', 'N/A')} |",
    ]
    exchange_note = data.get('exchange_note', '')
    if exchange_note:
        lines.append(f"| 交易所 | {exchange_note} |")
    lines.extend([
        f"| 收盘价 | {_safe_fmt(data.get('close'))} 元 |",
        f"| 涨跌幅 | {_safe_fmt(data.get('pct_change'))}% |",
        f"| 成交额 | {_safe_fmt(data.get('amount'))} 元 |",
        f"| 换手率 | {_safe_fmt(data.get('turnover_rate'))}% |",
        f"| PE-TTM | {_safe_fmt(data.get('pe_ttm'))} |",
    ])
    pe_pct = data.get('pe_percentile_3y')
    if pe_pct is not None:
        lines.append(f"| PE近3年分位 | {_safe_fmt(pe_pct, 1)}% |")
    lines.extend([
        f"| PB | {_safe_fmt(data.get('pb'))} |",
        f"| 总市值 | {_fmt_wan(data.get('total_mv'))} |",
        f"| 行业(Tushare) | {data.get('industry', 'N/A')} |",
    ])
    board = data.get("industry_board_name")
    if board:
        lines.append(f"| 东财行业板块 | {board} |")
    # 财务指标
    fina = data.get("fina", {})
    if fina:
        lines.append(f"| --- 最新财报（{fina.get('end_date', '')}） | --- |")
        lines.append(f"| 营收同比(YoY) | {_safe_fmt(fina.get('or_yoy'))}% |")
        lines.append(f"| 归母净利润同比(YoY) | {_safe_fmt(fina.get('netprofit_yoy'))}% |")
        lines.append(f"| ROE | {_safe_fmt(fina.get('roe'))}% |")
        lines.append(f"| 毛利率 | {_safe_fmt(fina.get('grossprofit_margin'))}% |")
    chip = data.get("chip", {})
    if chip:
        lines.append(f"| 筹码获利比 | {_safe_fmt(chip.get('winner_rate'))}% |")
        lines.append(
            f"| 成本分布 (15%/50%/85%) | "
            f"{_safe_fmt(chip.get('cost_15pct'))} / "
            f"{_safe_fmt(chip.get('cost_50pct'))} / "
            f"{_safe_fmt(chip.get('cost_85pct'))} 元 |"
        )
    ind_5d = data.get("industry_5d", [])
    if ind_5d:
        lines.append("")
        lines.append("| 日期 | 行业涨跌幅 |")
        lines.append("|------|----------|")
        for r in ind_5d:
            lines.append(f"| {r.get('trade_date', '')} | {_safe_fmt(r.get('pct_change'))}% |")
    return "\n".join(lines)


@tool
async def get_capital_flow(ts_code: str) -> str:
    """获取资金流向数据：主力净流入(近1/5/10日)、近5日资金明细、北向资金持股量及变动。
    适用场景：判断主力资金态度、北向资金动向，评估筹码稳定性。"""
    from app.services.stock_data_collection_service import StockDataCollectionService

    svc = StockDataCollectionService()
    pure_code = ts_code.split(".")[0] if "." in ts_code else ts_code
    try:
        data = await svc._get_capital_flow(ts_code, pure_code)
    except Exception as e:
        logger.warning(f"[tool:get_capital_flow] {ts_code} 异常: {e}")
        return f"获取资金流向失败: {e}"

    if not data:
        return "暂无资金流向数据"

    lines = [
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 主力净流入 近1日 | {_fmt_flow(data.get('net_1d'))} |",
        f"| 主力净流入 近5日 | {_fmt_flow(data.get('net_5d'))} |",
        f"| 主力净流入 近10日 | {_fmt_flow(data.get('net_10d'))} |",
    ]
    hk = data.get("hk_hold", {})
    if hk:
        days_lag = hk.get("days_lag")
        lag_suffix = f"，距今已 {days_lag} 天" if days_lag is not None and days_lag >= 5 else ""
        lines.append(
            f"| 北向持股({hk.get('trade_date', '')}{lag_suffix}) | "
            f"{_safe_fmt(hk.get('vol'), 0)} 股, 占流通 {_safe_fmt(hk.get('ratio'))}% |"
        )
        if hk.get("vol_change_pct") is not None:
            prev_date = hk.get("prev_date", "")
            base_label = f"较上期({prev_date})" if prev_date else "较上期"
            lines.append(f"| 北向{base_label}持股变动 | {_safe_fmt(hk.get('vol_change_pct'))}% |")
        if days_lag is not None and days_lag >= 10:
            lines.append(
                f"| 北向数据频率 | 该股北向持股本地为季报频次（非日频），"
                f"最新快照距今 {days_lag} 天 |"
            )
    flow_detail = data.get("flow_detail", [])
    if flow_detail:
        lines.append("")
        lines.append("| 日期 | 净流入 | 涨跌幅 |")
        lines.append("|------|--------|--------|")
        for r in flow_detail:
            lines.append(
                f"| {r.get('trade_date', '')} "
                f"| {_fmt_flow(r.get('net_amount'))} "
                f"| {_safe_fmt(r.get('pct_change'))}% |"
            )
    return "\n".join(lines)


@tool
async def get_shareholder_info(ts_code: str) -> str:
    """获取股东信息：近4季股东人数变化、近3个月大股东减持明细、未来1个月限售股解禁预告。
    适用场景：评估筹码集中度趋势、减持压力和解禁风险。"""
    from app.services.stock_data_collection_service import StockDataCollectionService

    svc = StockDataCollectionService()
    try:
        data = await svc._get_shareholder_info(ts_code)
    except Exception as e:
        logger.warning(f"[tool:get_shareholder_info] {ts_code} 异常: {e}")
        return f"获取股东信息失败: {e}"

    if not data:
        return "暂无股东信息数据"

    lines = []
    holder_nums = data.get("holder_nums", [])
    if holder_nums:
        lines.append("| 报告期 | 股东人数 | 环比变化 |")
        lines.append("|--------|---------|---------|")
        for r in holder_nums:
            qoq = f"{r['qoq_pct']}%" if r.get("qoq_pct") is not None else "-"
            lines.append(f"| {r.get('end_date', '')} | {r.get('holder_num', 'N/A')} 户 | {qoq} |")

    reductions = data.get("reductions", [])
    if reductions:
        lines.append("")
        lines.append("| 公告日 | 股东名称 | 减持股数 | 变动比例 | 均价 |")
        lines.append("|--------|---------|---------|---------|------|")
        for r in reductions:
            lines.append(
                f"| {r.get('ann_date', '')} | {r.get('holder_name', '')} "
                f"| {_safe_fmt(r.get('change_vol'), 0)} 股 "
                f"| {_safe_fmt(r.get('change_ratio'))}% "
                f"| {_safe_fmt(r.get('avg_price'))} 元 |"
            )
    else:
        lines.append("")
        lines.append("近3个月: 无大股东减持")

    upcoming = data.get("upcoming_floats", [])
    if upcoming:
        lines.append("")
        lines.append("| 解禁日期 | 解禁股数 | 股份类型 | 占比 |")
        lines.append("|---------|---------|---------|------|")
        for r in upcoming:
            lines.append(
                f"| {r.get('float_date', '')} "
                f"| {_safe_fmt(r.get('float_share'), 0)} 万股 "
                f"| {r.get('share_type', '')} "
                f"| {_safe_fmt(r.get('float_ratio'))}% |"
            )
    else:
        lines.append("")
        lines.append("未来1个月: 无解禁计划")

    return "\n".join(lines) if lines else "暂无股东信息"


@tool
async def get_technical_indicators(ts_code: str) -> str:
    """获取技术指标：均线多周期结构分析(排列形态/支撑阻力/趋势方向/核心博弈点/收敛度/乖离率)、RSI多周期分析(超买超卖/趋势/背离/跨周期共振)、多级别MACD分析(零轴/交叉/柱体/背离/跨级别共振)、布林线多级别分析(通道宽度/价格位置/%B/Bandwidth/中轨方向/突破信号/跨级别共振)、K线形态识别(单根形态/组合形态/重心趋势)、ATR波动率(历史分位数)、量价异动。
    适用场景：分析均线多空排列与支撑阻力、RSI超买超卖与背离信号、MACD多级别趋势共振、顶底背离信号、布林通道波动率与趋势方向、K线Price Action形态、波动率异常。"""
    from app.services.stock_data_collection_service import StockDataCollectionService

    svc = StockDataCollectionService()
    try:
        data = await svc._get_technical_indicators(ts_code)
    except Exception as e:
        logger.warning(f"[tool:get_technical_indicators] {ts_code} 异常: {e}")
        return f"获取技术指标失败: {e}"

    if not data:
        return "暂无技术指标数据（交易日数不足）"

    lines = []

    # --- 均线系统分析 ---
    ma_analysis = data.get("ma_analysis")
    if ma_analysis:
        lines.append(f"**均线系统** 收盘价: {_safe_fmt(ma_analysis.get('close'))}")
        lines.append("")
        lines.append("| 周期 | 均线 | 排列形态 | 价格位置 | 数值 |")
        lines.append("|------|------|---------|---------|------|")
        for s in ma_analysis.get('slices', []):
            lines.append(
                f"| {s['level']} | {s['names']} | {s['arrangement']} "
                f"| {s['position']} | {s['values']} |"
            )
        structure = ma_analysis.get('structure', {})
        if structure:
            lines.append("")
            lines.append(f"**整体趋势:** {structure.get('trend', '')}")
            if structure.get('short_signal'):
                lines.append(f"**短期异动:** {structure['short_signal']}")
            if structure.get('battle_point'):
                lines.append(f"**博弈点:** {structure['battle_point']}")
        convergence = ma_analysis.get('convergence', {})
        if convergence:
            parts = []
            if convergence.get('convergence_desc'):
                parts.append(convergence['convergence_desc'])
            if convergence.get('bias_desc'):
                parts.append(convergence['bias_desc'])
            if parts:
                lines.append(f"**均线形态:** {'；'.join(parts)}")
    lines.append("")

    rsi_analysis = data.get("rsi_analysis")
    if rsi_analysis:
        lines.append("**RSI 多周期分析**")
        lines.append("")
        lines.append("| 周期 | RSI值 | 超买超卖区间 | 趋势方向 | 背离信号 |")
        lines.append("|------|-------|------------|---------|---------|")
        for s in rsi_analysis.get('slices', []):
            div_text = s['divergence'] if '背离' in s['divergence'] else '无'
            lines.append(
                f"| RSI{s['period']} ({s['label']}) | {_safe_fmt(s['rsi_value'], 1)} "
                f"| {s['zone']} | {s['trend']} | {div_text} |"
            )
        cross = rsi_analysis.get('cross_period', {})
        if cross:
            lines.append("")
            lines.append(f"**共振状态:** {cross.get('resonance', '')}")
            if cross.get('divergence_analysis'):
                lines.append(f"**长短分歧:** {cross['divergence_analysis']}")
            if cross.get('extreme_warning'):
                lines.append(f"**极值预警:** {cross['extreme_warning']}")
            if cross.get('divergence_signals'):
                lines.append(f"**背离汇总:** {cross['divergence_signals']}")
        lines.append("")

    macd_multi = data.get("macd_multi")
    if macd_multi:
        lines.append("")
        lines.append("**MACD 多级别动能与趋势分析**")
        lines.append("")
        lines.append("| 级别 | 零轴位置 (大势) | 交叉状态 (短期方向) | 柱体动能 (力度) | 背离信号 | 关键数值 |")
        lines.append("|------|----------------|-------------------|----------------|---------|---------|")
        for key in ['monthly', 'weekly', 'daily']:
            lv = macd_multi.get(key)
            if not lv:
                continue
            div_text = lv['divergence'] if '背离' in lv['divergence'] else '无'
            lines.append(
                f"| {lv['level']} | {lv['zero_axis']} | {lv['cross_state']} "
                f"| {lv['bar_momentum']} | {div_text} "
                f"| DIF={_safe_fmt(lv.get('dif'), 2)}, DEA={_safe_fmt(lv.get('dea'), 2)} |"
            )
        cross = macd_multi.get('cross_level', {})
        if cross:
            lines.append("")
            lines.append(f"**共振状态:** {cross.get('resonance_state', '')}")
            if cross.get('battle_analysis'):
                lines.append(f"**长短博弈:** {cross['battle_analysis']}")

    # ---- 布林线多级别分析 ----
    boll_multi = data.get("boll_multi")
    if boll_multi:
        lines.append("")
        lines.append("**布林线多级别通道与趋势分析**")
        lines.append("")
        lines.append("| 级别 | 通道宽度 (波动率) | 价格位置 (%B) | 中轨方向 (趋势) | 突破/回踩信号 | 布林形态 | 关键数值 |")
        lines.append("|------|------------------|--------------|----------------|--------------|---------|---------|")
        for key in ['monthly', 'weekly', 'daily']:
            lv = boll_multi.get(key)
            if not lv:
                continue
            lines.append(
                f"| {lv['level']} | {lv['channel_width']}(BW={_safe_fmt(lv.get('bandwidth'), 1)}%) "
                f"| {lv['price_position']}(%B={_safe_fmt(lv.get('percent_b'), 2)}) "
                f"| {lv['mid_direction']} | {lv['signal']} "
                f"| {lv['pattern']} "
                f"| 上={_safe_fmt(lv.get('upper'), 2)} 中={_safe_fmt(lv.get('middle'), 2)} 下={_safe_fmt(lv.get('lower'), 2)} |"
            )
        cross = boll_multi.get('cross_level', {})
        if cross:
            lines.append("")
            lines.append(f"**共振状态:** {cross.get('resonance_state', '')}")
            if cross.get('battle_analysis'):
                lines.append(f"**长短博弈:** {cross['battle_analysis']}")
    # ---- K 线形态 ----
    candle = data.get("candlestick")
    if candle:
        lines.append("")
        lines.append("**K 线形态识别**")
        lines.append("")
        daily_p = candle.get('daily_patterns', [])
        if daily_p:
            lines.append("| 日期 | 涨跌幅 | K 线形态 |")
            lines.append("|------|--------|---------|")
            for d in daily_p:
                lines.append(
                    f"| {d['date']} | {_safe_fmt(d['pct_change'])}% | {d['pattern']} |"
                )
        combo = candle.get('combo_patterns', [])
        if combo and combo != ['无显著组合形态']:
            lines.append(f"**组合形态:** {'；'.join(combo)}")
        gravity = candle.get('gravity_trend', '')
        if gravity:
            lines.append(f"**重心趋势:** {gravity}")

    # ---- ATR 波动率 ----
    atr = data.get("atr")
    if atr:
        lines.append("")
        lines.append(f"**波动率(ATR14):** ATR={_safe_fmt(atr.get('atr'), 2)}"
                     f"(占股价{_safe_fmt(atr.get('atr_pct'), 2)}%) {atr.get('desc', '')}")
    lines.append("")

    # ---- 量价动能分析 ----
    vp = data.get("volume_price")
    if vp:
        lines.append("")
        lines.append("**量价动能分析**")
        turnover = vp.get('turnover')
        vol_mean = vp.get('vol_5d_mean')
        refs = []
        if turnover is not None:
            refs.append(f"换手率: {_safe_fmt(turnover)}%")
        if vol_mean is not None:
            refs.append(f"5日均量: {_fmt_vol(vol_mean)}")
        if refs:
            lines.append(' | '.join(refs))
        lines.append("")

        daily = vp.get('daily_detail', [])
        if daily:
            lines.append("| 日期 | 涨跌幅 | 成交量 | 量比 | 形态定性 |")
            lines.append("|------|--------|--------|------|---------|")
            for d in daily:
                lines.append(
                    f"| {d['date']} | {_safe_fmt(d['pct_change'])}% "
                    f"| {_fmt_vol(d['volume'])} "
                    f"| {d['vol_desc']} | {d['pattern']} |"
                )

        mid_long = vp.get('mid_long', {})
        if mid_long:
            lines.append("")
            if mid_long.get('mid_structure'):
                lines.append(f"**中线结构:** {mid_long['mid_structure']}")
            if mid_long.get('volume_pressure'):
                lines.append(f"**压力预警:** {mid_long['volume_pressure']}")
            anomalies = mid_long.get('key_anomalies', [])
            if anomalies:
                lines.append(f"**核心异动:** {'；'.join(anomalies)}")
        prompt = vp.get('analysis_prompt', '')
        if prompt:
            lines.append("")
            lines.append(f"**分析提示:** {prompt}")

    # ---- 多维指标冲突与共振验证 ----
    cv = data.get("cross_verification")
    if cv:
        lines.append("")
        lines.append("**多维指标冲突与共振验证**")
        conflicts = cv.get('conflicts', [])
        if conflicts:
            lines.append("矛盾点: " + '；'.join(conflicts))
        confirmations = cv.get('confirmations', [])
        if confirmations:
            lines.append("共振确认: " + '；'.join(confirmations))
        risks = cv.get('risks', [])
        if risks:
            lines.append("风险因素: " + '；'.join(risks))

    return "\n".join(lines) if lines else "暂无技术指标"


@tool
async def get_financial_reports(ts_code: str) -> str:
    """获取财报披露日期：近一年的财报预约披露日期和实际披露日期。
    适用场景：关注即将发布的财报，评估业绩公布时间节点风险。"""
    from app.services.stock_data_collection_service import StockDataCollectionService

    svc = StockDataCollectionService()
    try:
        data = await svc._get_financial_reports(ts_code)
    except Exception as e:
        logger.warning(f"[tool:get_financial_reports] {ts_code} 异常: {e}")
        return f"获取财报信息失败: {e}"

    if not data:
        return "暂无财报披露计划"

    disclosures = data.get("disclosures", [])
    if not disclosures:
        return "暂无近期财报披露计划"

    lines = [
        "| 报告期 | 预约披露日 |",
        "|--------|----------|",
    ]
    for r in disclosures:
        actual = r.get("actual_date", "")
        pre = r.get("pre_date", "")
        date_str = actual if (actual and actual not in ("None", "")) else pre
        lines.append(f"| {r.get('end_date', '')} | {date_str} |")
    return "\n".join(lines)


@tool
async def get_risk_alerts(ts_code: str) -> str:
    """获取风险警示：交易所风险警示公告(ST/*ST等)和股权质押统计(质押笔数、比例、未解押股份)。
    适用场景：评估股票的合规风险和质押爆仓风险。"""
    from app.services.stock_data_collection_service import StockDataCollectionService

    svc = StockDataCollectionService()
    try:
        data = await svc._get_risk_alerts(ts_code)
    except Exception as e:
        logger.warning(f"[tool:get_risk_alerts] {ts_code} 异常: {e}")
        return f"获取风险警示失败: {e}"

    if not data:
        return "暂无风险警示和质押数据"

    lines = []
    alerts = data.get("alerts", [])
    if alerts:
        lines.append("| 起始日期 | 结束日期 | 类型 |")
        lines.append("|---------|---------|------|")
        for r in alerts:
            lines.append(f"| {r.get('start_date', '')} | {r.get('end_date', '')} | {r.get('type', '')} |")
    else:
        lines.append("近期无风险警示公告")

    pledge = data.get("pledge", {})
    if pledge:
        lines.append("")
        lines.append(f"**质押情况({pledge.get('end_date', '')}):**")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 质押笔数 | {pledge.get('pledge_count', 'N/A')} 笔 |")
        lines.append(f"| 质押比例 | {_safe_fmt(pledge.get('pledge_ratio'))}% |")
        lines.append(f"| 未解押股份 | {_safe_fmt(pledge.get('unrest_pledge'), 0)} 万股 |")
    else:
        lines.append("")
        lines.append("暂无质押数据")

    return "\n".join(lines)


@tool
async def get_nine_turn(ts_code: str) -> str:
    """获取神奇九转指标：上涨/下跌连续计数和见顶/见底信号(近30日)。
    适用场景：捕捉阶段性顶底反转信号，辅助择时判断。"""
    from app.services.stock_data_collection_service import StockDataCollectionService

    svc = StockDataCollectionService()
    try:
        data = await svc._get_nine_turn(ts_code)
    except Exception as e:
        logger.warning(f"[tool:get_nine_turn] {ts_code} 异常: {e}")
        return f"获取九转指标失败: {e}"

    if not data:
        return "暂无神奇九转数据"

    lines = [f"最新日期: {data.get('latest_date', 'N/A')}"]
    up_c = data.get("up_count")
    down_c = data.get("down_count")
    up_signal = data.get("nine_up_turn")
    down_signal = data.get("nine_down_turn")

    def _signal_qualifier(count: int, signal_label: str) -> str:
        # count==9 当日为首次触发；count>9 表示触发后序列继续延伸（事实陈述，不下结论）。
        if count == 9:
            return f"（九转{signal_label}信号触发日）"
        extra = count - 9
        return f"（九转{signal_label}信号触发后序列继续延伸{extra}日）"

    parts = []
    if up_c is not None and up_c > 0:
        s = f"上涨计数={int(up_c)}"
        if up_signal == "+9":
            s += _signal_qualifier(int(up_c), "见顶")
        parts.append(s)
    if down_c is not None and down_c > 0:
        s = f"下跌计数={int(down_c)}"
        if down_signal == "-9":
            s += _signal_qualifier(int(down_c), "见底")
        parts.append(s)

    lines.append(f"当前状态: {'，'.join(parts)}" if parts else "当前状态: 无连续计数")

    signals = data.get("recent_signals", [])
    if signals:
        lines.append("")
        lines.append("近期触发日（仅首次触发，非延续）:")
        lines.append("")
        lines.append("| 日期 | 信号 |")
        lines.append("|------|------|")
        for s in signals:
            lines.append(f"| {s.get('date', '')} | {s.get('type', '')} |")

    return "\n".join(lines)


# ------------------------------------------------------------------
# 工具注册表（供 Agent 绑定使用）
# ------------------------------------------------------------------

@tool
async def get_recent_anns(ts_code: str, days: int = 30) -> str:
    """获取股票近 N 天的公司公告元数据（来源：AkShare 东方财富聚合，免费）。

    返回 Markdown 表格（日期 / 类型 / 标题 / URL），仅含元数据不含正文；正文需另行抓取。
    适用场景：判断个股是否发生重大事件（减持/回购/业绩/诉讼/重大合同等），补全纯量价+财报
    数据无法覆盖的"事件面"。数据表为 `stock_anns`，由 `tasks.sync_stock_anns` 每交易日增量同步。

    参数：
      - ts_code: 股票代码（'300750.SZ' 或纯 6 位 '300750'）
      - days:    回看天数（默认 30）
    """
    from app.services.stock_data_collection_service import collectors

    try:
        data = await collectors.get_recent_announcements(ts_code, days=days, limit=50)
    except Exception as e:
        logger.warning(f"[tool:get_recent_anns] {ts_code} 异常: {e}")
        return f"获取近期公告失败: {e}"

    if not data.get('data_available'):
        return f"{ts_code} 在 stock_anns 表中暂无记录（可能尚未触发同步，或该股票代码无对应数据）。"
    items = data.get('items') or []
    if not items:
        latest = data.get('latest_date') or 'N/A'
        earliest = data.get('earliest_date') or 'N/A'
        return f"{ts_code} 近 {days} 天无新公告（表内已覆盖范围 {earliest} ~ {latest}）。"

    header_lines = [
        f"**{ts_code} 近 {days} 天公告（共 {data.get('total_in_window', 0)} 条）**",
        "",
        "| 日期 | 类型 | 事件标签 | 情绪 | 标题 | URL |",
        "|------|------|---------|------|------|-----|",
    ]
    for r in items:
        date = (r.get('ann_date') or '').strip()
        anno_type = (r.get('anno_type') or '—').strip()
        title = (r.get('title') or '').strip().replace('|', '｜')
        url = r.get('url') or ''
        event_tags = r.get('event_tags') or []
        tags_str = ','.join(event_tags) if event_tags else '—'
        impact = r.get('sentiment_impact')
        score = r.get('sentiment_score')
        if impact and score is not None:
            arrow = '🟢' if impact == 'bullish' else ('🔴' if impact == 'bearish' else '⚪')
            sent_str = f"{arrow}{score:+.2f}"
        else:
            sent_str = '未打分'
        header_lines.append(f"| {date} | {anno_type} | {tags_str} | {sent_str} | {title} | {url} |")
    return "\n".join(header_lines)


@tool
async def get_recent_news(ts_code: str, days: int = 7) -> str:
    """获取该股近 N 天关联的财经快讯（财新要闻 + 东财个股新闻聚合）。

    数据源：`news_flash` 表，GIN 数组索引按 `related_ts_codes` 反查。
    返回 Markdown 表格（时间 / 来源 / 标题 / 摘要），适合判断"除公告之外的舆情面"：
    产业动态、监管表态、媒体报道、行业分析等。与 `get_recent_anns` 互补——
    公告走 cninfo/eastmoney 聚合，本工具走财经媒体快讯，两者覆盖事件面不同侧。

    参数：
      - ts_code: 股票代码（'300750.SZ' 或纯 6 位 '300750'）
      - days:    回看天数（默认 7）
    """
    from app.services.stock_data_collection_service import collectors

    try:
        data = await collectors.get_recent_news(ts_code, days=days, limit=30)
    except Exception as e:
        logger.warning(f"[tool:get_recent_news] {ts_code} 异常: {e}")
        return f"获取近期快讯失败: {e}"

    if not data.get('data_available'):
        return f"{ts_code} 在 news_flash 表中暂无关联快讯（可能尚未触发同步，或近 {days} 天无覆盖）。"
    items = data.get('items') or []
    if not items:
        return f"{ts_code} 近 {days} 天无关联快讯。"

    lines = [
        f"**{ts_code} 近 {days} 天关联快讯（共 {data.get('total_in_window', 0)} 条）**",
        "",
        "| 时间 | 来源 | 情绪 | 主题 | 标题 | 摘要 |",
        "|------|------|------|------|------|------|",
    ]
    for r in items:
        t = (r.get('publish_time') or '').strip().replace('T', ' ')[:16]
        src = (r.get('source') or '—').strip()
        title = (r.get('title') or '').strip().replace('|', '｜')
        summary = (r.get('summary') or '').strip().replace('|', '｜').replace('\n', ' ')
        if len(summary) > 120:
            summary = summary[:120] + '…'
        impact = r.get('sentiment_impact')
        score = r.get('sentiment_score')
        if impact and score is not None:
            arrow = '🟢' if impact == 'bullish' else ('🔴' if impact == 'bearish' else '⚪')
            sent_str = f"{arrow}{score:+.2f}"
        else:
            sent_str = '未打分'
        theme_tags = r.get('sentiment_tags') or []
        theme_str = ','.join(theme_tags) if theme_tags else '—'
        lines.append(f"| {t} | {src} | {sent_str} | {theme_str} | {title} | {summary} |")
    return "\n".join(lines)


@tool
async def get_today_cctv_news(date: str = "", lookback_days: int = 3) -> str:
    """获取指定日期或最近 N 天的新闻联播文字稿（宏观背景 / 政策信号）。

    数据源：`cctv_news` 表（AkShare `news_cctv` 同步）。
    适用场景：宏观风险专家判断当下政策倾向、监管基调、国际局势；CIO 做跨股
    宏观定位（如供给侧、军工、新能源等主题的联播曝光度）。

    参数：
      - date:          指定单日 'YYYY-MM-DD' 或 'YYYYMMDD'；留空则走 lookback_days 模式
      - lookback_days: 不传 date 时回看最近 N 天（默认 3）
    """
    from app.services.stock_data_collection_service import collectors

    try:
        query_date = date.strip() if date else None
        data = await collectors.get_today_cctv_news(date=query_date, lookback_days=int(lookback_days), limit=60)
    except Exception as e:
        logger.warning(f"[tool:get_today_cctv_news] 异常: {e}")
        return f"获取新闻联播失败: {e}"

    if not data.get('data_available'):
        if query_date:
            return f"{query_date} 无新闻联播记录（可能为放假日或尚未同步）。"
        return f"近 {lookback_days} 天无新闻联播记录（可能尚未触发同步）。"

    items = data.get('items') or []
    header = (
        f"**新闻联播 {query_date}**"
        if query_date
        else f"**新闻联播近 {lookback_days} 天（共 {len(items)} 条）**"
    )
    lines = [header, "", "| 日期 | 序号 | 标题 |", "|------|------|------|"]
    for r in items:
        d = (r.get('news_date') or '').strip()
        seq = r.get('seq_no') or ''
        title = (r.get('title') or '').strip().replace('|', '｜')
        lines.append(f"| {d} | {seq} | {title} |")
    return "\n".join(lines)


@tool
async def get_macro_snapshot() -> str:
    """获取宏观经济指标快照（CPI / PPI / PMI / M2 / 新增社融 / GDP / Shibor）。

    数据源：`macro_indicators` 表（AkShare 免费宏观接口同步）。
    适用场景：宏观风险专家判断通胀/通缩、货币松紧、经济景气度；CIO 做跨股宏观
    定位（如周期股 vs 科技股在当下货币环境的相对吸引力）。

    返回 Markdown 表格：各指标最新值 + 同比 + 报告期 + 距今滞后天数。
    滞后天数是 LLM 判断数据时效性的关键信号（CPI 月度数据通常滞后 40~60 天）。
    """
    from app.services.stock_data_collection_service import collectors

    try:
        data = await collectors.get_macro_snapshot()
    except Exception as e:
        logger.warning(f"[tool:get_macro_snapshot] 异常: {e}")
        return f"获取宏观指标失败: {e}"

    if not data.get('data_available'):
        return "宏观指标表（macro_indicators）暂无数据（可能尚未触发同步）。"

    latest = data.get('latest') or {}
    if not latest:
        return "宏观指标表中无有效快照。"

    # 指标中文名映射（按业务含义排序，便于 LLM 消费）
    display = [
        ('cpi_yoy',          'CPI 同比',          '%'),
        ('ppi_yoy',          'PPI 同比',          '%'),
        ('pmi_manu',         '制造业 PMI',        '指数（荣枯线 50）'),
        ('pmi_nonmanu',      '非制造业 PMI',      '指数（荣枯线 50）'),
        ('m2_yoy',           'M2 同比',           '%'),
        ('new_credit_month', '新增社融当月',       '亿元'),
        ('gdp_yoy',          'GDP 季度同比',      '%'),
        ('shibor_on',        'Shibor 隔夜',        '%'),
        ('shibor_1w',        'Shibor 1 周',        '%'),
        ('shibor_1m',        'Shibor 1 月',        '%'),
    ]

    lines = [
        "**中国宏观经济指标（最新快照）**",
        "",
        "| 指标 | 最新值 | 单位 | 报告期 | 发布日 | 距今 | 同比(%) |",
        "|------|--------|------|--------|--------|------|---------|",
    ]
    any_row = False
    for code, name, unit in display:
        snap = latest.get(code)
        if not snap:
            continue
        any_row = True
        value = snap.get('value')
        yoy = snap.get('yoy')
        period = snap.get('period_date') or '—'
        publish = snap.get('publish_date') or '—'
        lag = snap.get('lag_days')
        lag_str = f"{lag} 天" if isinstance(lag, int) else '—'
        value_str = _safe_fmt(value, 2) if value is not None else '—'
        # yoy 与 value 相同字段时，重复显示没意义，留空
        if yoy is not None and value is not None and abs(float(yoy) - float(value)) < 1e-9:
            yoy_str = '—'
        else:
            yoy_str = _safe_fmt(yoy, 2) if yoy is not None else '—'
        lines.append(f"| {name} | {value_str} | {unit} | {period} | {publish} | {lag_str} | {yoy_str} |")

    if not any_row:
        return "宏观指标快照为空（所有指标均未入库）。"
    return "\n".join(lines)


CIO_TOOLS = [
    get_basic_market,
    get_capital_flow,
    get_shareholder_info,
    get_technical_indicators,
    get_financial_reports,
    get_risk_alerts,
    get_nine_turn,
    get_recent_anns,
    get_recent_news,        # news_anns Phase 2
    get_today_cctv_news,    # news_anns Phase 2
    get_macro_snapshot,     # news_anns Phase 3
]
"""CIO Agent 可用的数据查询工具（含公告、快讯、联播、宏观指标 = news_anns Phase 1/2/3）"""
