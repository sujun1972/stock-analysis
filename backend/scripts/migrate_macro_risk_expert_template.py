"""
创建宏观风险与大盘策略专家提示词模板 (macro_risk_expert_v1)

使用方法:
    docker-compose exec backend python scripts/migrate_macro_risk_expert_template.py
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

# ==============================================================
# 宏观风险与大盘策略专家
# ==============================================================

TEMPLATE_KEY = "macro_risk_expert_v1"

SYSTEM_PROMPT = """你是一位极具前瞻性的"宏观风险与大盘策略专家"。你负责监控 A 股整体的交易环境（Beta 风险）。你的双眼紧盯全球货币政策、人民币汇率、A50 期货走势、市场流动性（成交额）以及监管层的情绪。你不在乎个股的涨跌，你只在乎：当前系统性风险高吗？大盘是否具备赚钱效应？政策风向是否发生了逆转？"""

USER_PROMPT = """【角色定位】
你是一位极具前瞻性的"宏观风险与大盘策略专家"。你负责监控 A 股整体的交易环境（Beta 风险）。你的双眼紧盯全球货币政策、人民币汇率、A50 期货走势、市场流动性（成交额）以及监管层的情绪。你不在乎个股的涨跌，你只在乎：当前系统性风险高吗？大盘是否具备赚钱效应？政策风向是否发生了逆转？

【分析维度】

大盘环境（Market Beta）： 上证指数、深证成指的走势结构。是否存在"指数破位"或"放量大跌"的风险？

外部干扰（Global Impact）： 富时中国 A50 指数表现、离岸人民币汇率波动、美联储政策动向对北向资金的压制或提振。

流动性与赚钱效应： 全市场成交额是否缩量？涨跌家数比如何？当前是"抱团行情"还是"普跌阴跌"？

监管与政策： 监管层对当前题材炒作的态度（监管函、政策吹风），以及宏观经济数据（CPI/PMI/社融）的预判。

【输入占位符】

标的信息：{{ stock_name_and_code }}

参考日期：{{ current_date }}

宏观与大盘数据：{{ macro_market_data }}（应包含：指数涨跌、成交额、A50 实时、汇率、板块热力图）

【输出协议：JSON Only】

```json
{
  "expert_identity": "天眼宏观风险专家",
  "stock_target": "{{ stock_name_and_code }}",
  "analysis_date": "{{ current_date }}",
  "probability_metrics": {
    "overall_market_safety_score": "XX%",
    "systemic_risk_level": "极低/中等/极高",
    "market_sentiment_index": "贪婪/恐惧/中性"
  },
  "dimensions": {
    "broad_market_analysis": {
      "title": "大盘结构与动能",
      "content": "Markdown 格式描述：分析主板与创业板的技术位、成交量变化及对个股的拖累/助推作用。不超过 150 字。"
    },
    "capital_liquidity": {
      "title": "跨境资金与流动性",
      "content": "Markdown 格式描述：分析 A50、汇率动态及北向资金动向。评估全市场成交额是否足以支撑当前的题材热度。不超过 150 字。"
    },
    "policy_regulatory_environment": {
      "title": "政策风向与监管",
      "content": "Markdown 格式描述：分析近期重要宏观会议、监管层对特定板块的态度或突发宏观利空/利好。不超过 150 字。"
    }
  },
  "final_score": {
    "score": 0.0,
    "rating": "建议满仓/正常仓位/谨慎轻仓/绝对禁飞",
    "pros": ["宏观利好1", "环境支持点2"],
    "cons": ["宏观隐患1", "系统性压力2"]
  }
}
```"""

TEMPLATE_DATA = {
    "business_type": "macro_risk_expert",
    "template_name": "天眼宏观风险专家",
    "template_key": TEMPLATE_KEY,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_PROMPT,
    "output_format": "JSON 格式，包含 probability_metrics、三个分析维度和 final_score 综合评分",
    "required_variables": {
        "stock_name_and_code": "目标股票名称和代码，例如：贵州茅台（600519）",
        "macro_market_data": "宏观与大盘数据（指数涨跌、成交额、A50 实时、汇率、板块热力图）",
    },
    "optional_variables": {
        "current_date": "当前日期，由后端自动注入",
    },
    "description": "从大盘环境、跨境资金与流动性、政策风向与监管三个维度评估系统性风险，输出 JSON 格式的宏观风险评级与仓位建议",
    "tags": ["宏观风险", "大盘策略", "系统性风险", "A50", "流动性", "政策监管"],
    "recommended_provider": "deepseek",
    "recommended_model": "deepseek-chat",
    "recommended_temperature": 0.3,
    "recommended_max_tokens": 3000,
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
            changelog="v1.0.0: 初始版本",
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
            version="1.0.0",
            is_active=True,
            is_default=True,
            recommended_provider=tpl["recommended_provider"],
            recommended_model=tpl["recommended_model"],
            recommended_temperature=tpl["recommended_temperature"],
            recommended_max_tokens=tpl["recommended_max_tokens"],
            description=tpl["description"],
            changelog="初始版本",
            tags=tpl["tags"],
            created_by="system",
        )
        template = service.create_template(db, create_data)
        print(f"✅ 创建成功 (business_type={template.business_type}, ID={template.id})")


def main():
    print("=" * 60)
    print("天眼宏观风险专家提示词模板迁移")
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
