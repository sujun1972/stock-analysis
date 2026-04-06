"""
配置管理 API
管理系统配置、数据源设置等
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.services.config_service import ConfigService
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


class DataSourceConfigRequest(BaseModel):
    """数据源配置请求"""

    tushare_token: Optional[str] = None
    earliest_history_date: Optional[str] = None
    max_requests_per_minute: Optional[int] = None


@router.get("/source")
@handle_api_errors
async def get_data_source_config(
    current_user: User = Depends(require_admin)
):
    """
    获取数据源配置

    Returns:
        当前数据源配置信息
    """
    config_service = ConfigService()
    config = await config_service.get_data_source_config()

    return ApiResponse.success(data=config)


@router.post("/source")
@handle_api_errors
async def update_data_source_config(
    request: DataSourceConfigRequest,
    current_user: User = Depends(require_admin)
):
    """
    更新数据源配置

    Args:
        request: 数据源配置请求
            - data_source: 主数据源名称 ('akshare' 或 'tushare')
            - minute_data_source: 分时数据源名称 ('akshare' 或 'tushare')
            - realtime_data_source: 实时数据源名称 ('akshare' 或 'tushare')
            - tushare_token: Tushare Token (可选)

    Returns:
        更新后的配置信息
    """
    config_service = ConfigService()

    # 更新数据源配置
    config = await config_service.update_data_source(
        tushare_token=request.tushare_token,
        earliest_history_date=request.earliest_history_date,
        max_requests_per_minute=request.max_requests_per_minute,
    )

    return ApiResponse.success(
        data=config,
        message="配置已保存",
    )


@router.get("/all")
@handle_api_errors
async def get_all_configs(
    current_user: User = Depends(require_admin)
):
    """
    获取所有系统配置

    Returns:
        所有配置信息的字典
    """
    config_service = ConfigService()
    configs = await config_service.get_all_configs()

    return ApiResponse.success(data=configs)


class SystemSettingsRequest(BaseModel):
    """系统设置请求"""
    stock_analysis_url: Optional[str] = None


@router.get("/system")
@handle_api_errors
async def get_system_settings():
    """
    获取系统设置（公开接口，无需认证）

    Returns:
        系统设置信息
    """
    config_service = ConfigService()

    # 获取股票分析页面URL配置
    stock_analysis_url = await config_service.get_config("stock_analysis_url")
    if not stock_analysis_url:
        stock_analysis_url = "http://localhost:3000/analysis?code={code}"

    return ApiResponse.success(data={
        "stock_analysis_url": stock_analysis_url
    })


@router.post("/system")
@handle_api_errors
async def update_system_settings(
    request: SystemSettingsRequest,
    current_user: User = Depends(require_admin)
):
    """
    更新系统设置（需要管理员权限）

    Args:
        request: 系统设置请求
            - stock_analysis_url: 股票分析页面URL

    Returns:
        更新后的设置信息
    """
    config_service = ConfigService()

    # 更新股票分析URL
    if request.stock_analysis_url is not None:
        await config_service.set_config(
            "stock_analysis_url",
            request.stock_analysis_url,
            "股票分析页面URL模板（使用 {code} 作为占位符）"
        )

    # 返回更新后的配置
    stock_analysis_url = await config_service.get_config("stock_analysis_url")

    return ApiResponse.success(
        data={"stock_analysis_url": stock_analysis_url},
        message="系统设置已更新"
    )


@router.get("/sync-status")
@handle_api_errors
async def get_sync_status(
    current_user: User = Depends(require_admin)
):
    """
    获取同步状态

    Returns:
        当前同步状态信息
    """
    config_service = ConfigService()
    status = await config_service.get_sync_status()

    return ApiResponse.success(data=status)
