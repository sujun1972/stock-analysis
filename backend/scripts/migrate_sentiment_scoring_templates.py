"""创建/更新舆情打分提示词模板（business_type=sentiment_scoring）。

- `anns_sentiment_v1`：公告批量打分（事件标签 + 情绪 + 影响方向）
- `news_flash_sentiment_v1`：快讯批量打分（情绪 + 主题标签）

两个模板均走批量模式，单次 prompt 最多 30 条，LLM 返回 JSON 数组。

使用方法：
    docker exec stock_backend python /app/scripts/migrate_sentiment_scoring_templates.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.prompt_template_service import get_prompt_template_service
from app.schemas.llm_prompt_template import PromptTemplateCreate, PromptTemplateUpdate


# ============================================================================
# 模板 1：公告批量打分
# ============================================================================

ANNS_TEMPLATE_KEY = "anns_sentiment_v1"

ANNS_SYSTEM_PROMPT = """你是一名 A 股研究员，专门为上市公司公告打标签 + 判断其对股价的隐含影响方向。你的输出将被下游 AI 专家和量化策略消费，必须保持客观、严格、可机读。

【硬约束】
1. **只看数据、不脑补**：仅依据输入的公告标题与元数据（公告类型），不引入外部新闻或你的个人观点。
2. **分类必须来自固定枚举**（见下方）；标题涉及多类事件时选择最主要的 1-2 个。
3. **sentiment_score 必须在 [-1.0, 1.0] 之间**；|score| ≥ 0.5 才可赋 bullish/bearish，否则 neutral。
4. **输出严格 JSON 数组**，与输入条目一一对应（顺序、数量完全一致）；禁止输出解释文字、Markdown、```json``` 包裹。
5. **scoring_reason 限 40 字内**，只描述判断依据，不展开投资建议。

【事件标签枚举（event_tags，多选，最多 2 个）】
- 减持        — 股东 / 高管 / 大股东减持
- 增持        — 股东 / 高管 / 大股东增持
- 回购        — 公司回购股份
- 业绩预增    — 净利润 / 营收同比明显增长的预告
- 业绩预减    — 净利润 / 营收同比明显下滑的预告
- 诉讼        — 公司被起诉 / 起诉他人 / 仲裁 / 重大判决
- 重组        — 资产重组 / 借壳 / 并购 / 收购
- 股权激励    — 限制性股票 / 股票期权授予
- 可转债      — 可转债发行 / 转股 / 回售
- 定增        — 非公开发行 / 定向增发
- 分红派息    — 现金分红 / 转增股本
- 资产出售    — 出售子公司 / 重大资产
- 合同订单    — 重大合同 / 中标 / 订单
- 其他        — 以上都不符合时使用

【情绪影响方向（sentiment_impact）】
- bullish    — 通常利好股价（业绩预增、增持、回购、重大合同、分红派息）
- bearish    — 通常利空股价（业绩预减、减持、诉讼、重大违规）
- neutral    — 影响方向模糊（季报 / 年报常规披露、股东大会公告、董事变更）"""

ANNS_USER_PROMPT_TEMPLATE = """请对以下公告列表逐条打标签并评分。以 JSON 数组返回，元素顺序与输入一致。

【输入（共 {{ batch_size }} 条）】
```json
{{ announcements_json }}
```

【输出 JSON 数组 Schema（每个元素对应输入中同位置的 1 条公告）】
```json
[
  {
    "id": "（回填输入 id，便于回写）",
    "event_tags": ["枚举值1", "枚举值2"],    // 1~2 个事件标签
    "sentiment_score": 0.6,                    // [-1.0, 1.0]
    "sentiment_impact": "bullish",             // bullish/bearish/neutral
    "scoring_reason": "业绩预增同比增长50%，符合业绩超预期判断"
  }
]
```

【示例】
输入: [{"id": "001", "title": "关于控股股东减持公司股份计划的预披露公告", "anno_type": "减持", "stock_name": "某公司"}]
输出: [{"id": "001", "event_tags": ["减持"], "sentiment_score": -0.6, "sentiment_impact": "bearish", "scoring_reason": "控股股东减持通常对短期股价形成抛压"}]

**只返回 JSON 数组，不要任何其他文字。**"""


# ============================================================================
# 模板 2：快讯批量打分
# ============================================================================

NEWS_TEMPLATE_KEY = "news_flash_sentiment_v1"

NEWS_SYSTEM_PROMPT = """你是一名 A 股市场研究员，专门为财经快讯打情绪标签 + 提取主题标签。你的输出将被下游 AI 专家消费，必须客观、可机读。

【硬约束】
1. **只基于标题 + 摘要 + 关联股票代码**，不引入外部信息。
2. **sentiment_score 必须在 [-1.0, 1.0] 之间**；|score| ≥ 0.3 才可赋 bullish/bearish，否则 neutral。
3. **sentiment_tags 是主题标签**（如"行业政策"、"业绩"、"并购"、"海外"），最多 3 个；**不是事件枚举**。
4. **输出严格 JSON 数组**，与输入条目一一对应（顺序、数量完全一致）；禁止输出解释文字、Markdown、```json``` 包裹。
5. **scoring_reason 限 40 字内**。

【情绪分档参考】
- +0.6 ~ +1.0 : 明确利好（业绩超预期 / 行业政策加码 / 中标大订单 / 重大合作）
- +0.3 ~ +0.6 : 温和利好（季报预增 / 增持 / 回购 / 券商上调评级）
- -0.3 ~ +0.3 : 中性（常规披露 / 行业资讯 / 分析师观点不明）
- -0.6 ~ -0.3 : 温和利空（业绩下滑 / 减持 / 下调评级 / 诉讼纠纷）
- -1.0 ~ -0.6 : 明确利空（重大违规 / 立案调查 / 重大诉讼败诉 / 业绩暴雷）"""

NEWS_USER_PROMPT_TEMPLATE = """请对以下财经快讯逐条打情绪分 + 主题标签。以 JSON 数组返回，元素顺序与输入一致。

【输入（共 {{ batch_size }} 条）】
```json
{{ news_items_json }}
```

【输出 JSON 数组 Schema】
```json
[
  {
    "id": "（回填输入 id，便于回写）",
    "sentiment_score": 0.5,                   // [-1.0, 1.0]
    "sentiment_impact": "bullish",            // bullish/bearish/neutral
    "sentiment_tags": ["业绩", "行业政策"],    // 主题标签 0~3 个
    "scoring_reason": "三季报净利润同比+45%"
  }
]
```

【示例】
输入: [{"id": "1001", "title": "某券商调高比亚迪评级至买入，目标价上调至300元", "summary": "", "related_ts_codes": ["002594.SZ"]}]
输出: [{"id": "1001", "sentiment_score": 0.5, "sentiment_impact": "bullish", "sentiment_tags": ["评级调整", "机构观点"], "scoring_reason": "券商上调评级并上调目标价"}]

**只返回 JSON 数组，不要任何其他文字。**"""


# ============================================================================

TEMPLATES = [
    {
        "template_key": ANNS_TEMPLATE_KEY,
        "business_type": "sentiment_scoring",
        "template_name": "公告舆情打分（批量）",
        "system_prompt": ANNS_SYSTEM_PROMPT,
        "user_prompt_template": ANNS_USER_PROMPT_TEMPLATE,
        "output_format": "JSON 数组，与输入条目一一对应；每项含 id/event_tags/sentiment_score/sentiment_impact/scoring_reason",
        "required_variables": {
            "batch_size": "本批次公告条数（整数）",
            "announcements_json": "公告数组 JSON（含 id/title/anno_type/stock_name）",
        },
        "optional_variables": {},
        "description": (
            "对 stock_anns 公告批量打事件标签 + 情绪分。"
            "单次最多 30 条，输出 JSON 数组与输入一一对应。"
            "事件标签 13 类枚举，情绪分 [-1.0, 1.0]。"
        ),
        "tags": ["舆情打分", "公告", "事件分类", "批量"],
        "recommended_provider": "deepseek",
        "recommended_model": "deepseek-chat",
        "recommended_temperature": 0.2,
        "recommended_max_tokens": 4000,
        "changelog": "v1.0.0: 初始版本 — 公告批量打分（事件标签 + 情绪）",
    },
    {
        "template_key": NEWS_TEMPLATE_KEY,
        "business_type": "sentiment_scoring",
        "template_name": "快讯舆情打分（批量）",
        "system_prompt": NEWS_SYSTEM_PROMPT,
        "user_prompt_template": NEWS_USER_PROMPT_TEMPLATE,
        "output_format": "JSON 数组，与输入条目一一对应；每项含 id/sentiment_score/sentiment_impact/sentiment_tags/scoring_reason",
        "required_variables": {
            "batch_size": "本批次快讯条数（整数）",
            "news_items_json": "快讯数组 JSON（含 id/title/summary/related_ts_codes）",
        },
        "optional_variables": {},
        "description": (
            "对 news_flash 财经快讯批量打情绪分 + 主题标签。"
            "单次最多 30 条，输出 JSON 数组与输入一一对应。"
            "情绪分 [-1.0, 1.0]，主题标签自由枚举（最多 3 个）。"
        ),
        "tags": ["舆情打分", "快讯", "情绪分析", "批量"],
        "recommended_provider": "deepseek",
        "recommended_model": "deepseek-chat",
        "recommended_temperature": 0.2,
        "recommended_max_tokens": 4000,
        "changelog": "v1.0.0: 初始版本 — 快讯批量打分（情绪 + 主题）",
    },
]


def migrate_one(db: Session, data: dict) -> None:
    service = get_prompt_template_service()
    existing = service.get_template_by_key(db, data["template_key"])
    if existing:
        print(f"⚠️  模板已存在 (key={data['template_key']}, ID={existing.id})，更新内容...")
        update_data = PromptTemplateUpdate(
            template_name=data["template_name"],
            system_prompt=data["system_prompt"],
            user_prompt_template=data["user_prompt_template"],
            output_format=data["output_format"],
            required_variables=data["required_variables"],
            optional_variables=data["optional_variables"],
            description=data["description"],
            tags=data["tags"],
            recommended_provider=data["recommended_provider"],
            recommended_model=data["recommended_model"],
            recommended_temperature=data["recommended_temperature"],
            recommended_max_tokens=data["recommended_max_tokens"],
            changelog=data["changelog"],
            updated_by="system",
        )
        updated = service.update_template(db, existing.id, update_data)
        print(f"✅ 更新成功 (ID={updated.id})")
    else:
        print(f"📝 创建模板: {data['template_key']}")
        create_data = PromptTemplateCreate(
            business_type=data["business_type"],
            template_name=data["template_name"],
            template_key=data["template_key"],
            system_prompt=data["system_prompt"],
            user_prompt_template=data["user_prompt_template"],
            output_format=data["output_format"],
            required_variables=data["required_variables"],
            optional_variables=data["optional_variables"],
            version="1.0.0",
            is_active=True,
            is_default=True,
            recommended_provider=data["recommended_provider"],
            recommended_model=data["recommended_model"],
            recommended_temperature=data["recommended_temperature"],
            recommended_max_tokens=data["recommended_max_tokens"],
            description=data["description"],
            changelog=data["changelog"],
            tags=data["tags"],
            created_by="system",
        )
        template = service.create_template(db, create_data)
        print(f"✅ 创建成功: {template.template_name} (ID={template.id})")


def main() -> None:
    print("=" * 60)
    print("Phase 5 舆情打分 Prompt 模板迁移")
    print("=" * 60)
    db: Session = SessionLocal()
    try:
        for t in TEMPLATES:
            migrate_one(db, t)
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
    print("=" * 60)
    print("完成！")


if __name__ == "__main__":
    main()
