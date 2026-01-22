"""
配置管理 API
管理系统配置、数据源设置等
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from loguru import logger

from app.services.config_service import ConfigService

router = APIRouter()


class DataSourceConfigRequest(BaseModel):
    """数据源配置请求"""
    data_source: str
    realtime_data_source: Optional[str] = None
    tushare_token: Optional[str] = None


@router.get("/source")
async def get_data_source_config():
    """
    获取数据源配置

    Returns:
        当前数据源配置信息
    """
    try:
        config_service = ConfigService()
        config = await config_service.get_data_source_config()

        return {
            "code": 200,
            "message": "success",
            "data": config
        }
    except Exception as e:
        logger.error(f"获取数据源配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/source")
async def update_data_source_config(request: DataSourceConfigRequest):
    """
    更新数据源配置

    Args:
        request: 数据源配置请求
            - data_source: 主数据源名称 ('akshare' 或 'tushare')
            - realtime_data_source: 实时数据源名称 ('akshare' 或 'tushare')
            - tushare_token: Tushare Token (可选)

    Returns:
        更新后的配置信息
    """
    try:
        config_service = ConfigService()

        # 更新数据源配置
        config = await config_service.update_data_source(
            data_source=request.data_source,
            realtime_data_source=request.realtime_data_source,
            tushare_token=request.tushare_token
        )

        return {
            "code": 200,
            "message": f"成功切换数据源：主数据源={request.data_source}，实时数据源={request.realtime_data_source or '未更改'}",
            "data": config
        }
    except ValueError as e:
        logger.error(f"数据源配置错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新数据源配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all")
async def get_all_configs():
    """
    获取所有系统配置

    Returns:
        所有配置信息的字典
    """
    try:
        config_service = ConfigService()
        configs = await config_service.get_all_configs()

        return {
            "code": 200,
            "message": "success",
            "data": configs
        }
    except Exception as e:
        logger.error(f"获取所有配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-status")
async def get_sync_status():
    """
    获取同步状态

    Returns:
        当前同步状态信息
    """
    try:
        config_service = ConfigService()
        status = await config_service.get_sync_status()

        return {
            "code": 200,
            "message": "success",
            "data": status
        }
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
