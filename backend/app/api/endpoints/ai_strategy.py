"""
AI策略生成API端点
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from app.api.error_handler import handle_api_errors
from app.schemas.ai_config import (
    AIProviderConfigCreate,
    AIProviderConfigUpdate,
    AIProviderConfigResponse,
    AIStrategyGenerateRequest,
    AIStrategyGenerateResponse,
)
from app.repositories.ai_config_repository import ai_config_repository
from app.services.ai_service import ai_strategy_service
from app.core.exceptions import AIServiceError

router = APIRouter()


# ============ AI策略生成端点 ============

@router.post("/generate", response_model=AIStrategyGenerateResponse)
@handle_api_errors
async def generate_strategy(request: AIStrategyGenerateRequest):
    """
    使用AI生成策略代码

    Args:
        request: 策略生成请求
            - strategy_requirement: 策略需求描述
            - provider: 指定AI提供商（可选，不指定则使用默认）
            - use_custom_prompt: 是否使用自定义提示词模板
            - custom_prompt_template: 自定义提示词模板（可选）

    Returns:
        AIStrategyGenerateResponse: 生成结果
            - success: 是否成功
            - strategy_code: 生成的策略代码
            - strategy_metadata: 策略元信息
            - provider_used: 使用的AI提供商
            - tokens_used: 使用的token数
            - generation_time: 生成耗时(秒)
    """
    try:
        # 获取AI提供商配置
        if request.provider:
            provider_config_obj = ai_config_repository.get_by_provider(request.provider)
            if not provider_config_obj:
                raise HTTPException(status_code=404, detail=f"未找到AI提供商配置: {request.provider}")
        else:
            provider_config_obj = ai_config_repository.get_default()
            if not provider_config_obj:
                raise HTTPException(status_code=404, detail="未配置默认AI提供商，请先在管理页面配置")

        if not provider_config_obj.is_active:
            raise HTTPException(status_code=400, detail=f"AI提供商 {provider_config_obj.provider} 未启用")

        # 构建配置字典
        provider_config = {
            "provider": provider_config_obj.provider,
            "api_key": provider_config_obj.api_key,
            "api_base_url": provider_config_obj.api_base_url,
            "model_name": provider_config_obj.model_name,
            "max_tokens": provider_config_obj.max_tokens,
            "temperature": provider_config_obj.temperature / 100.0,  # 转换回0-1范围
            "timeout": provider_config_obj.timeout,
        }

        # 调用AI服务生成策略
        result = await ai_strategy_service.generate_strategy(
            strategy_requirement=request.strategy_requirement,
            provider_config=provider_config,
            custom_prompt_template=request.custom_prompt_template if request.use_custom_prompt else None
        )

        return AIStrategyGenerateResponse(
            success=True,
            strategy_code=result["strategy_code"],
            strategy_metadata=result["strategy_metadata"],
            provider_used=provider_config_obj.provider,
            tokens_used=result["tokens_used"],
            generation_time=result["generation_time"],
        )

    except AIServiceError as e:
        logger.error(f"AI策略生成失败: {str(e)}")
        return AIStrategyGenerateResponse(
            success=False,
            provider_used=request.provider or "unknown",
            error_message=str(e),
        )
    except Exception as e:
        logger.error(f"策略生成异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"策略生成失败: {str(e)}")


# ============ AI配置管理端点 (Admin) ============

@router.get("/providers", response_model=List[AIProviderConfigResponse])
@handle_api_errors
async def list_ai_providers():
    """
    获取所有AI提供商配置列表

    Returns:
        List[AIProviderConfigResponse]: AI提供商配置列表（API密钥已脱敏）
    """
    configs = ai_config_repository.get_all()

    # 转换为响应模型（温度参数转换回0-1范围）
    response_configs = []
    for config in configs:
        config_dict = {
            "id": config.id,
            "provider": config.provider,
            "display_name": config.display_name,
            "api_key": config.api_key,
            "api_base_url": config.api_base_url,
            "model_name": config.model_name,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature / 100.0,
            "is_active": config.is_active,
            "is_default": config.is_default,
            "priority": config.priority,
            "rate_limit": config.rate_limit,
            "timeout": config.timeout,
            "description": config.description,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }
        response_configs.append(AIProviderConfigResponse(**config_dict))

    return response_configs


@router.get("/providers/{provider}", response_model=AIProviderConfigResponse)
@handle_api_errors
async def get_ai_provider(provider: str):
    """
    获取指定AI提供商配置

    Args:
        provider: 提供商名称

    Returns:
        AIProviderConfigResponse: AI提供商配置（API密钥已脱敏）
    """
    config = ai_config_repository.get_by_provider(provider)
    if not config:
        raise HTTPException(status_code=404, detail=f"未找到AI提供商配置: {provider}")

    config_dict = {
        "id": config.id,
        "provider": config.provider,
        "display_name": config.display_name,
        "api_key": config.api_key,
        "api_base_url": config.api_base_url,
        "model_name": config.model_name,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature / 100.0,
        "is_active": config.is_active,
        "is_default": config.is_default,
        "priority": config.priority,
        "rate_limit": config.rate_limit,
        "timeout": config.timeout,
        "description": config.description,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }
    return AIProviderConfigResponse(**config_dict)


@router.post("/providers", response_model=AIProviderConfigResponse, status_code=201)
@handle_api_errors
async def create_ai_provider(config: AIProviderConfigCreate):
    """
    创建AI提供商配置

    Args:
        config: AI提供商配置

    Returns:
        AIProviderConfigResponse: 创建的配置
    """
    # 检查是否已存在
    existing = ai_config_repository.get_by_provider(config.provider)
    if existing:
        raise HTTPException(status_code=400, detail=f"AI提供商配置已存在: {config.provider}")

    # 创建配置
    config_dict = config.model_dump()
    created_config = ai_config_repository.create(config_dict)

    # 转换响应
    response_dict = {
        "id": created_config.id,
        "provider": created_config.provider,
        "display_name": created_config.display_name,
        "api_key": created_config.api_key,
        "api_base_url": created_config.api_base_url,
        "model_name": created_config.model_name,
        "max_tokens": created_config.max_tokens,
        "temperature": created_config.temperature / 100.0,
        "is_active": created_config.is_active,
        "is_default": created_config.is_default,
        "priority": created_config.priority,
        "rate_limit": created_config.rate_limit,
        "timeout": created_config.timeout,
        "description": created_config.description,
        "created_at": created_config.created_at,
        "updated_at": created_config.updated_at,
    }
    return AIProviderConfigResponse(**response_dict)


@router.put("/providers/{provider}", response_model=AIProviderConfigResponse)
@handle_api_errors
async def update_ai_provider(provider: str, config: AIProviderConfigUpdate):
    """
    更新AI提供商配置

    Args:
        provider: 提供商名称
        config: 更新的配置

    Returns:
        AIProviderConfigResponse: 更新后的配置
    """
    config_dict = config.model_dump(exclude_unset=True)
    updated_config = ai_config_repository.update(provider, config_dict)

    if not updated_config:
        raise HTTPException(status_code=404, detail=f"未找到AI提供商配置: {provider}")

    response_dict = {
        "id": updated_config.id,
        "provider": updated_config.provider,
        "display_name": updated_config.display_name,
        "api_key": updated_config.api_key,
        "api_base_url": updated_config.api_base_url,
        "model_name": updated_config.model_name,
        "max_tokens": updated_config.max_tokens,
        "temperature": updated_config.temperature / 100.0,
        "is_active": updated_config.is_active,
        "is_default": updated_config.is_default,
        "priority": updated_config.priority,
        "rate_limit": updated_config.rate_limit,
        "timeout": updated_config.timeout,
        "description": updated_config.description,
        "created_at": updated_config.created_at,
        "updated_at": updated_config.updated_at,
    }
    return AIProviderConfigResponse(**response_dict)


@router.delete("/providers/{provider}")
@handle_api_errors
async def delete_ai_provider(provider: str):
    """
    删除AI提供商配置

    Args:
        provider: 提供商名称

    Returns:
        {"message": "删除成功"}
    """
    deleted = ai_config_repository.delete(provider)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"未找到AI提供商配置: {provider}")

    return {"message": f"成功删除AI提供商配置: {provider}"}


@router.get("/providers/default/info", response_model=AIProviderConfigResponse)
@handle_api_errors
async def get_default_provider():
    """
    获取默认AI提供商配置

    Returns:
        AIProviderConfigResponse: 默认AI提供商配置
    """
    config = ai_config_repository.get_default()
    if not config:
        raise HTTPException(status_code=404, detail="未配置默认AI提供商")

    config_dict = {
        "id": config.id,
        "provider": config.provider,
        "display_name": config.display_name,
        "api_key": config.api_key,
        "api_base_url": config.api_base_url,
        "model_name": config.model_name,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature / 100.0,
        "is_active": config.is_active,
        "is_default": config.is_default,
        "priority": config.priority,
        "rate_limit": config.rate_limit,
        "timeout": config.timeout,
        "description": config.description,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }
    return AIProviderConfigResponse(**config_dict)
