"""
创建/更新"顶级游资观点"提示词模板

template_key: top_speculative_investor_v1
business_type: hot_money_view

变更说明（v2.0.0）：
  - 移除"由 AI 收集数据"的描述
  - 新增 {{ stock_data_collection }} 占位符，由系统自动填入当天的个股数据分析
  - 模板结构调整：个股数据作为已知输入，AI 专注于游资逻辑推演

使用方法:
    cd /Volumes/MacDriver/stock-analysis/backend
    python scripts/migrate_hot_money_view_template.py
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

TEMPLATE_KEY = "top_speculative_investor_v1"

SYSTEM_PROMPT = """你是一名拥有 15 年实战经验的 A 股顶级游资操盘手，深谙短线资金博弈之道。你能从公开盘面数据、龙虎榜动向和市场情绪中，精准判断游资是否有意参与某只股票的行情。"""

USER_PROMPT_TEMPLATE = """【角色设定】
你是一名拥有 15 年实战经验的 A 股顶级游资操盘手，深谙短线资金博弈之道。

【目标标的】
{{ stock_name_and_code }}

【系统已收集的个股多维度数据】
以下数据由系统从本地数据库自动提取，截至今日（{{ current_date }}）：

{{ stock_data_collection }}

---

【分析任务】

基于以上数据，请从顶级游资视角对该标的进行综合研判：

一、资金结构研判
- 主力资金的近期动向是否呈现游资特征（短线快进快出 vs 机构慢慢建仓）？
- 换手率与股东人数变化是否暗示筹码在向强势资金集中？

二、技术形态与介入窗口
- 当前均线结构是否具备游资喜欢的"顺势"条件？
- 近期是否有量价配合的启动信号或明显的出货迹象？

三、游资参与意愿评估
- 综合行业位置、资金流向、板块联动，该股是否符合当前游资的偏好题材？
- 评估游资潜在参与度：高（可能主导行情）/ 中（跟随参与）/ 低（暂不关注）

四、操作建议（基于以上分析）
- 若游资参与意愿高：潜在关注价位区间及止损参考
- 若游资参与意愿低：说明主要制约因素

【输出格式】
请用简洁的短线交易语言输出，避免学术化表达。重点突出关键信号，每个维度不超过 150 字。"""

TEMPLATE_DATA = {
    "business_type": "hot_money_view",
    "template_name": "顶级游资观点",
    "template_key": TEMPLATE_KEY,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_PROMPT_TEMPLATE,
    "output_format": "结构化文本，按四个维度分节输出，语言简洁，聚焦短线逻辑",
    "required_variables": {
        "stock_name_and_code": "目标股票名称和代码，例如：恒逸石化（000703）",
        "stock_data_collection": "由系统自动填入的个股多维度数据（基础盘面、资金流向、技术指标、财报公告）",
    },
    "optional_variables": {
        "current_date": "当前日期，由后端自动注入",
    },
    "description": "基于系统自动收集的个股多维度数据，从顶级游资视角进行综合研判，评估游资参与意愿并给出操作建议",
    "tags": ["游资观点", "短线分析", "资金博弈", "量价分析"],
    "recommended_provider": "deepseek",
    "recommended_model": "deepseek-chat",
    "recommended_temperature": 0.4,
    "recommended_max_tokens": 3000,
}


def migrate():
    db: Session = SessionLocal()
    try:
        service = get_prompt_template_service()
        existing = service.get_template_by_key(db, TEMPLATE_KEY)

        if existing:
            print(f"⚠️  模板已存在 (key={TEMPLATE_KEY}, ID={existing.id})，直接更新内容...")
            update_data = PromptTemplateUpdate(
                template_name=TEMPLATE_DATA["template_name"],
                system_prompt=TEMPLATE_DATA["system_prompt"],
                user_prompt_template=TEMPLATE_DATA["user_prompt_template"],
                output_format=TEMPLATE_DATA["output_format"],
                required_variables=TEMPLATE_DATA["required_variables"],
                optional_variables=TEMPLATE_DATA["optional_variables"],
                description=TEMPLATE_DATA["description"],
                tags=TEMPLATE_DATA["tags"],
                recommended_provider=TEMPLATE_DATA["recommended_provider"],
                recommended_model=TEMPLATE_DATA["recommended_model"],
                recommended_temperature=TEMPLATE_DATA["recommended_temperature"],
                recommended_max_tokens=TEMPLATE_DATA["recommended_max_tokens"],
                changelog="v2.0.0: 移除 AI 数据收集职责，新增 {{ stock_data_collection }} 占位符由系统自动填入当天个股数据",
                updated_by="system",
            )
            updated = service.update_template(db, existing.id, update_data)
            print(f"✅ 模板更新成功 (ID={updated.id})")
        else:
            print(f"📝 模板不存在，创建新模板...")
            template_data = PromptTemplateCreate(
                business_type=TEMPLATE_DATA["business_type"],
                template_name=TEMPLATE_DATA["template_name"],
                template_key=TEMPLATE_KEY,
                system_prompt=TEMPLATE_DATA["system_prompt"],
                user_prompt_template=TEMPLATE_DATA["user_prompt_template"],
                output_format=TEMPLATE_DATA["output_format"],
                required_variables=TEMPLATE_DATA["required_variables"],
                optional_variables=TEMPLATE_DATA["optional_variables"],
                version="2.0.0",
                is_active=True,
                is_default=True,
                recommended_provider=TEMPLATE_DATA["recommended_provider"],
                recommended_model=TEMPLATE_DATA["recommended_model"],
                recommended_temperature=TEMPLATE_DATA["recommended_temperature"],
                recommended_max_tokens=TEMPLATE_DATA["recommended_max_tokens"],
                description=TEMPLATE_DATA["description"],
                changelog="初始版本：基于系统收集数据的游资观点分析",
                tags=TEMPLATE_DATA["tags"],
                created_by="system",
            )
            template = service.create_template(db, template_data)
            print(f"✅ 创建成功: {template.template_name} (ID={template.id})")

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def main():
    print("=" * 60)
    print("顶级游资观点提示词模板迁移 (v2.0.0)")
    print("=" * 60)
    print()
    migrate()
    print()
    print("=" * 60)
    print("完成！访问 http://localhost:3001/settings/prompt-templates 查看")
    print("=" * 60)


if __name__ == "__main__":
    main()
