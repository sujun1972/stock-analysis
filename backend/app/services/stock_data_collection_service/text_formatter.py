"""
报告文本格式化

将结构化数据字典转换为 Markdown + YAML 格式的个股分析报告。
"""

from typing import Dict

from .formatters import fmt, fmt_pe, fmt_amount, fmt_wan, fmt_flow, fmt_vol


def format_as_text(data: Dict) -> str:
    lines = []
    lines.append(f"# 个股数据收集报告：{data.get('stock_name', '')}（{data.get('ts_code', '')}）")
    lines.append(f"数据收集时间：{data.get('collected_at', '')}")

    basic = data.get('basic_market', {})
    exchange_note = basic.get('exchange_note', '')
    if exchange_note:
        lines.append(f"交易所：{exchange_note}")
    lines.append("")

    # ================================================================
    # 一、基础盘面
    # ================================================================
    _format_basic_market(lines, basic)

    # ================================================================
    # 二、资金流向
    # ================================================================
    _format_capital_flow(lines, data)

    # ================================================================
    # 三、股东变化
    # ================================================================
    _format_shareholder(lines, data.get('shareholder', {}))

    # ================================================================
    # 四、技术指标（YAML 格式）
    # ================================================================
    _format_technical(lines, data)

    # ================================================================
    # 五、财报与公告
    # ================================================================
    _format_financial_risk(lines, data)

    return '\n'.join(lines)


# ------------------------------------------------------------------
# 各章节内部格式化
# ------------------------------------------------------------------

def _format_basic_market(lines: list, basic: Dict):
    lines.append("## 一、基础盘面与行业位置")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 交易日期 | {basic.get('trade_date', 'N/A')} |")
    lines.append(f"| 收盘价 | {fmt(basic.get('close'))} 元 |")
    lines.append(f"| 涨跌幅 | {fmt(basic.get('pct_change'))}% |")
    lines.append(f"| 成交额 | {fmt_amount(basic.get('amount'))} |")
    lines.append(f"| 换手率 | {fmt(basic.get('turnover_rate'))}% |")
    lines.append(f"| PE-TTM | {fmt_pe(basic.get('pe_ttm'))} |")

    pe_pct = basic.get('pe_percentile_3y')
    if pe_pct is not None:
        lines.append(f"| PE近3年分位 | {fmt(pe_pct, 1)}%（样本{basic.get('pe_sample_count', 0)}个交易日） |")

    lines.append(f"| PB | {fmt(basic.get('pb'))} |")
    lines.append(f"| 总市值 | {fmt_wan(basic.get('total_mv'))} |")
    lines.append(f"| 行业(Tushare) | {basic.get('industry') or 'N/A'} |")
    lines.append(f"| 地区 | {basic.get('area') or 'N/A'} |")

    board_name = basic.get('industry_board_name', '')
    if board_name:
        lines.append(f"| 东财行业板块 | {board_name} |")

    # 财务指标（最新一期）
    fina = basic.get('fina', {})
    if fina:
        lines.append(f"| --- 最新财报（{fina.get('end_date', '')}） | --- |")
        lines.append(f"| 营收同比(YoY) | {fmt(fina.get('or_yoy'))}% |")
        lines.append(f"| 归母净利润同比(YoY) | {fmt(fina.get('netprofit_yoy'))}% |")
        lines.append(f"| ROE | {fmt(fina.get('roe'))}% |")
        lines.append(f"| 毛利率 | {fmt(fina.get('grossprofit_margin'))}% |")

    chip = basic.get('chip', {})
    if chip:
        lines.append(f"| 筹码获利比 | {fmt(chip.get('winner_rate'))}% |")
        lines.append(
            f"| 成本分布 (15%/50%/85%) | "
            f"{fmt(chip.get('cost_15pct'))} / "
            f"{fmt(chip.get('cost_50pct'))} / "
            f"{fmt(chip.get('cost_85pct'))} 元 |"
        )
        lines.append(f"| 加权平均成本 | {fmt(chip.get('weight_avg'))} 元 |")

    ind_5d = basic.get('industry_5d', [])
    if ind_5d:
        lines.append("")
        lines.append("**行业板块近5日涨跌幅：**")
        lines.append("")
        lines.append("| 日期 | 涨跌幅 |")
        lines.append("|------|--------|")
        for r in ind_5d:
            lines.append(f"| {r.get('trade_date', '')} | {fmt(r.get('pct_change'))}% |")
    lines.append("")


def _format_capital_flow(lines: list, data: Dict):
    capital = data.get('capital_flow', {})
    lines.append("## 二、资金流向与筹码变动")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 主力净流入 近1日 | {fmt_flow(capital.get('net_1d'))} |")
    lines.append(f"| 主力净流入 近5日 | {fmt_flow(capital.get('net_5d'))} |")
    lines.append(f"| 主力净流入 近10日 | {fmt_flow(capital.get('net_10d'))} |")

    # 北向资金（北交所不适用，直接跳过）
    is_bse = data.get('ts_code', '').endswith('.BJ')
    hk = capital.get('hk_hold', {})
    if hk:
        lines.append(
            f"| 北向持股({hk.get('trade_date', '')}) | "
            f"{fmt(hk.get('vol'), 0)} 股，占流通 {fmt(hk.get('ratio'))}% |"
        )
        if hk.get('vol_change_pct') is not None:
            lines.append(f"| 北向较历史变动 | {fmt(hk.get('vol_change_pct'))}% |")
    elif not is_bse:
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
                f"| {fmt_flow(r.get('net_amount'))} "
                f"| {fmt(r.get('pct_change'))}% |"
            )
    lines.append("")


def _format_shareholder(lines: list, shareholder: Dict):
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
                f"| {fmt(r.get('change_vol'), 0)} 股 "
                f"| {fmt(r.get('change_ratio'))}% "
                f"| {fmt(r.get('avg_price'))} 元 |"
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
                f"| {fmt(r.get('float_share'), 0)} 万股 "
                f"| {r.get('share_type', '')} "
                f"| {fmt(r.get('float_ratio'))}% |"
            )
    else:
        lines.append("")
        lines.append("未来1个月：无解禁计划")
    lines.append("")


def _format_technical(lines: list, data: Dict):
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
        lines.append(f"  当前价: {fmt(pp.get('close'))}")
        lines.append(f"  20日波动区间: [{fmt(pp.get('low_20d'))}, {fmt(pp.get('high_20d'))}]")
        lines.append(f"  区间分位: {pp.get('percentile_20d')}%")
        lines.append(f"  距上方阻力: +{fmt(pp.get('resist_pct', 0), 1)}% ({fmt(pp.get('high_20d'))})")
        lines.append(f"  距下方支撑: -{fmt(pp.get('support_pct', 0), 1)}% ({fmt(pp.get('low_20d'))})")
        if atr:
            lines.append(f"  波动率:")
            lines.append(f"    ATR14: {fmt(atr.get('atr'), 2)}")
            lines.append(f"    占股价: {fmt(atr.get('atr_pct'), 2)}%")
            lines.append(f"    历史分位: {atr.get('percentile')}%")
            lines.append(f"    定性: {atr.get('desc', '')}")

    # --- 均线系统 ---
    if ma_analysis:
        lines.append("")
        lines.append("均线系统:")
        lines.append(f"  最新收盘价: {fmt(ma_analysis.get('close'))}")
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
            lines.append(f"      值: {fmt(s['rsi_value'], 1)}")
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
            lines.append(f"      DIF: {fmt(lv.get('dif'), 2)}")
            lines.append(f"      DEA: {fmt(lv.get('dea'), 2)}")
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
            lines.append(f"      通道宽度: {lv['channel_width']} (BW={fmt(lv.get('bandwidth'), 1)}%)")
            lines.append(f"      价格位置: {lv['price_position']} (%B={fmt(lv.get('percent_b'), 2)})")
            lines.append(f"      中轨方向: {lv['mid_direction']}")
            lines.append(f"      信号: {lv['signal']}")
            lines.append(f"      形态: {lv['pattern']}")
            lines.append(f"      上轨: {fmt(lv.get('upper'), 2)}")
            lines.append(f"      中轨: {fmt(lv.get('middle'), 2)}")
            lines.append(f"      下轨: {fmt(lv.get('lower'), 2)}")
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
                lines.append(f"      涨跌幅: {fmt(d['pct_change'])}%")
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
        lines.append(f"  ATR14: {fmt(atr.get('atr'), 2)}")
        lines.append(f"  占股价: {fmt(atr.get('atr_pct'), 2)}%")
        lines.append(f"  定性: {atr.get('desc', '')}")

    # --- 量价动能 ---
    if vp:
        lines.append("")
        lines.append("量价动能分析:")
        turnover = vp.get('turnover')
        vol_mean = vp.get('vol_5d_mean')
        if turnover is not None:
            lines.append(f"  换手率: {fmt(turnover)}%")
        if vol_mean is not None:
            lines.append(f"  5日均量: {fmt_vol(vol_mean)}")
        daily = vp.get('daily_detail', [])
        if daily:
            lines.append("  近5日量价推演:")
            for d in daily:
                lines.append(f"    - 日期: {d['date']}")
                lines.append(f"      涨跌幅: {fmt(d['pct_change'])}%")
                lines.append(f"      成交量: {fmt_vol(d['volume'])}")
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

    # --- 信号汇总 ---
    if cross_verification:
        lines.append("")
        lines.append("信号汇总:")
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
        risks_list = cross_verification.get('risks', [])
        if risks_list:
            lines.append("  风险因素:")
            for r in risks_list:
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
                    qualifier = f"已触发九转{signal_label}信号（连续{count}日）"
                elif count >= 7:
                    qualifier = f"接近九转阈值（{count}/9），尚未触发"
                elif count >= 4:
                    qualifier = f"处于{direction}序列中段（{count}/9）"
                else:
                    qualifier = f"处于{direction}序列初期（{count}/9）"
                lines.append(f"  {direction}计数: {count}")
                lines.append(f"  {direction}状态: {qualifier}")
        signals = nine_turn.get('recent_signals', [])
        if signals:
            lines.append("  近期信号:")
            for s in signals:
                lines.append(f"    - 日期: {s.get('date', '')}")
                lines.append(f"      类型: {s.get('type', '')}")
        if not up_c and not down_c:
            lines.append("  状态: 无连续计数（多空交替频繁）")

    lines.append("```")
    lines.append("")

    # ---- 综合推理任务 ----
    if cross_verification:
        verify_prompt = cross_verification.get('prompt', '')
        if verify_prompt:
            lines.append("**【综合推理任务】**")
            lines.append("")
            for prompt_line in verify_prompt.split('\n'):
                lines.append(f"> {prompt_line}")
            lines.append("")


def _format_financial_risk(lines: list, data: Dict):
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
        lines.append(f"| 质押比例 | {fmt(pledge.get('pledge_ratio'))}% |")
        lines.append(f"| 未解押股份 | {fmt(pledge.get('unrest_pledge'), 0)} 万股 |")
