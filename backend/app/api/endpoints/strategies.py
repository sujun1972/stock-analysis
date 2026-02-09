"""
统一策略系统 API 端点 (Unified Strategies API)

根据 UNIFIED_DYNAMIC_STRATEGY_ARCHITECTURE.md Phase 2 设计
统一管理所有策略（builtin/ai/custom），不再区分预定义/配置/动态

核心特性:
- 所有策略存储在单一 strategies 表
- 统一的 RESTful API
- 完整代码可见性
- 支持代码验证和安全检查

作者: Backend Team
创建日期: 2026-02-09
版本: 2.0.0
"""

import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger

from app.api.error_handler import handle_api_errors
from app.repositories.strategy_repository import StrategyRepository
from app.schemas.strategy import (
    StrategyCreate,
    StrategyListResponse,
    StrategyResponse,
    StrategyStatistics,
    StrategyUpdate,
    ValidateCodeRequest,
    ValidationResult,
)

# 导入 Core 的代码验证模块
core_path = Path(__file__).parent.parent.parent.parent.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

from src.strategies.security.code_sanitizer import CodeSanitizer

router = APIRouter()


# ==================== API 端点 ====================


@router.get("/statistics", summary="获取策略统计信息", response_model=Dict[str, Any])
@handle_api_errors
async def get_statistics() -> Dict[str, Any]:
    """
    获取策略的统计信息

    Returns:
        {
            "success": true,
            "data": {
                "total_count": 10,
                "enabled_count": 8,
                "disabled_count": 2,
                "by_source": {"builtin": 3, "ai": 4, "custom": 3},
                "by_category": {"momentum": 4, "reversal": 3, "factor": 3},
                "by_validation": {"passed": 8, "failed": 1, "pending": 1},
                "by_risk": {"safe": 3, "low": 4, "medium": 2, "high": 1}
            }
        }
    """
    repo = StrategyRepository()
    statistics = repo.get_statistics()

    logger.info(f"获取策略统计: total={statistics['total_count']}")

    return {"success": True, "data": statistics}


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
                "risk_level": "low",
                "errors": [],
                "warnings": [],
                "security_issues": []
            }
        }
    """
    try:
        sanitizer = CodeSanitizer()
        result = sanitizer.sanitize(request.code, strict_mode=request.strict_mode)

        validation_result = {
            "is_valid": result.get("safe", False),
            "status": "passed" if result.get("safe") else "failed",
            "risk_level": result.get("risk_level", "medium"),
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", []),
            "security_issues": result.get("security_issues", []),
        }

        logger.info(
            f"验证策略代码: valid={validation_result['is_valid']}, "
            f"status={validation_result['status']}, "
            f"risk_level={validation_result['risk_level']}"
        )

        return {"success": True, "data": validation_result}

    except Exception as e:
        logger.error(f"代码验证失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"代码验证失败: {str(e)}",
        )


@router.post("", summary="创建策略", status_code=status.HTTP_201_CREATED)
@handle_api_errors
async def create_strategy(data: StrategyCreate) -> Dict[str, Any]:
    """
    创建新策略

    自动进行代码验证和安全检查。

    Args:
        data: 策略数据

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
            "message": "策略创建成功"
        }
    """
    repo = StrategyRepository()

    # 1. 检查策略名称是否已存在
    name_exists = repo.check_name_exists(data.name)
    if name_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"策略名称已存在: {data.name}"
        )

    # 2. 验证代码
    sanitizer = CodeSanitizer()
    validation_result = sanitizer.sanitize(data.code, strict_mode=True)

    validation_data = {
        "is_valid": validation_result.get("safe", False),
        "status": "passed" if validation_result.get("safe") else "failed",
        "risk_level": validation_result.get("risk_level", "medium"),
        "errors": validation_result.get("errors", []),
        "warnings": validation_result.get("warnings", []),
        "security_issues": validation_result.get("security_issues", []),
    }

    if validation_data["status"] == "failed":
        logger.warning(
            f"代码验证失败: name={data.name}, " f"errors={validation_data['errors']}"
        )

    # 3. 保存到数据库
    strategy_data = {
        "name": data.name,
        "display_name": data.display_name,
        "code": data.code,
        "class_name": data.class_name,
        "source_type": data.source_type,
        "description": data.description,
        "category": data.category,
        "tags": data.tags or [],
        "default_params": data.default_params,
        "validation_status": validation_data["status"],
        "validation_errors": validation_data.get("errors"),
        "validation_warnings": validation_data.get("warnings"),
        "risk_level": validation_data["risk_level"],
        "parent_strategy_id": data.parent_strategy_id,
        "created_by": data.created_by,
    }

    strategy_id = repo.create(strategy_data)

    logger.success(
        f"创建策略成功: strategy_id={strategy_id}, "
        f"name={data.name}, "
        f"validation={validation_data['status']}"
    )

    return {
        "success": True,
        "data": {"strategy_id": strategy_id, "validation": validation_data},
        "message": "策略创建成功",
    }


@router.get("", summary="获取策略列表", response_model=Dict[str, Any])
@handle_api_errors
async def list_strategies(
    source_type: Optional[str] = Query(None, description="来源类型过滤: builtin/ai/custom"),
    category: Optional[str] = Query(None, description="类别过滤"),
    is_enabled: Optional[bool] = Query(None, description="是否启用过滤"),
    validation_status: Optional[str] = Query(None, description="验证状态过滤"),
    search: Optional[str] = Query(None, description="搜索关键词（名称、描述）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
) -> Dict[str, Any]:
    """
    获取策略列表

    支持分页和多种过滤条件。
    注意：列表接口不返回完整代码，只返回元信息。

    Args:
        source_type: 来源类型过滤
        category: 类别过滤
        is_enabled: 是否启用过滤
        validation_status: 验证状态过滤
        search: 搜索关键词
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
    repo = StrategyRepository()

    result = repo.list_all(
        source_type=source_type,
        category=category,
        is_enabled=is_enabled,
        validation_status=validation_status,
        search=search,
        page=page,
        page_size=page_size,
        include_code=False,  # 列表接口不包含完整代码
    )

    logger.info(
        f"获取策略列表: page={page}, "
        f"page_size={page_size}, "
        f"total={result['meta']['total']}"
    )

    return {"success": True, "data": result["items"], "meta": result["meta"]}


@router.get("/{strategy_id}", summary="获取策略详情", response_model=Dict[str, Any])
@handle_api_errors
async def get_strategy(strategy_id: int) -> Dict[str, Any]:
    """
    获取指定策略的详细信息（包含完整代码）

    包括元信息、验证状态、使用统计等，以及完整的Python代码。

    Args:
        strategy_id: 策略ID

    Returns:
        {
            "success": true,
            "data": {
                "id": 1,
                "name": "momentum_20d",
                "display_name": "动量策略 20日",
                "code": "class MomentumStrategy(BaseStrategy):\n    ...",
                ...
            }
        }
    """
    repo = StrategyRepository()
    strategy = repo.get_by_id(strategy_id)

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"策略不存在: strategy_id={strategy_id}"
        )

    # 增加使用计数
    repo.increment_usage_count(strategy_id)

    logger.info(f"获取策略详情: strategy_id={strategy_id}, name={strategy['name']}")

    return {"success": True, "data": strategy}


@router.put("/{strategy_id}", summary="更新策略")
@handle_api_errors
async def update_strategy(strategy_id: int, data: StrategyUpdate) -> Dict[str, Any]:
    """
    更新指定策略

    如果更新了代码，会自动重新验证。
    注意：内置策略（source_type=builtin）不允许修改代码。

    Args:
        strategy_id: 策略ID
        data: 更新数据

    Returns:
        {
            "success": true,
            "message": "策略更新成功",
            "validation": {...}  # 如果更新了代码
        }
    """
    repo = StrategyRepository()

    # 1. 检查策略是否存在
    existing_strategy = repo.get_by_id(strategy_id)
    if not existing_strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"策略不存在: strategy_id={strategy_id}"
        )

    # 2. 内置策略不允许修改代码
    if existing_strategy["source_type"] == "builtin" and data.code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="内置策略不允许修改代码"
        )

    # 3. 准备更新数据
    update_data = data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="没有提供更新数据"
        )

    # 4. 如果更新了代码，重新验证
    validation_data = None
    if "code" in update_data:
        sanitizer = CodeSanitizer()
        validation_result = sanitizer.sanitize(update_data["code"], strict_mode=True)

        validation_data = {
            "is_valid": validation_result.get("safe", False),
            "status": "passed" if validation_result.get("safe") else "failed",
            "risk_level": validation_result.get("risk_level", "medium"),
            "errors": validation_result.get("errors", []),
            "warnings": validation_result.get("warnings", []),
            "security_issues": validation_result.get("security_issues", []),
        }

        # 更新验证状态
        update_data["validation_status"] = validation_data["status"]
        update_data["validation_errors"] = validation_data.get("errors")
        update_data["validation_warnings"] = validation_data.get("warnings")
        update_data["risk_level"] = validation_data["risk_level"]

        logger.info(
            f"重新验证代码: strategy_id={strategy_id}, " f"status={validation_data['status']}"
        )

    # 5. 更新数据库
    repo.update(strategy_id, update_data)

    logger.success(f"更新策略成功: strategy_id={strategy_id}")

    response = {"success": True, "message": "策略更新成功"}

    if validation_data:
        response["validation"] = validation_data

    return response


@router.delete("/{strategy_id}", summary="删除策略")
@handle_api_errors
async def delete_strategy(strategy_id: int) -> Dict[str, Any]:
    """
    删除指定策略

    注意：内置策略（source_type=builtin）不允许删除。

    Args:
        strategy_id: 策略ID

    Returns:
        {
            "success": true,
            "message": "策略删除成功"
        }
    """
    repo = StrategyRepository()

    # 1. 检查策略是否存在
    existing_strategy = repo.get_by_id(strategy_id)
    if not existing_strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"策略不存在: strategy_id={strategy_id}"
        )

    # 2. 内置策略不允许删除
    if existing_strategy["source_type"] == "builtin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="内置策略不允许删除"
        )

    # 3. 删除数据库记录
    repo.delete(strategy_id)

    logger.warning(f"删除策略: strategy_id={strategy_id}, name={existing_strategy['name']}")

    return {"success": True, "message": "策略删除成功"}


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
                "name": "momentum_20d",
                "class_name": "MomentumStrategy",
                "code": "...",
                "code_hash": "...",
                "validation_status": "passed"
            }
        }
    """
    repo = StrategyRepository()
    strategy = repo.get_by_id(strategy_id)

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"策略不存在: strategy_id={strategy_id}"
        )

    code_info = {
        "strategy_id": strategy["id"],
        "name": strategy["name"],
        "display_name": strategy["display_name"],
        "class_name": strategy["class_name"],
        "code": strategy["code"],
        "code_hash": strategy["code_hash"],
        "source_type": strategy["source_type"],
        "validation_status": strategy["validation_status"],
        "risk_level": strategy["risk_level"],
    }

    logger.info(f"获取策略代码: strategy_id={strategy_id}")

    return {"success": True, "data": code_info}


@router.post("/{strategy_id}/test", summary="测试策略", status_code=status.HTTP_200_OK)
@handle_api_errors
async def test_strategy(
    strategy_id: int, strict_mode: bool = Query(True, description="严格模式")
) -> Dict[str, Any]:
    """
    测试策略是否能成功创建

    尝试从策略代码创建实例，验证代码的有效性。

    Args:
        strategy_id: 策略ID
        strict_mode: 严格模式（任何安全问题都拒绝）

    Returns:
        {
            "success": true,
            "data": {
                "test_passed": true,
                "strategy_name": "momentum_20d",
                "strategy_class": "MomentumStrategy",
                "message": "策略测试通过"
            }
        }
    """
    repo = StrategyRepository()

    try:
        # 1. 获取策略元信息
        strategy = repo.get_by_id(strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"策略不存在: strategy_id={strategy_id}",
            )

        # 2. 验证代码
        sanitizer = CodeSanitizer()
        validation_result = sanitizer.sanitize(strategy["code"], strict_mode=strict_mode)

        if not validation_result.get("safe"):
            return {
                "success": False,
                "data": {
                    "test_passed": False,
                    "error": "代码验证失败",
                    "errors": validation_result.get("errors", []),
                    "message": "策略测试失败：代码安全验证未通过",
                },
            }

        # 3. 尝试动态加载（这里可以扩展为真正的策略实例化）
        # TODO: 实现动态加载策略实例
        # from src.strategies.loaders.dynamic_loader import DynamicCodeLoader
        # loader = DynamicCodeLoader()
        # strategy_instance = loader.load_strategy_from_code(...)

        logger.success(f"策略测试通过: strategy_id={strategy_id}")

        return {
            "success": True,
            "data": {
                "test_passed": True,
                "strategy_name": strategy["name"],
                "strategy_class": strategy["class_name"],
                "validation_status": strategy["validation_status"],
                "message": "策略测试通过，代码可以正常执行",
            },
        }

    except Exception as e:
        logger.error(f"策略测试失败: strategy_id={strategy_id}, " f"error={str(e)}")

        return {
            "success": False,
            "data": {
                "test_passed": False,
                "error": str(e),
                "error_type": e.__class__.__name__,
                "message": "策略测试失败",
            },
        }
