"""
策略管理器
负责策略注册、实例化和管理
"""

from typing import Dict, List, Type, Any, Optional
from loguru import logger

from .base_strategy import BaseStrategy
from .complex_indicator_strategy import ComplexIndicatorStrategy
from .ml_model_strategy import MLModelStrategy


class StrategyManager:
    """策略管理器单例"""

    _instance = None
    _strategies: Dict[str, Type[BaseStrategy]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化并注册所有策略"""
        self.register_strategy('complex_indicator', ComplexIndicatorStrategy)
        self.register_strategy('ml_model', MLModelStrategy)
        logger.info(f"策略管理器初始化完成，已注册 {len(self._strategies)} 个策略")

    def register_strategy(self, strategy_id: str, strategy_class: Type[BaseStrategy]):
        """
        注册策略

        参数:
            strategy_id: 策略唯一标识
            strategy_class: 策略类
        """
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"{strategy_class} 必须继承自 BaseStrategy")

        self._strategies[strategy_id] = strategy_class
        logger.debug(f"注册策略: {strategy_id} -> {strategy_class.__name__}")

    def get_strategy(
        self,
        strategy_id: str,
        params: Optional[Dict[str, Any]] = None
    ) -> BaseStrategy:
        """
        获取策略实例

        参数:
            strategy_id: 策略ID
            params: 策略参数

        返回:
            策略实例
        """
        if strategy_id not in self._strategies:
            raise ValueError(f"未知策略: {strategy_id}")

        strategy_class = self._strategies[strategy_id]

        # 如果没有提供参数，使用默认参数
        if params is None:
            params = self._get_default_params(strategy_class)

        return strategy_class(params)

    def _get_default_params(self, strategy_class: Type[BaseStrategy]) -> Dict[str, Any]:
        """获取策略默认参数"""
        params = {}
        for param in strategy_class.get_parameters():
            params[param.name] = param.default
        return params

    def list_strategies(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册策略

        返回:
            策略信息列表
        """
        strategies = []

        for strategy_id, strategy_class in self._strategies.items():
            # 创建临时实例获取元数据
            temp_instance = strategy_class(self._get_default_params(strategy_class))
            metadata = temp_instance.get_metadata()

            strategies.append({
                'id': strategy_id,
                'name': metadata['name'],
                'description': metadata['description'],
                'version': metadata['version'],
                'parameter_count': len(metadata['parameters'])
            })

        return strategies

    def get_strategy_metadata(self, strategy_id: str) -> Dict[str, Any]:
        """
        获取策略完整元数据

        参数:
            strategy_id: 策略ID

        返回:
            策略元数据（包含参数定义）
        """
        if strategy_id not in self._strategies:
            raise ValueError(f"未知策略: {strategy_id}")

        strategy_class = self._strategies[strategy_id]
        temp_instance = strategy_class(self._get_default_params(strategy_class))

        return {
            'id': strategy_id,
            **temp_instance.get_metadata()
        }

    def validate_strategy_params(
        self,
        strategy_id: str,
        params: Dict[str, Any]
    ) -> bool:
        """
        验证策略参数

        参数:
            strategy_id: 策略ID
            params: 待验证的参数

        返回:
            是否有效
        """
        try:
            self.get_strategy(strategy_id, params)
            return True
        except Exception as e:
            logger.error(f"参数验证失败: {e}")
            return False


# 全局单例
strategy_manager = StrategyManager()
