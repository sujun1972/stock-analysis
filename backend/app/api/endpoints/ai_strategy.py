"""
AI策略生成API端点
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from loguru import logger
from celery.result import AsyncResult

from app.api.error_handler import handle_api_errors
from app.core.dependencies import get_current_active_user, require_admin
from app.models.user import User
from app.models.api_response import ApiResponse
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
from app.celery_app import celery_app
from app.tasks.ai_strategy_tasks import generate_strategy_async

router = APIRouter()


# ============ AI策略生成端点 ============

@router.post("/generate", response_model=AIStrategyGenerateResponse)
@handle_api_errors
async def generate_strategy(
    request: AIStrategyGenerateRequest,
    current_user: User = Depends(get_current_active_user)
):
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
            "temperature": float(provider_config_obj.temperature),  # 转换回0-1范围
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

@router.get("/providers")
@handle_api_errors
async def list_providers(current_user: User = Depends(require_admin)):
    """
    获取所有AI提供商配置列表

    Returns:
        ApiResponse: AI提供商配置列表（API密钥已脱敏）
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
            "temperature": float(config.temperature),
            "is_active": config.is_active,
            "is_default": config.is_default,
            "priority": config.priority,
            "rate_limit": config.rate_limit,
            "timeout": config.timeout,
            "description": config.description,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }
        response_configs.append(config_dict)

    return ApiResponse.success(
        data=response_configs,
        message=f"成功获取 {len(response_configs)} 个AI提供商配置"
    )


@router.get("/providers/{provider}")
@handle_api_errors
async def get_provider(provider: str, current_user: User = Depends(require_admin)):
    """
    获取指定AI提供商配置

    Args:
        provider: 提供商名称

    Returns:
        ApiResponse: AI提供商配置（API密钥已脱敏）
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
        "temperature": float(config.temperature),
        "is_active": config.is_active,
        "is_default": config.is_default,
        "priority": config.priority,
        "rate_limit": config.rate_limit,
        "timeout": config.timeout,
        "description": config.description,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }
    return ApiResponse.success(
        data=config_dict,
        message=f"成功获取AI提供商配置: {provider}"
    )


@router.post("/providers", status_code=201)
@handle_api_errors
async def create_provider(
    config: AIProviderConfigCreate,
    current_user: User = Depends(require_admin)
):
    """
    创建AI提供商配置

    Args:
        config: AI提供商配置

    Returns:
        ApiResponse: 创建的配置
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
        "temperature": float(config.temperature),
        "is_active": created_config.is_active,
        "is_default": created_config.is_default,
        "priority": created_config.priority,
        "rate_limit": created_config.rate_limit,
        "timeout": created_config.timeout,
        "description": created_config.description,
        "created_at": created_config.created_at,
        "updated_at": created_config.updated_at,
    }
    return ApiResponse.success(
        data=response_dict,
        message=f"成功创建AI提供商配置: {config.provider}"
    )


@router.put("/providers/{provider}")
@handle_api_errors
async def update_provider(
    provider: str,
    config: AIProviderConfigUpdate,
    current_user: User = Depends(require_admin)
):
    """
    更新AI提供商配置

    Args:
        provider: 提供商名称
        config: 更新的配置

    Returns:
        ApiResponse: 更新后的配置
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
        "temperature": float(updated_config.temperature),  # 修复：使用updated_config而不是config
        "is_active": updated_config.is_active,
        "is_default": updated_config.is_default,
        "priority": updated_config.priority,
        "rate_limit": updated_config.rate_limit,
        "timeout": updated_config.timeout,
        "description": updated_config.description,
        "created_at": updated_config.created_at,
        "updated_at": updated_config.updated_at,
    }
    return ApiResponse.success(
        data=response_dict,
        message=f"成功更新AI提供商配置: {provider}"
    )


@router.delete("/providers/{provider}")
@handle_api_errors
async def delete_provider(provider: str, current_user: User = Depends(require_admin)):
    """
    删除AI提供商配置

    Args:
        provider: 提供商名称

    Returns:
        {"success": true, "message": "删除成功"}
    """
    deleted = ai_config_repository.delete(provider)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"未找到AI提供商配置: {provider}")

    return ApiResponse.success(message=f"成功删除AI提供商配置: {provider}")


@router.get("/providers/default/info")
@handle_api_errors
async def get_default_provider_info(current_user: User = Depends(require_admin)):
    """
    获取默认AI提供商配置

    Returns:
        ApiResponse: 默认AI提供商配置
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
        "temperature": float(config.temperature),
        "is_active": config.is_active,
        "is_default": config.is_default,
        "priority": config.priority,
        "rate_limit": config.rate_limit,
        "timeout": config.timeout,
        "description": config.description,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }
    return ApiResponse.success(
        data=config_dict,
        message="成功获取默认AI提供商配置"
    )


# ============ 异步AI策略生成端点 ============

@router.post("/async-generate", status_code=status.HTTP_202_ACCEPTED)
@handle_api_errors
async def async_generate_strategy(
    request: AIStrategyGenerateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    异步生成策略代码（立即返回task_id）

    流程：
    1. 验证AI提供商配置
    2. 提交Celery异步任务
    3. 立即返回task_id
    4. 客户端轮询 GET /ai-strategy/status/{task_id} 获取进度和结果

    Args:
        request: 策略生成请求
            - strategy_requirement: 策略需求描述
            - provider: 指定AI提供商（可选）
            - use_custom_prompt: 是否使用自定义提示词模板
            - custom_prompt_template: 自定义提示词模板（可选）

    Returns:
        {
            "task_id": "abc-123-def",
            "status": "pending",
            "message": "AI策略生成任务已提交",
            "provider_used": "deepseek"
        }
    """
    try:
        # 获取AI提供商配置
        if request.provider:
            provider_config_obj = ai_config_repository.get_by_provider(request.provider)
            if not provider_config_obj:
                raise HTTPException(
                    status_code=404,
                    detail=f"未找到AI提供商配置: {request.provider}"
                )
        else:
            provider_config_obj = ai_config_repository.get_default()
            if not provider_config_obj:
                raise HTTPException(
                    status_code=404,
                    detail="未配置默认AI提供商，请先在管理页面配置"
                )

        if not provider_config_obj.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"AI提供商 {provider_config_obj.provider} 未启用"
            )

        # 构建配置字典
        provider_config = {
            "provider": provider_config_obj.provider,
            "api_key": provider_config_obj.api_key,
            "api_base_url": provider_config_obj.api_base_url,
            "model_name": provider_config_obj.model_name,
            "max_tokens": provider_config_obj.max_tokens,
            "temperature": float(provider_config_obj.temperature),
            "timeout": provider_config_obj.timeout,
        }

        # 提交Celery异步任务（立即返回）
        task = generate_strategy_async.delay(
            strategy_requirement=request.strategy_requirement,
            provider_config=provider_config,
            custom_prompt_template=(
                request.custom_prompt_template if request.use_custom_prompt else None
            )
        )

        logger.info(
            f"AI策略生成任务已提交 [task_id={task.id}], "
            f"provider={provider_config_obj.provider}"
        )

        return ApiResponse.success(
            data={
                "task_id": task.id,
                "status": "pending",
                "provider_used": provider_config_obj.provider
            },
            message=f"AI策略生成任务已提交，使用提供商: {provider_config_obj.provider}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交AI策略生成任务失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"任务提交失败: {str(e)}")


@router.get("/status/{task_id}")
@handle_api_errors
async def get_task_status(task_id: str, current_user: User = Depends(get_current_active_user)):
    """
    查询AI策略生成任务状态

    Args:
        task_id: Celery任务ID

    Returns:
        - PENDING: 任务排队中
        - PROGRESS: 生成中（包含进度信息）
        - SUCCESS: 成功（包含完整结果）
        - FAILURE: 失败（包含错误信息）
    """
    try:
        task = AsyncResult(task_id, app=celery_app)

        data = {
            "task_id": task_id,
            "status": task.state
        }
        message = ""

        if task.state == 'PENDING':
            message = "任务排队中，等待AI服务..."

        elif task.state == 'PROGRESS':
            # 返回进度信息（只返回状态文字，不返回具体进度百分比）
            info = task.info or {}
            message = info.get('status', 'AI策略生成进行中...')

        elif task.state == 'SUCCESS':
            # 返回完整结果
            result = task.result
            data["strategy_code"] = result.get('strategy_code')
            data["strategy_metadata"] = result.get('strategy_metadata')
            data["tokens_used"] = result.get('tokens_used')
            data["generation_time"] = result.get('generation_time')
            data["provider_used"] = result.get('provider_used')
            message = "策略生成成功"

        elif task.state == 'FAILURE':
            # 返回错误信息
            error = str(task.info) if task.info else "未知错误"
            data["error"] = error
            message = f"策略生成失败: {error}"

        else:
            message = f"未知状态: {task.state}"

        return ApiResponse.success(data=data, message=message)

    except Exception as e:
        logger.error(f"查询任务状态失败 [task_id={task_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询状态失败: {str(e)}")


@router.delete("/cancel/{task_id}")
@handle_api_errors
async def cancel_task(task_id: str, current_user: User = Depends(get_current_active_user)):
    """
    取消AI策略生成任务

    Args:
        task_id: Celery任务ID

    Returns:
        {"message": "任务已取消", "task_id": "..."}
    """
    try:
        task = AsyncResult(task_id, app=celery_app)

        if task.state in ['PENDING', 'PROGRESS']:
            task.revoke(terminate=True)
            logger.info(f"AI策略生成任务已取消 [task_id={task_id}]")
            return ApiResponse.success(data={"task_id": task_id}, message="任务已取消")
        else:
            return ApiResponse.error(
                message=f"任务当前状态为 {task.state}，无法取消",
                code=400,
                data={"task_id": task_id, "state": task.state}
            )

    except Exception as e:
        logger.error(f"取消任务失败 [task_id={task_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")
