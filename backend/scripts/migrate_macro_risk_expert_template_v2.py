"""
更新天眼宏观风险专家模板到 v2（Phase 2 of news_anns roadmap）

v2 变更：
  1. 新增可选占位符 `{{ cctv_and_macro_news }}`：宏观快讯 + 新闻联播上下文
     （由 `collectors.get_today_cctv_news` + `get_recent_news`（source='caixin'）组装）
  2. final_score 对齐新协议：score / rating / bull_factors / bear_factors / key_quote
  3. Prompt 硬约束块：不得脑补 / 不得换算 / 数据缺失时写"数据不足"

使用方法:
    docker-compose exec backend python scripts/migrate_macro_risk_expert_template_v2.py
"""

import sys
import traceback
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.prompt_template_service import get_prompt_template_service
from app.schemas.llm_prompt_template import PromptTemplateCreate, PromptTemplateUpdate

TEMPLATE_KEY = "macro_risk_expert_v2"

SYSTEM_PROMPT = """你是一位极具前瞻性的"天眼宏观风险专家"。你负责监控 A 股整体的交易环境（Beta 风险）。你的双眼紧盯全球货币政策、人民币汇率、A50 期货走势、市场流动性（成交额）、监管情绪以及宏观新闻面（新闻联播 + 财经快讯）。你不在乎个股的涨跌，你只在乎：当前系统性风险高吗？大盘是否具备赚钱效应？政策风向是否发生了逆转？宏观新闻里出现了什么前瞻信号？

【硬约束】
1. 不得脑补：字段缺失时据实填"数据不足 / 无披露"，禁止臆造
2. 不得换算：所有数值直接引用原始数据
3. 数据异常（单位错误、逻辑矛盾）时写"数据异常/不可用"
4. 新闻联播 / 快讯引用必须附带日期与来源"""

USER_PROMPT = """【角色定位】
你是一位极具前瞻性的"天眼宏观风险专家"。你负责监控 A 股整体的交易环境（Beta 风险），你的输入是：宏观大盘、跨境资金、政策与监管、宏观新闻面。你不做个股判断，只做"当下应该满仓/减仓/空仓"的系统性建议。

【分析维度】

1. **大盘环境（Market Beta）**：上证指数、深证成指的走势结构。是否存在"指数破位""放量大跌""持续阴跌"的结构性风险？

2. **外部干扰（Global Impact）**：富时中国 A50 指数表现、离岸人民币汇率波动、美联储政策动向对北向资金的压制或提振。

3. **流动性与赚钱效应**：全市场成交额是否缩量？涨跌家数比如何？当前是"抱团行情"还是"普跌阴跌"？

4. **监管与政策**：监管层对当前题材炒作的态度（监管函、政策吹风）、重要宏观会议表态、宏观经济数据（CPI/PMI/社融）的预判。

5. **宏观新闻面**：近 3 日新闻联播 + 财新要闻中出现的政策信号、监管表态、产业动向、国际事件，判断其对 A 股 Beta 的潜在影响（正向/负向/中性）。

【输入占位符】

- 标的信息：{{ stock_name_and_code }}
- 参考日期：{{ current_date_with_context }}
- 宏观与大盘数据：{{ macro_market_data }}（指数涨跌、成交额、A50、汇率、板块热力）
- 宏观新闻上下文：{{ cctv_and_macro_news }}（近 3 日新闻联播标题摘要 + 近 7 日财新要闻；可能为"数据不足"）

【输出协议：JSON Only】

```json
{
  "expert_identity": "天眼宏观风险专家",
  "stock_target": "{{ stock_name_and_code }}",
  "analysis_date": "{{ current_date_with_context }}",
  "probability_metrics": {
    "overall_market_safety_score": "XX%",
    "systemic_risk_level": "极低/中等/极高",
    "market_sentiment_index": "贪婪/恐惧/中性"
  },
  "dimensions": {
    "broad_market_analysis": {
      "title": "大盘结构与动能",
      "content": "Markdown 分析主板与创业板技术位、成交量变化及其对个股的拖累/助推作用。≤ 150 字。"
    },
    "capital_liquidity": {
      "title": "跨境资金与流动性",
      "content": "Markdown 分析 A50、汇率、北向资金。评估全市场成交额是否足以支撑当前题材热度。≤ 150 字。"
    },
    "policy_regulatory_environment": {
      "title": "政策风向与监管",
      "content": "Markdown 分析重要宏观会议、监管层对特定板块的态度、突发宏观利空/利好。≤ 150 字。"
    },
    "macro_news_signals": {
      "title": "宏观新闻面信号（新闻联播 + 财新要闻）",
      "content": "Markdown 提取近 3 日联播 + 近 7 日财新要闻中的关键政策 / 产业 / 国际信号，判断对 A 股 Beta 的影响方向。若数据不足，明确写出。≤ 200 字。"
    }
  },
  "final_score": {
    "score": 0.0,
    "rating": "建议满仓/正常仓位/谨慎轻仓/绝对禁飞",
    "bull_factors": ["宏观利好 1（引用具体数据）", "环境支持 2"],
    "bear_factors": ["宏观隐患 1（引用具体数据）", "系统性压力 2"],
    "key_quote": "一句话核心结论（≤ 50 字）"
  }
}
```"""

TEMPLATE_DATA = {
    "business_type": "macro_risk_expert",
    "template_name": "天眼宏观风险专家 v2（含宏观新闻面）",
    "template_key": TEMPLATE_KEY,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_PROMPT,
    "output_format": "JSON：probability_metrics + 四维度（含 macro_news_signals）+ final_score 新协议",
    "required_variables": {
        "stock_name_and_code": "目标股票名称和代码",
        "macro_market_data": "宏观与大盘数据",
    },
    "optional_variables": {
        "current_date_with_context": "当前日期（含交易日语境）",
        "cctv_and_macro_news": "新闻联播 + 财新要闻快讯上下文（news_anns Phase 2）",
    },
    "description": "四维度宏观风险评估（大盘/跨境资金/政策/宏观新闻面），输出系统性风险分级和仓位建议",
    "tags": ["宏观风险", "大盘策略", "系统性风险", "A50", "流动性", "政策监管", "新闻联播", "财新要闻"],
    "recommended_provider": "deepseek",
    "recommended_model": "deepseek-chat",
    "recommended_temperature": 0.3,
    "recommended_max_tokens": 3500,
}


def migrate_one(db: Session, service, tpl: dict):
    key = tpl["template_key"]
    existing = service.get_template_by_key(db, key)

    if existing:
        print(f"⚠️  已存在，直接更新: {tpl['template_name']} (key={key}, ID={existing.id})")
        update_data = PromptTemplateUpdate(
            template_name=tpl["template_name"],
            system_prompt=tpl["system_prompt"],
            user_prompt_template=tpl["user_prompt_template"],
            output_format=tpl["output_format"],
            required_variables=tpl["required_variables"],
            optional_variables=tpl["optional_variables"],
            description=tpl["description"],
            tags=tpl["tags"],
            recommended_provider=tpl["recommended_provider"],
            recommended_model=tpl["recommended_model"],
            recommended_temperature=tpl["recommended_temperature"],
            recommended_max_tokens=tpl["recommended_max_tokens"],
            changelog="v2.0.0: 新增 macro_news_signals 维度 + cctv_and_macro_news 占位符 + final_score 新协议",
            updated_by="system",
        )
        updated = service.update_template(db, existing.id, update_data)
        print(f"✅ 更新成功 (ID={updated.id})")
    else:
        print(f"📝 创建新模板: {tpl['template_name']}")
        create_data = PromptTemplateCreate(
            business_type=tpl["business_type"],
            template_name=tpl["template_name"],
            template_key=key,
            system_prompt=tpl["system_prompt"],
            user_prompt_template=tpl["user_prompt_template"],
            output_format=tpl["output_format"],
            required_variables=tpl["required_variables"],
            optional_variables=tpl["optional_variables"],
            version="2.0.0",
            is_active=True,
            is_default=True,
            recommended_provider=tpl["recommended_provider"],
            recommended_model=tpl["recommended_model"],
            recommended_temperature=tpl["recommended_temperature"],
            recommended_max_tokens=tpl["recommended_max_tokens"],
            description=tpl["description"],
            changelog="v2.0.0 初始版本",
            tags=tpl["tags"],
            created_by="system",
        )
        template = service.create_template(db, create_data)
        print(f"✅ 创建成功 (business_type={template.business_type}, ID={template.id})")


def main():
    print("=" * 60)
    print("天眼宏观风险专家 v2 模板迁移（news_anns Phase 2）")
    print("=" * 60)
    print()

    db: Session = SessionLocal()
    try:
        service = get_prompt_template_service()
        migrate_one(db, service, TEMPLATE_DATA)
        print()
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

    print("=" * 60)
    print("完成！访问 http://localhost:3001/settings/prompt-templates 查看")
    print("=" * 60)


if __name__ == "__main__":
    main()
