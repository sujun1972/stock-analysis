"""
策略动态加载器 - 统一入口

完全数据库驱动的策略加载系统，支持入场策略、离场策略、选股策略的动态加载。
策略代码存储在数据库中，运行时通过 exec() 动态执行。

功能:
- 从数据库记录动态加载策略实例
- 代码哈希验证（SHA-256）
- 安全的命名空间隔离
- 支持自定义配置参数覆盖
- 选股策略执行：构建全市场价格 DataFrame，调用 calculate_scores()，返回 top-N 股票代码
"""
import sys
import asyncio
import hashlib
from datetime import datetime, timedelta
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
        import src.features
        import src.features.technical_indicators
        import src.features.alpha_factors
        core_module.strategies = src.strategies
        core_module.ml = src.ml
        core_module.features = src.features

        sys.modules['core'] = core_module
        sys.modules['core.strategies'] = src.strategies
        sys.modules['core.ml'] = src.ml
        sys.modules['core.features'] = src.features
        # 选股策略常用子模块别名
        sys.modules['core.strategies.technical_indicators'] = src.features.technical_indicators
        sys.modules['core.strategies.alpha_factors'] = src.features.alpha_factors
        sys.modules['core.features.technical_indicators'] = src.features.technical_indicators
        sys.modules['core.features.alpha_factors'] = src.features.alpha_factors

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

    @staticmethod
    async def run_stock_selection(
        strategy_record: Dict[str, Any],
        lookback_days: int = 60,
        top_n: Optional[int] = None,
    ) -> List[str]:
        """
        执行选股策略，返回按评分降序排列的 ts_code 列表。

        流程：
        1. 加载策略实例
        2. 从 stock_daily 获取近 lookback_days 天收盘价，构建 prices DataFrame
        3. 系统层数据清洗（过滤非交易日、补齐停牌 NaN、剔除覆盖率不足的股票）
        4. 调用 strategy.calculate_scores(prices, features, {})
        5. 过滤评分 <= 0 的股票，按评分降序返回

        Args:
            strategy_record: 来自 StrategyRepository.get_by_id() 的策略字典
            lookback_days: 价格回看天数（多取 10 天作为缓冲，保证实际可用交易日足够）
            top_n: 最多返回股票数量；None 时从 default_params.top_n 读取；
                   仍为 None 则返回所有评分 > 0 的股票（不限数量）

        Returns:
            ts_code 列表，如 ["000001.SZ", "600000.SH", ...]
            策略执行失败时返回空列表并记录警告日志。

        Raises:
            ValueError: 策略类型不是 stock_selection
        """
        import pandas as pd
        import numpy as np
        from app.repositories.stock_daily_repository import StockDailyRepository

        if strategy_record.get("strategy_type") != "stock_selection":
            raise ValueError(
                f"策略 {strategy_record.get('id')} 不是选股策略，"
                f"实际类型: {strategy_record.get('strategy_type')}"
            )

        strategy = StrategyDynamicLoader.load_strategy(strategy_record)

        # 计算日期范围（多取 10 天缓冲以覆盖非交易日）
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=lookback_days + 10)).strftime("%Y%m%d")

        daily_repo = StockDailyRepository()

        def _fetch_prices() -> list:
            """从 stock_daily 同步拉取全市场收盘价（在线程池中执行）"""
            conn = daily_repo.db.get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT code, date, close
                    FROM stock_daily
                    WHERE date >= %s AND date <= %s
                      AND close IS NOT NULL AND close > 0
                    ORDER BY date ASC
                    """,
                    (start_date, end_date),
                )
                rows = cur.fetchall()
                cur.close()
                return rows
            finally:
                daily_repo.db.release_connection(conn)

        rows = await asyncio.to_thread(_fetch_prices)
        if not rows:
            logger.warning(f"选股策略 {strategy_record.get('id')} 无可用价格数据，返回空列表")
            return []

        def _code_to_ts_code(code: str) -> str:
            """将纯数字代码（如 600000）转为 ts_code 格式（如 600000.SH）"""
            if "." in code:
                return code.upper()
            if code.startswith("6"):
                return f"{code}.SH"
            if code.startswith("4") or code.startswith("8"):
                return f"{code}.BJ"
            return f"{code}.SZ"

        # 构建 prices DataFrame: index=日期, columns=ts_code
        df = pd.DataFrame(rows, columns=["code", "date", "close"])
        df["date"] = pd.to_datetime(df["date"].astype(str))
        # psycopg2 返回 Decimal，需转 float 才能正确做 groupby/mean
        df["close"] = df["close"].astype(float)
        df["ts_code"] = df["code"].apply(_code_to_ts_code)
        # stock_daily 同一日期同一股票可能存在重复行，取均值去重
        df = df.groupby(["date", "ts_code"], as_index=False)["close"].mean()
        prices = df.pivot(index="date", columns="ts_code", values="close")
        prices = prices.sort_index().tail(lookback_days)

        # 系统层数据清洗——策略代码无需重复处理以下问题：
        # - 周末/节假日在 stock_daily 中可能存有少量测试数据，pivot 后产生几乎全 NaN 的行，
        #   导致分位数计算退化（threshold=0，所有股票都通过）
        # - 新股或长期停牌的股票覆盖率不足，不具备因子计算意义
        # - 短暂停牌产生的 NaN 用前向填充补齐，保持价格序列连续
        prices = prices[prices.notna().sum(axis=1) >= max(10, len(prices.columns) * 0.1)]
        prices = prices.loc[:, prices.notna().mean() >= 0.5]
        prices = prices.ffill().dropna(axis=1)

        # 调用策略打分（空 features，选股策略自行从 prices 计算因子）
        features = pd.DataFrame(index=prices.columns)
        try:
            scores = await asyncio.to_thread(
                strategy.calculate_scores, prices, features, {}
            )
        except Exception as e:
            logger.warning(f"选股策略 {strategy_record.get('id')} calculate_scores 失败: {e}")
            return []

        if scores is None or scores.empty:
            return []

        # 兼容策略返回 list-wrapped 值的情况（部分策略返回 [[score]] 而非 score）
        scores = pd.to_numeric(
            scores.apply(lambda x: x[0] if isinstance(x, (list, tuple)) and len(x) > 0 else x),
            errors="coerce",
        )

        # top_n 优先级：调用参数 > default_params.top_n > 不限制
        if top_n is None:
            dp = strategy_record.get("default_params") or {}
            top_n = dp.get("top_n") if isinstance(dp, dict) else None

        # 只保留评分 > 0 的股票（评分 = 0 表示所有因子均未满足，无选择意义）
        valid_scores = scores[scores > 0].dropna()
        result = (valid_scores.nlargest(top_n) if top_n else valid_scores.sort_values(ascending=False)).index.tolist()

        logger.info(
            f"选股策略执行完成: id={strategy_record.get('id')}, "
            f"候选={len(valid_scores)}, 选出={len(result)}"
        )
        return result
