"""
API路由模块
"""

from fastapi import APIRouter
from .endpoints import stocks, data, features, models, backtest

# 创建主路由
router = APIRouter()

# 注册子路由
router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
router.include_router(data.router, prefix="/data", tags=["data"])
router.include_router(features.router, prefix="/features", tags=["features"])
router.include_router(models.router, prefix="/models", tags=["models"])
router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])

__all__ = ['router']
