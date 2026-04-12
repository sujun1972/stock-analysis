"""
迁移个股数据收集提示词模板到数据库

新增模板：
  - stock_data_collection  个股多维度数据收集

使用方法:
    cd /Volumes/MacDriver/stock-analysis/backend
    python scripts/migrate_stock_data_collection_template.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.prompt_template_service import get_prompt_template_service
from app.schemas.llm_prompt_template import PromptTemplateCreate

SYSTEM_PROMPT = """你是一名专业的证券数据研究员，具备极强的数据抓取与清洗能力。你的任务是针对特定股票，检索并整理截至指定日期的多维度客观资讯。"""

USER_PROMPT_TEMPLATE = """【角色设定】
你是一名专业的证券数据研究员，具备极强的数据抓取与清洗能力。你的任务是针对特定股票，检索并整理截至指定日期的多维度客观资讯。

【硬性执行标准】

纯数据输出：禁止任何主观评论、定性分析、买入建议或评分。

真实性原则：严禁捏造数据。

时间锚点：当前的真实日期是 {{ current_date }}。所有数据需以该时间点为基准，调取最近一个交易日{{ latest_trade_date }}及近期的历史记录。

【目标标的】
{{ stock_name_and_code }}

【输出格式与维度要求】

一、 基础盘面与行业位置
收盘价/涨跌幅：[元 / %]

成交额/换手率：[元 / %]

市盈率 (PE-TTM)：

行业坐标：所属板块（汽车零部件）近5个交易日的涨跌幅对比。

筹码获利比：当前股价下，市场获利筹码的近似比例（%）。

二、 资金流向与筹码变动（核心）
资金流向：近1日/5日/10日主力资金净流入/流出金额。

北向资金：最新持股数及较上季度的增减比例。

股东人数：列出近四个季度的数值及环比变化率。

重要减持/解禁：近三个月内大股东减持的明细（日期、价格、数量）及未来一月内的解禁预告。

三、 技术指标详情
均线数值：必须提供 MA5, MA10, MA20, MA60, MA120 的具体价位。

量价异动：最近5个交易日内是否存在"放量滞涨"或"缩量回调"的情况。

RSI (7/14/21)：列出三个周期的完整数值。

四、 财报与敏感公告
财报预约：年报及一季报的具体披露日期。

风险警示：近一个月内是否有监管发函、违规违规、质押冻结等公告。"""

TEMPLATE = {
    "business_type": "stock_data_collection",
    "template_name": "个股多维度数据收集",
    "template_key": "stock_data_collection_v1",
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_PROMPT_TEMPLATE,
    "output_format": "结构化文本，按维度分节输出，禁止主观评论与买入建议",
    "required_variables": {
        "stock_name_and_code": "目标股票名称和代码，例如：比亚迪（002594）",
    },
    "optional_variables": {},
    "description": "针对特定股票收集多维度客观资讯，包含基础盘面、资金流向、技术指标、财报公告四大维度，纯数据输出无主观评论",
    "tags": ["个股分析", "数据收集", "资金流向", "技术指标", "基本面"],
    "recommended_provider": "deepseek",
    "recommended_model": "deepseek-chat",
    "recommended_temperature": 0.2,
    "recommended_max_tokens": 4000,
}


def migrate():
    db: Session = SessionLocal()
    try:
        service = get_prompt_template_service()

        key = TEMPLATE["template_key"]
        existing = service.get_template_by_key(db, key)
        if existing:
            print(f"⚠️  已存在，跳过: {TEMPLATE['template_name']} (key={key}, ID={existing.id})")
            return

        template_data = PromptTemplateCreate(
            business_type=TEMPLATE["business_type"],
            template_name=TEMPLATE["template_name"],
            template_key=key,
            system_prompt=TEMPLATE["system_prompt"],
            user_prompt_template=TEMPLATE["user_prompt_template"],
            output_format=TEMPLATE["output_format"],
            required_variables=TEMPLATE["required_variables"],
            optional_variables=TEMPLATE["optional_variables"],
            version="1.0.0",
            is_active=True,
            is_default=True,
            recommended_provider=TEMPLATE["recommended_provider"],
            recommended_model=TEMPLATE["recommended_model"],
            recommended_temperature=TEMPLATE["recommended_temperature"],
            recommended_max_tokens=TEMPLATE["recommended_max_tokens"],
            description=TEMPLATE["description"],
            changelog="初始版本",
            tags=TEMPLATE["tags"],
            created_by="system",
        )

        template = service.create_template(db, template_data)
        print(f"✅ 创建成功: {template.template_name} (business_type={template.business_type}, ID={template.id})")

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def main():
    print("=" * 60)
    print("个股数据收集提示词模板迁移")
    print("=" * 60)
    print()
    migrate()
    print()
    print("=" * 60)
    print("完成！访问 http://localhost:3001/settings/prompt-templates 查看")
    print("=" * 60)


if __name__ == "__main__":
    main()
