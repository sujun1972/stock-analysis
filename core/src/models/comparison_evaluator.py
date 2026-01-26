"""
模型对比评估器
用于对比多个模型的性能，特别是Ridge基准 vs LightGBM
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from .model_trainer import ModelTrainer


class ComparisonEvaluator:
    """模型对比评估器"""

    def __init__(self):
        """初始化对比评估器"""
        self.models = {}
        self.results = {}

    def add_model(
        self,
        name: str,
        trainer: ModelTrainer
    ):
        """
        添加模型到对比列表

        参数:
            name: 模型名称（如 'Ridge', 'LightGBM'）
            trainer: 训练好的ModelTrainer实例
        """
        self.models[name] = trainer

    def evaluate_all(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: pd.DataFrame,
        y_valid: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> pd.DataFrame:
        """
        评估所有模型并生成对比报告

        参数:
            X_train, y_train: 训练集
            X_valid, y_valid: 验证集
            X_test, y_test: 测试集

        返回:
            对比结果DataFrame
        """
        results = []

        for name, trainer in self.models.items():
            print(f"\n评估 [{name}] 模型...")

            # 评估训练集
            train_metrics = trainer.evaluate(X_train, y_train, dataset_name='train', verbose=False)

            # 评估验证集
            valid_metrics = trainer.evaluate(X_valid, y_valid, dataset_name='valid', verbose=False)

            # 评估测试集
            test_metrics = trainer.evaluate(X_test, y_test, dataset_name='test', verbose=False)

            # 计算过拟合程度
            overfit_ic = abs(train_metrics['ic'] - test_metrics['ic'])
            overfit_rank_ic = abs(train_metrics['rank_ic'] - test_metrics['rank_ic'])

            result = {
                'model': name,
                'train_ic': train_metrics['ic'],
                'train_rank_ic': train_metrics['rank_ic'],
                'train_mae': train_metrics['mae'],
                'train_rmse': train_metrics.get('rmse', 0),
                'valid_ic': valid_metrics['ic'],
                'valid_rank_ic': valid_metrics['rank_ic'],
                'valid_mae': valid_metrics['mae'],
                'valid_rmse': valid_metrics.get('rmse', 0),
                'test_ic': test_metrics['ic'],
                'test_rank_ic': test_metrics['rank_ic'],
                'test_mae': test_metrics['mae'],
                'test_rmse': test_metrics.get('rmse', 0),
                'test_r2': test_metrics['r2'],
                'overfit_ic': overfit_ic,
                'overfit_rank_ic': overfit_rank_ic
            }

            results.append(result)

            print(f"  Train IC: {train_metrics['ic']:.6f}, Valid IC: {valid_metrics['ic']:.6f}, Test IC: {test_metrics['ic']:.6f}")
            print(f"  Overfit (IC): {overfit_ic:.6f}")

        # 转换为DataFrame
        results_df = pd.DataFrame(results)

        self.results = results_df

        return results_df

    def print_comparison(self):
        """打印格式化的对比表格"""
        if len(self.results) == 0:
            print("⚠️  尚未进行评估，请先调用evaluate_all方法")
            return

        print("\n" + "=" * 100)
        print("【模型对比报告】")
        print("=" * 100)

        # IC对比
        print("\n【IC (Information Coefficient)】")
        print(f"{'模型':<15} {'Train IC':<12} {'Valid IC':<12} {'Test IC':<12} {'过拟合':<12}")
        print("-" * 70)
        for _, row in self.results.iterrows():
            print(f"{row['model']:<15} {row['train_ic']:>10.6f}  {row['valid_ic']:>10.6f}  {row['test_ic']:>10.6f}  {row['overfit_ic']:>10.6f}")

        # Rank IC对比
        print("\n【Rank IC (Spearman Correlation)】")
        print(f"{'模型':<15} {'Train RIC':<12} {'Valid RIC':<12} {'Test RIC':<12} {'过拟合':<12}")
        print("-" * 70)
        for _, row in self.results.iterrows():
            print(f"{row['model']:<15} {row['train_rank_ic']:>10.6f}  {row['valid_rank_ic']:>10.6f}  {row['test_rank_ic']:>10.6f}  {row['overfit_rank_ic']:>10.6f}")

        # MAE对比
        print("\n【MAE (Mean Absolute Error)】")
        print(f"{'模型':<15} {'Train MAE':<12} {'Valid MAE':<12} {'Test MAE':<12}")
        print("-" * 70)
        for _, row in self.results.iterrows():
            print(f"{row['model']:<15} {row['train_mae']:>10.6f}  {row['valid_mae']:>10.6f}  {row['test_mae']:>10.6f}")

        # 判定
        print("\n" + "=" * 100)
        print("【判定】")
        print("=" * 100)

        # 找出最佳模型
        best_test_ic = self.results.loc[self.results['test_ic'].idxmax()]
        best_overfit = self.results.loc[self.results['overfit_ic'].idxmin()]

        print(f"\n✓ Test IC 最优: {best_test_ic['model']} (IC={best_test_ic['test_ic']:.6f})")
        print(f"✓ 过拟合最小: {best_overfit['model']} (Overfit={best_overfit['overfit_ic']:.6f})")

        # 判定Ridge是否可以替代LightGBM
        if 'Ridge' in self.results['model'].values and 'LightGBM' in self.results['model'].values:
            ridge_row = self.results[self.results['model'] == 'Ridge'].iloc[0]
            lgb_row = self.results[self.results['model'] == 'LightGBM'].iloc[0]

            print(f"\n【Ridge vs LightGBM】")
            print(f"  Ridge Test IC:     {ridge_row['test_ic']:.6f}")
            print(f"  LightGBM Test IC:  {lgb_row['test_ic']:.6f}")
            print(f"  Ridge 过拟合:      {ridge_row['overfit_ic']:.6f}")
            print(f"  LightGBM 过拟合:   {lgb_row['overfit_ic']:.6f}")

            if ridge_row['test_ic'] > lgb_row['test_ic'] * 0.8 and ridge_row['overfit_ic'] < lgb_row['overfit_ic']:
                print(f"\n✓✓✓ 建议: 使用 Ridge 模型")
                print(f"  - Ridge Test IC 接近LightGBM (≥80%)")
                print(f"  - Ridge 过拟合更小")
            elif ridge_row['test_ic'] > lgb_row['test_ic']:
                print(f"\n✓✓ 建议: 使用 Ridge 模型")
                print(f"  - Ridge Test IC 优于 LightGBM")
            elif lgb_row['test_ic'] > 0 and lgb_row['overfit_ic'] < 0.3:
                print(f"\n✓ 建议: 使用 LightGBM")
                print(f"  - LightGBM Test IC 更优且过拟合可控")
            else:
                print(f"\n⚠️  警告: LightGBM 过拟合严重")
                print(f"  - 建议优先使用 Ridge 或增强正则化")

    def get_comparison_dict(self) -> Dict:
        """
        获取对比结果字典（用于API返回）

        返回:
            包含所有模型对比结果的字典
        """
        if len(self.results) == 0:
            return {}

        result_dict = {
            'models': self.results['model'].tolist(),
            'comparison': self.results.to_dict(orient='records'),
            'best_test_ic_model': self.results.loc[self.results['test_ic'].idxmax(), 'model'],
            'best_overfit_model': self.results.loc[self.results['overfit_ic'].idxmin(), 'model']
        }

        # 添加Ridge vs LightGBM的判定
        if 'Ridge' in self.results['model'].values and 'LightGBM' in self.results['model'].values:
            ridge_row = self.results[self.results['model'] == 'Ridge'].iloc[0]
            lgb_row = self.results[self.results['model'] == 'LightGBM'].iloc[0]

            recommendation = ''
            if ridge_row['test_ic'] > lgb_row['test_ic'] * 0.8 and ridge_row['overfit_ic'] < lgb_row['overfit_ic']:
                recommendation = 'ridge'
            elif ridge_row['test_ic'] > lgb_row['test_ic']:
                recommendation = 'ridge'
            elif lgb_row['test_ic'] > 0 and lgb_row['overfit_ic'] < 0.3:
                recommendation = 'lightgbm'
            else:
                recommendation = 'ridge'  # 默认推荐Ridge

            result_dict['recommendation'] = recommendation
            result_dict['ridge_vs_lgb'] = {
                'ridge_test_ic': float(ridge_row['test_ic']),
                'lgb_test_ic': float(lgb_row['test_ic']),
                'ridge_overfit': float(ridge_row['overfit_ic']),
                'lgb_overfit': float(lgb_row['overfit_ic'])
            }

        return result_dict
