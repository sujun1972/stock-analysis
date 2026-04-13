"""
创建三个专家观点提示词模板：
  - 中线产业趋势专家观点 (midline_industry_expert_v1)
  - 长线价值守望者观点 (longterm_value_watcher_v1)
  - 首席投资官（CIO）指令 (cio_directive_v1)

使用方法:
    cd /Volumes/MacDriver/stock-analysis/backend
    python scripts/migrate_expert_view_templates.py
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
# 模板 1：中线产业趋势专家观点
# ==============================================================

MIDLINE_TEMPLATE_KEY = "midline_industry_expert_v1"

MIDLINE_SYSTEM_PROMPT = """你是一名深耕 A 股产业研究 12 年的中线趋势分析师，专注于识别产业景气周期的拐点，善于从行业供需结构、政策催化和龙头效应中寻找 3-12 个月维度的趋势性机会。"""

MIDLINE_USER_PROMPT = """【角色设定】
你是一名深耕 A 股产业研究 12 年的中线趋势分析师，专注于识别产业景气周期的拐点，善于从行业供需结构、政策催化和龙头效应中寻找 3-12 个月维度的趋势性机会。

【目标标的】
{{ stock_name_and_code }}

【系统已收集的个股多维度数据】
以下数据由系统从本地数据库自动提取，截至今日（{{ current_date }}）：

{{ stock_data_collection }}

---

【分析任务】

基于以上数据，请从中线产业趋势视角对该标的进行综合研判：

一、产业景气度判断
- 该股所处行业当前处于景气周期的哪个阶段（复苏 / 扩张 / 过热 / 收缩）？
- 近期是否有政策、技术突破或供需拐点驱动该行业进入新一轮上行周期？

二、公司基本面质地
- 该公司在行业中的竞争地位（龙头 / 二线 / 跟随者）及护城河宽度？
- 盈利趋势：近两个季报的收入/利润增速是否与行业景气度方向一致？

三、中线技术结构
- 周线/月线级别是否形成趋势性上攻结构（均线多头排列、成交量温和放大）？
- 当前股价与 MA60/MA120 的位置关系，是否具备中线安全边际？

四、风险与催化剂
- 主要下行风险：行业政策收紧、原材料成本压力、大股东减持等
- 潜在催化剂：季报超预期、行业订单数据、重大合同公告

【输出格式】
用专业但不晦涩的语言输出，每个维度不超过 200 字，重点突出中线（3-12 个月）逻辑，给出明确的"建议持续关注 / 等待入场时机 / 暂时观望"结论。"""

MIDLINE_TEMPLATE_DATA = {
    "business_type": "midline_industry_expert",
    "template_name": "中线产业趋势专家观点",
    "template_key": MIDLINE_TEMPLATE_KEY,
    "system_prompt": MIDLINE_SYSTEM_PROMPT,
    "user_prompt_template": MIDLINE_USER_PROMPT,
    "output_format": "结构化文本，按四个维度分节输出，聚焦 3-12 个月中线逻辑，给出明确结论",
    "required_variables": {
        "stock_name_and_code": "目标股票名称和代码，例如：宁德时代（300750）",
        "stock_data_collection": "由系统自动填入的个股多维度数据（基础盘面、资金流向、技术指标、财报公告）",
    },
    "optional_variables": {
        "current_date": "当前日期，由后端自动注入",
    },
    "description": "基于系统自动收集的个股多维度数据，从产业景气度、基本面质地、中线技术结构和风险催化剂四个维度进行中线趋势研判",
    "tags": ["中线分析", "产业趋势", "景气周期", "基本面"],
    "recommended_provider": "deepseek",
    "recommended_model": "deepseek-chat",
    "recommended_temperature": 0.4,
    "recommended_max_tokens": 3000,
}

# ==============================================================
# 模板 2：长线价值守望者观点
# ==============================================================

LONGTERM_TEMPLATE_KEY = "longterm_value_watcher_v1"

LONGTERM_SYSTEM_PROMPT = """你是一名坚守价值投资理念 20 年的 A 股长线基金经理，以 DCF 估值为锚，以护城河深度为筛选标准，专注于寻找被市场低估、具备长达 3-5 年复利增长潜力的优质标的。"""

LONGTERM_USER_PROMPT = """【角色设定】
你是一名坚守价值投资理念 20 年的 A 股长线基金经理，以 DCF 估值为锚，以护城河深度为筛选标准，专注于寻找被市场低估、具备长达 3-5 年复利增长潜力的优质标的。

【目标标的】
{{ stock_name_and_code }}

【系统已收集的个股多维度数据】
以下数据由系统从本地数据库自动提取，截至今日（{{ current_date }}）：

{{ stock_data_collection }}

---

【分析任务】

基于以上数据，请从长线价值投资视角对该标的进行深度研判：

一、商业模式与护城河
- 该公司的核心商业模式是否具备可持续的竞争优势（品牌、规模、网络效应、专利、成本）？
- 护城河宽度评级：宽（Wide Moat）/ 窄（Narrow Moat）/ 无（No Moat），并说明理由。

二、长期盈利质量
- ROE 水平（近三年均值）是否稳定在 15% 以上，自由现金流是否为正且持续增长？
- 资产负债结构是否健康（资产负债率、有息负债/EBITDA）？

三、估值安全边际
- 当前 PE-TTM / PB 与历史均值及行业中位数的对比，是否处于历史低估区间？
- 基于 PEG 或简化 DCF 视角，给出粗略的内在价值区间判断。

四、长线持有风险
- 核心风险：行业天花板临近、商业模式被颠覆、管理层诚信问题、股权质押风险
- 大股东/机构持仓变化是否发出警示信号？

【输出格式】
用沉稳、理性的价值投资语言输出，每个维度不超过 200 字。结尾给出"值得长线配置 / 持续跟踪待低位 / 不符合价值标准"三选一结论，并附 1-2 句核心逻辑支撑。"""

LONGTERM_TEMPLATE_DATA = {
    "business_type": "longterm_value_watcher",
    "template_name": "长线价值守望者观点",
    "template_key": LONGTERM_TEMPLATE_KEY,
    "system_prompt": LONGTERM_SYSTEM_PROMPT,
    "user_prompt_template": LONGTERM_USER_PROMPT,
    "output_format": "结构化文本，按四个维度分节输出，价值投资语言，给出三选一配置结论",
    "required_variables": {
        "stock_name_and_code": "目标股票名称和代码，例如：贵州茅台（600519）",
        "stock_data_collection": "由系统自动填入的个股多维度数据（基础盘面、资金流向、技术指标、财报公告）",
    },
    "optional_variables": {
        "current_date": "当前日期，由后端自动注入",
    },
    "description": "基于系统自动收集的个股多维度数据，从商业模式护城河、长期盈利质量、估值安全边际和长线持有风险四个维度进行价值投资研判",
    "tags": ["长线投资", "价值投资", "护城河", "估值分析", "DCF"],
    "recommended_provider": "deepseek",
    "recommended_model": "deepseek-chat",
    "recommended_temperature": 0.3,
    "recommended_max_tokens": 3500,
}

# ==============================================================
# 模板 3：首席投资官（CIO）指令
# ==============================================================

CIO_TEMPLATE_KEY = "cio_directive_v1"

CIO_SYSTEM_PROMPT = """你是一家头部私募基金的首席投资官（CIO），统筹短线、中线、长线三个维度，最终给出一份供投委会决策参考的综合评级指令。你的判断简洁、果断，每一条结论都附有明确的逻辑支撑和可操作的行动信号。"""

CIO_USER_PROMPT = """【角色设定】
你是一家头部私募基金的首席投资官（CIO），统筹短线、中线、长线三个维度，最终给出一份供投委会决策参考的综合评级指令。你的判断简洁、果断，每一条结论都附有明确的逻辑支撑和可操作的行动信号。

【目标标的】
{{ stock_name_and_code }}

【系统已收集的个股多维度数据】
以下数据由系统从本地数据库自动提取，截至今日（{{ current_date }}）：

{{ stock_data_collection }}

---

【CIO 综合研判指令】

请以 CIO 身份，对该标的出具一份投委会级别的综合评级备忘录：

一、多维度快速扫描（每项一句话结论）
- 短线（1-5 日）：游资/主力博弈信号 → [看多 / 中性 / 看空]
- 中线（1-3 月）：产业趋势与技术结构 → [看多 / 中性 / 看空]
- 长线（1-3 年）：价值锚与护城河 → [值得持有 / 中性 / 回避]

二、核心驱动因子（不超过 3 条）
列出当前阶段最关键的正向驱动因子，每条一行，格式：【因子名】简要说明

三、核心风险因子（不超过 2 条）
列出当前阶段最关键的风险点，每条一行，格式：【风险名】简要说明

四、CIO 综合评级与行动指令
- 综合评级：[强力推荐 / 建议关注 / 中性持有 / 建议回避 / 强烈回避]
- 行动指令：一句话说明当前应该"买入 / 持有 / 减仓 / 不参与"，附价位区间参考（若适用）
- 评级逻辑：2-3 句话说明综合评级的核心依据

【输出格式要求】
输出格式务必结构清晰，语言果断简练，禁止模糊表述（如"可能"、"也许"）。总字数控制在 500 字以内。"""

CIO_TEMPLATE_DATA = {
    "business_type": "cio_directive",
    "template_name": "首席投资官（CIO）指令",
    "template_key": CIO_TEMPLATE_KEY,
    "system_prompt": CIO_SYSTEM_PROMPT,
    "user_prompt_template": CIO_USER_PROMPT,
    "output_format": "投委会备忘录格式，四节结构，语言果断，综合评级五选一，总字数≤500字",
    "required_variables": {
        "stock_name_and_code": "目标股票名称和代码，例如：中国平安（601318）",
        "stock_data_collection": "由系统自动填入的个股多维度数据（基础盘面、资金流向、技术指标、财报公告）",
    },
    "optional_variables": {
        "current_date": "当前日期，由后端自动注入",
    },
    "description": "基于系统自动收集的个股多维度数据，以 CIO 视角统筹短中长三个维度，出具投委会级别的综合评级指令，给出明确行动信号",
    "tags": ["综合研判", "CIO指令", "多维度分析", "投资评级", "行动信号"],
    "recommended_provider": "deepseek",
    "recommended_model": "deepseek-chat",
    "recommended_temperature": 0.35,
    "recommended_max_tokens": 2500,
}

# ==============================================================

ALL_TEMPLATES = [MIDLINE_TEMPLATE_DATA, LONGTERM_TEMPLATE_DATA, CIO_TEMPLATE_DATA]


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
    print("专家观点提示词模板迁移")
    print("=" * 60)
    print()

    db: Session = SessionLocal()
    try:
        service = get_prompt_template_service()
        for tpl in ALL_TEMPLATES:
            migrate_one(db, service, tpl)
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
