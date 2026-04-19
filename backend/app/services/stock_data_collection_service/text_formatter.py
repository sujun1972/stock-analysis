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
    # 二B、集合竞价（盘前/盘尾博弈）
    # ================================================================
    _format_auction(lines, data.get('auction') or {})

    # ================================================================
    # 二C、聪明资金（融资融券 + 龙虎榜）
    # ================================================================
    _format_smart_money(lines, data.get('smart_money') or {})

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
    # 大盘指数当日对比（用于个股相对强度判断）
    mkt = basic.get('market_index') or {}
    if mkt:
        sh_pct = mkt.get('pct_change_sh')
        sz_pct = mkt.get('pct_change_sz')
        stock_pct = basic.get('pct_change')
        rel_parts = []
        if sh_pct is not None:
            rel_parts.append(f"上证 {fmt(mkt.get('close_sh'))}（{fmt(sh_pct)}%）")
        if sz_pct is not None:
            rel_parts.append(f"深证 {fmt(mkt.get('close_sz'))}（{fmt(sz_pct)}%）")
        lines.append(f"| 大盘指数（{mkt.get('trade_date', '')}） | " + "；".join(rel_parts) + " |")
        if stock_pct is not None and sh_pct is not None and sz_pct is not None:
            rel_sh = round(stock_pct - sh_pct, 2)
            rel_sz = round(stock_pct - sz_pct, 2)
            lines.append(
                f"| 个股 vs 大盘 | 跑赢上证 {rel_sh:+.2f}pct，跑赢深证 {rel_sz:+.2f}pct |"
            )
    lines.append(f"| 成交额 | {fmt_amount(basic.get('amount'))} |")
    lines.append(f"| 换手率 | {fmt(basic.get('turnover_rate'))}% |")
    lines.append(f"| PE-TTM | {fmt_pe(basic.get('pe_ttm'))} |")

    pe_pct = basic.get('pe_percentile_3y')
    if pe_pct is not None:
        band_label = basic.get('pe_band_label', '')
        suffix = f" — {band_label}" if band_label else ''
        lines.append(
            f"| PE近3年分位 | {fmt(pe_pct, 1)}%（样本{basic.get('pe_sample_count', 0)}个交易日）{suffix} |"
        )
        pe_band = basic.get('pe_band') or {}
        if pe_band:
            current_pe = basic.get('pe_ttm')
            cur_str = f"{current_pe:.2f}" if current_pe else 'N/A'
            lines.append(
                f"| PE Band(3年) | 下轨P10={pe_band.get('p10')}, 中轨P50={pe_band.get('p50')}, "
                f"上轨P90={pe_band.get('p90')}, 极端P99={pe_band.get('p99')} "
                f"[range {pe_band.get('min')}~{pe_band.get('max')}]; 当前 PE={cur_str} |"
            )
            # 当前 PE 与 3 年 P90 的偏离度（仅做事实陈述，不下"透支/钝化"等结论）
            if pe_pct >= 95 and current_pe and pe_band.get('p90') and current_pe > pe_band['p90']:
                over_p90_pct = round((current_pe - pe_band['p90']) / pe_band['p90'] * 100, 1)
                lines.append(
                    f"| PE 与 P90 偏离度 | 当前 PE {cur_str} 较 3 年 P90({pe_band['p90']}) "
                    f"{over_p90_pct:+.1f}%；分位 {pe_pct}% |"
                )

    lines.append(f"| PB | {fmt(basic.get('pb'))} |")
    total_mv = basic.get('total_mv')   # 万元
    circ_mv = basic.get('circ_mv')     # 万元
    lines.append(f"| 总市值 | {fmt_wan(total_mv)} |")
    if circ_mv is not None:
        lines.append(f"| 流通市值 | {fmt_wan(circ_mv)} |")
        # 限售股市值 + 占总股本比例（事实陈述，不下结论）
        if total_mv is not None and total_mv > 0 and circ_mv >= 0:
            restricted_mv = total_mv - circ_mv
            restricted_pct = round(restricted_mv / total_mv * 100, 2)
            circ_pct = round(circ_mv / total_mv * 100, 2)
            if restricted_mv > 0:
                lines.append(
                    f"| 限售股市值 | {fmt_wan(restricted_mv)} "
                    f"（占总市值 {restricted_pct}%；流通占比 {circ_pct}%） |"
                )
    lines.append(f"| 行业(Tushare) | {basic.get('industry') or 'N/A'} |")
    lines.append(f"| 地区 | {basic.get('area') or 'N/A'} |")

    board_name = basic.get('industry_board_name', '')
    if board_name:
        lines.append(f"| 东财行业板块 | {board_name} |")

    # 财务指标（最新一期）
    fina = basic.get('fina', {})
    if fina:
        days_lag = fina.get('days_since_end')
        lag_note = f"，距今 {days_lag} 天" if days_lag is not None else ''
        lines.append(f"| --- 最新财报（报告期 {fina.get('end_date', '')}{lag_note}） | --- |")
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

    repurchase = basic.get('repurchase') or {}
    if repurchase:
        lines.append("")
        lines.append("**股票回购（近1年，正面估值信号）：**")
        lines.append("")
        active = repurchase.get('active_plan')
        if active:
            lines.append(
                f"- 最新进行中计划（{active.get('ann_date', '')}，状态：{active.get('proc', '')}）："
            )
            low = active.get('low_limit')
            high = active.get('high_limit')
            amt = active.get('amount')  # 单位：万元
            vol = active.get('vol')     # 单位：万股
            price_range = f"{fmt(low)} ~ {fmt(high)} 元" if low and high else 'N/A'
            lines.append(f"    - 回购价区间：{price_range}")
            lines.append(f"    - 计划回购数量：{fmt(vol, 2) if vol else 'N/A'} 万股")
            lines.append(f"    - 计划回购金额：{fmt(amt, 2) if amt else 'N/A'} 万元")
            if active.get('exp_date'):
                lines.append(f"    - 预计实施期限：{active.get('exp_date')}")
        lines.append(
            f"- 近1年回购统计：进行中 {repurchase.get('active_count_1y', 0)} 项 / "
            f"已完成 {repurchase.get('completed_count_1y', 0)} 项 / "
            f"已完成金额合计 {fmt(repurchase.get('total_completed_amount_1y'), 2)} 万元"
        )
    lines.append("")


def _format_capital_flow(lines: list, data: Dict):
    capital = data.get('capital_flow', {})
    lines.append("## 二、资金流向与筹码变动")
    lines.append("")
    caliber = capital.get('flow_caliber')
    if caliber:
        lines.append(f"> 口径说明：{caliber}")
        lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 主力净额 近1日（超大单+大单） | {fmt_flow(capital.get('net_1d'))} |")
    lines.append(f"| 主力净额 近5日（超大单+大单） | {fmt_flow(capital.get('net_5d'))} |")
    lines.append(f"| 主力净额 近10日（超大单+大单） | {fmt_flow(capital.get('net_10d'))} |")

    # 资金净额 vs 累计涨幅（事实陈述：方向是否同向；AI 自行判断"背离"含义）
    fvp = capital.get('flow_vs_price') or {}
    if fvp:
        cum5 = fvp.get('cum_pct_5d')
        cum10 = fvp.get('cum_pct_10d')
        net5 = fvp.get('net_5d')
        net10 = fvp.get('net_10d')
        same5 = fvp.get('same_direction_5d')
        same10 = fvp.get('same_direction_10d')
        if cum5 is not None and net5 is not None:
            tag5 = '同向' if same5 else '反向（资金与价格不一致）'
            lines.append(
                f"| 资金 vs 价格 近5日 | 累计涨幅 {cum5:+.2f}% / 主力累计净额 "
                f"{fmt_flow(net5)} → {tag5} |"
            )
        if cum10 is not None and net10 is not None:
            tag10 = '同向' if same10 else '反向（资金与价格不一致）'
            lines.append(
                f"| 资金 vs 价格 近10日 | 累计涨幅 {cum10:+.2f}% / 主力累计净额 "
                f"{fmt_flow(net10)} → {tag10} |"
            )

    # 北向资金（北交所不适用，直接跳过）
    is_bse = data.get('ts_code', '').endswith('.BJ')
    hk = capital.get('hk_hold', {})
    if hk:
        days_lag = hk.get('days_lag')
        # 部分股票北向持股为季报频次（仅季末有数据），距今 ≥ 5 个交易日即可能"过期"
        lag_suffix = ''
        if days_lag is not None and days_lag >= 5:
            lag_suffix = f"，距今已 {days_lag} 天"
        lines.append(
            f"| 北向持股({hk.get('trade_date', '')}{lag_suffix}) | "
            f"{fmt(hk.get('vol'), 0)} 股，占流通 {fmt(hk.get('ratio'))}% |"
        )
        if hk.get('vol_change_pct') is not None:
            prev_date = hk.get('prev_date', '')
            base_label = f"较上期({prev_date})" if prev_date else "较上期"
            lines.append(f"| 北向{base_label}持股变动 | {fmt(hk.get('vol_change_pct'))}% |")
        # 数据滞后事实陈述（不替 AI 下"勿据此判断高位接盘"等结论）
        if days_lag is not None and days_lag >= 10:
            lines.append(
                f"| 北向数据频率 | 该股北向持股本地为季报频次（非日频）；"
                f"最新快照距今 {days_lag} 天 |"
            )
    elif not is_bse:
        lines.append("| 北向资金 | 本地无持股数据 |")

    flow_detail = capital.get('flow_detail', [])
    if flow_detail:
        lines.append("")
        lines.append("**近5日资金流向明细：**")
        lines.append("")
        lines.append("| 日期 | 主力净额 | 超大单(≥100万) | 大单(20~100万) | 中单(4~20万) | 小单(<4万) | 涨跌幅 |")
        lines.append("|------|---------|-----------------|-----------------|---------------|-------------|--------|")
        for r in flow_detail:
            lines.append(
                f"| {r.get('trade_date', '')} "
                f"| {fmt_flow(r.get('net_amount'))} "
                f"| {fmt_flow(r.get('net_elg'))} "
                f"| {fmt_flow(r.get('net_lg'))} "
                f"| {fmt_flow(r.get('net_md'))} "
                f"| {fmt_flow(r.get('net_sm'))} "
                f"| {fmt(r.get('pct_change'))}% |"
            )

    block = capital.get('block_trade') or {}
    if block and block.get('records_30d'):
        lines.append("")
        lines.append("**大宗交易（近30日，vol 单位：万股，amount 单位：万元）：**")
        lines.append("")
        premium = block.get('avg_premium_pct')
        premium_str = f"{premium:+.2f}%" if premium is not None else 'N/A'
        lines.append(
            f"- 总笔数：{block.get('records_30d', 0)} 笔 | "
            f"累计成交量：{fmt(block.get('total_vol_wan'), 2)} 万股 | "
            f"累计成交额：{fmt(block.get('total_amount_wan'), 2)} 万元 | "
            f"平均折溢价率：{premium_str}"
        )
        top_buyers = block.get('top_buyers', [])
        if top_buyers:
            lines.append("- TOP3 买方营业部：")
            for b in top_buyers:
                lines.append(f"    - {b.get('buyer', '')} — {fmt(b.get('amount_wan'), 2)} 万元")
    lines.append("")


def _format_auction(lines: list, auction: Dict):
    if not auction:
        return
    open_a = auction.get('open_auction') or {}
    close_a = auction.get('close_auction') or {}
    if not open_a and not close_a:
        return

    lines.append("## 二B、集合竞价异动（盘前/盘尾博弈）")
    lines.append("")

    if open_a:
        gap = open_a.get('gap_pct')
        gap_str = f"{gap:+.2f}%" if gap is not None else 'N/A'
        direction = ''
        if gap is not None:
            if gap > 2:
                direction = '（强势高开）'
            elif gap > 0:
                direction = '（小幅高开）'
            elif gap > -2:
                direction = '（小幅低开）'
            else:
                direction = '（大幅低开）'
        lines.append(
            f"**开盘集合竞价（{open_a.get('trade_date', 'N/A')}）**"
        )
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 竞价成交价 | {fmt(open_a.get('open'))} 元 |")
        lines.append(f"| 前一日收盘 | {fmt(open_a.get('prev_close'))} 元 |")
        lines.append(f"| 跳空幅度 | {gap_str} {direction} |")
        lines.append(f"| 竞价成交量 | {fmt_vol(open_a.get('vol'))} |")
        lines.append(f"| 竞价成交额 | {fmt_amount(open_a.get('amount'))} |")

    if close_a:
        share = close_a.get('vol_share_pct')
        share_str = f"{share:.2f}%" if share is not None else 'N/A'
        lines.append("")
        lines.append(
            f"**收盘集合竞价（{close_a.get('trade_date', 'N/A')}）**"
        )
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 竞价收盘价 | {fmt(close_a.get('close'))} 元 |")
        lines.append(f"| 竞价成交量 | {fmt_vol(close_a.get('vol'))} |")
        lines.append(f"| 竞价成交额 | {fmt_amount(close_a.get('amount'))} |")
        lines.append(f"| 占当日成交量比例 | {share_str} |")
    lines.append("")


def _format_smart_money(lines: list, sm: Dict):
    """渲染聪明资金（融资融券 + 龙虎榜）。"""
    margin = sm.get('margin')
    events = sm.get('top_list_events') or []
    if not margin and not events:
        return

    lines.append("## 二C、聪明资金（融资融券 + 龙虎榜）")
    lines.append("")

    # ---- 融资融券 ----
    if margin:
        days_lag = margin.get('days_lag')
        lag_suffix = f"，距今 {days_lag} 天" if days_lag is not None and days_lag >= 2 else ''
        lines.append(f"**融资融券（最新 {margin.get('trade_date', '')}{lag_suffix}）：**")
        lines.append("")
        rzye = margin.get('rzye')      # 元
        rqye = margin.get('rqye')      # 元
        rzrqye = margin.get('rzrqye')  # 元
        net_5d = margin.get('net_buy_5d')  # 元
        rzye_chg = margin.get('rzye_change_5d_pct')

        def _fmt_yuan(v):
            """元 → 带正负号的"亿元"或"万元"。融资明细需显示净额方向，故区别于 fmt_amount。"""
            if v is None:
                return 'N/A'
            v = float(v)
            sign = '+' if v >= 0 else '-'
            absv = abs(v)
            unit = (absv / 1e8, '亿元') if absv >= 1e8 else (absv / 1e4, '万元')
            return f"{sign}{unit[0]:.2f} {unit[1]}"

        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 融资余额 (rzye) | {_fmt_yuan(rzye) if rzye else 'N/A'} |")
        lines.append(f"| 融券余额 (rqye) | {_fmt_yuan(rqye) if rqye else 'N/A'} |")
        lines.append(f"| 两融合计 (rzrqye) | {_fmt_yuan(rzrqye) if rzrqye else 'N/A'} |")
        lines.append(f"| 近5日 融资净买入 | {_fmt_yuan(net_5d)} |")
        if rzye_chg is not None:
            lines.append(f"| 近5日 融资余额变动率 | {rzye_chg:+.2f}% |")
        lines.append("")
        lines.append("近5日融资明细（rzmre=融资买入额, rzche=融资偿还额, net=买-还）:")
        lines.append("")
        lines.append("| 日期 | 融资余额 | 融资买入 | 融资偿还 | 净买入 |")
        lines.append("|------|---------|---------|---------|--------|")
        for r in margin.get('detail') or []:
            lines.append(
                f"| {r.get('trade_date', '')} | "
                f"{_fmt_yuan(r.get('rzye'))} | "
                f"{_fmt_yuan(r.get('rzmre'))} | "
                f"{_fmt_yuan(r.get('rzche'))} | "
                f"{_fmt_yuan(r.get('net_buy'))} |"
            )

    # ---- 龙虎榜 ----
    if events:
        lines.append("")
        lines.append(f"**龙虎榜（近60日上榜 {len(events)} 次）：**")
        lines.append("")
        for ev in events:
            l_buy = ev.get('l_buy') or 0
            l_sell = ev.get('l_sell') or 0
            net_amt = ev.get('net_amount') or 0
            amt = ev.get('amount') or 0
            l_amt = ev.get('l_amount') or 0
            ratio_to_amt = (l_amt / amt * 100) if amt else 0

            lines.append(
                f"### {ev.get('trade_date', '')} 上榜（涨跌幅 {ev.get('pct_change', 0):+.2f}%，"
                f"换手率 {ev.get('turnover_rate', 0):.2f}%）"
            )
            lines.append("")
            lines.append(f"- 上榜原因：{ev.get('reason', '')}")
            lines.append(
                f"- 当日成交额：{amt/1e8:.2f} 亿元；前五合计成交：{l_amt/1e8:.2f} 亿元"
                f"（占当日 {ratio_to_amt:.1f}%）"
            )
            lines.append(
                f"- 前五买入合计：{l_buy/1e8:.2f} 亿元；前五卖出合计：{l_sell/1e8:.2f} 亿元；"
                f"前五净额：{'+' if net_amt >= 0 else '-'}{abs(net_amt)/1e8:.2f} 亿元"
            )
            buyers = ev.get('buyers') or []
            sellers = ev.get('sellers') or []
            if buyers:
                lines.append("")
                lines.append("**买方席位（按净买入降序）：**")
                lines.append("")
                lines.append("| 席位 | 性质标签 | 买入(万元) | 卖出(万元) | 净买入(万元) |")
                lines.append("|------|---------|-----------|-----------|-------------|")
                for b in buyers:
                    lines.append(
                        f"| {b.get('exalter', '')[:30]} | {b.get('seat_tag', '') or '—'} | "
                        f"{(b.get('buy') or 0)/1e4:.2f} | {(b.get('sell') or 0)/1e4:.2f} | "
                        f"{(b.get('net_buy') or 0)/1e4:+.2f} |"
                    )
            if sellers:
                lines.append("")
                lines.append("**卖方席位（按净卖出降序）：**")
                lines.append("")
                lines.append("| 席位 | 性质标签 | 买入(万元) | 卖出(万元) | 净买入(万元) |")
                lines.append("|------|---------|-----------|-----------|-------------|")
                for s in sellers:
                    lines.append(
                        f"| {s.get('exalter', '')[:30]} | {s.get('seat_tag', '') or '—'} | "
                        f"{(s.get('buy') or 0)/1e4:.2f} | {(s.get('sell') or 0)/1e4:.2f} | "
                        f"{(s.get('net_buy') or 0)/1e4:+.2f} |"
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

        # 数据频率事实陈述（不替 AI 下"应假设户数已增加"等结论）
        days_lag = shareholder.get('holder_nums_days_lag')
        if days_lag is not None and days_lag >= 60:
            lines.append("")
            lines.append(
                f"> 数据频率说明：股东人数披露非日频，最新一条距今 {days_lag} 天。"
            )
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
            avg_price_val = r.get('avg_price')
            avg_price_str = f"{fmt(avg_price_val)} 元" if avg_price_val is not None else "—"
            lines.append(
                f"| {r.get('ann_date', '')} | {r.get('holder_name', '')} "
                f"| {fmt(r.get('change_vol'), 0)} 股 "
                f"| {fmt(r.get('change_ratio'))}% "
                f"| {avg_price_str} |"
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

    # --- 均线系统（精简 K-V 格式：每条均线一行 = 数值 + 价格位置 + 排列）---
    if ma_analysis:
        lines.append("")
        lines.append("均线系统:")
        close_val = ma_analysis.get('close')
        lines.append(f"  close: {fmt(close_val)}")
        # 各级别均线压缩为 K-V：每个均线一行，含值 + 价/线位置（价在上/价在下）
        for s in ma_analysis.get('slices', []):
            # values 形如 "MA5=28.52, MA10=25.19"，arrangement 含金叉/死叉等结构信息
            ma_values = s.get('values', '')
            # 把"价格位置"压缩成"价在上/价在下"标志（避免"受均线支撑"这类冗余措辞）
            position = s.get('position', '')
            pos_flag = '价在上' if '站上' in position else ('价在下' if '低于' in position else '混合')
            lines.append(
                f"  [{s['level']}] {ma_values} | 排列: {s.get('arrangement', '')} | 位置: {pos_flag}"
            )
        # 结构信息只保留可量化字段（短期异动、核心博弈点），删除"整体趋势"主观短语
        structure = ma_analysis.get('structure', {})
        if structure:
            if structure.get('short_signal'):
                lines.append(f"  short_signal: {structure['short_signal']}")
            if structure.get('battle_point'):
                lines.append(f"  battle_point: {structure['battle_point']}")
        convergence = ma_analysis.get('convergence', {})
        if convergence:
            if convergence.get('convergence_desc'):
                lines.append(f"  convergence: {convergence['convergence_desc']}")
            if convergence.get('bias_desc'):
                lines.append(f"  bias20: {convergence['bias_desc']}")

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

        # 布林上轨动态推演：列出不同次日收盘下重新计算的上轨数值
        boll_proj = cross_verification.get('boll_projection') or {}
        projs = boll_proj.get('projections') or []
        if projs:
            today_upper = boll_proj.get('today_upper')
            lines.append(f"  布林上轨明日推演（今日上轨 {today_upper:.2f}）:")
            for p in projs:
                lines.append(
                    f"    - 明日{p['label']} 收 {p['next_close']:.2f} → "
                    f"新上轨 ≈ {p['projected_upper']:.2f} "
                    f"（距明日收盘 {p['gain_to_upper_pct']:+.1f}%，"
                    f"上轨较今日 {p['upper_shift_pct']:+.1f}%）"
                )

    # --- TD 序列（即神奇九转，原始算法为 Tom DeMark Sequential，第 9 根为变盘窗口）---
    if nine_turn:
        lines.append("")
        lines.append("TD序列（Tom DeMark Sequential，国内常称'神奇九转'；第9根为变盘窗口阈值）:")
        lines.append(f"  日期: {nine_turn.get('latest_date', '')}")
        up_c = nine_turn.get('up_count')
        down_c = nine_turn.get('down_count')
        up_signal = nine_turn.get('nine_up_turn')
        down_signal = nine_turn.get('nine_down_turn')
        if up_c is not None and up_c > 0:
            count = int(up_c)
            extra = count - 9 if count > 9 else 0
            triggered_flag = (up_signal == '+9')
            lines.append(
                f"  TD_buy_setup_count: {count}  "
                f"(triggered={triggered_flag}, "
                f"extension_after_9={extra})"
            )
        if down_c is not None and down_c > 0:
            count = int(down_c)
            extra = count - 9 if count > 9 else 0
            triggered_flag = (down_signal == '-9')
            lines.append(
                f"  TD_sell_setup_count: {count}  "
                f"(triggered={triggered_flag}, "
                f"extension_after_9={extra})"
            )
        signals = nine_turn.get('recent_signals', [])
        if signals:
            lines.append("  recent_initial_triggers:")
            for s in signals:
                lines.append(f"    - {{date: {s.get('date', '')}, type: {s.get('type', '')}}}")
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

    forecasts = financial.get('forecasts', [])
    if forecasts:
        lines.append("")
        lines.append("**业绩预告（最近24个月，按公告日倒序）：**")
        lines.append("")
        lines.append("| 报告期 | 公告日 | 预告类型 | 净利变动幅度 | 预告净利润区间（亿） | 变动原因 |")
        lines.append("|--------|--------|---------|------------|--------------------|---------|")
        for r in forecasts:
            pct_min = r.get('p_change_min')
            pct_max = r.get('p_change_max')
            pct_str = (
                f"{fmt(pct_min, 1)}% ~ {fmt(pct_max, 1)}%"
                if pct_min is not None and pct_max is not None
                else 'N/A'
            )
            # net_profit_min/max 单位为万元 → 亿元
            np_min = r.get('net_profit_min')
            np_max = r.get('net_profit_max')
            if np_min is not None and np_max is not None:
                np_str = f"{np_min / 1e4:.2f} ~ {np_max / 1e4:.2f}"
            else:
                np_str = 'N/A'
            reason = (r.get('change_reason') or '').replace('|', '/').replace('\n', ' ')[:80]
            lines.append(
                f"| {r.get('end_date', '')} | {r.get('ann_date', '')} | "
                f"{r.get('type', '')} | {pct_str} | {np_str} | {reason} |"
            )

        # Forward PE 推演：把"预告净利润"翻译成"远期 PE"，让 AI 直接判断股价是否已透支预期
        fwd = financial.get('forecast_forward_pe') or {}
        if fwd:
            lines.append("")
            lines.append(
                f"**Forward PE 推演（基于 {fwd.get('forecast_end_date')} 报告期预告，"
                f"公告日 {fwd.get('forecast_ann_date')}）：**"
            )
            lines.append("")
            lines.append("| 口径 | 净利润（亿） | 市值（亿） | Forward PE |")
            lines.append("|------|-------------|-----------|-----------|")
            lines.append(
                f"| 预告下限（最保守） | {fwd.get('np_min_yi')} | "
                f"{fwd.get('total_mv_yi')} | **{fwd.get('forward_pe_high')}x** |"
            )
            lines.append(
                f"| 预告中值 | {fwd.get('np_mid_yi')} | "
                f"{fwd.get('total_mv_yi')} | **{fwd.get('forward_pe_mid')}x** |"
            )
            lines.append(
                f"| 预告上限（最乐观） | {fwd.get('np_max_yi')} | "
                f"{fwd.get('total_mv_yi')} | **{fwd.get('forward_pe_low')}x** |"
            )
            cur_pe = fwd.get('current_pe_ttm')
            if cur_pe and cur_pe > 0:
                fpe_low = fwd.get('forward_pe_low')
                fpe_mid = fwd.get('forward_pe_mid')
                fpe_high = fwd.get('forward_pe_high')
                # 仅做事实级偏离度陈述：当前 PE 相对三档 Forward PE 的位置
                deltas = []
                if fpe_low:
                    deltas.append(f"vs 最乐观 {fpe_low}x：{(cur_pe - fpe_low) / fpe_low * 100:+.1f}%")
                if fpe_mid:
                    deltas.append(f"vs 中值 {fpe_mid}x：{(cur_pe - fpe_mid) / fpe_mid * 100:+.1f}%")
                if fpe_high:
                    deltas.append(f"vs 最保守 {fpe_high}x：{(cur_pe - fpe_high) / fpe_high * 100:+.1f}%")
                lines.append("")
                lines.append(
                    f"> 当前 PE-TTM {cur_pe:.2f}x 相对预告 Forward PE 的偏离度："
                    + "；".join(deltas) + "。"
                )

    express_list = financial.get('express', [])
    if express_list:
        lines.append("")
        lines.append("**业绩快报（最近24个月，按公告日倒序）：**")
        lines.append("")
        lines.append("| 报告期 | 公告日 | 营业收入（亿） | 归母净利（亿） | 稀释EPS | 稀释ROE(%) | 净利YoY(%) | 营收YoY(%) |")
        lines.append("|--------|--------|--------------|--------------|---------|-----------|------------|-----------|")
        for r in express_list:
            # revenue / n_income 单位为元 → 亿元
            rev = r.get('revenue')
            ni = r.get('n_income')
            rev_str = f"{rev / 1e8:.2f}" if rev is not None else 'N/A'
            ni_str = f"{ni / 1e8:.2f}" if ni is not None else 'N/A'
            lines.append(
                f"| {r.get('end_date', '')} | {r.get('ann_date', '')} | {rev_str} | {ni_str} | "
                f"{fmt(r.get('diluted_eps'), 3)} | {fmt(r.get('diluted_roe'), 2)} | "
                f"{fmt(r.get('yoy_net_profit'), 2)} | {fmt(r.get('yoy_sales'), 2)} |"
            )

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
