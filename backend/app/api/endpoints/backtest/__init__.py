"""
回测模块 - 路由聚合器

将所有回测相关的子模块路由聚合到统一的 router
"""
from fastapi import APIRouter

from . import execution, metrics, parallel, optimization, analysis, async_backtest

router = APIRouter()

# 注册各功能模块路由
router.include_router(execution.router, prefix="", tags=["backtest-execution"])
router.include_router(metrics.router, tags=["backtest-metrics"])
router.include_router(parallel.router, tags=["backtest-parallel"])
router.include_router(optimization.router, tags=["backtest-optimization"])
router.include_router(analysis.router, tags=["backtest-analysis"])
router.include_router(async_backtest.router, tags=["backtest-async"])

# 导出核心函数供其他模块使用
from .execution import execute_backtest_core

__all__ = ['router', 'execute_backtest_core']
