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

import asyncio
from typing import Dict, Any, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from loguru import logger

from app.core.exceptions import AIServiceError


# --------------------------------------------------------------------------
# Provider 级并发限流（进程内按 provider 名共享的 Semaphore）
# --------------------------------------------------------------------------
# 所有 ChatModel 实例（直接 generate_strategy 或 LangGraph Agent 内部的 LLM
# 节点）都走 _wrap_with_semaphore，把并发集中到单一闸门，避免批量分析时
# "股票层 × 专家层 × Agent 工具轮次" 并发乘积冲爆 provider。
#
# 上限从 ai_provider_configs.max_concurrent 读取；NULL 时按内置默认值。
# 懒加载 + 首次缓存后不再变更 —— 改 DB 需重启 backend / celery_worker。
_PROVIDER_SEMAPHORES: Dict[str, asyncio.Semaphore] = {}

_PROVIDER_DEFAULT_CONCURRENCY = {
    "deepseek": 32,  # 官方 API 文档声明不限并发
    "openai": 16,
    "gemini": 8,     # 免费档 RPM 较低，留出余量
}
_FALLBACK_CONCURRENCY = 8


def _get_provider_semaphore(provider: str, configured_limit: Optional[int]) -> asyncio.Semaphore:
    """返回该 provider 在本进程内共享的 Semaphore。

    无锁懒加载：并发首次访问时 dict.setdefault 保证最终只留一个实例。
    首次创建后 configured_limit 的后续变更不生效（需重启进程）。
    """
    key = provider.lower()
    sem = _PROVIDER_SEMAPHORES.get(key)
    if sem is not None:
        return sem
    limit = configured_limit if (configured_limit and configured_limit > 0) else \
            _PROVIDER_DEFAULT_CONCURRENCY.get(key, _FALLBACK_CONCURRENCY)
    new_sem = asyncio.Semaphore(limit)
    sem = _PROVIDER_SEMAPHORES.setdefault(key, new_sem)
    if sem is new_sem:
        logger.info(f"[LangChainClient] provider={key} 并发上限={limit}")
    return sem


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


def _wrap_with_semaphore(model: BaseChatModel, provider: str, configured_limit: Optional[int]) -> BaseChatModel:
    """给 ChatModel 的 `_agenerate` 套上 provider 级 Semaphore。

    `_agenerate` 是 BaseChatModel 的底层异步抽象：`ainvoke` / `astream` /
    LangGraph Agent 的 LLM 节点都会调它，所以包这一层就能覆盖所有异步调用路径。
    同步 `_generate` 在本项目不会走到（所有调用点都是 async），不必包装。

    model 是 Pydantic BaseModel，普通属性赋值会触发 frozen 校验，
    需用 `object.__setattr__` 绕过。
    """
    sem = _get_provider_semaphore(provider, configured_limit)
    orig_agenerate = model._agenerate

    async def _agenerate_limited(*args, **kwargs):
        async with sem:
            return await orig_agenerate(*args, **kwargs)

    object.__setattr__(model, "_agenerate", _agenerate_limited)
    return model


def create_chat_model(provider: str, config: Dict[str, Any]) -> BaseChatModel:
    """
    根据 provider 名称和配置字典创建 LangChain ChatModel。

    Args:
        provider: "deepseek" / "openai" / "gemini"
        config: 包含 api_key, model_name, max_tokens, temperature, timeout, max_concurrent 等字段

    Returns:
        LangChain BaseChatModel 实例（已挂接 provider 级并发闸）
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
    max_concurrent = config.get("max_concurrent")  # None → 按 provider 默认

    if provider_lower in ("deepseek", "openai"):
        api_base_url = config.get("api_base_url") or _DEFAULT_BASE_URLS.get(provider_lower, "")
        model = factory(
            api_key=api_key,
            api_base_url=api_base_url,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
    else:
        model = factory(
            api_key=api_key,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )

    return _wrap_with_semaphore(model, provider_lower, max_concurrent)


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
