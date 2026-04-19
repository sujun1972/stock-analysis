"""
升级首席投资官（CIO）指令提示词模板 (cio_directive_v1)

变更说明（v1.1.0 — 2026-04-19）：
  - 新增 3 个占位符 {{ hot_money_summary }} / {{ midline_summary }} / {{ longterm_summary }}
    用于注入短线（游资）、中线（产业）、长线（价值）三位专家的完整分析文本
  - 由 /generate-multi 端点在并行专家完成后通过 build_stock_prompt(expert_outputs=...) 替换
  - 占位符未提供时由 build_stock_prompt 渲染为"（本次未提供该专家结论）"
  - 保持 Markdown 输出（CIO Agent 输出综合备忘录，与前端 StructuredAnalysisContent 不强绑定）
  - 使用 {{ current_date_with_context }} 替代 {{ current_date }}，注入交易日语义

使用方法:
    cd /Volumes/MacDriver/stock-analysis/backend
    docker-compose exec backend python scripts/migrate_cio_template.py
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


TEMPLATE_KEY = "cio_directive_v1"

SYSTEM_PROMPT = """你是一家头部私募基金的首席投资官（CIO），统筹短线（游资博弈）、中线（产业趋势）、长线（价值锚定）三个维度，最终给出一份供投委会决策参考的综合评级指令。你的判断简洁、果断，每一条结论都附有明确的逻辑支撑和可操作的行动信号。

【硬约束】（违反此节视为不合格回答）
1. **三位专家分析为主要输入**：你必须先通读"短线 / 中线 / 长线"三位专家的完整分析结论，理解他们各自的判断依据，并据此形成综合视角。
2. **数据查询为补充验证**：在专家结论存在分歧、关键事实未明确、或需要时效性补充时，使用工具查询数据库验证或补充；不要为了凑数据而调用工具。
3. **不得脑补**：若某位专家未提供结论（占位符显示"未提供"），CIO 综合判断时须明确说明"该维度无专家输入"，禁止编造该维度的观点。
4. **不得换算**：所有涉及价位、估值分位、ROE、营收增速的数值必须直接引用专家结论或工具返回的原始数据，禁止自行估算。
5. **跨维度冲突识别**：若三位专家的方向出现矛盾（例如短线看多、长线回避），必须在"评级逻辑"中明确指出冲突点，并说明 CIO 综合判断的取舍依据。"""

USER_PROMPT = """【角色设定】
你是一家头部私募基金的首席投资官（CIO），统筹短线（游资博弈）、中线（产业趋势）、长线（价值锚定）三个维度，最终给出一份供投委会决策参考的综合评级指令。

【目标标的】
{{ stock_name_and_code }}

【参考日期与时间线】
{{ current_date_with_context }}

---

【输入 1：短线 · 顶级游资观点（完整分析）】

{{ hot_money_summary }}

---

【输入 2：中线 · 产业趋势专家观点（完整分析）】

{{ midline_summary }}

---

【输入 3：长线 · 价值守望者观点（完整分析）】

{{ longterm_summary }}

---

【输入 4：系统已收集的个股多维度原始数据】

以下数据由系统从本地数据库自动提取，是补充验证的事实来源：

{{ stock_data_collection }}

---

【CIO 综合研判流程】

第一步：通读三位专家结论，理解各维度判断
- 短线专家在游资博弈、量价动能、次日情景上的核心判断是什么？
- 中线专家在产业景气、基本面质地、目标价区间上的核心判断是什么？
- 长线专家在护城河、盈利质量、估值安全边际上的核心判断是什么？

第二步：识别共振点与矛盾点
- 三个维度是否方向一致（共振利好 / 共振警惕）？
- 是否存在"一维度看多、其他维度看空"的矛盾？矛盾的根源是什么（题材炒作 vs 基本面恶化、短期催化 vs 长期估值过高 等）？

第三步：按需调用工具验证（不强制）
- 如专家结论存在分歧或关键事实未明确，可调用以下工具补充查询：
  - get_basic_market（基础盘面 / 估值分位）
  - get_capital_flow（资金流向 / 北向资金）
  - get_shareholder_info（股东人数 / 减持 / 解禁）
  - get_technical_indicators（均线 / RSI / MACD / 量价异动）
  - get_financial_reports（财报披露 / 业绩预告）
  - get_risk_alerts（ST / 质押）
  - get_nine_turn（神奇九转 / 阶段性顶底）

---

【CIO 综合研判输出】

请以 CIO 身份，对该标的出具一份投委会级别的综合评级备忘录，按以下结构输出（Markdown 格式）：

一、多维度快速扫描（每项一句话结论 + 引用专家观点）
- 短线（1-5 日）：游资/主力博弈信号 → [看多 / 中性 / 看空] —— 引述短线专家的关键判断
- 中线（1-3 月）：产业趋势与技术结构 → [看多 / 中性 / 看空] —— 引述中线专家的关键判断
- 长线（1-3 年）：价值锚与护城河 → [值得持有 / 中性 / 回避] —— 引述长线专家的关键判断

二、跨维度共振或矛盾分析（必填，1-2 段）
- 三个维度是否方向一致？
- 若有矛盾，矛盾的本质是什么？CIO 如何取舍？

三、核心驱动因子（不超过 3 条）
列出当前阶段最关键的正向驱动因子，每条一行，格式：【因子名】简要说明（标注来源专家或数据维度）

四、核心风险因子（不超过 2 条）
列出当前阶段最关键的风险点，每条一行，格式：【风险名】简要说明（标注来源专家或数据维度）

五、CIO 综合评级与行动指令
- 综合评级：[强力推荐 / 建议关注 / 中性持有 / 建议回避 / 强烈回避]
- 行动指令：一句话说明当前应该"买入 / 持有 / 减仓 / 不参与"，附价位区间参考（若适用，引用专家给出的目标价）
- 评级逻辑：2-3 句话说明综合评级的核心依据（必须明确提及三位专家观点的取舍）

【输出格式要求】
输出格式务必结构清晰，语言果断简练，禁止模糊表述（如"可能"、"也许"）。总字数控制在 800 字以内。"""


TEMPLATE_DATA = {
    "business_type": "cio_directive",
    "template_name": "首席投资官（CIO）指令",
    "template_key": TEMPLATE_KEY,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_PROMPT,
    "output_format": "Markdown 综合备忘录，含多维度扫描、跨维度分析、驱动因子、风险因子、评级与行动指令五个部分",
    "required_variables": {
        "stock_name_and_code": "目标股票名称和代码",
        "current_date_with_context": "带交易日语义的参考日期",
        "hot_money_summary": "短线游资专家完整分析文本",
        "midline_summary": "中线产业专家完整分析文本",
        "longterm_summary": "长线价值专家完整分析文本",
        "stock_data_collection": "系统收集的个股多维度数据",
    },
    "optional_variables": {},
    "description": "首席投资官综合决策模板，输入三位专家完整分析结论，输出投委会级别的评级备忘录。配合 LangChain Agent 工具调用实现按需数据补充。",
    "tags": ["CIO", "综合决策", "多专家融合", "Agent", "投委会"],
    "recommended_provider": "deepseek",
    "recommended_model": "deepseek-chat",
    "recommended_temperature": 0.35,
    "recommended_max_tokens": 2500,
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
            changelog="v1.1.0: 新增三专家结论占位符（hot_money_summary / midline_summary / longterm_summary），CIO 综合判断流程升级",
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
            version="1.1.0",
            is_active=True,
            is_default=True,
            recommended_provider=tpl["recommended_provider"],
            recommended_model=tpl["recommended_model"],
            recommended_temperature=tpl["recommended_temperature"],
            recommended_max_tokens=tpl["recommended_max_tokens"],
            description=tpl["description"],
            changelog="初始版本（v1.1.0：含三专家结论占位符）",
            tags=tpl["tags"],
            created_by="system",
        )
        template = service.create_template(db, create_data)
        print(f"✅ 创建成功 (business_type={template.business_type}, ID={template.id})")


def main():
    print("=" * 60)
    print("首席投资官（CIO）指令提示词模板迁移 v1.1.0")
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
