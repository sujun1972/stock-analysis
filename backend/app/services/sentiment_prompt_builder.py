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

### 3. 【看暗流】：分析龙虎榜数据，顶级游资今天主攻了哪个方向？机构在建仓什么？

请在 `capital_flow_analysis` 字段中包含：
- `hot_money_direction`: 对象，包含 `themes`(题材数组), `stocks`(股票代码数组), `concentration`("高度集中"/"分散"/"无明显方向")
- `institution_direction`: 对象，包含 `sectors`(行业数组), `style`("防御性"/"进攻性"/"均衡配置")
- `capital_consensus`: "游资机构共振"/"游资单边进攻"/"机构独立建仓"/"资金分歧"
- `analysis`: 详细分析（200-400字）

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
