"""
迁移现有提示词到数据库

将硬编码在代码中的提示词迁移到llm_prompt_templates表

使用方法:
    cd /Volumes/MacDriver/stock-analysis/backend
    python scripts/migrate_prompt_templates.py
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.prompt_template_service import get_prompt_template_service
from app.schemas.llm_prompt_template import PromptTemplateCreate


def migrate_sentiment_analysis_prompt():
    """迁移市场情绪分析提示词"""

    print("正在迁移市场情绪分析提示词...")

    # 系统提示词
    system_prompt = "你是一位拥有20年实战经验的A股短线大师，擅长通过盘后数据精准解读市场情绪和资金动向。"

    # 用户提示词模板(使用Jinja2语法)
    user_prompt_template = """# A股盘后情绪深度分析任务

## 今日市场数据（{{ trade_date }}）

### 一、大盘基础数据
- **上证指数**: 收盘 {{ sh_close }} 点，涨跌幅 {{ sh_change }}%
- **深证成指**: 收盘 {{ sz_close }} 点，涨跌幅 {{ sz_change }}%
- **创业板指**: 收盘 {{ cyb_close }} 点，涨跌幅 {{ cyb_change }}%
- **两市总成交额**: {{ total_amount }} 亿元

### 二、情绪核心数据
- **涨停家数**: {{ limit_up_count }} 只（剔除ST）
- **跌停家数**: {{ limit_down_count }} 只
- **涨跌比**: {{ "%.2f"|format(rise_fall_ratio) }}
- **炸板率**: {{ "%.1f%%"|format(blast_rate * 100) }}
- **最高连板**: {{ max_continuous_days }} 天

#### 连板天梯树（高度分布）:
{{ continuous_ladder_text }}

#### 涨停股票列表（前10）:
{{ limit_up_stocks_text }}

#### 炸板股票列表（前5）:
{{ blast_stocks_text }}

### 三、情绪周期量化结果
- **周期阶段**: {{ cycle_stage_cn }}
- **赚钱效应指数**: {{ "%.1f"|format(money_making_index) }}/100
- **情绪得分**: {{ "%.1f"|format(sentiment_score) }}/100
- **置信度**: {{ "%.1f"|format(confidence_score) }}%
- **阶段持续天数**: {{ stage_duration_days }} 天

### 四、龙虎榜资金动向

#### 机构动向（净买入前3）:
{{ institution_top_stocks_text }}

#### 顶级游资打板（一线游资主导）:
{{ hot_money_top_stocks_text }}

#### 游资活跃度:
- 一线顶级游资出现: {{ top_tier_count }} 次
- 机构出现: {{ institution_count }} 次

---

## 请以JSON格式回答以下四个灵魂拷问

**非常重要**: 请将整个分析结果放在一个JSON代码块中，格式如下：

```json
{
  "space_analysis": { ... },
  "sentiment_analysis": { ... },
  "capital_flow_analysis": { ... },
  "tomorrow_tactics": { ... }
}
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

**现在请开始分析！**
"""

    # 定义必填变量
    required_variables = {
        "trade_date": "交易日期",
        "sh_close": "上证指数收盘价",
        "sh_change": "上证指数涨跌幅",
        "sz_close": "深证成指收盘价",
        "sz_change": "深证成指涨跌幅",
        "cyb_close": "创业板指收盘价",
        "cyb_change": "创业板指涨跌幅",
        "total_amount": "两市总成交额(亿元)",
        "limit_up_count": "涨停家数",
        "limit_down_count": "跌停家数",
        "rise_fall_ratio": "涨跌比",
        "blast_rate": "炸板率",
        "max_continuous_days": "最高连板天数",
        "continuous_ladder_text": "连板天梯文本",
        "limit_up_stocks_text": "涨停股票列表文本",
        "blast_stocks_text": "炸板股票列表文本",
        "cycle_stage_cn": "周期阶段中文",
        "money_making_index": "赚钱效应指数",
        "sentiment_score": "情绪得分",
        "confidence_score": "置信度",
        "stage_duration_days": "阶段持续天数",
        "institution_top_stocks_text": "机构动向文本",
        "hot_money_top_stocks_text": "游资动向文本",
        "top_tier_count": "一线游资出现次数",
        "institution_count": "机构出现次数"
    }

    template_data = PromptTemplateCreate(
        business_type="sentiment_analysis",
        template_name="市场情绪四维度灵魂拷问",
        template_key="soul_questioning_v1",
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
        output_format="JSON格式，包含四个字段：space_analysis, sentiment_analysis, capital_flow_analysis, tomorrow_tactics",
        required_variables=required_variables,
        optional_variables={},
        version="1.0.0",
        is_active=True,
        is_default=True,
        recommended_provider="deepseek",
        recommended_model="deepseek-chat",
        recommended_temperature=0.7,
        recommended_max_tokens=4000,
        description="市场情绪分析的核心提示词，通过四个维度（看空间、看情绪、看暗流、明日战术）全面解读盘后数据",
        changelog="初始版本，从sentiment_ai_analysis_service.py迁移",
        tags=["市场情绪", "四维度分析", "灵魂拷问"],
        created_by="system"
    )

    db = SessionLocal()
    try:
        service = get_prompt_template_service()

        # 检查是否已存在
        existing = service.get_template_by_key(db, "soul_questioning_v1")
        if existing:
            print(f"❌ 模板已存在: {existing.template_name} (ID={existing.id})")
            return

        # 创建模板
        template = service.create_template(db, template_data)
        print(f"✅ 迁移成功: {template.template_name} (ID={template.id})")
        print(f"   - 业务类型: {template.business_type}")
        print(f"   - 模板Key: {template.template_key}")
        print(f"   - 版本: {template.version}")
        print(f"   - 必填变量数: {len(template.required_variables)}")

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """主函数"""
    print("=" * 60)
    print("LLM提示词模板迁移工具")
    print("=" * 60)
    print()

    # 迁移市场情绪分析提示词
    migrate_sentiment_analysis_prompt()

    print()
    print("=" * 60)
    print("迁移完成！")
    print("=" * 60)
    print()
    print("下一步:")
    print("1. 访问 http://localhost:3001/settings/prompt-templates 查看模板")
    print("2. 修改 sentiment_ai_analysis_service.py 使用新的模板系统")
    print()


if __name__ == "__main__":
    main()
