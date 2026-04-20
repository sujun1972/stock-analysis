"""
创建/更新"中线产业趋势专家·事后复盘"提示词模板

template_key: midline_review_v1
business_type: midline_review

用途：
  由中线产业趋势专家自己复盘其在 original_analysis_date 给出的分析报告。
  重点评估 3-12 个月维度的产业景气度演变、业绩兑现度、技术结构演变和
  目标价区间命中进度。

使用方法:
    cd /Volumes/MacDriver/stock-analysis/backend
    python scripts/migrate_midline_review_template.py
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

TEMPLATE_KEY = "midline_review_v1"

SYSTEM_PROMPT = """你是一名深耕 A 股产业研究 12 年的中线趋势分析师，正在对自己此前发出的一份中线产业趋势分析报告进行事后复盘。复盘目标是诚实评估原报告在 3-12 个月维度上的趋势判断是否被市场验证，定位误判根因，并沉淀可迁移的产业研判经验。

【硬约束】（违反此节视为不合格回答）
1. **不得脑补**：原报告 JSON 中未涵盖的维度，不得引入新论断；后续市场数据若字段缺失，据实填"数据不足"。
2. **必须对照具体数据**：评估命中度时，要同时引用"原报告预测值 vs 事后真实数据"两组数据。例如原报告判断"ROE 18.2%"，需引用后续新财报披露的 ROE 数值。
3. **时间尺度意识**：中线判断的验证窗口是 3-12 个月。若原报告距今不足 1 个月，应在 `review_adequacy` 中明确指出"评估时效不足"，但仍可对已暴露的早期信号（业绩预告、板块排名）做初步判定。
4. **区分"方向"与"速度"**：即使方向正确，若速度偏差过大（如预测"半年上行 30%"实际只涨 5%），也应归为"部分命中"。
5. **评分含义**：本次 `final_score.score` 不是股票投资价值，而是对**原报告中线趋势判断准确度**的打分（0=完全误判，10=高度精准）。"""

USER_PROMPT_TEMPLATE = """【角色设定】
你正在复盘自己在 {{ original_analysis_date }} 发出的一份中线产业趋势分析报告。距今已过去 {{ days_since_original }} 个自然日。

【目标标的】
{{ stock_name_and_code }}

【参考日期与时间线】
{{ current_date_with_context }}

---

【原分析报告（{{ original_analysis_date }}）】
以下是你此前给出的完整 JSON 报告。所有产业景气度判断、业绩预期、目标价区间都来自这里：

```json
{{ original_analysis_json }}
```

---

【当前市场数据快照（复盘事实来源）】
以下数据由系统从本地数据库自动提取，反映**原报告之后至今**的真实市场走势与基本面变化。重点对照原报告在"产业景气度 / 公司基本面 / 中线技术结构"三块的预测：

{{ stock_data_collection }}

---

【复盘六维框架】

1. **产业景气度演变**
   - 原报告预判的景气阶段（复苏 / 扩张 / 过热 / 收缩）是否被验证？
   - 所属东财板块/主题概念在原报告后的累计涨跌幅、板块相对强度变化？
   - 政策催化 / 供需拐点是否如期兑现？

2. **公司基本面兑现度**
   - 原报告后是否有新的业绩预告/快报/财报披露？数值方向是否与原判断一致？
   - 新 ROE / 毛利率 vs 原报告引用值：提升 / 持平 / 下降？
   - 是否出现超预期或低于预期？

3. **中线技术结构演变**
   - 周线 MACD / 月线布林 / MA60/MA120 位置的演变方向是否与原报告判断一致？
   - 是否突破原阻力位或跌破原支撑位？
   - 筹码结构（获利比、成本）是否按预期演变？

4. **目标价区间命中进度**
   - 原报告给出的 3-12 个月目标价区间 [下沿, 上沿] 是什么？
   - 当前价 vs 目标区间：已突破上沿 / 在区间内 / 跌破下沿 / 尚未启动？
   - 若按原入场价执行，当前浮盈/浮亏多少 %？

5. **误判归因**
   - 若预测偏差明显，归因为下列之一：
     - 【产业误判】：对行业景气周期阶段判断错误
     - 【个股特质盲区】：行业对但公司本身有问题（如竞争劣势、管理瑕疵）
     - 【估值锚错误】：Forward PE 推演依据的业绩增速假设过于乐观/悲观
     - 【外部冲击】：正常周期节奏下合理，但被政策/黑天鹅打破
   - 每项都要标明归因 + 具体证据

6. **Prompt 改进 & 可迁移经验**
   - 若本次误判源于"数据盲区"，建议在 stock_data_collection 层面补充哪些字段（如产业链上下游数据、细分行业份额）？
   - 若源于"判断偏差"，建议在 prompt 中强化哪些约束？
   - 本次复盘最重要的 1~2 条可迁移经验。

---

【输出协议：JSON Only】

严格按以下结构输出。所有文本字段使用 Markdown 语法以增强可读性。
注意：JSON 文本值必须为一行有效字符串，换行用 \\n 转义，引号用 \\" 转义，确保可直接被 json.loads 解析。

{
  "expert_identity": "【中线·复盘】产业趋势分析师",
  "stock_target": "{{ stock_name_and_code }}",
  "original_analysis_date": "{{ original_analysis_date }}",
  "review_date": "{{ current_date }}",
  "days_since_original": "{{ days_since_original }} 个自然日",

  "review_adequacy": "充分（跨越 ≥1 个月 + 有新财报披露）/ 部分充分（跨越 ≥1 个月但无新财报）/ 时效不足（< 1 个月）。若时效不足需在 key_quote 中额外标注。",

  "prediction_summary": "Markdown：用 2~3 句话复述原报告核心判断（景气阶段 + 目标价区间 + 核心催化剂）。不超过 150 字。",

  "hit_rate": {
    "industry_cycle": {
      "predicted_stage": "原报告判断的景气阶段",
      "actual_evolution": "原报告后真实的板块表现（板块相对强度 + 涨跌幅）",
      "verdict": "命中 / 部分命中 / 未命中",
      "evidence": "引用板块近期累计涨跌幅、相对强度数据"
    },
    "earnings_fulfillment": {
      "predicted_direction": "原报告对业绩方向的判断（预增/预减/稳健）",
      "actual_disclosure": "原报告后真实披露的业绩预告/财报数值；若无新披露填'尚无新财报披露'",
      "verdict": "兑现 / 部分兑现 / 未兑现 / 等待披露",
      "evidence": "引用具体 ROE / 营收 / 净利润数值和同比增速"
    },
    "technical_evolution": {
      "predicted": "原报告的周线 MACD / 月线布林 / MA 结构判断",
      "actual": "当前真实技术结构",
      "verdict": "命中 / 部分命中 / 未命中",
      "evidence": "引用当前 MA60/MA120 位置、MACD 状态"
    },
    "price_target": {
      "predicted_range": "原报告的 [下沿, 上沿] 目标价",
      "current_price_position": "当前价 vs 区间的位置（已突破上沿 / 在区间内 / 跌破下沿 / 尚未启动）",
      "verdict": "命中 / 部分命中 / 未命中 / 尚未验证",
      "evidence": "引用当前价 + 原入场价 + 浮盈/浮亏 %"
    },
    "score_rating": {
      "predicted_score": "X.X / 10（原报告评分）",
      "predicted_rating": "原评级",
      "retrospective_verdict": "评分偏高 / 评分合理 / 评分偏低",
      "reason": "一句话说明"
    }
  },

  "mispriced_factors": [
    {
      "factor": "具体被误判的维度（纯文本）",
      "attribution": "产业误判 / 个股特质盲区 / 估值锚错误 / 外部冲击",
      "evidence": "对比原报告与真实数据的具体证据（纯文本）"
    }
  ],

  "execution_retrospective": {
    "entry_executed_result": "若按原入场区间买入，当前浮盈/浮亏（具体幅度 %）",
    "stop_loss_triggered": "是 / 否 / 未执行（说明原因）",
    "catalyst_fulfilled": "原报告列出的催化剂是否兑现（列出每个催化剂 + 兑现状态）",
    "overall_verdict": "Markdown：若严格按原报告执行中线持有，整体战果评价。不超过 120 字。"
  },

  "prompt_improvement_hints": [
    "建议 1（纯文本，具体可落地，如建议在数据收集中补充产业链上下游景气度指标）",
    "建议 2"
  ],

  "lesson_for_future": "Markdown：本次复盘最核心的 1~2 条可迁移教训。用条件句表达（如\"当板块 Top5 连续出栈且业绩预告降速时，目标价上沿应下调 15%\"）。不超过 150 字。",

  "final_score": {
    "score": 0.0,
    "rating": "高度精准 / 基本命中 / 部分命中 / 明显偏差 / 完全误判",
    "bull_factors": ["原报告做对的地方1（纯文本不含 Markdown 格式）", "做对的地方2"],
    "bear_factors": ["原报告做错的地方1（纯文本不含 Markdown 格式）", "做错的地方2"],
    "key_quote": "一句话核心复盘结论，不超过 50 字。若 review_adequacy='时效不足' 则在此处以【时效提示】开头。"
  }
}

---

【评分严格标准】（对原报告中线趋势判断准确度的打分）

**9.0~10.0 高度精准**：
- 景气阶段判断 + 业绩方向 + 目标价区间命中进度三项全中
- 新披露的 ROE/营收与原判断偏差 < 10%
- 按原报告持有当前浮盈明显且在目标区间进度内

**7.0~8.9 基本命中**：
- 三项中两项完全正确，一项部分偏差（如目标价区间命中但速度慢于预期）
- 新 ROE/营收偏差 10~25%
- 按原报告持有持平或小幅盈利

**5.0~6.9 部分命中**：
- 产业景气度方向对但幅度明显偏差
- 业绩方向对但数值偏离大（或尚无新披露无法验证）
- 按原报告持有小幅亏损

**3.0~4.9 明显偏差**：
- 景气阶段判断错误（如预判扩张实际已进入收缩）
- 业绩兑现度不及 50%
- 按原报告持有明显亏损（-5% ~ -15%）

**0.0~2.9 完全误判**：
- 景气周期判断反向
- 业绩大幅低于原预期或出现暴雷
- 按原报告持有亏损 > 15% 或触发中线止损

**【时效不足降级规则】**：若 review_adequacy='时效不足'（< 1 个月），评分上限封顶 7.0（即使早期信号全部利好），因为中线判断需要时间验证。"""

TEMPLATE_DATA = {
    "business_type": "midline_review",
    "template_name": "中线产业趋势专家·事后复盘",
    "template_key": TEMPLATE_KEY,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_PROMPT_TEMPLATE,
    "output_format": (
        "JSON Only，顶层字段：expert_identity/stock_target/original_analysis_date/"
        "review_date/days_since_original/review_adequacy/prediction_summary/hit_rate/"
        "mispriced_factors/execution_retrospective/prompt_improvement_hints/"
        "lesson_for_future/final_score"
    ),
    "required_variables": {
        "stock_name_and_code": "目标股票名称和代码",
        "stock_data_collection": "当前最新的个股多维度数据（事后事实来源）",
        "current_date_with_context": "当前日期 + 是否交易日 + 下一交易日的完整时间线语义",
        "original_analysis_date": "被复盘的原分析报告生成日期",
        "original_analysis_json": "被复盘的原中线专家报告完整 JSON 文本",
        "days_since_original": "距原报告的自然日天数",
    },
    "optional_variables": {
        "current_date": "当前日期",
        "latest_trade_date": "最近一个交易日",
        "next_trade_date": "下一个交易日",
    },
    "description": (
        "中线产业趋势专家对自己此前发出的中线分析报告的事后复盘。"
        "聚焦 3-12 个月维度的产业景气度演变、业绩兑现度、技术结构演变和"
        "目标价区间命中进度。时效不足时评分封顶 7.0。"
    ),
    "tags": ["中线专家", "事后复盘", "产业景气度", "业绩兑现"],
    "recommended_provider": "deepseek",
    "recommended_model": "deepseek-chat",
    "recommended_temperature": 0.3,
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
                changelog="v1.0.0: 初始版本 — 中线专家自评框架（产业景气度/业绩兑现/技术演变/目标价进度）",
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
                version="1.0.0",
                is_active=True,
                is_default=True,
                recommended_provider=TEMPLATE_DATA["recommended_provider"],
                recommended_model=TEMPLATE_DATA["recommended_model"],
                recommended_temperature=TEMPLATE_DATA["recommended_temperature"],
                recommended_max_tokens=TEMPLATE_DATA["recommended_max_tokens"],
                description=TEMPLATE_DATA["description"],
                changelog="初始版本：中线专家自评产业趋势判断",
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
    print("中线产业趋势专家·事后复盘提示词模板迁移 (v1.0.0)")
    print("=" * 60)
    print()
    migrate()
    print()
    print("=" * 60)
    print("完成！访问 http://localhost:3001/settings/prompt-templates 查看")
    print("=" * 60)


if __name__ == "__main__":
    main()
