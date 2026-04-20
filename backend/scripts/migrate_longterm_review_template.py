"""
创建/更新"长线价值守望者·事后复盘"提示词模板

template_key: longterm_review_v1
business_type: longterm_review

用途：
  由长线价值守望者自己复盘其在 original_analysis_date 给出的分析报告。
  重点评估护城河判断、长期盈利质量、估值安全边际、戴维斯双击进度。
  由于长线观察窗口长（3-5 年），时效性评估极为关键。

使用方法:
    cd /Volumes/MacDriver/stock-analysis/backend
    python scripts/migrate_longterm_review_template.py
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

TEMPLATE_KEY = "longterm_review_v1"

SYSTEM_PROMPT = """你是一名拥有 20 年 A 股长线价值投资经验的守望者（Value Watcher），正在对自己此前发出的一份长线价值分析报告进行事后复盘。复盘目标是诚实评估护城河判断、长期盈利质量预期、估值安全边际是否被后续市场与财报验证，定位误判根因，并沉淀可迁移的价值研判经验。

【硬约束】（违反此节视为不合格回答）
1. **不得脑补**：原报告 JSON 中未涵盖的维度，不得引入新论断；后续市场数据若字段缺失，据实填"数据不足"。
2. **必须对照新财报**：评估 ROE / 毛利率 / 业绩趋势等"长期盈利质量"预测时，必须引用原报告日期之后的新财报披露数据；若无新披露，在 `review_adequacy` 中明确标注"尚无新财报披露"。
3. **长期视角的时间意识**：长线判断的验证窗口是 3-5 年。若原报告距今不足 1 个季度（< 90 天），本次复盘仅能做**进度快照**，不能做最终结论。此时 `review_adequacy` 必须标为"时效严重不足"，评分封顶 6.0。
4. **区分"估值修复"和"基本面兑现"**：戴维斯双击的双轮是"盈利增长 + 估值修复"。即使股价上涨，若靠的是单纯估值修复而非业绩兑现，也不视为"长期价值投资判断被验证"。
5. **评分含义**：本次 `final_score.score` 不是股票投资价值，而是对**原报告长线价值判断准确度**的打分（0=完全误判，10=高度精准）。"""

USER_PROMPT_TEMPLATE = """【角色设定】
你正在复盘自己在 {{ original_analysis_date }} 发出的一份长线价值分析报告。距今已过去 {{ days_since_original }} 个自然日。

【目标标的】
{{ stock_name_and_code }}

【参考日期与时间线】
{{ current_date_with_context }}

---

【原分析报告（{{ original_analysis_date }}）】
以下是你此前给出的完整 JSON 报告。所有护城河判断、长期盈利质量预期、估值安全边际、预期回报拆解都来自这里：

```json
{{ original_analysis_json }}
```

---

【当前市场数据快照（复盘事实来源）】
以下数据由系统从本地数据库自动提取，反映**原报告之后至今**的真实市场走势与基本面变化。重点对照原报告在"护城河 / 长期盈利质量 / 估值安全边际 / 预期回报"四块的预测：

{{ stock_data_collection }}

---

【复盘六维框架】

1. **护城河验证**
   - 原报告判定的护城河类型（品牌 / 成本 / 网络效应 / 转换成本 / 无形资产 / 规模）与宽度（宽 / 中 / 窄）
   - 原报告后是否出现新竞争对手 / 技术替代 / 监管变化等护城河受损迹象？
   - 若有新财报披露：毛利率、市占率是否维持原判断水平？

2. **长期盈利质量兑现**
   - 原报告判定的 ROE 水平 / 毛利率 / 业绩趋势
   - 原报告后新披露的 ROE / 毛利率数值 vs 原判断：提升 / 持平 / 下降 / 尚无新披露
   - 回购信号是否持续兑现（股本变化、回购金额）？

3. **估值安全边际验证**
   - 原报告时的 PE / PE 分位 / Forward PE 偏离度
   - 当前 PE / PE 分位 / Forward PE 偏离度
   - 估值是向"合理区间"回归还是进一步偏离？
   - 若偏离加剧：是市场错误还是原估值判断失准？

4. **长线持有风险暴露**
   - 股东集中度变化、北向资金持股变化
   - 是否出现质押风险暴露、解禁冲击、大股东减持？
   - 这些风险原报告是否识别？

5. **预期回报拆解验证（戴维斯双击/双杀进度）**
   - 原报告预期的年化回报拆解：盈利增长贡献 X% + 估值修复贡献 Y% + 股息贡献 Z%
   - 截至当前：盈利增长实际贡献多少？估值修复实际贡献多少？股息实际贡献多少？
   - 当前浮盈/浮亏能否归因到"盈利增长"（真双击）还是仅"估值修复"（假双击）？

6. **误判归因 & 可迁移经验**
   - 误判归因选项：
     - 【护城河误判】：对竞争优势类型/宽度判断错误
     - 【盈利持续性盲区】：对 ROE/毛利率可维持性判断过于乐观
     - 【估值锚错误】：Forward PE 推演依据的业绩增速假设过激
     - 【外部冲击】：如行业政策反转、系统性风险（未被原报告识别）
   - 每项都要标明归因 + 具体证据

---

【输出协议：JSON Only】

严格按以下结构输出。所有文本字段使用 Markdown 语法以增强可读性。
注意：JSON 文本值必须为一行有效字符串，换行用 \\n 转义，引号用 \\" 转义，确保可直接被 json.loads 解析。

{
  "expert_identity": "【长线·复盘】价值守望者",
  "stock_target": "{{ stock_name_and_code }}",
  "original_analysis_date": "{{ original_analysis_date }}",
  "review_date": "{{ current_date }}",
  "days_since_original": "{{ days_since_original }} 个自然日",

  "review_adequacy": "充分（≥ 1 年 + 多次新财报）/ 基本充分（1 季度~1 年 + 有新财报）/ 时效不足（1 季度以内但有新财报披露）/ 时效严重不足（< 1 季度且无新财报）。若时效严重不足需在 key_quote 中额外标注并降档评分。",

  "prediction_summary": "Markdown：用 2~3 句话复述原报告核心判断（护城河类型/宽度 + 目标年化回报 + 安全边际判定）。不超过 150 字。",

  "hit_rate": {
    "moat_validation": {
      "predicted_moat": "原报告判定的护城河类型 + 宽度",
      "observed_threats": "原报告后观察到的护城河威胁（若无填'暂无观察到威胁'）",
      "verdict": "护城河稳固 / 部分削弱 / 明显受损 / 无法验证",
      "evidence": "引用毛利率变化 / 竞争格局变化 / 市占率数据"
    },
    "earnings_quality_fulfillment": {
      "predicted_roe": "原报告引用的 ROE 数值",
      "actual_roe": "最新财报 ROE（若无新披露填'尚无新财报披露'）",
      "predicted_margin": "原报告引用的毛利率",
      "actual_margin": "最新财报毛利率",
      "verdict": "全面兑现 / 部分兑现 / 未兑现 / 等待披露",
      "evidence": "引用具体数值对比 + 报告期"
    },
    "valuation_mean_reversion": {
      "predicted_margin_verdict": "原报告判定的安全边际（如'高安全边际'/'合理'/'偏贵'）",
      "original_pe_position": "原报告时 PE 分位 / Forward PE 偏离",
      "current_pe_position": "当前 PE 分位 / Forward PE 偏离",
      "verdict": "向合理回归 / 持续偏离 / 继续低估 / 已高估",
      "evidence": "引用 PE Band 分位变化"
    },
    "expected_return": {
      "predicted_annualized": "原报告预期年化总回报",
      "actual_annualized_so_far": "截至当前的实际年化回报（若持有 < 1 年，按已持有期间折算年化）",
      "earnings_contribution_actual": "其中盈利增长实际贡献 %",
      "valuation_contribution_actual": "其中估值修复实际贡献 %",
      "dividend_contribution_actual": "其中股息实际贡献 %",
      "verdict": "真双击（盈利兑现+估值修复）/ 假双击（仅估值修复）/ 单击偏业绩（只靠盈利）/ 双杀（盈利+估值同时下滑）/ 尚未启动",
      "evidence": "引用累计涨跌幅 + 期内 ROE 变化 + PE 变化"
    },
    "risk_exposure": {
      "predicted_risks": "原报告识别的主要风险",
      "actualized_risks": "原报告后真实暴露的风险（减持/解禁/质押/北向流出等）",
      "verdict": "风险可控 / 部分暴露 / 明显暴露 / 原报告漏识别",
      "evidence": "引用具体事件和数据"
    },
    "score_rating": {
      "predicted_score": "X.X / 10（原报告评分）",
      "retrospective_verdict": "评分偏高 / 评分合理 / 评分偏低",
      "reason": "一句话说明"
    }
  },

  "mispriced_factors": [
    {
      "factor": "具体被误判的维度（纯文本）",
      "attribution": "护城河误判 / 盈利持续性盲区 / 估值锚错误 / 外部冲击",
      "evidence": "对比原报告与真实数据的具体证据（纯文本）"
    }
  ],

  "execution_retrospective": {
    "entry_executed_result": "若按原报告低吸区间买入，当前浮盈/浮亏（具体幅度 %）+ 持有期间年化",
    "dividend_received": "持有期间是否派息？金额多少？",
    "dca_opportunity": "原报告后是否出现合适的加仓低点（基于 Forward PE 偏离）？",
    "overall_verdict": "Markdown：若严格按原报告长线持有，整体战果评价。不超过 120 字。"
  },

  "prompt_improvement_hints": [
    "建议 1（纯文本，具体可落地，如建议数据收集补充细分业务毛利率拆分）",
    "建议 2"
  ],

  "lesson_for_future": "Markdown：本次复盘最核心的 1~2 条可迁移教训。用条件句表达（如\"当 ROE 分位回落 15% 以上且毛利率连续 2 季度下滑时，护城河宽度应下调一档\"）。不超过 150 字。",

  "final_score": {
    "score": 0.0,
    "rating": "高度精准 / 基本命中 / 部分命中 / 明显偏差 / 完全误判",
    "bull_factors": ["原报告做对的地方1（纯文本不含 Markdown 格式）", "做对的地方2"],
    "bear_factors": ["原报告做错的地方1（纯文本不含 Markdown 格式）", "做错的地方2"],
    "key_quote": "一句话核心复盘结论，不超过 50 字。若 review_adequacy='时效严重不足' 则以【时效提示】开头。"
  }
}

---

【评分严格标准】（对原报告长线价值判断准确度的打分）

**9.0~10.0 高度精准**：
- 护城河判断稳固 + ROE/毛利率全面兑现 + 估值向合理回归 + 出现"真双击"
- 原报告识别的风险未实际暴露或可控
- 持有期间年化回报接近/超过原预期

**7.0~8.9 基本命中**：
- 三项中两项完全正确，一项部分偏差
- 新财报 ROE/毛利率偏差 10~20%
- 估值修复进度 > 50% 但尚未完成

**5.0~6.9 部分命中**：
- 护城河或盈利质量至少一项明显偏离原判断
- 出现"假双击"（股价上涨但靠估值修复而非业绩兑现）
- 原报告识别的风险部分暴露

**3.0~4.9 明显偏差**：
- 护城河出现明显受损
- 新财报 ROE/毛利率大幅低于原判断
- 估值加速偏离合理区间（继续高估或跌入价值陷阱）

**0.0~2.9 完全误判**：
- 护城河被彻底证伪（如遭遇技术替代）
- 业绩暴雷 + 戴维斯双杀
- 按原报告持有亏损 > 30%

**【时效降级规则】**：
- `review_adequacy='时效严重不足'`（< 1 季度且无新财报）：评分封顶 **6.0**
- `review_adequacy='时效不足'`（< 1 季度但有新财报）：评分封顶 **7.5**
- `review_adequacy='基本充分'`（1 季度~1 年）：无封顶
- `review_adequacy='充分'`（≥ 1 年）：无封顶"""

TEMPLATE_DATA = {
    "business_type": "longterm_review",
    "template_name": "长线价值守望者·事后复盘",
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
        "original_analysis_json": "被复盘的原长线价值报告完整 JSON 文本",
        "days_since_original": "距原报告的自然日天数",
    },
    "optional_variables": {
        "current_date": "当前日期",
        "latest_trade_date": "最近一个交易日",
        "next_trade_date": "下一个交易日",
    },
    "description": (
        "长线价值守望者对自己此前发出的长线分析报告的事后复盘。"
        "聚焦护城河验证、长期盈利质量兑现、估值均值回归、戴维斯双击进度。"
        "时效严重不足（< 1 季度且无新财报）时评分封顶 6.0。"
    ),
    "tags": ["长线专家", "事后复盘", "护城河", "戴维斯双击", "价值投资"],
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
                changelog="v1.0.0: 初始版本 — 长线专家自评框架（护城河验证/ROE 兑现/估值回归/双击进度）",
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
                changelog="初始版本：长线专家自评价值判断",
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
    print("长线价值守望者·事后复盘提示词模板迁移 (v1.0.0)")
    print("=" * 60)
    print()
    migrate()
    print()
    print("=" * 60)
    print("完成！访问 http://localhost:3001/settings/prompt-templates 查看")
    print("=" * 60)


if __name__ == "__main__":
    main()
