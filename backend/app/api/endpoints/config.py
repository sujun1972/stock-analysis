"""
配置管理 API
管理系统配置、数据源设置等
"""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.services.config_service import ConfigService

router = APIRouter()


class DataSourceConfigRequest(BaseModel):
    """数据源配置请求"""

    data_source: str
    minute_data_source: Optional[str] = None
    realtime_data_source: Optional[str] = None
    tushare_token: Optional[str] = None


@router.get("/source")
@handle_api_errors
async def get_data_source_config():
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
async def update_data_source_config(request: DataSourceConfigRequest):
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
        data_source=request.data_source,
        minute_data_source=request.minute_data_source,
        realtime_data_source=request.realtime_data_source,
        tushare_token=request.tushare_token,
    )

    return ApiResponse.success(
        data=config,
        message=f"成功切换数据源：主数据源={request.data_source}，分时数据源={request.minute_data_source or '未更改'}，实时数据源={request.realtime_data_source or '未更改'}",
    )


@router.get("/all")
@handle_api_errors
async def get_all_configs():
    """
    获取所有系统配置

    Returns:
        所有配置信息的字典
    """
    config_service = ConfigService()
    configs = await config_service.get_all_configs()

    return ApiResponse.success(data=configs)


@router.get("/sync-status")
@handle_api_errors
async def get_sync_status():
    """
    获取同步状态

    Returns:
        当前同步状态信息
    """
    config_service = ConfigService()
    status = await config_service.get_sync_status()

    return ApiResponse.success(data=status)
