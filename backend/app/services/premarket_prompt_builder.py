"""盘前碰撞分析 - Prompt 构建模块

职责：
- 维护 COLLISION_PROMPT 模板常量
- 将昨晚战术 + 今晨外盘 + 核心快讯格式化为 LLM Prompt
- 将碰撞分析 JSON 结果格式化为极简行动指令（200 字以内）
"""

import json
from typing import Dict, Any
from loguru import logger


class PremarketPromptBuilder:
    """盘前碰撞 Prompt 构建器"""

    COLLISION_PROMPT = """# A股盘前计划碰撞测试任务

你是一位拥有20年实战经验的A股短线大师,现在需要在开盘前(8:00-8:30)进行"计划碰撞测试"。

## 输入A：昨晚的计划(来自明日战术日报)

{yesterday_tactics}

## 输入B：今晨的环境(隔夜外盘数据)

### 外盘核心指标
- **富时A50期指**: {a50_change}%  ← 直接影响A股大盘开盘
- **中概股指数**: {china_concept_change}%  ← 外资对中国资产的态度
- **WTI原油**: {oil_change}%  | **COMEX黄金**: {gold_change}%  | **伦敦铜**: {copper_change}%
- **美元兑人民币**: {usdcnh_change}%  ← 外资流向指标
- **美股三大指数**: 标普{sp500_change}% | 纳指{nasdaq_change}% | 道指{dow_change}%

## 输入C：突发新闻(22:00-8:00核心快讯)

{critical_news}

---

## 请执行以下分析,并以JSON格式输出

**非常重要**: 请将整个分析结果放在一个JSON代码块中，格式如下：

```json
{{
  "macro_tone": {{
    "direction": "高开/低开/平开",
    "confidence": "置信度(%)",
    "a50_impact": "A50对开盘的具体影响分析",
    "reasoning": "综合外盘判断(100字)"
  }},
  "holdings_alert": {{
    "has_risk": true,
    "affected_sectors": ["板块1", "板块2"],
    "affected_stocks": [
      {{"code": "000001", "name": "某股票", "reason": "利空原因"}}
    ],
    "actions": "针对持仓的具体操作建议"
  }},
  "plan_adjustment": {{
    "cancel_buy": [
      {{"stock": "000001", "reason": "昨晚计划买入,但今晨外盘XX,取消"}}
    ],
    "early_stop_loss": [
      {{"stock": "600000", "reason": "昨晚计划止损XX价,但今晨新闻YY,提前到竞价止损"}}
    ],
    "keep_plan": "哪些计划依然有效,可以继续执行",
    "reasoning": "调整理由(150字)"
  }},
  "auction_focus": {{
    "stocks": [
      {{"code": "000001", "name": "某股票", "reason": "竞价必盯原因"}}
    ],
    "conditions": {{
      "participate_conditions": "如果XXX,则参与竞价买入",
      "avoid_conditions": "如果YYY,则竞价止损"
    }},
    "actions": "9:15-9:25具体操作步骤"
  }}
}}
```

## 核心要求

1. **宏观定调**: 根据A50和外盘,预测今日A股开盘是高开情绪好,还是低开有压力?
2. **持仓排雷**: 今晨的新闻中,是否有针对我计划中关注板块/个股的重大利空或利好?
3. **计划修正(最关键)**: 基于今晨环境,昨晚的买入计划是否需要取消?昨晚的止损动作是否需要提前到竞价阶段直接核按钮?
4. **竞价盯盘目标**: 给出今早9:15-9:25必须死盯的1-2个核心标的及应对条件

**输出格式**: 必须输出完整的JSON代码块,避免编造不存在的股票代码。如果昨晚的战术日报中没有具体股票,则根据市场情绪和外盘环境给出通用建议。

现在请开始碰撞测试!
"""

    def build_collision_prompt(
        self,
        yesterday_tactics: Dict[str, Any],
        overnight_data: Dict[str, float],
        critical_news: str,
    ) -> str:
        """构建碰撞测试 Prompt"""
        tactics_text = json.dumps(yesterday_tactics, ensure_ascii=False, indent=2)

        return self.COLLISION_PROMPT.format(
            yesterday_tactics=tactics_text,
            a50_change=overnight_data.get('a50_change', 0),
            china_concept_change=overnight_data.get('china_concept_change', 0),
            oil_change=overnight_data.get('wti_crude_change', 0),
            gold_change=overnight_data.get('comex_gold_change', 0),
            copper_change=overnight_data.get('lme_copper_change', 0),
            usdcnh_change=overnight_data.get('usdcnh_change', 0),
            sp500_change=overnight_data.get('sp500_change', 0),
            nasdaq_change=overnight_data.get('nasdaq_change', 0),
            dow_change=overnight_data.get('dow_change', 0),
            critical_news=critical_news,
        )

    def format_action_command(self, analysis: Dict[str, Any]) -> str:
        """基于碰撞分析结果生成极简行动指令（200 字以内）"""
        if analysis.get("parse_failed"):
            return "AI分析解析失败,请手动查看完整报告"

        try:
            macro = analysis.get('macro_tone', {})
            holdings = analysis.get('holdings_alert', {})
            adjustment = analysis.get('plan_adjustment', {})
            auction = analysis.get('auction_focus', {})

            command_lines = []

            direction = macro.get('direction', '未知')
            confidence = macro.get('confidence', '?')
            command_lines.append(f"【开盘预期】{direction}, 信心{confidence}")

            if holdings.get('has_risk'):
                affected = holdings.get('affected_stocks', [])
                if affected:
                    stock_names = ', '.join([s.get('name', s.get('code', '')) for s in affected[:2]])
                    command_lines.append(f"【风险提示】{stock_names}有利空, 关注")

            cancel_count = len(adjustment.get('cancel_buy', []))
            stop_count = len(adjustment.get('early_stop_loss', []))
            if cancel_count > 0 or stop_count > 0:
                command_lines.append(f"【计划修正】取消买入{cancel_count}只, 提前止损{stop_count}只")
            else:
                keep_plan = adjustment.get('keep_plan', '')
                if keep_plan:
                    command_lines.append(f"【计划修正】{keep_plan[:30]}")

            focus_stocks = auction.get('stocks', [])
            if focus_stocks:
                stock_names = ', '.join([s.get('name', s.get('code', '')) for s in focus_stocks[:2]])
                command_lines.append(f"【竞价盯盘】死盯: {stock_names}")

            return "\n".join(command_lines) if command_lines else "今日保持观望，谨慎参与"

        except Exception as e:
            logger.error(f"生成行动指令失败: {e}")
            return "行动指令生成失败,请查看详细分析"


premarket_prompt_builder = PremarketPromptBuilder()
