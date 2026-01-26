"""
池化训练Pipeline
集成多股票数据加载、Ridge基准对比、完整训练流程
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from src.data_pipeline.pooled_data_loader import PooledDataLoader
from src.models.model_trainer import ModelTrainer
from src.models.comparison_evaluator import ComparisonEvaluator
from src.data_pipeline.data_splitter import DataSplitter
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PooledTrainingPipeline:
    """
    池化训练Pipeline

    功能：
    1. 加载多股票数据并池化
    2. 在合并训练集上fit Scaler
    3. 训练LightGBM主模型
    4. 训练Ridge基准模型
    5. 对比评估两个模型
    6. 生成完整报告
    """

    def __init__(
        self,
        scaler_type: str = 'robust',
        verbose: bool = True
    ):
        """
        初始化池化训练Pipeline

        参数:
            scaler_type: 缩放器类型 ('standard', 'robust', 'minmax')
            verbose: 是否输出详细日志
        """
        self.scaler_type = scaler_type
        self.verbose = verbose

        self.pooled_loader = PooledDataLoader(verbose=verbose)
        self.scaler = None
        self.comparison_evaluator = ComparisonEvaluator()

        # 训练结果
        self.pooled_df = None
        self.successful_symbols = []
        self.feature_cols = []
        self.target_col = None

    def load_and_prepare_data(
        self,
        symbol_list: List[str],
        start_date: str,
        end_date: str,
        target_period: int = 10,
        train_ratio: float = 0.7,
        valid_ratio: float = 0.15
    ) -> Tuple:
        """
        加载并准备池化数据

        参数:
            symbol_list: 股票代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            target_period: 目标预测周期
            train_ratio: 训练集比例
            valid_ratio: 验证集比例

        返回:
            (X_train, y_train, X_valid, y_valid, X_test, y_test)
        """
        logger.info("=" * 80)
        logger.info("【池化训练Pipeline】开始")
        logger.info("=" * 80)

        # 1. 加载池化数据
        self.pooled_df, total_samples, self.successful_symbols = self.pooled_loader.load_pooled_data(
            symbol_list=symbol_list,
            start_date=start_date,
            end_date=end_date,
            target_period=target_period
        )

        # 2. 准备训练数据
        self.target_col = f'target_{target_period}d_return'

        X_train, y_train, X_valid, y_valid, X_test, y_test, self.feature_cols = \
            self.pooled_loader.prepare_pooled_training_data(
                pooled_df=self.pooled_df,
                target_col=self.target_col,
                train_ratio=train_ratio,
                valid_ratio=valid_ratio
            )

        # 3. 在合并训练集上fit Scaler
        logger.info(f"\n在合并训练集上fit Scaler (类型: {self.scaler_type})...")

        # 创建scaler
        from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler

        if self.scaler_type == 'standard':
            self.scaler = StandardScaler()
        elif self.scaler_type == 'robust':
            self.scaler = RobustScaler()
        elif self.scaler_type == 'minmax':
            self.scaler = MinMaxScaler()
        else:
            raise ValueError(f"不支持的scaler类型: {self.scaler_type}")

        # Fit scaler on training data
        X_train_scaled = pd.DataFrame(
            self.scaler.fit_transform(X_train),
            columns=X_train.columns,
            index=X_train.index
        )
        X_valid_scaled = pd.DataFrame(
            self.scaler.transform(X_valid),
            columns=X_valid.columns,
            index=X_valid.index
        )
        X_test_scaled = pd.DataFrame(
            self.scaler.transform(X_test),
            columns=X_test.columns,
            index=X_test.index
        )

        logger.info("✓ Scaler已在合并训练集上完成fit")

        return X_train_scaled, y_train, X_valid_scaled, y_valid, X_test_scaled, y_test

    def train_with_baseline(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: pd.DataFrame,
        y_valid: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        lightgbm_params: Optional[Dict] = None,
        ridge_params: Optional[Dict] = None,
        enable_ridge_baseline: bool = True
    ) -> Dict:
        """
        训练主模型和基准模型并对比

        参数:
            X_train, y_train: 训练集
            X_valid, y_valid: 验证集
            X_test, y_test: 测试集
            lightgbm_params: LightGBM参数
            ridge_params: Ridge参数
            enable_ridge_baseline: 是否启用Ridge基准

        返回:
            包含所有结果的字典
        """
        logger.info("\n" + "=" * 80)
        logger.info("开始训练模型")
        logger.info("=" * 80)

        # 默认参数（审计建议的强正则化配置）
        default_lgb_params = {
            'max_depth': 3,
            'num_leaves': 7,
            'n_estimators': 200,
            'learning_rate': 0.03,
            'min_child_samples': 100,
            'reg_alpha': 2.0,
            'reg_lambda': 2.0,
            'subsample': 0.7,
            'colsample_bytree': 0.7,
            'verbose': -1
        }

        default_ridge_params = {
            'alpha': 1.0
        }

        # 合并参数
        lgb_params = {**default_lgb_params, **(lightgbm_params or {})}
        ridge_params = {**default_ridge_params, **(ridge_params or {})}

        # 1. 训练LightGBM
        logger.info("\n[LightGBM] 训练中...")
        trainer_lgb = ModelTrainer(model_type='lightgbm', model_params=lgb_params)
        trainer_lgb.train(X_train, y_train, X_valid, y_valid)

        self.comparison_evaluator.add_model('LightGBM', trainer_lgb)

        # 2. 训练Ridge（如果启用）
        if enable_ridge_baseline:
            logger.info("\n[Ridge] 训练基准模型...")
            trainer_ridge = ModelTrainer(model_type='ridge', model_params=ridge_params)
            trainer_ridge.train(X_train, y_train, X_valid, y_valid)

            self.comparison_evaluator.add_model('Ridge', trainer_ridge)

        # 3. 对比评估
        logger.info("\n" + "=" * 80)
        logger.info("评估所有模型")
        logger.info("=" * 80)

        results_df = self.comparison_evaluator.evaluate_all(
            X_train, y_train,
            X_valid, y_valid,
            X_test, y_test
        )

        # 4. 打印对比报告
        self.comparison_evaluator.print_comparison()

        # 5. 返回结果
        result_dict = self.comparison_evaluator.get_comparison_dict()
        result_dict['total_samples'] = len(self.pooled_df)
        result_dict['successful_symbols'] = self.successful_symbols
        result_dict['num_symbols'] = len(self.successful_symbols)
        result_dict['feature_count'] = len(self.feature_cols)
        result_dict['has_baseline'] = enable_ridge_baseline

        # 提取LightGBM和Ridge的具体指标（用于Backend API）
        comparison_list = result_dict.get('comparison', [])

        lgb_metrics = {}
        ridge_metrics = {}

        for model_result in comparison_list:
            if model_result['model'] == 'LightGBM':
                lgb_metrics = {
                    'train_ic': model_result['train_ic'],
                    'train_rank_ic': model_result['train_rank_ic'],
                    'train_mae': model_result['train_mae'],
                    'valid_ic': model_result['valid_ic'],
                    'valid_rank_ic': model_result['valid_rank_ic'],
                    'valid_mae': model_result['valid_mae'],
                    'test_ic': model_result['test_ic'],
                    'test_rank_ic': model_result['test_rank_ic'],
                    'test_mae': model_result['test_mae'],
                    'test_r2': model_result['test_r2'],
                    'overfit_ic': model_result['overfit_ic']
                }
            elif model_result['model'] == 'Ridge':
                ridge_metrics = {
                    'train_ic': model_result['train_ic'],
                    'train_rank_ic': model_result['train_rank_ic'],
                    'train_mae': model_result['train_mae'],
                    'valid_ic': model_result['valid_ic'],
                    'valid_rank_ic': model_result['valid_rank_ic'],
                    'valid_mae': model_result['valid_mae'],
                    'test_ic': model_result['test_ic'],
                    'test_rank_ic': model_result['test_rank_ic'],
                    'test_mae': model_result['test_mae'],
                    'test_r2': model_result['test_r2'],
                    'overfit_ic': model_result['overfit_ic']
                }

        result_dict['lgb_metrics'] = lgb_metrics
        result_dict['ridge_metrics'] = ridge_metrics

        # 对比结果
        if 'ridge_vs_lgb' in result_dict:
            result_dict['comparison_result'] = result_dict['ridge_vs_lgb']

        return result_dict

    def run_full_pipeline(
        self,
        symbol_list: List[str],
        start_date: str,
        end_date: str,
        target_period: int = 10,
        lightgbm_params: Optional[Dict] = None,
        ridge_params: Optional[Dict] = None,
        enable_ridge_baseline: bool = True,
        train_ratio: float = 0.7,
        valid_ratio: float = 0.15
    ) -> Dict:
        """
        运行完整的池化训练Pipeline

        参数:
            symbol_list: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            target_period: 目标预测周期
            lightgbm_params: LightGBM参数
            ridge_params: Ridge参数
            enable_ridge_baseline: 是否启用Ridge基准
            train_ratio: 训练集比例
            valid_ratio: 验证集比例

        返回:
            包含所有结果的字典
        """
        # 1. 加载和准备数据
        X_train, y_train, X_valid, y_valid, X_test, y_test = self.load_and_prepare_data(
            symbol_list=symbol_list,
            start_date=start_date,
            end_date=end_date,
            target_period=target_period,
            train_ratio=train_ratio,
            valid_ratio=valid_ratio
        )

        # 2. 训练和对比
        results = self.train_with_baseline(
            X_train, y_train,
            X_valid, y_valid,
            X_test, y_test,
            lightgbm_params=lightgbm_params,
            ridge_params=ridge_params,
            enable_ridge_baseline=enable_ridge_baseline
        )

        logger.info("\n" + "=" * 80)
        logger.info("【池化训练Pipeline】完成")
        logger.info("=" * 80)

        return results
