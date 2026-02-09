"""
配置驱动策略适配器 (Config Strategy Adapter)

将 Core v6.0 的配置驱动策略包装为异步方法，供 FastAPI 使用。

配置驱动策略特点:
- 从数据库加载参数配置
- 基于预定义策略类型 (momentum, mean_reversion, multi_factor)
- 支持参数调优和 A/B 测试

作者: Backend Team
创建日期: 2026-02-09
版本: 1.0.0
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

# 添加 core 项目到 Python 路径
core_path = Path(__file__).parent.parent.parent.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

# 导入 Core 模块
from src.strategies import StrategyFactory
from src.strategies.base_strategy import BaseStrategy

from app.core.exceptions import AdapterError
from app.repositories.strategy_config_repository import StrategyConfigRepository


class ConfigStrategyAdapter:
    """
    配置驱动策略适配器

    包装 Core 的 StrategyFactory，支持从数据库配置创建策略。

    示例:
        >>> adapter = ConfigStrategyAdapter()
        >>> strategy = await adapter.create_strategy_from_config(config_id=1)
        >>> types = await adapter.get_available_strategy_types()
    """

    def __init__(self):
        """初始化配置驱动策略适配器"""
        self.factory = StrategyFactory()
        self.repo = StrategyConfigRepository()

    async def create_strategy_from_config(self, config_id: int) -> BaseStrategy:
        """
        从配置创建策略（异步）

        Args:
            config_id: 配置ID

        Returns:
            策略实例

        Raises:
            AdapterError: 配置不存在或已禁用
        """

        def _create():
            # 从数据库加载配置
            config_data = self.repo.get_by_id(config_id)

            if not config_data:
                raise AdapterError(
                    f"配置不存在",
                    error_code="CONFIG_NOT_FOUND",
                    config_id=config_id
                )

            if not config_data['is_enabled']:
                raise AdapterError(
                    f"配置已禁用",
                    error_code="CONFIG_DISABLED",
                    config_id=config_id
                )

            # 提取策略类型和配置参数
            strategy_type = config_data['strategy_type']
            config = config_data['config']

            # 调用 Core 的 StrategyFactory 创建策略
            strategy = self.factory.create(strategy_type, config)

            logger.info(
                f"成功创建配置驱动策略: "
                f"config_id={config_id}, "
                f"type={strategy_type}, "
                f"name={config_data.get('name', 'N/A')}"
            )

            return strategy

        return await asyncio.to_thread(_create)

    async def get_available_strategy_types(self) -> List[Dict[str, Any]]:
        """
        获取可用的预定义策略类型（异步）

        Returns:
            策略类型列表，包含类型、名称、描述和默认参数
        """

        def _get_types():
            return [
                {
                    'type': 'momentum',
                    'name': '动量策略',
                    'description': '选择近期涨幅最大的股票',
                    'default_params': {
                        'lookback_period': 20,
                        'threshold': 0.10,
                        'top_n': 20
                    },
                    'param_schema': {
                        'lookback_period': {
                            'type': 'integer',
                            'min': 5,
                            'max': 60,
                            'description': '回看周期（交易日）'
                        },
                        'threshold': {
                            'type': 'float',
                            'min': 0.0,
                            'max': 1.0,
                            'description': '涨幅阈值'
                        },
                        'top_n': {
                            'type': 'integer',
                            'min': 1,
                            'max': 100,
                            'description': '选股数量'
                        }
                    }
                },
                {
                    'type': 'mean_reversion',
                    'name': '均值回归策略',
                    'description': '选择偏离均值的股票',
                    'default_params': {
                        'lookback_period': 20,
                        'std_threshold': 2.0,
                        'top_n': 20
                    },
                    'param_schema': {
                        'lookback_period': {
                            'type': 'integer',
                            'min': 5,
                            'max': 60,
                            'description': '回看周期（交易日）'
                        },
                        'std_threshold': {
                            'type': 'float',
                            'min': 0.5,
                            'max': 5.0,
                            'description': '标准差阈值'
                        },
                        'top_n': {
                            'type': 'integer',
                            'min': 1,
                            'max': 100,
                            'description': '选股数量'
                        }
                    }
                },
                {
                    'type': 'multi_factor',
                    'name': '多因子策略',
                    'description': '综合多个因子进行选股',
                    'default_params': {
                        'factors': ['momentum', 'value', 'quality'],
                        'weights': [0.4, 0.3, 0.3],
                        'top_n': 30
                    },
                    'param_schema': {
                        'factors': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': '因子列表'
                        },
                        'weights': {
                            'type': 'array',
                            'items': {'type': 'float'},
                            'description': '因子权重（总和应为1.0）'
                        },
                        'top_n': {
                            'type': 'integer',
                            'min': 1,
                            'max': 100,
                            'description': '选股数量'
                        }
                    }
                }
            ]

        return await asyncio.to_thread(_get_types)

    async def validate_config(
        self,
        strategy_type: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证策略配置（异步）

        Args:
            strategy_type: 策略类型
            config: 配置参数

        Returns:
            验证结果字典，包含:
                - is_valid: 是否有效
                - errors: 错误列表
                - warnings: 警告列表
        """

        def _validate():
            errors = []
            warnings = []

            # 检查策略类型是否支持
            supported_types = ['momentum', 'mean_reversion', 'multi_factor']
            if strategy_type not in supported_types:
                errors.append({
                    'field': 'strategy_type',
                    'message': f'不支持的策略类型: {strategy_type}',
                    'supported_types': supported_types
                })
                return {
                    'is_valid': False,
                    'errors': errors,
                    'warnings': warnings
                }

            # 获取策略类型的参数 schema
            types_list = [
                {
                    'type': 'momentum',
                    'required_params': ['lookback_period', 'top_n'],
                    'optional_params': ['threshold']
                },
                {
                    'type': 'mean_reversion',
                    'required_params': ['lookback_period', 'std_threshold', 'top_n'],
                    'optional_params': []
                },
                {
                    'type': 'multi_factor',
                    'required_params': ['factors', 'weights', 'top_n'],
                    'optional_params': []
                }
            ]

            strategy_schema = next(
                (s for s in types_list if s['type'] == strategy_type),
                None
            )

            if not strategy_schema:
                errors.append({
                    'field': 'strategy_type',
                    'message': f'未找到策略类型的配置: {strategy_type}'
                })
                return {
                    'is_valid': False,
                    'errors': errors,
                    'warnings': warnings
                }

            # 检查必需参数
            for param in strategy_schema['required_params']:
                if param not in config:
                    errors.append({
                        'field': param,
                        'message': f'缺少必需参数: {param}'
                    })

            # 参数类型和范围检查
            if 'lookback_period' in config:
                lookback = config['lookback_period']
                if not isinstance(lookback, int):
                    errors.append({
                        'field': 'lookback_period',
                        'message': 'lookback_period 必须是整数'
                    })
                elif lookback < 5 or lookback > 60:
                    warnings.append({
                        'field': 'lookback_period',
                        'message': f'lookback_period={lookback} 超出建议范围 [5, 60]'
                    })

            if 'top_n' in config:
                top_n = config['top_n']
                if not isinstance(top_n, int):
                    errors.append({
                        'field': 'top_n',
                        'message': 'top_n 必须是整数'
                    })
                elif top_n < 1:
                    errors.append({
                        'field': 'top_n',
                        'message': 'top_n 必须大于0'
                    })
                elif top_n > 100:
                    warnings.append({
                        'field': 'top_n',
                        'message': f'top_n={top_n} 较大，可能影响性能'
                    })

            # multi_factor 特殊验证
            if strategy_type == 'multi_factor':
                if 'factors' in config and 'weights' in config:
                    factors = config['factors']
                    weights = config['weights']
                    if len(factors) != len(weights):
                        errors.append({
                            'field': 'weights',
                            'message': 'factors 和 weights 长度必须相同'
                        })
                    elif abs(sum(weights) - 1.0) > 0.01:
                        warnings.append({
                            'field': 'weights',
                            'message': f'权重总和为 {sum(weights):.2f}，建议为 1.0'
                        })

            return {
                'is_valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }

        return await asyncio.to_thread(_validate)

    async def list_configs(
        self,
        strategy_type: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取配置列表（异步）

        Args:
            strategy_type: 策略类型过滤
            is_enabled: 是否启用过滤
            page: 页码
            page_size: 每页数量

        Returns:
            包含 items 和 meta 的字典
        """

        def _list():
            return self.repo.list(
                strategy_type=strategy_type,
                is_enabled=is_enabled,
                page=page,
                page_size=page_size
            )

        return await asyncio.to_thread(_list)

    async def get_config_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取配置（异步）

        Args:
            config_id: 配置ID

        Returns:
            配置字典，不存在则返回 None
        """

        def _get():
            return self.repo.get_by_id(config_id)

        return await asyncio.to_thread(_get)
