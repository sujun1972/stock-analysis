"""
LangChain 统一 LLM 客户端层

替代原有的 DeepSeekClient / GeminiClient / OpenAIClient（httpx 手搓方式），
通过 LangChain ChatModel 提供统一接口。

支持的 Provider：
- deepseek: 走 ChatOpenAI（OpenAI 兼容接口）
- openai:   走 ChatOpenAI
- gemini:   走 ChatGoogleGenerativeAI

向后兼容：保留 generate_strategy(prompt) -> (content, tokens_used) 签名，
使现有 Service 层几乎无需改动。

作者: AI Strategy Team
创建日期: 2026-04-15
"""

from typing import Dict, Any, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from loguru import logger

from app.core.exceptions import AIServiceError


# --------------------------------------------------------------------------
# Provider → LangChain ChatModel 工厂
# --------------------------------------------------------------------------

def _create_openai_compatible_model(
    api_key: str,
    api_base_url: str,
    model_name: str,
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> BaseChatModel:
    """创建 OpenAI 兼容的 ChatModel（OpenAI / DeepSeek / 任何 OpenAI-API 兼容服务）"""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        api_key=api_key,
        base_url=api_base_url,
        model=model_name,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
    )


def _create_gemini_model(
    api_key: str,
    model_name: str,
    max_tokens: int,
    temperature: float,
    timeout: int,
    **kwargs,
) -> BaseChatModel:
    """创建 Google Gemini ChatModel"""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        google_api_key=api_key,
        model=model_name,
        max_output_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
    )


# Provider 名称 → 构造函数映射
_MODEL_FACTORIES = {
    "deepseek": _create_openai_compatible_model,
    "openai": _create_openai_compatible_model,
    "gemini": _create_gemini_model,
}

# Provider → 默认 base_url（仅 OpenAI 兼容类需要）
_DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
}


def create_chat_model(provider: str, config: Dict[str, Any]) -> BaseChatModel:
    """
    根据 provider 名称和配置字典创建 LangChain ChatModel。

    Args:
        provider: "deepseek" / "openai" / "gemini"
        config: 包含 api_key, model_name, max_tokens, temperature, timeout 等字段

    Returns:
        LangChain BaseChatModel 实例
    """
    provider_lower = provider.lower()
    factory = _MODEL_FACTORIES.get(provider_lower)
    if not factory:
        raise AIServiceError(f"不支持的 AI 提供商: {provider}")

    api_key = config.get("api_key", "")
    model_name = config.get("model_name", "")
    max_tokens = config.get("max_tokens", 4000)
    temperature = config.get("temperature", 0.7)
    timeout = config.get("timeout", 60)

    if provider_lower in ("deepseek", "openai"):
        api_base_url = config.get("api_base_url") or _DEFAULT_BASE_URLS.get(provider_lower, "")
        return factory(
            api_key=api_key,
            api_base_url=api_base_url,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
    else:
        return factory(
            api_key=api_key,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )


# --------------------------------------------------------------------------
# 统一调用接口（兼容旧签名）
# --------------------------------------------------------------------------

class LangChainClient:
    """
    LangChain 统一客户端，替代原有的 AIProviderClient 子类。

    保持与旧接口相同的 generate_strategy(prompt) -> (content, tokens_used) 签名，
    使上层 Service 几乎无需改动。
    """

    def __init__(self, provider: str, config: Dict[str, Any]):
        self.provider = provider
        self.model: BaseChatModel = create_chat_model(provider, config)

    async def generate_strategy(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Tuple[str, int]:
        """
        调用 LLM 生成内容。

        Args:
            prompt: 用户消息内容
            system_prompt: 系统消息（可选）

        Returns:
            (生成的文本内容, 使用的 token 数)
        """
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            response = await self.model.ainvoke(messages)

            content = response.content or ""
            tokens_used = 0

            # 从 response.usage_metadata 提取 token（LangChain 标准）
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens_used = response.usage_metadata.get("total_tokens", 0)
            # 降级：从 response.response_metadata 提取
            elif hasattr(response, "response_metadata") and response.response_metadata:
                token_usage = response.response_metadata.get("token_usage", {})
                tokens_used = token_usage.get("total_tokens", 0)

            return content, tokens_used

        except Exception as e:
            logger.error(f"LangChain {self.provider} 调用失败: {e}", exc_info=True)
            raise AIServiceError(f"{self.provider} 调用失败: {e}")
