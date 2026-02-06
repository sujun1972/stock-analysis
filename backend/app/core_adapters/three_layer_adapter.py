"""
三层架构适配器 (Three-Layer Architecture Adapter)

将 Core 的三层架构模块包装为异步方法，供 FastAPI 使用。

核心功能:
- 获取选股器/入场/退出策略元数据
- 验证策略组合有效性
- 执行三层架构回测
- 缓存回测结果

作者: Backend Team
创建日期: 2026-02-06
版本: 1.0.0
"""

import asyncio
import hashlib
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

# 添加 core 项目到 Python 路径
core_path = Path(__file__).parent.parent.parent.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

# 导入 Core 的三层架构模块
from src.strategies.three_layer import (
    # 基类
    StockSelector,
    EntryStrategy,
    ExitStrategy,
    StrategyComposer,
    # 选股器实现
    MomentumSelector,
    ValueSelector,
    ExternalSelector,
    # 入场策略实现
    ImmediateEntry,
    MABreakoutEntry,
    RSIOversoldEntry,
    # 退出策略实现
    FixedStopLossExit,
    ATRStopLossExit,
    TimeBasedExit,
    CombinedExit,
)

# 单独导入 MLSelector
from src.strategies.three_layer.selectors import MLSelector

# 导入回测引擎
from src.backtest import BacktestEngine

# 导入 Backend 依赖
from app.core.cache import cache
from app.core.config import settings
from app.core.exceptions import BacktestError, DataQueryError

# 导入数据适配器
from .data_adapter import DataAdapter


class ThreeLayerAdapter:
    """
    Core 三层架构适配器

    职责:
    1. 封装 Core 的三层架构调用
    2. 参数格式转换（API DTO → Core 对象）
    3. 结果格式转换（Core Response → API JSON）
    4. 异步调用支持
    5. 缓存管理
    """

    # 策略注册表
    SELECTOR_REGISTRY = {
        "momentum": MomentumSelector,
        "value": ValueSelector,
        "external": ExternalSelector,
        "ml": MLSelector,
    }

    ENTRY_REGISTRY = {
        "immediate": ImmediateEntry,
        "ma_breakout": MABreakoutEntry,
        "rsi_oversold": RSIOversoldEntry,
    }

    EXIT_REGISTRY = {
        "fixed_stop_loss": FixedStopLossExit,
        "atr_stop_loss": ATRStopLossExit,
        "time_based": TimeBasedExit,
        "combined": CombinedExit,
    }

    def __init__(self, data_adapter: Optional[DataAdapter] = None):
        """
        初始化适配器

        Args:
            data_adapter: 数据适配器实例（可选，用于依赖注入）
        """
        self.data_adapter = data_adapter or DataAdapter()
        logger.info("✓ ThreeLayerAdapter initialized")

    async def get_selectors(self) -> List[Dict[str, Any]]:
        """
        获取所有选股器元数据

        Returns:
            [
                {
                    'id': 'momentum',
                    'name': '动量选股器',
                    'description': '...',
                    'version': '1.0.0',
                    'parameters': [...]
                },
                ...
            ]

        Note:
            结果会被缓存1天
        """
        # 检查缓存
        cache_key = "three_layer:selectors:metadata"
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

        # 生成元数据
        selectors = []
        for selector_id, selector_class in self.SELECTOR_REGISTRY.items():
            try:
                # 使用类方法获取参数定义
                parameters = selector_class.get_parameters()
                # 实例化获取名称（需要实例才能访问属性）
                instance = selector_class(params={})

                # 构建元数据（转换dataclass为dict）
                param_list = []
                for param in parameters:
                    param_dict = {
                        "name": param.name,
                        "label": param.label,
                        "type": param.type,
                        "default": param.default,
                        "description": param.description,
                    }
                    if param.min_value is not None:
                        param_dict["min_value"] = param.min_value
                    if param.max_value is not None:
                        param_dict["max_value"] = param.max_value
                    if param.options is not None:
                        param_dict["options"] = param.options
                    param_list.append(param_dict)

                selectors.append({
                    "id": selector_id,
                    "name": instance.name,
                    "description": f"{instance.name}选股策略",
                    "version": "1.0.0",
                    "parameters": param_list,
                })
            except Exception as e:
                logger.error(f"获取选股器元数据失败: {selector_id} - {e}")
                continue

        # 缓存结果
        await cache.set(cache_key, selectors, ttl=86400)  # 1天

        return selectors

    async def get_entries(self) -> List[Dict[str, Any]]:
        """
        获取所有入场策略元数据

        Returns:
            [
                {
                    'id': 'immediate',
                    'name': '立即入场',
                    'description': '...',
                    'version': '1.0.0',
                    'parameters': [...]
                },
                ...
            ]

        Note:
            结果会被缓存1天
        """
        # 检查缓存
        cache_key = "three_layer:entries:metadata"
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

        # 生成元数据
        entries = []
        for entry_id, entry_class in self.ENTRY_REGISTRY.items():
            try:
                # 使用类方法获取参数定义
                parameters = entry_class.get_parameters()
                # 实例化获取名称
                instance = entry_class(params={})

                # 构建元数据
                param_list = []
                for param in parameters:
                    param_dict = {
                        "name": param.name,
                        "label": param.label,
                        "type": param.type,
                        "default": param.default,
                        "description": param.description,
                    }
                    if param.min_value is not None:
                        param_dict["min_value"] = param.min_value
                    if param.max_value is not None:
                        param_dict["max_value"] = param.max_value
                    if param.options is not None:
                        param_dict["options"] = param.options
                    param_list.append(param_dict)

                entries.append({
                    "id": entry_id,
                    "name": instance.name,
                    "description": f"{instance.name}策略",
                    "version": "1.0.0",
                    "parameters": param_list,
                })
            except Exception as e:
                logger.error(f"获取入场策略元数据失败: {entry_id} - {e}")
                continue

        # 缓存结果
        await cache.set(cache_key, entries, ttl=86400)  # 1天

        return entries

    async def get_exits(self) -> List[Dict[str, Any]]:
        """
        获取所有退出策略元数据

        Returns:
            [
                {
                    'id': 'fixed_stop_loss',
                    'name': '固定止损',
                    'description': '...',
                    'version': '1.0.0',
                    'parameters': [...]
                },
                ...
            ]

        Note:
            结果会被缓存1天
        """
        # 检查缓存
        cache_key = "three_layer:exits:metadata"
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

        # 生成元数据
        exits = []
        for exit_id, exit_class in self.EXIT_REGISTRY.items():
            try:
                # 使用类方法获取参数定义
                parameters = exit_class.get_parameters()
                # 实例化获取名称
                instance = exit_class(params={})

                # 构建元数据
                param_list = []
                for param in parameters:
                    param_dict = {
                        "name": param.name,
                        "label": param.label,
                        "type": param.type,
                        "default": param.default,
                        "description": param.description,
                    }
                    if param.min_value is not None:
                        param_dict["min_value"] = param.min_value
                    if param.max_value is not None:
                        param_dict["max_value"] = param.max_value
                    if param.options is not None:
                        param_dict["options"] = param.options
                    param_list.append(param_dict)

                exits.append({
                    "id": exit_id,
                    "name": instance.name,
                    "description": f"{instance.name}策略",
                    "version": "1.0.0",
                    "parameters": param_list,
                })
            except Exception as e:
                logger.error(f"获取退出策略元数据失败: {exit_id} - {e}")
                continue

        # 缓存结果
        await cache.set(cache_key, exits, ttl=86400)  # 1天

        return exits

    async def validate_strategy_combo(
        self,
        selector_id: str,
        selector_params: dict,
        entry_id: str,
        entry_params: dict,
        exit_id: str,
        exit_params: dict,
        rebalance_freq: str,
    ) -> Dict[str, Any]:
        """
        验证策略组合的有效性

        Args:
            selector_id: 选股器ID
            selector_params: 选股器参数
            entry_id: 入场策略ID
            entry_params: 入场策略参数
            exit_id: 退出策略ID
            exit_params: 退出策略参数
            rebalance_freq: 选股频率（D/W/M）

        Returns:
            {
                'valid': True/False,
                'errors': [...]
            }
        """
        errors = []

        # 验证 ID
        if selector_id not in self.SELECTOR_REGISTRY:
            errors.append(f"未知的选股器: {selector_id}")
        if entry_id not in self.ENTRY_REGISTRY:
            errors.append(f"未知的入场策略: {entry_id}")
        if exit_id not in self.EXIT_REGISTRY:
            errors.append(f"未知的退出策略: {exit_id}")

        # 验证调仓频率
        if rebalance_freq not in ["D", "W", "M"]:
            errors.append(f"无效的调仓��率: {rebalance_freq}，必须是 D/W/M 之一")

        if errors:
            return {"valid": False, "errors": errors}

        # 创建策略实例并验证参数
        try:
            selector = self.SELECTOR_REGISTRY[selector_id](params=selector_params)
            entry = self.ENTRY_REGISTRY[entry_id](params=entry_params)
            exit_strategy = self.EXIT_REGISTRY[exit_id](params=exit_params)

            # 使用 StrategyComposer 进行组合验证
            composer = await asyncio.to_thread(
                StrategyComposer,
                selector=selector,
                entry=entry,
                exit_strategy=exit_strategy,
                rebalance_freq=rebalance_freq,
            )

            # 调用验证方法
            validation_result = await asyncio.to_thread(composer.validate)
            return validation_result

        except ValueError as e:
            # 参数验证失败
            return {"valid": False, "errors": [f"参数验证失败: {str(e)}"]}
        except Exception as e:
            # 其他异常
            logger.error(f"策略组合验证失败: {e}")
            return {"valid": False, "errors": [f"验证过程出错: {str(e)}"]}

    async def run_backtest(
        self,
        selector_id: str,
        selector_params: dict,
        entry_id: str,
        entry_params: dict,
        exit_id: str,
        exit_params: dict,
        rebalance_freq: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 1000000.0,
        stock_codes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        执行三层架构回测

        Args:
            selector_id: 选股器ID
            selector_params: 选股器参数
            entry_id: 入场策略ID
            entry_params: 入场策略参数
            exit_id: 退出策略ID
            exit_params: 退出策略参数
            rebalance_freq: 选股频率（D/W/M）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            initial_capital: 初始资金
            stock_codes: 股票池（可选，用于限制选股范围）

        Returns:
            {
                'success': True/False,
                'data': {...},  # 回测结果
                'error': '...'  # 错误信息（如果失败）
            }
        """
        # 1. 检查缓存
        cache_key = self._generate_cache_key(
            selector_id,
            selector_params,
            entry_id,
            entry_params,
            exit_id,
            exit_params,
            rebalance_freq,
            start_date,
            end_date,
            initial_capital,
            stock_codes,
        )

        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info(f"回测结果命中缓存: {cache_key[:16]}...")
            return cached_result

        # 2. 创建策略组件
        try:
            selector = self.SELECTOR_REGISTRY[selector_id](params=selector_params)
            entry = self.ENTRY_REGISTRY[entry_id](params=entry_params)
            exit_strategy = self.EXIT_REGISTRY[exit_id](params=exit_params)
        except KeyError as e:
            return {"success": False, "error": f"未知的策略ID: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"策略创建失败: {str(e)}"}

        # 3. 获取价格数据
        try:
            prices = await self._fetch_price_data(
                stock_codes=stock_codes, start_date=start_date, end_date=end_date
            )

            if prices.empty:
                return {"success": False, "error": "未找到符合条件的价格数据"}

            logger.info(f"加载价格数据: {prices.shape[0]} 天, {prices.shape[1]} 只股票")

        except Exception as e:
            logger.error(f"数据获取失败: {e}")
            return {"success": False, "error": f"数据获取失败: {str(e)}"}

        # 4. 执行回测（调用 Core）
        try:
            engine = BacktestEngine(initial_capital=initial_capital)

            # 在线程池中执行回测（避免阻塞）
            result = await asyncio.to_thread(
                engine.backtest_three_layer,
                selector=selector,
                entry=entry,
                exit_strategy=exit_strategy,
                prices=prices,
                start_date=start_date,
                end_date=end_date,
                rebalance_freq=rebalance_freq,
                initial_capital=initial_capital,
            )

            # 转换 Core 的 Response 对象为字典
            result_dict = self._convert_response_to_dict(result)

            # 5. 缓存结果
            if result_dict.get("success"):
                await cache.set(cache_key, result_dict, ttl=3600)  # 1小时
                logger.info(f"回测结果已缓存: {cache_key[:16]}...")

            return result_dict

        except Exception as e:
            logger.error(f"回测执行失败: {e}", exc_info=True)
            return {"success": False, "error": f"回测执行失败: {str(e)}"}

    async def _fetch_price_data(
        self, stock_codes: Optional[List[str]], start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        从数据库获取价格数据

        Args:
            stock_codes: 股票代码列表（可选）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            DataFrame(index=日期, columns=股票代码, values=收盘价)

        Raises:
            DataQueryError: 数据获取失败
        """
        try:
            # 如果未指定股票池，获取全市场股票
            if not stock_codes:
                stock_list = await self.data_adapter.get_stock_list()
                stock_codes = [s["code"] for s in stock_list]

            # 转换日期格式
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

            # 并发获取所有股票数据
            tasks = []
            for code in stock_codes:
                task = self.data_adapter.get_daily_data(
                    code=code, start_date=start_dt, end_date=end_dt
                )
                tasks.append((code, task))

            # 等待所有任务完成
            all_data = {}
            for code, task in tasks:
                try:
                    df = await task
                    if not df.empty and "close" in df.columns:
                        # 确保日期索引
                        if "trade_date" in df.columns:
                            df = df.set_index("trade_date")
                        all_data[code] = df["close"]
                except Exception as e:
                    logger.warning(f"获取股票 {code} 数据失败: {e}")
                    continue

            if not all_data:
                raise DataQueryError("未获取到任何有效的价格数据")

            # 合并为宽表格式
            prices = pd.DataFrame(all_data)
            prices.index = pd.to_datetime(prices.index)
            prices = prices.sort_index()

            # 过滤日期范围
            prices = prices.loc[start_date:end_date]

            return prices

        except Exception as e:
            logger.error(f"获取价格数据失败: {e}")
            raise DataQueryError(f"价格数据获取失败: {str(e)}")

    def _generate_cache_key(self, *args) -> str:
        """
        生成缓存键

        Args:
            *args: 所有参数

        Returns:
            缓存键字符串
        """
        # 序列化参数并生成哈希
        key_data = json.dumps(args, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"three_layer:backtest:{key_hash}"

    def _convert_response_to_dict(self, response) -> Dict[str, Any]:
        """
        将 Core 的 Response 对象转换为字典

        Args:
            response: Core 的 Response 对象

        Returns:
            字典格式的结果
        """
        try:
            # Response 对象有 success 和 data 属性
            result = {"success": response.success}

            if response.success:
                # 转换数据
                data = {}
                if hasattr(response, "data") and response.data:
                    for key, value in response.data.items():
                        if isinstance(value, pd.DataFrame):
                            # DataFrame 转换为可序列化格式
                            data[key] = value.to_dict(orient="records")
                        elif isinstance(value, pd.Series):
                            # Series 转换为字典
                            data[key] = value.to_dict()
                        else:
                            data[key] = value

                result["data"] = data

                # 添加元信息
                if hasattr(response, "message"):
                    result["message"] = response.message
                if hasattr(response, "metadata"):
                    result["metadata"] = response.metadata
            else:
                # 失败情况
                result["error"] = getattr(response, "error", "未知错误")

            return result

        except Exception as e:
            logger.error(f"转换Response对象失败: {e}")
            return {"success": False, "error": f"结果转换失败: {str(e)}"}
