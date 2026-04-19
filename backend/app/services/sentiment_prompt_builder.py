"""市场情绪 AI 分析 - Prompt 构建模块

将聚合后的打板专题数据格式化为 LLM Prompt（七节数据 + 四个灵魂拷问）。
"""

from typing import Dict, Any


class SentimentPromptBuilder:
    """市场情绪 Prompt 构建器"""

    def build(self, data: Dict[str, Any]) -> str:
        """基于打板专题数据构建分析 Prompt"""
        trade_date = data['trade_date']
        top_list_data = data['top_list_data']
        limit_list_data = data['limit_list_data']
        limit_step_data = data['limit_step_data']
        limit_cpt_data = data['limit_cpt_data']
        mkt_flow = data.get('mkt_flow')
        hsgt_flow = data.get('hsgt_flow')
        top_inst_summary = data.get('top_inst_summary') or {}

        # 分类涨跌停数据
        limit_up_list = [s for s in limit_list_data if s.get('limit_type') == 'U']
        limit_down_list = [s for s in limit_list_data if s.get('limit_type') == 'D']
        blast_list = [s for s in limit_list_data if s.get('limit_type') == 'Z']

        # 按连板数降序排列
        limit_up_list_sorted = sorted(
            limit_up_list,
            key=lambda x: (x.get('limit_times') or 0),
            reverse=True
        )

        # 构建连板天梯文本
        step_by_nums: dict = {}
        for row in limit_step_data:
            n = str(row.get('nums', ''))
            if n not in step_by_nums:
                step_by_nums[n] = []
            step_by_nums[n].append(f"{row.get('name', '')}({row.get('ts_code', '')})")

        ladder_lines = []
        for nums_key in sorted(step_by_nums.keys(), key=lambda x: int(x) if x.isdigit() else 0, reverse=True):
            stocks_str = '、'.join(step_by_nums[nums_key][:5])
            if len(step_by_nums[nums_key]) > 5:
                stocks_str += f" 等{len(step_by_nums[nums_key])}只"
            ladder_lines.append(f"- {nums_key}连板({len(step_by_nums[nums_key])}只): {stocks_str}")
        continuous_ladder_text = '\n'.join(ladder_lines) if ladder_lines else '- 暂无连板数据'

        # 涨停股票列表（前15，按连板数排序）
        limit_up_lines = []
        for i, s in enumerate(limit_up_list_sorted[:15], 1):
            lt = s.get('limit_times') or 1
            ft = s.get('first_time') or '--'
            ot = s.get('open_times') or 0
            industry = s.get('industry') or ''
            limit_up_lines.append(
                f"{i}. {s.get('name', '')}({s.get('ts_code', '')}) "
                f"- {lt}连板 | 封板时间:{ft} | 炸板次数:{ot} | 所属行业:{industry}"
            )
        limit_up_stocks_text = '\n'.join(limit_up_lines) if limit_up_lines else '- 无涨停数据'

        # 跌停股票列表（前5）
        limit_down_lines = []
        for i, s in enumerate(limit_down_list[:5], 1):
            industry = s.get('industry') or ''
            limit_down_lines.append(
                f"{i}. {s.get('name', '')}({s.get('ts_code', '')}) - 所属行业:{industry}"
            )
        limit_down_stocks_text = '\n'.join(limit_down_lines) if limit_down_lines else '- 无跌停数据'

        # 炸板股票列表（前5）
        blast_lines = []
        for i, s in enumerate(blast_list[:5], 1):
            ft = s.get('first_time') or '--'
            industry = s.get('industry') or ''
            blast_lines.append(
                f"{i}. {s.get('name', '')}({s.get('ts_code', '')}) "
                f"- 首次封板:{ft} | 所属行业:{industry}"
            )
        blast_stocks_text = '\n'.join(blast_lines) if blast_lines else '- 无炸板数据'

        # 龙虎榜数据（净买入前5 / 净卖出前5）
        top_list_sorted = sorted(top_list_data, key=lambda x: x.get('net_amount') or 0, reverse=True)
        net_buy_top5 = top_list_sorted[:5]
        net_sell_top5 = sorted(top_list_data, key=lambda x: x.get('net_amount') or 0)[:5]

        net_buy_lines = []
        for i, s in enumerate(net_buy_top5, 1):
            amt = (s.get('net_amount') or 0) / 1e8
            reason = s.get('reason') or ''
            net_buy_lines.append(
                f"{i}. {s.get('name', '')}({s.get('ts_code', '')}) "
                f"- 净买入 {amt:.2f}亿 | 上榜原因:{reason}"
            )
        net_buy_text = '\n'.join(net_buy_lines) if net_buy_lines else '- 无龙虎榜净买入数据'

        net_sell_lines = []
        for i, s in enumerate(net_sell_top5, 1):
            amt = (s.get('net_amount') or 0) / 1e8
            reason = s.get('reason') or ''
            net_sell_lines.append(
                f"{i}. {s.get('name', '')}({s.get('ts_code', '')}) "
                f"- 净卖出 {abs(amt):.2f}亿 | 上榜原因:{reason}"
            )
        net_sell_text = '\n'.join(net_sell_lines) if net_sell_lines else '- 无龙虎榜净卖出数据'

        # 最强板块（前10）
        cpt_lines = []
        for i, c in enumerate(limit_cpt_data[:10], 1):
            cpt_lines.append(
                f"{i}. {c.get('name', '')}({c.get('ts_code', '')}) "
                f"- 涨停{c.get('up_nums', 0)}只 | 连板{c.get('cons_nums', 0)}只 "
                f"| 高度{c.get('up_stat', '')} | 涨幅{c.get('pct_chg', 0) or 0:.2f}%"
            )
        cpt_text = '\n'.join(cpt_lines) if cpt_lines else '- 无板块数据'

        # 计算最高连板
        max_continuous = max(
            [int(k) for k in step_by_nums.keys() if k.isdigit()],
            default=0
        )
        max_continuous_stock = ''
        if max_continuous > 0 and str(max_continuous) in step_by_nums:
            max_continuous_stock = step_by_nums[str(max_continuous)][0]

        # 统计数据
        limit_up_count = len(limit_up_list)
        limit_down_count = len(limit_down_list)
        blast_count = len(blast_list)
        blast_rate = blast_count / (limit_up_count + blast_count) if (limit_up_count + blast_count) > 0 else 0

        # 八、主力资金流向（moneyflow_mkt_dc，单位：元）
        if mkt_flow:
            mkt_net_yi = (mkt_flow.get('net_amount') or 0) / 1e8
            mkt_net_rate = mkt_flow.get('net_amount_rate') or 0
            buy_elg_yi = (mkt_flow.get('buy_elg_amount') or 0) / 1e8
            buy_lg_yi = (mkt_flow.get('buy_lg_amount') or 0) / 1e8
            buy_md_yi = (mkt_flow.get('buy_md_amount') or 0) / 1e8
            buy_sm_yi = (mkt_flow.get('buy_sm_amount') or 0) / 1e8
            pct_sh = mkt_flow.get('pct_change_sh') or 0
            pct_sz = mkt_flow.get('pct_change_sz') or 0
            mkt_flow_text = (
                f"- **大盘主力净流入**: {mkt_net_yi:+.2f} 亿元（占比 {mkt_net_rate:+.2f}%）\n"
                f"- **超大单净买入**: {buy_elg_yi:+.2f} 亿元\n"
                f"- **大单净买入**: {buy_lg_yi:+.2f} 亿元\n"
                f"- **中单净买入**: {buy_md_yi:+.2f} 亿元\n"
                f"- **小单净买入**: {buy_sm_yi:+.2f} 亿元\n"
                f"- **指数涨跌**: 上证 {pct_sh:+.2f}% | 深证 {pct_sz:+.2f}%"
            )
        else:
            mkt_flow_text = "- 当日大盘资金流向数据缺失"

        # 九、北向资金动向（moneyflow_hsgt，单位：百万元）
        if hsgt_flow:
            north_yi = (hsgt_flow.get('north_money') or 0) / 100  # 百万元 → 亿元
            south_yi = (hsgt_flow.get('south_money') or 0) / 100
            hgt_yi = (hsgt_flow.get('hgt') or 0) / 100
            sgt_yi = (hsgt_flow.get('sgt') or 0) / 100
            hsgt_text = (
                f"- **北向资金净流入**: {north_yi:+.2f} 亿元（沪股通 {hgt_yi:+.2f} + 深股通 {sgt_yi:+.2f}）\n"
                f"- **南向资金净流入**: {south_yi:+.2f} 亿元"
            )
        else:
            hsgt_text = "- 当日北向资金数据缺失"

        # 十、游资/机构席位画像（top_inst，按 ABS(net_buy) TOP5）
        inst_count = top_inst_summary.get('institution_count', 0)
        hm_count = top_inst_summary.get('hot_money_count', 0)
        top_seats = top_inst_summary.get('top_seats', [])
        if top_seats:
            seat_lines = []
            for i, s in enumerate(top_seats, 1):
                tag = '机构' if s.get('is_institution') else '游资'
                net_yi = (s.get('net_buy') or 0) / 1e8
                seat_lines.append(
                    f"{i}. [{tag}] {s.get('exalter', '')} "
                    f"- 净{'买入' if net_yi >= 0 else '卖出'} {abs(net_yi):.2f}亿 "
                    f"| 参与 {s.get('stock_count', 0)} 只"
                )
            top_inst_text = (
                f"- **机构席位上榜数**: {inst_count} 家\n"
                f"- **游资席位上榜数**: {hm_count} 家\n\n"
                f"### TOP5 席位（按净买入绝对值排序）\n"
                + '\n'.join(seat_lines)
            )
        else:
            top_inst_text = "- 当日龙虎榜机构明细为空"

        prompt = f"""# A股打板专题盘后深度分析（{trade_date}）

你是一位拥有20年实战经验的A股短线大师，擅长通过盘后数据精准解读市场情绪和资金动向。以下数据均来自当日A股真实市场数据。

## 一、情绪核心数据

- **涨停家数**: {limit_up_count} 只
- **跌停家数**: {limit_down_count} 只
- **炸板家数**: {blast_count} 只
- **炸板率**: {blast_rate:.1%}
- **最高连板**: {max_continuous} 天（{max_continuous_stock}）

## 二、连板天梯（晋级结构）

{continuous_ladder_text}

## 三、涨停股票列表（前15，按连板数排序）

{limit_up_stocks_text}

## 四、跌停股票列表（前5）

{limit_down_stocks_text}

## 五、炸板股票列表（前5）

{blast_stocks_text}

## 六、最强概念板块 TOP10

{cpt_text}

## 七、龙虎榜资金动向

### 净买入前5（主力资金流入）
{net_buy_text}

### 净卖出前5（主力资金流出）
{net_sell_text}

## 八、大盘主力资金流向

{mkt_flow_text}

## 九、北向资金动向

{hsgt_text}

## 十、游资/机构席位画像

{top_inst_text}

---

## 请以JSON格式回答以下四个灵魂拷问

**非常重要**: 请将整个分析结果放在一个JSON代码块中，格式如下：

```json
{{
  "space_analysis": {{ ... }},
  "sentiment_analysis": {{ ... }},
  "capital_flow_analysis": {{ ... }},
  "tomorrow_tactics": {{ ... }}
}}
```

### 1. 【看空间】：今日最高连板是谁？代表什么题材？空间是否被打开？

请在 `space_analysis` 字段中包含：
- `max_continuous_stock`: 对象，包含 `code`(代码), `name`(名称), `days`(连板天数)
- `theme`: 题材名称（字符串）
- `space_level`: "超高空间"/"高空间"/"中等空间"/"低空间"
- `analysis`: 详细分析文字（150-300字）

### 2. 【看情绪】：结合炸板率和跌停数，今日接力资金赚钱效应如何？是该进攻还是防守？

请在 `sentiment_analysis` 字段中包含：
- `money_making_effect`: "超强"/"中等"/"较差"/"极差"
- `strategy`: "激进进攻"/"稳健参与"/"防守为主"/"空仓观望"
- `reasoning`: 详细推理（150-300字）

### 3. 【看暗流】：结合龙虎榜机构明细、北向资金、大盘主力净流入三层数据，判断今日真实资金意图

请在 `capital_flow_analysis` 字段中包含：
- `hot_money_direction`: 对象，包含 `themes`(题材数组), `stocks`(股票代码数组), `concentration`("高度集中"/"分散"/"无明显方向")
- `institution_direction`: 对象，包含 `sectors`(行业数组), `style`("防御性"/"进攻性"/"均衡配置")
- `capital_consensus`: "游资机构共振"/"游资单边进攻"/"机构独立建仓"/"资金分歧"
- `market_capital_signal`: 对象，包含 `main_flow_direction`("强势流入"/"温和流入"/"温和流出"/"强势流出"/"数据缺失"), `northbound_direction`("外资加仓"/"外资减仓"/"中性"/"数据缺失"), `consistency`("主力与北向共振"/"分歧"/"部分验证") —— 基于第八、九节数据作出判断
- `analysis`: 详细分析（200-400字），必须同时引用龙虎榜席位数据与大盘/北向资金数据

### 4. 【明日战术】：基于以上推演，制定明日集合竞价和开盘半小时的应对策略

请在 `tomorrow_tactics` 字段中包含：
- `call_auction_tactics`: 对象，包含 `participate_conditions`(参与条件), `avoid_conditions`(禁止条件)
- `opening_half_hour_tactics`: 对象，包含 `low_buy_opportunities`(低吸机会), `chase_opportunities`(追涨机会), `wait_signals`(观望信号)
- `buy_conditions`: 数组，包含3个买入条件
- `stop_loss_conditions`: 数组，包含3个止损条件

---

**输出要求**:
1. 必须输出完整的JSON格式，放在代码块中
2. 所有分析必须有理有据，引用具体数据
3. 避免模棱两可，给出明确的操作建议
4. 不要编造不存在的股票代码（可以用"主流题材龙头"等泛称）

**现在请开始分析！**"""

        return prompt


sentiment_prompt_builder = SentimentPromptBuilder()
