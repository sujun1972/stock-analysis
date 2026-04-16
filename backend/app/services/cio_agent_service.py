"""
CIO Agent 服务 — 首席投资官 Agent，可自主决定查询哪些数据维度。

与普通专家"被喂全量数据"不同，CIO Agent 绑定 7 个数据查询 Tool，
通过 Tool-calling 循环自主决定查询哪些数据，并根据其他专家的分析结论做出综合判断。

依赖：
- langchain>=1.0（create_agent，基于 LangGraph）
- langchain_tools.py 中定义的 CIO_TOOLS

作者: AI Strategy Team
创建日期: 2026-04-16
"""

import time
from typing import Dict, Any, Optional, List

from loguru import logger

from app.core.exceptions import AIServiceError


# ------------------------------------------------------------------
# CIO Agent 系统提示词
# ------------------------------------------------------------------

_CIO_AGENT_SYSTEM_PROMPT = """你是一家头部私募基金的首席投资官（CIO），统筹短线、中线、长线三个维度，\
最终给出一份供投委会决策参考的综合评级指令。

## 你的能力

你可以通过调用以下工具来查询任意股票的各维度数据（每个工具只需传入 ts_code 参数）：
- get_basic_market: 基础盘面（价格、估值、行业、筹码）
- get_capital_flow: 资金流向（主力净流入、北向资金）
- get_shareholder_info: 股东信息（股东人数变化、减持、解禁）
- get_technical_indicators: 技术指标（均线、RSI、MACD、量价异动）
- get_financial_reports: 财报披露（即将公布的财报日期）
- get_risk_alerts: 风险警示（ST、质押）
- get_nine_turn: 神奇九转（阶段性顶底信号）

## 工作流程

1. 先查看其他专家的分析结论（如有），了解短线/中线/长线各自的判断
2. 根据专家结论中提到的关键点，有针对性地调用工具查询数据来验证或补充
3. 不需要调用全部 7 个工具——只查询你认为对决策最关键的数据维度
4. 数据收集完毕后，输出综合评级

## 输出要求

最终输出必须是一个 JSON 对象，结构如下：

```json
{
  "multi_dimension_scan": {
    "short_term": {"view": "看多/中性/看空", "reason": "一句话理由"},
    "mid_term": {"view": "看多/中性/看空", "reason": "一句话理由"},
    "long_term": {"view": "值得持有/中性/回避", "reason": "一句话理由"}
  },
  "key_drivers": ["驱动因子1", "驱动因子2"],
  "key_risks": ["风险因子1", "风险因子2"],
  "comprehensive_rating": "强力推荐/建议关注/中性持有/建议回避/强烈回避",
  "action_directive": "一句话行动指令",
  "rating_logic": "2-3句话评级依据",
  "comprehensive_score": 7.5,
  "data_queried": ["get_basic_market", "get_capital_flow"]
}
```

其中 comprehensive_score 为 0-10 分的综合评分。data_queried 记录你实际调用的工具名。

禁止模糊表述（如"可能"、"也许"）。语言果断简练，总字数控制在 500 字以内。"""


# ------------------------------------------------------------------
# Agent 创建与执行
# ------------------------------------------------------------------

class CIOAgentService:
    """CIO Agent 服务：创建并执行 CIO Agent。"""

    MAX_ITERATIONS = 5
    """Agent 最大工具调用轮次（通过 LangGraph recursion_limit 控制，每轮 2 步）"""

    AGENT_TIMEOUT = 120
    """Agent 总超时时间（秒）"""

    async def run_agent(
        self,
        ts_code: str,
        stock_name: str,
        expert_summaries: Optional[List[Dict[str, Any]]] = None,
        provider: str = "deepseek",
        provider_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        运行 CIO Agent 分析指定股票。

        Args:
            ts_code: 股票代码，如 000001.SZ
            stock_name: 股票名称
            expert_summaries: 其他专家的分析摘要列表，每项包含 analysis_type, score, text_preview
            provider: AI 提供商名称
            provider_config: AI 提供商配置字典（含 api_key, model_name 等）

        Returns:
            {
                "content": str,          # Agent 最终输出文本
                "tokens_used": int,      # 总 token 消耗（所有轮次累计）
                "tool_calls": list,      # 工具调用记录
                "iterations": int,       # Agent 实际工具调用次数
                "generation_time": float # 总耗时（秒）
            }
        """
        from langchain.agents import create_agent
        from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

        from app.services.langchain_client import create_chat_model
        from app.services.langchain_tools import CIO_TOOLS

        if not provider_config:
            from app.services.ai_service import AIStrategyService
            ai_service = AIStrategyService()
            provider_config = ai_service.get_provider_config(provider)

        # 创建 ChatModel
        model = create_chat_model(provider, provider_config)

        # 创建 Agent（LangGraph CompiledStateGraph）
        agent = create_agent(
            model=model,
            tools=CIO_TOOLS,
            system_prompt=_CIO_AGENT_SYSTEM_PROMPT,
        )

        # 构建用户消息
        user_message = self._build_user_message(ts_code, stock_name, expert_summaries)

        # 执行 Agent（recursion_limit 控制最大迭代：每轮 tool call = 2 步，+1 作兜底）
        start_time = time.time()
        tool_call_records = []

        try:
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=user_message)]},
                config={"recursion_limit": self.MAX_ITERATIONS * 2 + 1},
            )

            generation_time = time.time() - start_time

            # 从 messages 中提取最终 AI 输出和工具调用记录
            messages = result.get("messages", [])
            content = ""
            total_tokens = 0

            for msg in messages:
                # 记录工具调用
                if isinstance(msg, ToolMessage):
                    tool_call_records.append({
                        "tool": msg.name,
                        "output_preview": str(msg.content)[:200],
                    })
                # 最后一条 AI 消息即为最终输出
                if isinstance(msg, AIMessage) and msg.content:
                    content = msg.content
                # 累计 token
                if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                    total_tokens += msg.usage_metadata.get("total_tokens", 0)
                elif hasattr(msg, "response_metadata") and msg.response_metadata:
                    token_usage = msg.response_metadata.get("token_usage", {})
                    total_tokens += token_usage.get("total_tokens", 0)

            # 如果未能从 metadata 获取 token，做粗略估算
            if total_tokens == 0:
                total_tokens = self._estimate_tokens(content, tool_call_records)

            logger.info(
                f"[CIO Agent] {ts_code} 分析完成: "
                f"{len(content)}字 / ~{total_tokens} tokens / "
                f"{len(tool_call_records)} tool calls / {generation_time:.2f}s"
            )

            return {
                "content": content,
                "tokens_used": total_tokens,
                "tool_calls": tool_call_records,
                "iterations": len(tool_call_records),
                "generation_time": round(generation_time, 2),
            }

        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(
                f"[CIO Agent] {ts_code} 执行失败 ({generation_time:.2f}s): {e}",
                exc_info=True,
            )
            raise AIServiceError(f"CIO Agent 执行失败: {e}")

    def _build_user_message(
        self,
        ts_code: str,
        stock_name: str,
        expert_summaries: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """构建发送给 CIO Agent 的用户消息。"""
        lines = [
            f"请对 {stock_name}（{ts_code}）进行 CIO 综合研判。",
        ]

        if expert_summaries:
            lines.append("")
            lines.append("【其他专家分析结论（供参考）】")
            for s in expert_summaries:
                score_str = f"（评分: {s['score']}）" if s.get("score") is not None else ""
                lines.append(f"### {s.get('analysis_type', '')}{score_str}")
                lines.append(s.get("text_preview", "")[:500])
                lines.append("")

        lines.append("")
        lines.append(
            "请根据需要调用工具查询数据，然后输出 JSON 格式的 CIO 综合评级。"
            "你不必调用全部工具——只查询你认为最关键的数据维度即可。"
        )

        return "\n".join(lines)

    @staticmethod
    def _estimate_tokens(content: str, tool_calls: list) -> int:
        """粗略估算总 token 消耗（中文约 1.5 字/token）。"""
        total_chars = len(content)
        for tc in tool_calls:
            total_chars += len(tc.get("output_preview", ""))
        return int(total_chars / 1.5) + 500  # 加上系统提示词和工具描述的基础消耗
