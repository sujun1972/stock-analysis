"""
动态策略API端点 (Dynamic Strategies API)

提供动态代码策略的CRUD操作和代码验证功能。

动态代码策略特点:
- 动态加载 Python 代码
- 支持 AI 生成策略
- 自动安全验证（AST 分析、权限检查、资源限制）

作者: Backend Team
创建日期: 2026-02-09
版本: 1.0.0
"""

import hashlib
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field, validator

from app.api.error_handler import handle_api_errors
from app.core_adapters.dynamic_strategy_adapter import DynamicStrategyAdapter
from app.repositories.dynamic_strategy_repository import DynamicStrategyRepository

router = APIRouter()


# ==================== Pydantic 模型 ====================


class DynamicStrategyCreate(BaseModel):
    """创建动态策略请求模型"""

    strategy_name: str = Field(..., description="策略名称（唯一）")
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="策略描述")
    class_name: str = Field(..., description="策略类名")
    generated_code: str = Field(..., description="Python策略代码")
    user_prompt: Optional[str] = Field(None, description="用户的自然语言描述")
    ai_model: Optional[str] = Field(None, description="AI模型名称")
    category: Optional[str] = Field(None, description="策略分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")

    @validator("strategy_name")
    def validate_strategy_name(cls, v):
        """验证策略名称"""
        if not v or len(v.strip()) == 0:
            raise ValueError("策略名称不能为空")
        if len(v) > 200:
            raise ValueError("策略名称不能超过200个字符")
        return v.strip()

    @validator("class_name")
    def validate_class_name(cls, v):
        """验证类名"""
        if not v or len(v.strip()) == 0:
            raise ValueError("类名不能为空")
        if not v[0].isupper():
            raise ValueError("类名必须以大写字母开头")
        return v.strip()

    @validator("generated_code")
    def validate_code(cls, v):
        """验证代码不为空"""
        if not v or len(v.strip()) == 0:
            raise ValueError("策略代码不能为空")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "strategy_name": "my_momentum_strategy",
                "display_name": "我的动量策略",
                "description": "基于动量因子的选股策略",
                "class_name": "MyMomentumStrategy",
                "generated_code": "class MyMomentumStrategy(BaseStrategy):\n    ...",
                "user_prompt": "创建一个基于20日动量的选股策略",
                "ai_model": "deepseek-coder",
                "category": "动量策略",
                "tags": ["动量", "因子"]
            }
        }


class DynamicStrategyUpdate(BaseModel):
    """更新动态策略请求模型"""

    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="策略描述")
    generated_code: Optional[str] = Field(None, description="Python策略代码")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    status: Optional[str] = Field(None, description="状态: draft, active, archived, deprecated")
    category: Optional[str] = Field(None, description="策略分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")

    @validator("status")
    def validate_status(cls, v):
        """验证状态"""
        if v is not None:
            allowed_statuses = ["draft", "active", "archived", "deprecated"]
            if v not in allowed_statuses:
                raise ValueError(
                    f"状态必须是以下之一: {', '.join(allowed_statuses)}"
                )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "display_name": "我的优化动量策略 v2",
                "description": "优化后的动量策略",
                "is_enabled": True,
                "status": "active"
            }
        }


class ValidateCodeRequest(BaseModel):
    """验证代码请求模型"""

    code: str = Field(..., description="Python策略代码")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "class MyStrategy(BaseStrategy):\n    def select_stocks(self, data):\n        return []"
            }
        }


# ==================== API 端点 ====================


@router.get("/statistics", summary="获取动态策略统计信息")
@handle_api_errors
async def get_statistics() -> Dict[str, Any]:
    """
    获取动态策略的统计信息

    Returns:
        {
            "success": true,
            "data": {
                "total_count": 10,
                "enabled_count": 8,
                "disabled_count": 2,
                "validation_passed": 7,
                "validation_failed": 1,
                "validation_pending": 2,
                "by_status": {"draft": 3, "active": 5, "archived": 2}
            }
        }
    """
    adapter = DynamicStrategyAdapter()
    statistics = await adapter.get_strategy_statistics()

    logger.info(f"获取动态策略统计: total={statistics['total_count']}")

    return {
        "success": True,
        "data": statistics
    }


@router.post("/validate", summary="验证策略代码", status_code=status.HTTP_200_OK)
@handle_api_errors
async def validate_code(request: ValidateCodeRequest) -> Dict[str, Any]:
    """
    验证策略代码的安全性和正确性

    使用 Core 的安全验证机制进行代码检查：
    - 语法检查
    - AST 分析
    - 危险操作检测
    - 安全问题识别

    Args:
        request: 验证代码请求

    Returns:
        {
            "success": true,
            "data": {
                "is_valid": true,
                "status": "passed",
                "errors": [],
                "warnings": [],
                "security_issues": []
            }
        }
    """
    adapter = DynamicStrategyAdapter()
    validation_result = await adapter.validate_strategy_code(request.code)

    logger.info(
        f"验证策略代码: "
        f"valid={validation_result['is_valid']}, "
        f"status={validation_result['status']}"
    )

    return {
        "success": True,
        "data": validation_result
    }


@router.post("", summary="创建动态策略", status_code=status.HTTP_201_CREATED)
@handle_api_errors
async def create_dynamic_strategy(data: DynamicStrategyCreate) -> Dict[str, Any]:
    """
    创建新的动态代码策略

    自动进行代码验证和安全检查。

    Args:
        data: 动态策略数据

    Returns:
        {
            "success": true,
            "data": {
                "strategy_id": 1,
                "validation": {
                    "is_valid": true,
                    "status": "passed",
                    ...
                }
            },
            "message": "动态策略创建成功"
        }
    """
    adapter = DynamicStrategyAdapter()

    # 1. 检查策略名称是否已存在
    name_exists = await adapter.check_strategy_name_exists(data.strategy_name)
    if name_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"策略名称已存在: {data.strategy_name}"
        )

    # 2. 验证代码
    validation_result = await adapter.validate_strategy_code(data.generated_code)

    if validation_result['status'] == 'failed':
        logger.warning(
            f"代码验证失败: strategy_name={data.strategy_name}, "
            f"errors={validation_result['errors']}"
        )

    # 3. 计算代码哈希
    code_hash = hashlib.sha256(data.generated_code.encode()).hexdigest()

    # 4. 保存到数据库
    repo = DynamicStrategyRepository()

    strategy_data = {
        'strategy_name': data.strategy_name,
        'display_name': data.display_name,
        'description': data.description,
        'class_name': data.class_name,
        'generated_code': data.generated_code,
        'code_hash': code_hash,
        'user_prompt': data.user_prompt,
        'ai_model': data.ai_model,
        'validation_status': validation_result['status'],
        'validation_errors': validation_result.get('errors'),
        'validation_warnings': validation_result.get('warnings'),
        'category': data.category,
        'tags': data.tags,
    }

    strategy_id = repo.create(strategy_data)

    logger.success(
        f"创建动态策略成功: strategy_id={strategy_id}, "
        f"name={data.strategy_name}, validation={validation_result['status']}"
    )

    return {
        "success": True,
        "data": {
            "strategy_id": strategy_id,
            "validation": validation_result
        },
        "message": "动态策略创建成功"
    }


@router.get("", summary="获取动态策略列表")
@handle_api_errors
async def list_dynamic_strategies(
    validation_status: Optional[str] = Query(None, description="验证状态过滤"),
    is_enabled: Optional[bool] = Query(None, description="是否启用过滤"),
    status_filter: Optional[str] = Query(None, alias="status", description="状态过滤"),
    category: Optional[str] = Query(None, description="分类过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
) -> Dict[str, Any]:
    """
    获取动态策略列表

    支持分页和多种过滤条件。

    Args:
        validation_status: 验证状态过滤
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
                "total": 50,
                "page": 1,
                "page_size": 20,
                "total_pages": 3
            }
        }
    """
    adapter = DynamicStrategyAdapter()

    result = await adapter.list_strategies(
        validation_status=validation_status,
        is_enabled=is_enabled,
        status=status_filter,
        page=page,
        page_size=page_size
    )

    logger.info(
        f"获取动态策略列表: page={page}, "
        f"page_size={page_size}, total={result['meta']['total']}"
    )

    return {
        "success": True,
        "data": result['items'],
        "meta": result['meta']
    }


@router.get("/{strategy_id}", summary="获取动态策略详情")
@handle_api_errors
async def get_dynamic_strategy(strategy_id: int) -> Dict[str, Any]:
    """
    获取指定动态策略的详细信息

    包括元信息、验证状态、测试结果等。

    Args:
        strategy_id: 策略ID

    Returns:
        {
            "success": true,
            "data": {
                "strategy_id": 1,
                "strategy_name": "my_momentum_strategy",
                ...
            }
        }
    """
    adapter = DynamicStrategyAdapter()
    metadata = await adapter.get_strategy_metadata(strategy_id)

    logger.info(f"获取动态策略详情: strategy_id={strategy_id}")

    return {
        "success": True,
        "data": metadata
    }


@router.get("/{strategy_id}/code", summary="获取策略代码")
@handle_api_errors
async def get_strategy_code(strategy_id: int) -> Dict[str, Any]:
    """
    获取指定策略的代码

    Args:
        strategy_id: 策略ID

    Returns:
        {
            "success": true,
            "data": {
                "strategy_id": 1,
                "strategy_name": "my_momentum_strategy",
                "class_name": "MyMomentumStrategy",
                "generated_code": "...",
                "code_hash": "...",
                "user_prompt": "...",
                "ai_model": "deepseek-coder",
                "validation_status": "passed"
            }
        }
    """
    adapter = DynamicStrategyAdapter()
    code_info = await adapter.get_strategy_code(strategy_id)

    logger.info(f"获取策略代码: strategy_id={strategy_id}")

    return {
        "success": True,
        "data": code_info
    }


@router.put("/{strategy_id}", summary="更新动态策略")
@handle_api_errors
async def update_dynamic_strategy(
    strategy_id: int,
    data: DynamicStrategyUpdate
) -> Dict[str, Any]:
    """
    更新指定动态策略

    如果更新了代码，会自动重新验证。

    Args:
        strategy_id: 策略ID
        data: 更新数据

    Returns:
        {
            "success": true,
            "message": "动态策略更新成功",
            "validation": {...}  # 如果更新了代码
        }
    """
    # 1. 检查策略是否存在
    adapter = DynamicStrategyAdapter()
    existing_strategy = await adapter.get_strategy_metadata(strategy_id)

    # 2. 准备更新数据
    update_data = data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有提供更新数据"
        )

    # 3. 如果更新了代码，重新验证
    validation_result = None
    if 'generated_code' in update_data:
        validation_result = await adapter.validate_strategy_code(
            update_data['generated_code']
        )

        # 更新验证状态
        update_data['validation_status'] = validation_result['status']
        update_data['validation_errors'] = validation_result.get('errors')
        update_data['validation_warnings'] = validation_result.get('warnings')

        # 更新代码哈希
        code_hash = hashlib.sha256(
            update_data['generated_code'].encode()
        ).hexdigest()
        update_data['code_hash'] = code_hash

        logger.info(
            f"重新验证代码: strategy_id={strategy_id}, "
            f"status={validation_result['status']}"
        )

    # 4. 更新数据库
    repo = DynamicStrategyRepository()
    repo.update(strategy_id, update_data)

    logger.success(f"更新动态策略成功: strategy_id={strategy_id}")

    response = {
        "success": True,
        "message": "动态策略更新成功"
    }

    if validation_result:
        response["validation"] = validation_result

    return response


@router.delete("/{strategy_id}", summary="删除动态策略")
@handle_api_errors
async def delete_dynamic_strategy(strategy_id: int) -> Dict[str, Any]:
    """
    删除指定动态策略

    Args:
        strategy_id: 策略ID

    Returns:
        {
            "success": true,
            "message": "动态策略删除成功"
        }
    """
    # 1. 检查策略是否存在
    adapter = DynamicStrategyAdapter()
    await adapter.get_strategy_metadata(strategy_id)

    # 2. 删除数据库记录
    repo = DynamicStrategyRepository()
    repo.delete(strategy_id)

    logger.warning(f"删除动态策略: strategy_id={strategy_id}")

    return {
        "success": True,
        "message": "动态策略删除成功"
    }


@router.post("/{strategy_id}/test", summary="测试动态策略", status_code=status.HTTP_200_OK)
@handle_api_errors
async def test_dynamic_strategy(
    strategy_id: int,
    strict_mode: bool = Query(True, description="严格模式")
) -> Dict[str, Any]:
    """
    测试动态策略是否能成功创建

    尝试从动态代码创建策略实例，验证代码的有效性。

    Args:
        strategy_id: 策略ID
        strict_mode: 严格模式（任何安全问题都拒绝）

    Returns:
        {
            "success": true,
            "data": {
                "test_passed": true,
                "strategy_name": "my_momentum_strategy",
                "strategy_class": "MyMomentumStrategy",
                "message": "策略测试通过"
            }
        }
    """
    adapter = DynamicStrategyAdapter()

    try:
        # 1. 获取策略元信息
        metadata = await adapter.get_strategy_metadata(strategy_id)

        # 2. 尝试创建策略
        strategy = await adapter.create_strategy_from_code(
            strategy_id=strategy_id,
            strict_mode=strict_mode
        )

        logger.success(f"动态策略测试通过: strategy_id={strategy_id}")

        return {
            "success": True,
            "data": {
                "test_passed": True,
                "strategy_name": metadata['strategy_name'],
                "strategy_class": strategy.__class__.__name__,
                "validation_status": metadata['validation_status'],
                "message": "策略测试通过，代码可以正常执行"
            }
        }

    except Exception as e:
        logger.error(
            f"动态策略测试失败: strategy_id={strategy_id}, "
            f"error={str(e)}"
        )

        return {
            "success": False,
            "data": {
                "test_passed": False,
                "error": str(e),
                "error_type": e.__class__.__name__,
                "message": "策略测试失败"
            }
        }
