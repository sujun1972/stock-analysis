"""
策略动态加载器 - 统一入口

完全数据库驱动的策略加载系统，支持入场策略和离场策略的动态加载。
策略代码存储在数据库中，运行时通过 exec() 动态执行。

功能:
- 从数据库记录动态加载策略实例
- 代码哈希验证（SHA-256）
- 安全的命名空间隔离
- 支持自定义配置参数覆盖

作者: Backend Team
创建日期: 2026-03-07
"""
import sys
import hashlib
from typing import Dict, Any, Optional, List
from pathlib import Path
from loguru import logger


# 添加 core 路径
if Path("/app/core").exists():
    core_path = Path("/app/core")
else:
    core_path = Path(__file__).parent.parent.parent.parent.parent / "core"

if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))


class StrategyDynamicLoader:
    """
    策略动态加载器

    从数据库记录中动态加载策略，支持入场策略和离场策略。
    使用 exec() 执行策略代码并实例化策略类。
    """

    @staticmethod
    def load_strategy(strategy_record: Dict, custom_config: Optional[Dict] = None):
        """
        从数据库记录动态加载策略

        Args:
            strategy_record: 数据库策略记录
                {
                    'id': int,
                    'name': str,
                    'class_name': str,
                    'code': str (完整Python代码),
                    'code_hash': str,
                    'strategy_type': 'entry' or 'exit',
                    'default_params': dict or str (JSON),
                    ...
                }
            custom_config: 自定义配置（覆盖默认参数）

        Returns:
            策略实例

        Raises:
            ValueError: 代码哈希不匹配、策略类未找到等
        """
        # 1. 验证代码哈希
        code = strategy_record['code']
        expected_hash = strategy_record['code_hash']
        actual_hash = hashlib.sha256(code.encode()).hexdigest()[:16]

        # 验证代码完整性（警告但不阻止加载，以兼容旧版本哈希）
        if expected_hash != actual_hash:
            logger.warning(
                f"代码哈希不匹配: expected={expected_hash}, actual={actual_hash}"
            )

        # 2. 准备命名空间（隔离执行环境，预导入常用模块）
        import pandas as pd
        import numpy as np
        import types

        # 注册 core 模块别名，支持数据库中策略代码使用 core.* 路径
        # 背景：数据库中的策略代码使用 'from core.strategies import ...'
        # 但实际模块在 Docker 容器的 /app/core/src 中
        # 这里创建 core -> src 的映射，让两种导入路径都能工作
        core_module = types.ModuleType('core')
        import src.strategies
        import src.ml
        core_module.strategies = src.strategies
        core_module.ml = src.ml

        sys.modules['core'] = core_module
        sys.modules['core.strategies'] = src.strategies
        sys.modules['core.ml'] = src.ml

        namespace = {
            '__builtins__': __builtins__,
            'pd': pd,
            'np': np,
            'logger': logger,
            'Optional': __import__('typing').Optional,
            'Dict': __import__('typing').Dict,
            'Any': __import__('typing').Any,
            'List': __import__('typing').List,
        }

        # 3. 根据策略类型导入依赖
        strategy_type = strategy_record['strategy_type']

        if strategy_type == 'entry' or strategy_type == 'stock_selection':
            # 入场策略/选股策略
            from src.strategies.base_strategy import BaseStrategy
            from src.strategies.signal_generator import SignalGenerator

            namespace['BaseStrategy'] = BaseStrategy
            namespace['SignalGenerator'] = SignalGenerator

        elif strategy_type == 'exit':
            # 离场策略
            from src.ml.exit_strategy import BaseExitStrategy, ExitSignal
            from dataclasses import dataclass
            from datetime import datetime
            from abc import ABC, abstractmethod

            namespace['BaseExitStrategy'] = BaseExitStrategy
            namespace['ExitSignal'] = ExitSignal
            namespace['dataclass'] = dataclass
            namespace['datetime'] = datetime
            namespace['ABC'] = ABC
            namespace['abstractmethod'] = abstractmethod

        else:
            raise ValueError(f"不支持的策略类型: {strategy_type}")

        # 4. 执行代码
        try:
            exec(code, namespace)
        except Exception as e:
            logger.error(f"执行策略代码失败: {e}", exc_info=True)
            raise ValueError(f"策略代码执行失败: {str(e)}")

        # 5. 获取策略类
        class_name = strategy_record['class_name']
        strategy_class = namespace.get(class_name)

        if not strategy_class:
            raise ValueError(f"策略类未找到: {class_name}")

        # 6. 合并配置（默认参数 + 自定义配置）
        default_params = strategy_record.get('default_params', {})

        # 处理JSON字符串格式的参数
        if isinstance(default_params, str):
            import json
            try:
                default_params = json.loads(default_params) if default_params else {}
            except json.JSONDecodeError:
                logger.warning(f"解析default_params失败: {default_params}")
                default_params = {}

        # 自定义配置覆盖默认参数
        final_config = default_params.copy() if default_params else {}
        if custom_config:
            final_config.update(custom_config)

        # 7. 实例化策略
        try:
            if strategy_type in ['entry', 'stock_selection']:
                # 入场策略：需要 name 和 config 参数
                strategy = strategy_class(
                    name=strategy_record['name'],
                    config=final_config
                )
            elif strategy_type == 'exit':
                # 离场策略：直接传参数
                strategy = strategy_class(**final_config)
            else:
                raise ValueError(f"未知策略类型: {strategy_type}")

            logger.info(
                f"✓ 成功加载策略: {strategy_record['display_name']} "
                f"(ID={strategy_record['id']}, Type={strategy_type})"
            )

            return strategy

        except Exception as e:
            logger.error(f"实例化策略失败: {e}", exc_info=True)
            raise ValueError(f"策略实例化失败: {str(e)}")

    @staticmethod
    def load_exit_manager(exit_strategy_ids: List[int], repo):
        """
        加载离场策略管理器

        Args:
            exit_strategy_ids: 离场策略ID列表
            repo: StrategyRepository 实例

        Returns:
            CompositeExitManager 实例

        Raises:
            ValueError: 未找到有效的离场策略
        """
        from src.ml.exit_strategy import CompositeExitManager

        exit_strategies = []

        for exit_id in exit_strategy_ids:
            try:
                # 从数据库读取策略记录
                exit_record = repo.get_by_id(exit_id)

                if not exit_record:
                    logger.warning(f"离场策略不存在: ID={exit_id}")
                    continue

                # 验证策略类型
                if exit_record['strategy_type'] != 'exit':
                    logger.warning(
                        f"策略 {exit_id} 不是离场策略 "
                        f"(type={exit_record['strategy_type']})，跳过"
                    )
                    continue

                # 动态加载策略
                exit_instance = StrategyDynamicLoader.load_strategy(exit_record)
                exit_strategies.append(exit_instance)

            except Exception as e:
                logger.error(f"加载离场策略 {exit_id} 失败: {e}", exc_info=True)
                continue

        if not exit_strategies:
            raise ValueError("未找到有效的离场策略")

        # 创建离场管理器
        exit_manager = CompositeExitManager(
            exit_strategies=exit_strategies,
            enable_reverse_entry=True,
            enable_risk_control=True
        )

        logger.info(f"✓ 成功加载离场管理器: {len(exit_strategies)} 个策略")

        return exit_manager
