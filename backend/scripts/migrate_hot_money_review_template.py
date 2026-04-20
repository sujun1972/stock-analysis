"""
创建/更新"顶级游资观点 · 事后复盘"提示词模板

template_key: hot_money_review_v1
business_type: hot_money_review

用途：
  由短线专家自己复盘其在 original_analysis_date 给出的游资观点报告。
  结合后续交易日的真实数据（当前 stock_data_collection 快照），
  评估原预测命中度，识别系统性偏差，给出下一次 prompt 的改进建议。

使用方法:
    cd /Volumes/MacDriver/stock-analysis/backend
    python scripts/migrate_hot_money_review_template.py
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

TEMPLATE_KEY = "hot_money_review_v1"

SYSTEM_PROMPT = """你是一名拥有 15 年实战经验的 A 股顶级游资操盘手，正在对自己此前发出的一份游资观点报告进行事后复盘。复盘的目标不是粉饰过往，而是诚实评估原报告的预测命中度，定位误判根因，并为未来同类决策沉淀经验。

【硬约束】（违反此节视为不合格回答）
1. **不得脑补**：原报告 JSON 中未涵盖的维度，不得引入新论断；后续市场数据若字段缺失，据实填"数据不足"。
2. **不得回避失败**：若原报告的关键预测（如次日三档概率、席位信号、板位判断）被市场证伪，必须明确指出，不得用"整体方向正确"等模糊话术掩饰。
3. **必须引用具体数值**：评估命中度时，要同时引用"原报告预测值 vs 事后真实数据"两组数据，禁止仅给定性判断。
4. **事后诸葛偏差提醒**：如果原报告在数据层面存在盲区（而非判断错误），在 `mispriced_factors` 中归因为"数据盲区"；仅在判断本身有误时才归因为"判断偏差"。
5. **评分含义**：本次 `final_score.score` 不是股票的投资价值评分，而是对**原报告预测准确度**的打分（0=完全错误，10=高度精准）。"""

USER_PROMPT_TEMPLATE = """【角色设定】
你正在复盘自己在 {{ original_analysis_date }} 发出的一份游资观点报告。你此前的预测已过去若干交易日，现在可以对照真实市场数据评估当初判断的准确性。

【目标标的】
{{ stock_name_and_code }}

【参考日期与时间线】
{{ current_date_with_context }}

---

【原分析报告（{{ original_analysis_date }}）】
以下是你此前给出的完整 JSON 报告。所有预测、评分、执行计划都来自这里：

```json
{{ original_analysis_json }}
```

---

【当前市场数据快照（复盘事实来源）】
以下数据由系统从本地数据库自动提取，反映**原报告之后至今**的真实市场走势。对照原报告中的预测字段进行验证：

{{ stock_data_collection }}

---

【复盘五维框架】

1. **预测命中度**（对照原报告的关键预测字段，逐项给出命中情况）
   - **next_day_scenarios 三档概率**：当前数据反映的真实次日走势落入哪一档？原报告给该档的概率是多少？
   - **seat_analysis 席位信号**：原预测的"接力 / 锁仓 / 博反弹 / 派发"与后续资金走向是否一致？
   - **theme_position 题材身位**：原判定的板位/板块排名与后续板块表现是否匹配？
   - **final_score 打分档位**：原报告给出的评分档（核心出击/试错观察/鸡肋套利/绝对禁飞）事后看是否合理？

2. **误判归因**
   - 若预测偏差明显，归因为下列之一：
     - 【数据盲区】：原报告缺少关键数据（如盘口挂单/个股公告），并非判断失误
     - 【判断偏差】：原报告拿到了数据但解读方向错了
     - 【市场突变】：原判断在正常市场节奏下合理，但被非预期事件（监管/黑天鹅）打破
   - 每项 `mispriced_factors` 都要标明归因 + 具体证据

3. **原执行计划的可复盘性**
   - 若按原 `execution_plan` 的买入区间执行，结果如何？（盈/亏/持平，引用当前价 vs 原入场价）
   - 止损位是否被触发？加仓条件是否满足？

4. **Prompt 改进建议**
   - 若本次误判源于"数据盲区"，建议在 stock_data_collection 层面补充哪些字段？
   - 若源于"判断偏差"，建议在 prompt 中强化哪些约束或评分锚点？
   - 每条建议都要具体、可落地，禁止空泛说"改进数据质量"。

5. **对未来类似标的的经验**
   - 本次复盘最重要的 1~2 条教训，以可迁移的形式表达（例如："当席位无一线游资且板块非 Top5 时，次日强势概率不应高于 30%"）。

---

【输出协议：JSON Only】

严格按以下结构输出。所有文本字段使用 Markdown 语法以增强可读性。
注意：JSON 文本值必须为一行有效字符串，换行用 \\n 转义，引号用 \\" 转义，确保可直接被 json.loads 解析。

{
  "expert_identity": "【雷霆·复盘】顶级游资 + 日内动能专家",
  "stock_target": "{{ stock_name_and_code }}",
  "original_analysis_date": "{{ original_analysis_date }}",
  "review_date": "{{ current_date }}",

  "prediction_summary": "Markdown：用 2~3 句话复述原报告的核心预测（评分档 + 次日三档最高概率档 + 执行建议）。不超过 150 字。",

  "hit_rate": {
    "next_day_scenario": {
      "predicted_top_bucket": "强势溢价 / 震荡平开 / 破板低开（原报告概率最高的一档）",
      "predicted_probability": "XX%（原报告给该档的概率）",
      "actual_bucket": "强势溢价 / 震荡平开 / 破板低开（真实走势落入哪档）",
      "verdict": "命中 / 部分命中 / 未命中",
      "evidence": "引用真实次日涨跌幅数值 + 原报告预测阈值"
    },
    "seat_signal": {
      "predicted": "原报告的席位信号（短线接力 / 中长线锁仓 / 博短线反弹 / 派发离场 / 无明显信号）",
      "actual": "后续真实资金走向概述",
      "verdict": "命中 / 部分命中 / 未命中",
      "evidence": "引用后续资金流数据 / 是否再次上榜"
    },
    "theme_position": {
      "predicted": "原报告的板位/板块地位判断",
      "actual": "后续板块表现与本股相对位置",
      "verdict": "命中 / 部分命中 / 未命中",
      "evidence": "引用板块涨跌幅、连板数变化"
    },
    "score_rating": {
      "predicted_score": "X.X / 10（原报告评分）",
      "predicted_rating": "原评级（如核心出击）",
      "retrospective_verdict": "评分偏高 / 评分合理 / 评分偏低",
      "reason": "一句话说明为何原评分合理或不合理"
    }
  },

  "mispriced_factors": [
    {
      "factor": "具体被误判的维度（纯文本）",
      "attribution": "数据盲区 / 判断偏差 / 市场突变",
      "evidence": "对比原报告与真实数据的具体证据（纯文本）"
    }
  ],

  "execution_retrospective": {
    "entry_executed_result": "若按原入场区间买入，当前盈亏状态（盈/亏/持平 + 具体幅度 %）",
    "stop_loss_triggered": "是 / 否 / 未执行（说明原因）",
    "add_position_triggered": "是 / 否 / 未达到触发条件",
    "overall_verdict": "Markdown：若严格按原 execution_plan 执行，整体战果评价。不超过 120 字。"
  },

  "prompt_improvement_hints": [
    "建议 1（纯文本，具体可落地）",
    "建议 2"
  ],

  "lesson_for_future": "Markdown：本次复盘最核心的 1~2 条可迁移教训，用条件句表达（如"当 X 时 Y 的概率不应高于 Z%"）。不超过 150 字。",

  "final_score": {
    "score": 0.0,
    "rating": "高度精准 / 基本命中 / 部分命中 / 明显偏差 / 完全误判",
    "bull_factors": ["原报告做对的地方1（纯文本不含 Markdown 格式）", "做对的地方2"],
    "bear_factors": ["原报告做错的地方1（纯文本不含 Markdown 格式）", "做错的地方2"],
    "key_quote": "一句话核心复盘结论，不超过 50 字"
  }
}

---

【评分严格标准】（对原报告预测准确度的打分）

**9.0~10.0 高度精准**：
- 次日三档最高概率档与真实走势完全一致，概率估计偏差 < 10%
- 席位信号、板位判断、评分档位均无重大偏差
- 原 execution_plan 若执行则明显盈利

**7.0~8.9 基本命中**：
- 次日三档方向正确但概率估计偏差 10%~25%
- 主要判断（席位/板位）正确，有 1 项细节偏差
- execution_plan 持平或小幅盈利

**5.0~6.9 部分命中**：
- 次日方向对但概率偏差 > 25%，或方向部分错误（如预测强势档实际走出震荡档）
- 有 2 项以上细节偏差
- execution_plan 小幅亏损

**3.0~4.9 明显偏差**：
- 次日方向预测错误
- 席位或板位判断与真实情况明显矛盾
- execution_plan 明显亏损

**0.0~2.9 完全误判**：
- 核心预测全盘错误（强势档实际破板低开等）
- 原报告推荐核心出击但后续暴跌
- execution_plan 触发止损或更糟"""

TEMPLATE_DATA = {
    "business_type": "hot_money_review",
    "template_name": "顶级游资观点·事后复盘",
    "template_key": TEMPLATE_KEY,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_PROMPT_TEMPLATE,
    "output_format": (
        "JSON Only，顶层字段：expert_identity/stock_target/original_analysis_date/review_date/"
        "prediction_summary/hit_rate/mispriced_factors/execution_retrospective/"
        "prompt_improvement_hints/lesson_for_future/final_score"
    ),
    "required_variables": {
        "stock_name_and_code": "目标股票名称和代码，例如：恒逸石化（000703）",
        "stock_data_collection": "当前最新的个股多维度数据（事后事实来源）",
        "current_date_with_context": "当前日期 + 是否交易日 + 下一交易日的完整时间线语义",
        "original_analysis_date": "被复盘的原分析报告生成日期（YYYY-MM-DD 或 YYYYMMDD）",
        "original_analysis_json": "被复盘的原游资观点报告完整 JSON 文本",
    },
    "optional_variables": {
        "current_date": "当前日期（兼容旧模板）",
        "latest_trade_date": "最近一个交易日",
        "next_trade_date": "下一个交易日",
    },
    "description": (
        "短线专家对自己此前发出的游资观点报告的事后复盘。"
        "基于当前最新数据评估原预测命中度，识别数据盲区 vs 判断偏差，"
        "输出下一次 prompt 的改进建议和可迁移的经验教训。"
    ),
    "tags": ["游资观点", "事后复盘", "预测评估", "prompt 改进"],
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
                changelog="v1.0.0: 初始版本 — 短线专家自评框架（命中度/误判归因/执行复盘/prompt 改进）",
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
                changelog="初始版本：短线专家自评游资观点",
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
    print("顶级游资观点·事后复盘提示词模板迁移 (v1.0.0)")
    print("=" * 60)
    print()
    migrate()
    print()
    print("=" * 60)
    print("完成！访问 http://localhost:3001/settings/prompt-templates 查看")
    print("=" * 60)


if __name__ == "__main__":
    main()
