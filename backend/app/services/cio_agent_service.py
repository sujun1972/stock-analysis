"""
CIO Agent 服务 — 首席投资官 Agent，可自主决定查询哪些数据维度。

与普通专家"被喂全量数据"不同，CIO Agent 绑定 7 个数据查询 Tool，
通过 Tool-calling 循环自主决定查询哪些数据，并根据其他专家的分析结论做出综合判断。

system_prompt 与 user_prompt 由调用方提供（来自数据库 cio_directive_v1 模板，
经 build_stock_prompt() 渲染，含完整的其他三专家分析文本）。本服务只负责执行 Agent，
不维护任何 prompt 模板。

依赖：
- langchain>=1.0（create_agent，基于 LangGraph）
- langchain_tools.py 中定义的 CIO_TOOLS
"""

import time
from typing import Dict, Any, Optional

from loguru import logger

from app.core.exceptions import AIServiceError


class CIOAgentService:
    """CIO Agent 服务：创建并执行 CIO Agent。"""

    MAX_ITERATIONS = 12
    """Agent 最大工具调用轮次。
    LangGraph recursion_limit 计的是节点执行次数，每次 tool 调用 ≈ 2 节点，
    加上首尾两次 LLM 决策节点。CIO v1.2 JSON schema 下实测 DeepSeek 会
    主动调 4-7 个工具（核心是 get_recent_anns / get_financial_reports /
    get_shareholder_info 以锚定 followup_triggers 的 event_ref），需留足预算。
    公式 recursion_limit = MAX_ITERATIONS * 2 + 3 在 run_agent 中使用。
    """

    AGENT_TIMEOUT = 180
    """Agent 总超时时间（秒）。JSON schema + 多工具调用比纯 Markdown 更耗时。"""

    async def run_agent(
        self,
        ts_code: str,
        stock_name: str,
        system_prompt: str,
        user_prompt: str,
        provider: str = "deepseek",
        provider_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        运行 CIO Agent 分析指定股票。

        Args:
            ts_code: 股票代码，如 000001.SZ
            stock_name: 股票名称（仅用于日志）
            system_prompt: 已渲染的 system_prompt（来自数据库 cio_directive_v1 模板）
            user_prompt: 已渲染的 user message（含完整的其他三专家分析文本，由
                build_stock_prompt(expert_outputs=...) 通过占位符替换注入；
                单 CIO 路径下未注入专家时占位符渲染为"未提供"提示）
            provider: AI 提供商名称
            provider_config: AI 提供商配置字典（含 api_key, model_name 等）

        Returns:
            {
                "content": str,           # Agent 最终输出文本
                "tokens_used": int,       # 总 token 消耗（所有轮次累计）
                "tool_calls": list,       # 工具调用记录
                "iterations": int,        # Agent 实际工具调用次数
                "generation_time": float, # 总耗时（秒）
            }
        """
        from langchain.agents import create_agent
        from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
        from langgraph.errors import GraphRecursionError

        from app.services.langchain_client import create_chat_model
        from app.services.langchain_tools import CIO_TOOLS

        if not provider_config:
            from app.services.ai_service import AIStrategyService
            ai_service = AIStrategyService()
            provider_config = ai_service.get_provider_config(provider)

        model = create_chat_model(provider, provider_config)

        # LangGraph CompiledStateGraph
        agent = create_agent(
            model=model,
            tools=CIO_TOOLS,
            system_prompt=system_prompt,
        )

        # recursion_limit 控制最大迭代：每轮 tool call ≈ 2 节点，+3 给首尾 LLM 决策节点
        start_time = time.time()
        tool_call_records = []

        try:
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=user_prompt)]},
                config={"recursion_limit": self.MAX_ITERATIONS * 2 + 3},
            )

            generation_time = time.time() - start_time

            messages = result.get("messages", [])
            content = ""
            total_tokens = 0

            for msg in messages:
                if isinstance(msg, ToolMessage):
                    tool_call_records.append({
                        "tool": msg.name,
                        "output_preview": str(msg.content)[:200],
                    })
                # 最后一条 AI 消息即为最终输出
                if isinstance(msg, AIMessage) and msg.content:
                    content = msg.content
                if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                    total_tokens += msg.usage_metadata.get("total_tokens", 0)
                elif hasattr(msg, "response_metadata") and msg.response_metadata:
                    token_usage = msg.response_metadata.get("token_usage", {})
                    total_tokens += token_usage.get("total_tokens", 0)

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

        except GraphRecursionError as e:
            # 递归上限触发：降级为"无工具直出"模式，让 LLM 基于已有三专家 + 数据收集做 JSON 综合判断。
            # 这是比整个失败更好的用户体验 —— followup_triggers 的事件锚点可能不够精确，但评级/价位主干仍然可用。
            elapsed = time.time() - start_time
            logger.warning(
                f"[CIO Agent] {ts_code} 触发递归上限（{elapsed:.2f}s, "
                f"已调 {len(tool_call_records)} 工具），降级为无工具直出模式"
            )
            return await self._fallback_direct_generate(
                ts_code=ts_code,
                stock_name=stock_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                provider=provider,
                provider_config=provider_config,
                tool_call_records=tool_call_records,
                elapsed_before=elapsed,
            )

        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(
                f"[CIO Agent] {ts_code} 执行失败 ({generation_time:.2f}s): {e}",
                exc_info=True,
            )
            raise AIServiceError(f"CIO Agent 执行失败: {e}")

    async def _fallback_direct_generate(
        self,
        ts_code: str,
        stock_name: str,
        system_prompt: str,
        user_prompt: str,
        provider: str,
        provider_config: Dict[str, Any],
        tool_call_records: list,
        elapsed_before: float,
    ) -> Dict[str, Any]:
        """
        递归上限降级路径：跳过 Agent 的 tool-calling 循环，直接让 LLM 基于
        已经提供的三专家分析 + stock_data_collection 生成综合 JSON。
        """
        from app.services.ai_service import AIStrategyService

        note = (
            "\n\n【注意：本次已跳过工具查询，请直接基于上方三位专家分析与系统收集的数据"
            "生成综合 JSON；followup_triggers 的 event_ref 仅从上述文本中可见的事件中引用，"
            "宁可 time_triggers=[] 也不要虚构。】"
        )
        full_prompt = f"{system_prompt}\n\n{user_prompt}{note}"

        fallback_start = time.time()
        try:
            ai_service = AIStrategyService()
            client = ai_service.create_client(provider, provider_config)
            content, tokens_used = await client.generate_strategy(full_prompt)
        except Exception as e:
            total_elapsed = elapsed_before + (time.time() - fallback_start)
            logger.error(
                f"[CIO Agent] {ts_code} 降级直出也失败 ({total_elapsed:.2f}s): {e}",
                exc_info=True,
            )
            raise AIServiceError(f"CIO Agent 执行失败（降级亦失败）: {e}")

        total_elapsed = elapsed_before + (time.time() - fallback_start)
        logger.info(
            f"[CIO Agent] {ts_code} 降级直出完成: {len(content)}字 / "
            f"~{tokens_used} tokens / {total_elapsed:.2f}s（含 {len(tool_call_records)} 次递归前工具调用）"
        )
        return {
            "content": content,
            "tokens_used": tokens_used,
            "tool_calls": tool_call_records,
            "iterations": len(tool_call_records),
            "generation_time": round(total_elapsed, 2),
            "fallback": "recursion_limit_direct",
        }

    @staticmethod
    def _estimate_tokens(content: str, tool_calls: list) -> int:
        """粗略估算总 token 消耗（中文约 1.5 字/token），仅在 metadata 缺失时兜底。"""
        total_chars = len(content)
        for tc in tool_calls:
            total_chars += len(tc.get("output_preview", ""))
        # +500 估算 system prompt 与工具描述的基础消耗
        return int(total_chars / 1.5) + 500
