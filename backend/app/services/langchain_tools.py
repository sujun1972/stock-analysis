"""
LangChain Tool 定义 — 将 StockDataCollectionService 的 7 个子方法注册为可被 Agent 调用的 Tool。

每个 Tool 接受 ts_code 参数，内部调用对应的数据收集方法，返回格式化文本。
Agent（如 CIO）可根据分析需要自主决定调用哪些 Tool。

作者: AI Strategy Team
创建日期: 2026-04-16
"""

import json
import math
from typing import Optional

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
    """获取股票基础盘面数据：最新收盘价、涨跌幅、成交额、换手率、PE-TTM、PB、总市值、
    所属行业、东财行业板块近5日涨跌幅、筹码获利比及成本分布。
    适用场景：了解股票当前估值水平、市场活跃度和行业位置。"""
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
        f"交易日期: {data.get('trade_date', 'N/A')}",
        f"收盘价: {_safe_fmt(data.get('close'))} 元",
        f"涨跌幅: {_safe_fmt(data.get('pct_change'))}%",
        f"成交额: {_safe_fmt(data.get('amount'))} 元",
        f"换手率: {_safe_fmt(data.get('turnover_rate'))}%",
        f"PE-TTM: {_safe_fmt(data.get('pe_ttm'))}",
        f"PB: {_safe_fmt(data.get('pb'))}",
        f"总市值: {_fmt_wan(data.get('total_mv'))}",
        f"行业(Tushare): {data.get('industry', 'N/A')}",
    ]
    board = data.get("industry_board_name")
    if board:
        lines.append(f"东财行业板块: {board}")
    ind_5d = data.get("industry_5d", [])
    if ind_5d:
        lines.append("行业近5日涨跌幅: " + ", ".join(
            f"{r.get('trade_date', '')}: {_safe_fmt(r.get('pct_change'))}%" for r in ind_5d
        ))
    chip = data.get("chip", {})
    if chip:
        lines.append(
            f"筹码获利比: {_safe_fmt(chip.get('winner_rate'))}%, "
            f"成本分布: 15%={_safe_fmt(chip.get('cost_15pct'))}, "
            f"50%={_safe_fmt(chip.get('cost_50pct'))}, "
            f"85%={_safe_fmt(chip.get('cost_85pct'))} 元"
        )
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
        f"主力净流入 近1日: {_fmt_flow(data.get('net_1d'))}",
        f"主力净流入 近5日: {_fmt_flow(data.get('net_5d'))}",
        f"主力净流入 近10日: {_fmt_flow(data.get('net_10d'))}",
    ]
    flow_detail = data.get("flow_detail", [])
    if flow_detail:
        lines.append("近5日明细:")
        for r in flow_detail:
            lines.append(
                f"  {r.get('trade_date', '')} 净流入 {_fmt_flow(r.get('net_amount'))} "
                f"涨跌 {_safe_fmt(r.get('pct_change'))}%"
            )
    hk = data.get("hk_hold", {})
    if hk:
        lines.append(
            f"北向持股({hk.get('trade_date', '')}): {_safe_fmt(hk.get('vol'), 0)} 股, "
            f"占流通 {_safe_fmt(hk.get('ratio'))}%"
        )
        if hk.get("vol_change_pct") is not None:
            lines.append(f"  较历史变动: {_safe_fmt(hk.get('vol_change_pct'))}%")
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
        lines.append("股东人数(近4季):")
        for r in holder_nums:
            qoq = f" 环比 {r['qoq_pct']}%" if r.get("qoq_pct") is not None else ""
            lines.append(f"  {r.get('end_date', '')}: {r.get('holder_num', 'N/A')} 户{qoq}")

    reductions = data.get("reductions", [])
    if reductions:
        lines.append("大股东减持(近3月):")
        for r in reductions:
            lines.append(
                f"  {r.get('ann_date', '')} {r.get('holder_name', '')} "
                f"减持 {_safe_fmt(r.get('change_vol'), 0)} 股"
                f"({_safe_fmt(r.get('change_ratio'))}%), 均价 {_safe_fmt(r.get('avg_price'))} 元"
            )
    else:
        lines.append("近3个月: 无大股东减持")

    upcoming = data.get("upcoming_floats", [])
    if upcoming:
        lines.append("解禁预告(未来1月):")
        for r in upcoming:
            lines.append(
                f"  {r.get('float_date', '')} 解禁 {_safe_fmt(r.get('float_share'), 0)} 万股"
                f"({r.get('share_type', '')}), 占比 {_safe_fmt(r.get('float_ratio'))}%"
            )
    else:
        lines.append("未来1个月: 无解禁计划")

    return "\n".join(lines) if lines else "暂无股东信息"


@tool
async def get_technical_indicators(ts_code: str) -> str:
    """获取技术指标：MA5/10/20/60/120均线、RSI7/14/21、MACD(DIF/DEA/柱)、量价异动检测、近5日量价。
    适用场景：分析技术面趋势、超买超卖、量价背离信号。"""
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
    ma = data.get("ma", {})
    if ma:
        lines.append(
            f"均线: MA5={_safe_fmt(ma.get('ma5'))} MA10={_safe_fmt(ma.get('ma10'))} "
            f"MA20={_safe_fmt(ma.get('ma20'))} MA60={_safe_fmt(ma.get('ma60'))} "
            f"MA120={_safe_fmt(ma.get('ma120'))}"
        )
    rsi = data.get("rsi", {})
    if rsi:
        lines.append(
            f"RSI: RSI7={_safe_fmt(rsi.get('rsi7'))} RSI14={_safe_fmt(rsi.get('rsi14'))} "
            f"RSI21={_safe_fmt(rsi.get('rsi21'))}"
        )
    macd = data.get("macd")
    if macd:
        lines.append(
            f"MACD: DIF={_safe_fmt(macd.get('dif'), 3)} DEA={_safe_fmt(macd.get('dea'), 3)} "
            f"MACD柱={_safe_fmt(macd.get('macd'), 3)}"
        )
    anomaly = data.get("anomaly", [])
    if anomaly:
        lines.append(f"量价异动: {'、'.join(anomaly)}")
    vol_5d = data.get("recent_5d_vol", [])
    if vol_5d:
        lines.append("近5日量价:")
        for r in vol_5d:
            lines.append(
                f"  {r.get('date', '')} 量 {_safe_fmt(r.get('volume'), 0)} 股 "
                f"涨跌 {_safe_fmt(r.get('pct_change'))}%"
            )
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

    lines = ["财报预约披露日期:"]
    for r in disclosures:
        actual = r.get("actual_date", "")
        pre = r.get("pre_date", "")
        date_str = actual if (actual and actual not in ("None", "")) else pre
        lines.append(f"  报告期 {r.get('end_date', '')}: 预约披露 {date_str}")
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
        lines.append("风险警示:")
        for r in alerts:
            lines.append(f"  {r.get('start_date', '')} ~ {r.get('end_date', '')} {r.get('type', '')}")
    else:
        lines.append("近期无风险警示公告")

    pledge = data.get("pledge", {})
    if pledge:
        lines.append(
            f"质押情况({pledge.get('end_date', '')}): "
            f"质押笔数 {pledge.get('pledge_count', 'N/A')} 笔, "
            f"质押比例 {_safe_fmt(pledge.get('pledge_ratio'))}%, "
            f"未解押 {_safe_fmt(pledge.get('unrest_pledge'), 0)} 万股"
        )
    else:
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

    parts = []
    if up_c is not None and up_c > 0:
        s = f"上涨计数={int(up_c)}"
        if up_signal == "+9":
            s += "（已触发九转见顶信号）"
        parts.append(s)
    if down_c is not None and down_c > 0:
        s = f"下跌计数={int(down_c)}"
        if down_signal == "-9":
            s += "（已触发九转见底信号）"
        parts.append(s)

    if parts:
        lines.append(f"当前状态: {'，'.join(parts)}")
    else:
        lines.append("当前状态: 无连续计数")

    signals = data.get("recent_signals", [])
    if signals:
        lines.append("近30日信号:")
        for s in signals:
            lines.append(f"  {s.get('date', '')} {s.get('type', '')}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# 工具注册表（供 Agent 绑定使用）
# ------------------------------------------------------------------

CIO_TOOLS = [
    get_basic_market,
    get_capital_flow,
    get_shareholder_info,
    get_technical_indicators,
    get_financial_reports,
    get_risk_alerts,
    get_nine_turn,
]
"""CIO Agent 可用的全部 7 个数据查询工具"""
