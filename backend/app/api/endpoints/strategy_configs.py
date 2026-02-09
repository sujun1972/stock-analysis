"""
策略配置API端点 (Strategy Configs API)

提供配置驱动策略的CRUD操作。

配置驱动策略特点:
- 从数据库加载参数配置
- 基于预定义策略类型 (momentum, mean_reversion, multi_factor)
- 支持参数调优和 A/B 测试

作者: Backend Team
创建日期: 2026-02-09
版本: 1.0.0
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field, validator

from app.api.error_handler import handle_api_errors
from app.core_adapters.config_strategy_adapter import ConfigStrategyAdapter
from app.repositories.strategy_config_repository import StrategyConfigRepository

router = APIRouter()


# ==================== Pydantic 模型 ====================


class StrategyConfigCreate(BaseModel):
    """创建策略配置请求模型"""

    strategy_type: str = Field(
        ..., description="策略类型: momentum, mean_reversion, multi_factor"
    )
    config: Dict[str, Any] = Field(..., description="策略参数")
    name: Optional[str] = Field(None, description="配置名称")
    description: Optional[str] = Field(None, description="配置描述")
    category: Optional[str] = Field(None, description="配置分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")

    @validator("strategy_type")
    def validate_strategy_type(cls, v):
        """验证策略类型"""
        allowed_types = ["momentum", "mean_reversion", "multi_factor"]
        if v not in allowed_types:
            raise ValueError(
                f"策略类型必须是以下之一: {', '.join(allowed_types)}"
            )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "strategy_type": "momentum",
                "config": {
                    "lookback_period": 20,
                    "threshold": 0.10,
                    "top_n": 20
                },
                "name": "中期动量策略",
                "description": "20日回看期的动量策略",
                "category": "趋势跟踪",
                "tags": ["动量", "中期"]
            }
        }


class StrategyConfigUpdate(BaseModel):
    """更新策略配置请求模型"""

    config: Optional[Dict[str, Any]] = Field(None, description="策略参数")
    name: Optional[str] = Field(None, description="配置名称")
    description: Optional[str] = Field(None, description="配置描述")
    category: Optional[str] = Field(None, description="配置分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    status: Optional[str] = Field(None, description="状态: active, archived, deprecated")

    @validator("status")
    def validate_status(cls, v):
        """验证状态"""
        if v is not None:
            allowed_statuses = ["active", "archived", "deprecated"]
            if v not in allowed_statuses:
                raise ValueError(
                    f"状态必须是以下之一: {', '.join(allowed_statuses)}"
                )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "config": {
                    "lookback_period": 30,
                    "threshold": 0.15,
                    "top_n": 15
                },
                "name": "长期动量策略",
                "is_enabled": True
            }
        }


class ValidateConfigRequest(BaseModel):
    """验证配置请求模型"""

    strategy_type: str = Field(..., description="策略类型")
    config: Dict[str, Any] = Field(..., description="策略参数")

    class Config:
        json_schema_extra = {
            "example": {
                "strategy_type": "momentum",
                "config": {
                    "lookback_period": 20,
                    "threshold": 0.10,
                    "top_n": 20
                }
            }
        }


# ==================== API 端点 ====================


@router.get("/types", summary="获取可用的策略类型")
@handle_api_errors
async def get_strategy_types() -> Dict[str, Any]:
    """
    获取可用的预定义策略类型

    返回策略类型列表，包含类型、名称、描述和默认参数。

    Returns:
        {
            "success": true,
            "data": [
                {
                    "type": "momentum",
                    "name": "动量策略",
                    "description": "选择近期涨幅最大的股票",
                    "default_params": {...},
                    "param_schema": {...}
                },
                ...
            ]
        }
    """
    adapter = ConfigStrategyAdapter()
    types = await adapter.get_available_strategy_types()

    logger.info(f"获取策略类型列表: {len(types)} 种策略")

    return {
        "success": True,
        "data": types,
        "meta": {"count": len(types)}
    }


@router.post("/validate", summary="验证策略配置", status_code=status.HTTP_200_OK)
@handle_api_errors
async def validate_config(request: ValidateConfigRequest) -> Dict[str, Any]:
    """
    验证策略配置参数

    检查参数类型、范围和必需字段。

    Args:
        request: 验证配置请求

    Returns:
        {
            "success": true,
            "data": {
                "is_valid": true,
                "errors": [],
                "warnings": []
            }
        }
    """
    adapter = ConfigStrategyAdapter()
    validation_result = await adapter.validate_config(
        strategy_type=request.strategy_type,
        config=request.config
    )

    logger.info(
        f"验证策略配置: type={request.strategy_type}, "
        f"valid={validation_result['is_valid']}"
    )

    return {
        "success": True,
        "data": validation_result
    }


@router.post("", summary="创建策略配置", status_code=status.HTTP_201_CREATED)
@handle_api_errors
async def create_config(data: StrategyConfigCreate) -> Dict[str, Any]:
    """
    创建新的策略配置

    Args:
        data: 策略配置数据

    Returns:
        {
            "success": true,
            "data": {
                "config_id": 1
            },
            "message": "策略配置创建成功"
        }
    """
    # 1. 验证配置参数
    adapter = ConfigStrategyAdapter()
    validation_result = await adapter.validate_config(
        strategy_type=data.strategy_type,
        config=data.config
    )

    if not validation_result['is_valid']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "配置参数验证失败",
                "errors": validation_result['errors']
            }
        )

    # 2. 保存到数据库
    repo = StrategyConfigRepository()

    config_data = {
        'strategy_type': data.strategy_type,
        'config': data.config,
        'name': data.name,
        'description': data.description,
        'category': data.category,
        'tags': data.tags,
    }

    config_id = repo.create(config_data)

    logger.success(
        f"创建策略配置成功: config_id={config_id}, "
        f"type={data.strategy_type}, name={data.name}"
    )

    return {
        "success": True,
        "data": {"config_id": config_id},
        "message": "策略配置创建成功"
    }


@router.get("", summary="获取配置列表")
@handle_api_errors
async def list_configs(
    strategy_type: Optional[str] = Query(None, description="策略类型过滤"),
    is_enabled: Optional[bool] = Query(None, description="是否启用过滤"),
    status_filter: Optional[str] = Query(None, alias="status", description="状态过滤"),
    category: Optional[str] = Query(None, description="分类过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
) -> Dict[str, Any]:
    """
    获取策略配置列表

    支持分页和多种过滤条件。

    Args:
        strategy_type: 策略类型过滤
        is_enabled: 是否启用过滤
        status_filter: 状态过滤
        category: 分类过滤
        page: 页码
        page_size: 每页数量

    Returns:
        {
            "success": true,
            "data": [...],
            "meta": {
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5
            }
        }
    """
    adapter = ConfigStrategyAdapter()

    result = await adapter.list_configs(
        strategy_type=strategy_type,
        is_enabled=is_enabled,
        page=page,
        page_size=page_size
    )

    logger.info(
        f"获取配置列表: page={page}, "
        f"page_size={page_size}, total={result['meta']['total']}"
    )

    return {
        "success": True,
        "data": result['items'],
        "meta": result['meta']
    }


@router.get("/{config_id}", summary="获取配置详情")
@handle_api_errors
async def get_config(config_id: int) -> Dict[str, Any]:
    """
    获取指定配置的详细信息

    Args:
        config_id: 配置ID

    Returns:
        {
            "success": true,
            "data": {
                "id": 1,
                "strategy_type": "momentum",
                "config": {...},
                ...
            }
        }
    """
    adapter = ConfigStrategyAdapter()
    config = await adapter.get_config_by_id(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置不存在: config_id={config_id}"
        )

    logger.info(f"获取配置详情: config_id={config_id}")

    return {
        "success": True,
        "data": config
    }


@router.put("/{config_id}", summary="更新配置")
@handle_api_errors
async def update_config(
    config_id: int,
    data: StrategyConfigUpdate
) -> Dict[str, Any]:
    """
    更新指定配置

    Args:
        config_id: 配置ID
        data: 更新数据

    Returns:
        {
            "success": true,
            "message": "配置更新成功"
        }
    """
    # 1. 检查配置是否存在
    adapter = ConfigStrategyAdapter()
    existing_config = await adapter.get_config_by_id(config_id)

    if not existing_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置不存在: config_id={config_id}"
        )

    # 2. 如果更新了配置参数，需要验证
    update_data = data.dict(exclude_unset=True)

    if 'config' in update_data:
        validation_result = await adapter.validate_config(
            strategy_type=existing_config['strategy_type'],
            config=update_data['config']
        )

        if not validation_result['is_valid']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "配置参数验证失败",
                    "errors": validation_result['errors']
                }
            )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有提供更新数据"
        )

    # 3. 更新数据库
    repo = StrategyConfigRepository()
    repo.update(config_id, update_data)

    logger.success(f"更新配置成功: config_id={config_id}")

    return {
        "success": True,
        "message": "配置更新成功"
    }


@router.delete("/{config_id}", summary="删除配置")
@handle_api_errors
async def delete_config(config_id: int) -> Dict[str, Any]:
    """
    删除指定配置

    Args:
        config_id: 配置ID

    Returns:
        {
            "success": true,
            "message": "配置删除成功"
        }
    """
    # 1. 检查配置是否存在
    adapter = ConfigStrategyAdapter()
    existing_config = await adapter.get_config_by_id(config_id)

    if not existing_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置不存在: config_id={config_id}"
        )

    # 2. 删除数据库记录
    repo = StrategyConfigRepository()
    repo.delete(config_id)

    logger.warning(f"删除配置: config_id={config_id}")

    return {
        "success": True,
        "message": "配置删除成功"
    }


@router.post("/{config_id}/test", summary="测试配置", status_code=status.HTTP_200_OK)
@handle_api_errors
async def test_config(config_id: int) -> Dict[str, Any]:
    """
    测试配置是否能成功创建策略

    尝试从配置创建策略实例，验证配置的有效性。

    Args:
        config_id: 配置ID

    Returns:
        {
            "success": true,
            "data": {
                "test_passed": true,
                "strategy_type": "momentum",
                "message": "配置测试通过"
            }
        }
    """
    adapter = ConfigStrategyAdapter()

    try:
        # 尝试创建策略
        strategy = await adapter.create_strategy_from_config(config_id)

        # 获取策略类型
        config = await adapter.get_config_by_id(config_id)

        logger.success(f"配置测试通过: config_id={config_id}")

        return {
            "success": True,
            "data": {
                "test_passed": True,
                "strategy_type": config['strategy_type'],
                "strategy_class": strategy.__class__.__name__,
                "message": "配置测试通过，策略创建成功"
            }
        }

    except Exception as e:
        logger.error(f"配置测试失败: config_id={config_id}, error={str(e)}")

        return {
            "success": False,
            "data": {
                "test_passed": False,
                "error": str(e),
                "message": "配置测试失败"
            }
        }
