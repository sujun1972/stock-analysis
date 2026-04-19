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

    MAX_ITERATIONS = 5
    """Agent 最大工具调用轮次（通过 LangGraph recursion_limit 控制，每轮 2 步）"""

    AGENT_TIMEOUT = 120
    """Agent 总超时时间（秒）"""

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

        # recursion_limit 控制最大迭代：每轮 tool call = 2 步，+1 作兜底
        start_time = time.time()
        tool_call_records = []

        try:
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=user_prompt)]},
                config={"recursion_limit": self.MAX_ITERATIONS * 2 + 1},
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

        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(
                f"[CIO Agent] {ts_code} 执行失败 ({generation_time:.2f}s): {e}",
                exc_info=True,
            )
            raise AIServiceError(f"CIO Agent 执行失败: {e}")

    @staticmethod
    def _estimate_tokens(content: str, tool_calls: list) -> int:
        """粗略估算总 token 消耗（中文约 1.5 字/token），仅在 metadata 缺失时兜底。"""
        total_chars = len(content)
        for tc in tool_calls:
            total_chars += len(tc.get("output_preview", ""))
        # +500 估算 system prompt 与工具描述的基础消耗
        return int(total_chars / 1.5) + 500
