"""
概念板块相关的 API 端点

提供概念管理、查询和更新功能
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
import sys
from pathlib import Path

from app.core.dependencies import require_admin
from app.models.user import User
from app.models.api_response import ApiResponse
from app.repositories import ConceptRepository

# 添加 core 模块到路径
core_path = Path(__file__).parent.parent.parent.parent.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

from src.database.connection_pool_manager import ConnectionPoolManager
from src.concept_fetcher import ConceptFetcher
from src.config.settings import get_settings

router = APIRouter()

# 初始化数据库连接池（仍用于 ConceptFetcher）
settings = get_settings()
db_settings = settings.database

pool_manager = ConnectionPoolManager(
    config={
        'host': db_settings.host,
        'port': db_settings.port,
        'database': db_settings.database,
        'user': db_settings.user,
        'password': db_settings.password
    },
    min_conn=2,
    max_conn=20
)


@router.get("/list")
async def get_concepts_list(
    page: int = Query(default=1, ge=1, description="页码（从1开始）"),
    page_size: int = Query(default=50, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索概念名称")
):
    """
    获取概念板块列表（支持分页）

    Args:
        page: 页码（从1开始）
        page_size: 每页数量（1-100）
        search: 搜索关键词（概念名称）

    Returns:
        概念列表及分页信息
    """
    try:
        # 使用 Repository 层
        repo = ConceptRepository()
        concepts, total = repo.list_concepts(page=page, page_size=page_size, search=search)

        return ApiResponse.success(
            data={
                "items": concepts,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            },
            message=f"成功获取第 {page} 页，共 {total} 个概念"
        ).to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取概念列表失败: {str(e)}")


@router.get("/{concept_id}")
async def get_concept_detail(concept_id: int):
    """
    获取概念详情

    Args:
        concept_id: 概念ID

    Returns:
        概念详细信息
    """
    try:
        # 使用 Repository 层
        repo = ConceptRepository()
        concept = repo.get_by_id(concept_id)

        if not concept:
            raise HTTPException(status_code=404, detail=f"概念 {concept_id} 不存在")

        return ApiResponse.success(
            data=concept,
            message="获取概念详情成功"
        ).to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取概念详情失败: {str(e)}")


@router.get("/{concept_id}/stocks")
async def get_concept_stocks(
    concept_id: int,
    limit: Optional[int] = Query(None, ge=1, le=1000, description="限制返回数量")
):
    """
    获取概念包含的股票列表

    Args:
        concept_id: 概念ID
        limit: 限制返回数量

    Returns:
        股票列表
    """
    try:
        # 使用 Repository 层
        repo = ConceptRepository()
        stocks = repo.get_concept_stocks(concept_id, limit=limit)

        return ApiResponse.success(
            data={
                "items": stocks,
                "total": len(stocks)
            },
            message=f"获取到 {len(stocks)} 只股票"
        ).to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取概念股票列表失败: {str(e)}")


@router.get("/stock/{stock_code}")
async def get_stock_concepts(stock_code: str):
    """
    获取股票所属的所有概念

    Args:
        stock_code: 股票代码（如 '000001.SZ'）

    Returns:
        概念列表
    """
    try:
        # 使用 Repository 层
        repo = ConceptRepository()
        concepts = repo.get_stock_concepts(stock_code)

        return ApiResponse.success(
            data={
                "items": concepts,
                "total": len(concepts)
            },
            message=f"获取到 {len(concepts)} 个概念"
        ).to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票概念失败: {str(e)}")


@router.post("/sync")
async def sync_concepts(
    source: Optional[str] = Query(
        None,
        description="数据源（可选）：None=使用系统配置，em=东方财富（推荐），tushare=Tushare Pro（需5000积分）"
    ),
    current_user: User = Depends(require_admin)
):
    """
    同步概念数据（异步任务）

    Args:
        source: 数据源（可选）
               - None: 使用系统配置的概念数据源（推荐）
               - 'em': 强制使用AkShare东方财富（466个概念，完整成分股，免费）
               - 'tushare': 强制使用Tushare Pro（需5000积分，数据稳定）

    Returns:
        任务ID和状态
    """
    try:
        # 导入 Celery 任务
        from app.tasks.sync_tasks import sync_concept_task

        # 提交异步任务
        task = sync_concept_task.apply_async(kwargs={'source': source})

        source_display = source or "系统配置的概念数据源"

        return ApiResponse.success(
            data={
                "task_id": task.id,
                "source": source_display,
                "status": "pending"
            },
            message="概念数据同步任务已提交"
        ).to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交同步任务失败: {str(e)}")


@router.get("/sync/status/{task_id}")
async def get_sync_status(
    task_id: str,
    current_user: User = Depends(require_admin)
):
    """
    查询概念同步任务状态

    Args:
        task_id: 任务ID

    Returns:
        任务状态和进度
    """
    try:
        from celery.result import AsyncResult
        from app.celery_app import celery_app

        task_result = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "state": task_result.state,
            "status": task_result.state
        }

        if task_result.state == 'PENDING':
            response["message"] = "任务等待中..."
        elif task_result.state == 'STARTED':
            response["message"] = "任务执行中..."
        elif task_result.state == 'PROGRESS':
            response["message"] = "任务进行中..."
            response["progress"] = task_result.info.get('progress', 0) if task_result.info else 0
        elif task_result.state == 'SUCCESS':
            response["message"] = "任务完成"
            response["result"] = task_result.result
        elif task_result.state == 'FAILURE':
            response["message"] = "任务失败"
            response["error"] = str(task_result.info)

        return ApiResponse.success(
            data=response,
            message="查询成功"
        ).to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询任务状态失败: {str(e)}")


@router.put("/stock/{stock_code}/concepts")
async def update_stock_concepts(
    stock_code: str,
    concept_ids: List[int],
    current_user: User = Depends(require_admin)
):
    """
    更新股票的概念标签

    Args:
        stock_code: 股票代码
        concept_ids: 概念ID列表

    Returns:
        更新结果
    """
    try:
        # 使用 Repository 层（包含事务处理）
        repo = ConceptRepository()
        added_count = repo.update_stock_concepts(stock_code, concept_ids)

        return ApiResponse.success(
            data={
                "stock_code": stock_code,
                "concepts_count": added_count
            },
            message=f"成功更新股票概念，添加了 {added_count} 个概念"
        ).to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新股票概念失败: {str(e)}")
