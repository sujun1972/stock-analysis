"""
机器学习模型策略
使用训练好的ML模型预测值生成交易信号
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger
from pathlib import Path
import sys

# 添加 core 模块路径
core_path = Path(__file__).parent.parent.parent.parent / 'core' / 'src'
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

from src.config.trading_rules import TradingCosts
from .base_strategy import BaseStrategy, StrategyParameter, ParameterType


class MLModelStrategy(BaseStrategy):
    """
    机器学习模型策略
    根据ML模型的预测值生成买卖信号
    """

    @property
    def name(self) -> str:
        return "机器学习模型策略"

    @property
    def description(self) -> str:
        return "使用训练好的机器学习模型预测未来收益率，根据预测值生成交易信号"

    @property
    def version(self) -> str:
        return "1.0.0"

    @classmethod
    def get_parameters(cls) -> List[StrategyParameter]:
        return [
            StrategyParameter(
                name="model_id",
                label="模型ID",
                type=ParameterType.SELECT,
                default="",
                description="使用的机器学习模型ID（必选，如无可用模型请先在AI实验室训练）。模型类型和预测周期由训练时确定。",
                category="model"
            ),
            # 注意: model_type 和 target_period 已从参数列表中移除
            # 这些属性在模型训练时已确定，应从模型元数据中获取，而不是作为可配置参数
            StrategyParameter(
                name="buy_threshold",
                label="买入阈值(%)",
                type=ParameterType.FLOAT,
                default=0.15,  # 降低至 0.15% 以匹配模型实际预测范围
                min_value=0.0,
                max_value=10.0,
                step=0.05,
                description="预测收益率超过此值时买入",
                category="signal"
            ),
            StrategyParameter(
                name="sell_threshold",
                label="卖出阈值(%)",
                type=ParameterType.FLOAT,
                default=-0.3,  # 降低至 -0.3% 以匹配模型实际预测范围
                min_value=-10.0,
                max_value=0.0,
                step=0.1,
                description="预测收益率低于此值时卖出",
                category="signal"
            ),
            StrategyParameter(
                name="commission",
                label="交易佣金率",
                type=ParameterType.FLOAT,
                default=TradingCosts.CommissionRates.STANDARD_RATE,  # 使用配置类的标准费率
                min_value=TradingCosts.CommissionRates.LOW_RATE,  # 最低万1.8
                max_value=TradingCosts.CommissionRates.HIGH_RATE,  # 最高万3
                step=0.00001,
                description="交易佣金费率（标准万2.5，低佣万1.8，高佣万3）",
                category="cost"
            ),
            StrategyParameter(
                name="slippage",
                label="滑点率",
                type=ParameterType.FLOAT,
                default=0.001,
                min_value=0.0,
                max_value=0.05,
                step=0.0001,
                description="价格滑点费率",
                category="cost"
            ),
            StrategyParameter(
                name="position_size",
                label="仓位比例",
                type=ParameterType.FLOAT,
                default=1.0,
                min_value=0.1,
                max_value=1.0,
                step=0.1,
                description="每次开仓使用的资金比例",
                category="risk"
            ),
            StrategyParameter(
                name="stop_loss",
                label="止损比例",
                type=ParameterType.FLOAT,
                default=0.05,
                min_value=0.01,
                max_value=0.20,
                step=0.01,
                description="止损比例(5%表示下跌5%时止损)",
                category="risk"
            ),
            StrategyParameter(
                name="take_profit",
                label="止盈比例",
                type=ParameterType.FLOAT,
                default=0.10,
                min_value=0.01,
                max_value=0.50,
                step=0.01,
                description="止盈比例(10%表示上涨10%时止盈)",
                category="risk"
            ),
        ]

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)

        # 从参数中提取模型ID（必需）
        self.model_id = self.params.get('model_id', '')

        # model_type 和 target_period 不再从参数中获取
        # 而是在需要时从模型的训练任务元数据中动态读取
        # 这样可以确保使用的是模型实际的属性，而不是用户可能错误配置的值
        self.model_type = None  # 延迟加载
        self.target_period = None  # 延迟加载

        # 交易参数
        self.buy_threshold = self.params.get('buy_threshold', 1.0)
        self.sell_threshold = self.params.get('sell_threshold', -1.0)

        # 成本参数（使用配置类的默认值）
        self.commission = self.params.get('commission', TradingCosts.CommissionRates.DEFAULT)
        self.slippage = self.params.get('slippage', 0.001)

        # 风控参数
        self.position_size = self.params.get('position_size', 1.0)
        self.stop_loss = self.params.get('stop_loss', 0.05)
        self.take_profit = self.params.get('take_profit', 0.10)

        # 模型缓存
        self.model = None
        self.model_dir = Path('data/models/saved')

        logger.info(
            f"初始化ML模型策略: model_id={self.model_id}, "
            f"buy_threshold={self.buy_threshold}%, sell_threshold={self.sell_threshold}%"
        )

    def get_metadata(self) -> Dict[str, Any]:
        """
        获取策略元数据，动态加载可用的ML模型列表

        重写基类方法以动态填充 model_id 参数的选项列表
        """
        # 调用基类方法获取基础元数据
        metadata = super().get_metadata()

        # 获取可用的模型列表
        available_models = self._get_available_models()

        # 为 model_id 参数添加 options
        for param in metadata['parameters']:
            if param['name'] == 'model_id':
                param['options'] = available_models
                break

        return metadata

    def _get_available_models(self) -> List[Dict[str, str]]:
        """
        获取可用的机器学习模型列表

        从数据库读取所有已完成的实验并转换为选项格式

        返回:
            模型选项列表，格式: [{"label": "股票代码 - 模型类型 (训练日期)", "value": "model_id"}, ...]
        """
        try:
            # 从数据库读取已完成的实验（core 模块已作为包安装）
            from src.database.db_manager import DatabaseManager

            db = DatabaseManager()

            # 查询所有已完成且有model_id的实验（按时间倒序，限制100个）
            query = """
                SELECT model_id,
                       config->>'symbol' as symbol,
                       config->>'model_type' as model_type,
                       config->>'target_period' as target_period,
                       train_completed_at
                FROM experiments
                WHERE status = 'completed'
                  AND model_id IS NOT NULL
                ORDER BY train_completed_at DESC
                LIMIT 100
            """

            results = db._execute_query(query)

            if not results:
                logger.warning("数据库中没有找到可用的ML模型")
                return []

            # 转换为选项格式
            options = []
            for row in results:
                model_id, symbol, model_type, target_period, completed_at = row

                # 格式化
                symbol = symbol or 'unknown'
                model_type = (model_type or 'unknown').upper()
                target_period = target_period or 5
                date_str = str(completed_at)[:10] if completed_at else 'unknown'

                # 构建标签: "000001 - LIGHTGBM - 5日 (2024-01-24)"
                label = f"{symbol} - {model_type} - {target_period}日 ({date_str})"

                options.append({
                    "label": label,
                    "value": model_id  # 使用 model_id 而不是 task_id
                })

            logger.info(f"从数据库找到 {len(options)} 个可用的ML模型")
            return options

        except Exception as e:
            logger.error(f"获取可用模型列表失败: {e}")
            # 发生错误时也返回空列表
            return []

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        根据ML模型预测生成交易信号

        参数:
            data: 价格数据DataFrame (必须包含 open, high, low, close, volume)

        返回:
            交易信号序列 (1=买入, -1=卖出, 0=持有)
        """
        logger.info(f"使用ML模型生成交易信号: model_id={self.model_id}")

        # 初始化信号序列
        signals = pd.Series(0, index=data.index)

        try:
            # 验证 model_id 必须提供
            if not self.model_id:
                error_msg = "ML模型策略必须指定 model_id 参数。请在策略配置中选择一个训练好的模型，或先在AI实验室训练新模型。"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # 尝试加载模型
            model = self._load_model_from_disk()
            if model is None:
                error_msg = f"无法加载模型 {self.model_id}。模型文件可能已被删除或损坏，请重新训练或选择其他模型。"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            # 生成预测
            predictions = self._generate_predictions(model, data)

            if predictions is None or len(predictions) == 0:
                error_msg = f"模型 {self.model_id} 预测失败。请检查模型是否正常或尝试重新训练。"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # 根据预测值生成信号
            # 预测上涨 > buy_threshold: 买入信号
            # 预测下跌 < sell_threshold: 卖出信号
            buy_signals = predictions > self.buy_threshold
            sell_signals = predictions < self.sell_threshold

            signals[buy_signals] = 1
            signals[sell_signals] = -1

            # 添加止损止盈逻辑
            signals = self._apply_risk_management(signals, data)

            logger.info(
                f"信号生成完成: 买入={buy_signals.sum()}, "
                f"卖出={sell_signals.sum()}, 持有={len(signals) - buy_signals.sum() - sell_signals.sum()}"
            )

            return signals

        except (ValueError, FileNotFoundError, RuntimeError) as e:
            # 重新抛出我们自定义的错误，让上层处理
            logger.error(f"ML模型策略执行失败: {e}")
            raise
        except Exception as e:
            # 其他未预期的错误也抛出，不使用回退策略
            logger.error(f"生成ML信号时发生未预期错误: {e}")
            raise RuntimeError(f"ML模型策略执行失败: {str(e)}")

    def _load_model_from_disk(self):
        """
        从磁盘加载模型

        需要从数据库查询模型路径，因为 model_id 和实际文件名可能不一致
        - LightGBM: .txt 文件
        - GRU: .pth 文件
        """
        try:
            # 从model_id中解析模型类型（model_id格式：symbol_modeltype_xxx）
            # 例如：600519_lightgbm_20260126_095641 -> lightgbm
            parts = self.model_id.split('_')
            if len(parts) < 2:
                logger.error(f"无效的model_id格式: {self.model_id}")
                return None

            actual_model_type = parts[1].lower()  # 'lightgbm' 或 'gru'

            # 从数据库查询模型的实际文件路径
            from src.database.db_manager import DatabaseManager
            db = DatabaseManager()

            query = """
                SELECT model_path, config
                FROM experiments
                WHERE model_id = %s AND status = 'completed'
                LIMIT 1
            """
            result = db._execute_query(query, (self.model_id,))

            if not result or not result[0][0]:
                logger.warning(f"未在数据库中找到模型 {self.model_id} 的路径信息")
                # 尝试使用旧的直接路径方式作为回退
                models_dir = Path('/data/models/ml_models')
                if actual_model_type == 'lightgbm':
                    model_path = models_dir / f"{self.model_id}.txt"
                elif actual_model_type == 'gru':
                    model_path = models_dir / f"{self.model_id}.pth"
                else:
                    logger.error(f"不支持的模型类型: {actual_model_type}")
                    return None
            else:
                # 使用数据库中存储的路径
                model_path = Path(result[0][0])
                config = result[0][1] if len(result[0]) > 1 else {}

                # 从配置中提取目标周期
                if config and isinstance(config, dict):
                    actual_target_period = config.get('target_period', 5)
                else:
                    actual_target_period = 5

                self.target_period = actual_target_period

            # 设置实例属性
            self.model_type = actual_model_type
            self.model_path = model_path  # 保存model_path供scaler使用

            # 检查文件是否存在
            if not model_path.exists():
                logger.warning(f"模型文件不存在: {model_path}")
                return None

            # 根据实际模型类型加载
            if actual_model_type == 'lightgbm':
                import lightgbm as lgb
                model = lgb.Booster(model_file=str(model_path))
                logger.info(f"成功加载 LightGBM 模型: {model_path} (预测周期: {self.target_period}日)")
            elif actual_model_type == 'gru':
                import torch
                model = torch.load(str(model_path))
                logger.info(f"成功加载 GRU 模型: {model_path} (预测周期: {self.target_period}日)")

            return model

        except Exception as e:
            logger.error(f"加载模型失败: {e}", exc_info=True)
            return None

    def _generate_predictions(self, model, data: pd.DataFrame) -> Optional[pd.Series]:
        """
        使用模型生成预测

        参数:
            model: 加载的模型对象 (LightGBM Booster 或 PyTorch GRU模型)
            data: 价格数据DataFrame (包含 open, high, low, close, volume)

        返回:
            预测的收益率序列 (%)
        """
        try:
            # core 模块已作为包安装，无需 sys.path 操作
            from src.data_pipeline import DataPipeline
            import pickle

            logger.info(f"开始生成真实预测: model_type={self.model_type}, 数据长度={len(data)}")

            # 步骤1: 使用DataPipeline准备特征（与训练时保持一致）
            pipeline = DataPipeline(
                target_periods=self.target_period,
                scaler_type='standard',
                cache_features=False,  # 禁用缓存，确保使用最新特征工程逻辑
                verbose=False
            )

            # 提取股票代码（从model_id解析: 000001_lightgbm_xxx -> 000001）
            symbol = self.model_id.split('_')[0]

            # 准备特征数据（不需要目标变量）
            # 为了获取特征,我们需要提供日期范围
            start_date = data.index.min().strftime('%Y%m%d')
            end_date = data.index.max().strftime('%Y%m%d')

            logger.info(f"准备特征: symbol={symbol}, 日期={start_date}~{end_date}")

            # 获取特征（会自动计算技术指标和Alpha因子）
            X, _ = pipeline.get_training_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                use_cache=False
            )

            logger.info(f"特征准备完成: shape={X.shape}, features={len(X.columns)}")

            # 步骤2: 加载保存的scaler进行特征缩放
            # 使用 model_path 派生 scaler 路径，而不是 model_id
            if hasattr(self, 'model_path') and self.model_path:
                # 从实际模型文件路径派生scaler路径
                scaler_path = self.model_path.with_name(self.model_path.stem + '_scaler.pkl')
            else:
                # 回退到使用 model_id（向后兼容）
                scaler_path = Path(f'/data/models/ml_models/{self.model_id}_scaler.pkl')

            if scaler_path.exists():
                with open(scaler_path, 'rb') as f:
                    scaler = pickle.load(f)

                if scaler is not None:
                    # 缩放特征
                    X_scaled = scaler.transform(X)
                    X_scaled = pd.DataFrame(X_scaled, columns=X.columns, index=X.index)
                    logger.info("✅ 已应用训练时的scaler")
                else:
                    logger.warning("⚠️ Scaler文件损坏,使用未缩放的特征")
                    X_scaled = X
            else:
                logger.warning(f"⚠️ 未找到scaler文件: {scaler_path}, 使用未缩放的特征")
                X_scaled = X

            # 步骤3: 根据模型类型进行预测
            if self.model_type == 'lightgbm':
                # LightGBM预测
                predictions_raw = model.predict(X_scaled)
                predictions = pd.Series(predictions_raw, index=X_scaled.index)
                logger.info(f"✅ LightGBM预测完成: {len(predictions)} 个预测值")

            elif self.model_type == 'gru':
                # GRU预测需要序列数据
                import torch

                # 获取序列长度（从训练配置中获取,默认20）
                seq_length = 20  # TODO: 应该从模型元数据中读取

                # 准备序列数据
                X_sequences = []
                valid_indices = []

                for i in range(seq_length, len(X_scaled)):
                    seq = X_scaled.iloc[i-seq_length:i].values
                    X_sequences.append(seq)
                    valid_indices.append(X_scaled.index[i])

                if len(X_sequences) == 0:
                    logger.error("数据长度不足以生成序列")
                    return None

                X_sequences = np.array(X_sequences)
                X_tensor = torch.FloatTensor(X_sequences)

                # GRU模型预测
                model.eval()
                with torch.no_grad():
                    predictions_raw = model(X_tensor).cpu().numpy().flatten()

                predictions = pd.Series(predictions_raw, index=valid_indices)
                logger.info(f"✅ GRU预测完成: {len(predictions)} 个预测值 (损失前{seq_length}个样本)")
            else:
                logger.error(f"不支持的模型类型: {self.model_type}")
                return None

            # 步骤4: 对齐预测结果与原始数据索引
            # 确保预测值的索引与输入数据对齐
            predictions_aligned = predictions.reindex(data.index)

            # 统计信息
            logger.info(f"预测统计: mean={predictions.mean():.4f}%, std={predictions.std():.4f}%, "
                       f"min={predictions.min():.4f}%, max={predictions.max():.4f}%")

            return predictions_aligned

        except Exception as e:
            logger.error(f"模型预测失败: {e}", exc_info=True)
            return None

    def _generate_fallback_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        回退策略：使用简单的移动平均交叉策略
        当ML模型不可用时使用
        """
        logger.info("使用回退策略：MA5/MA20交叉")
        signals = pd.Series(0, index=data.index)

        # 计算移动平均线
        ma5 = data['close'].rolling(window=5).mean()
        ma20 = data['close'].rolling(window=20).mean()

        # 金叉：MA5上穿MA20 -> 买入
        golden_cross = (ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))
        signals[golden_cross] = 1

        # 死叉：MA5下穿MA20 -> 卖出
        death_cross = (ma5 < ma20) & (ma5.shift(1) >= ma20.shift(1))
        signals[death_cross] = -1

        return signals

    def _apply_risk_management(
        self,
        signals: pd.Series,
        data: pd.DataFrame
    ) -> pd.Series:
        """
        应用止损止盈逻辑

        参数:
            signals: 原始信号
            data: 价格数据

        返回:
            调整后的信号
        """
        adjusted_signals = signals.copy()

        # 跟踪持仓状态
        position = 0
        entry_price = 0.0

        for i, date in enumerate(data.index):
            current_price = data.loc[date, 'close']

            # 如果有持仓，检查止损止盈
            if position > 0:
                # 计算盈亏比例
                pnl_ratio = (current_price - entry_price) / entry_price

                # 触发止损
                if pnl_ratio <= -self.stop_loss:
                    adjusted_signals.iloc[i] = -1
                    position = 0
                    logger.debug(f"触发止损: date={date}, pnl={pnl_ratio:.2%}")

                # 触发止盈
                elif pnl_ratio >= self.take_profit:
                    adjusted_signals.iloc[i] = -1
                    position = 0
                    logger.debug(f"触发止盈: date={date}, pnl={pnl_ratio:.2%}")

            # 更新持仓状态
            if adjusted_signals.iloc[i] == 1:
                position = 1
                entry_price = current_price
            elif adjusted_signals.iloc[i] == -1:
                position = 0

        return adjusted_signals
