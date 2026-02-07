"""
完整训练流程示例

演示端到端的模型训练流程：
1. 数据加载与预处理
2. 特征工程
3. 模型训练与验证
4. 模型评估
5. 模型保存与部署

适用场景：
- 生产环境模型训练
- 完整的训练工作流
- 最佳实践参考
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

import pandas as pd
import numpy as np
from loguru import logger
from typing import Tuple, Dict
import json
from datetime import datetime

from models import (
    LightGBMStockModel,
    RidgeStockModel,
    ModelTrainer,
    WeightedAverageEnsemble
)


class ModelPipeline:
    """模型训练流水线"""

    def __init__(self, config: Dict):
        """
        初始化流水线

        参数:
            config: 配置字典
        """
        self.config = config
        self.models = {}
        self.results = {}
        self.best_model = None

        # 创建输出目录
        self.output_dir = Path(config.get('output_dir', 'outputs'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("初始化模型训练流水线")
        logger.info(f"输出目录: {self.output_dir}")

    def load_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """
        步骤1: 加载数据

        返回:
            X: 特征DataFrame
            y: 目标Series
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤1: 加载数据")
        logger.info("=" * 60)

        # 这里使用模拟数据，实际使用时替换为真实数据加载
        n_samples = self.config.get('n_samples', 2000)
        n_features = self.config.get('n_features', 50)

        logger.info(f"生成示例数据: {n_samples} 样本, {n_features} 特征")

        np.random.seed(42)
        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f'feature_{i}' for i in range(n_features)]
        )

        y = pd.Series(
            0.1 * X['feature_0'] + 0.05 * X['feature_1'] +
            0.03 * X['feature_2'] + np.random.randn(n_samples) * 0.01,
            name='returns'
        )

        logger.info(f"✓ 数据加载完成: X.shape={X.shape}, y.shape={y.shape}")

        return X, y

    def preprocess_data(
        self,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        步骤2: 数据预处理

        参数:
            X: 原始特征
            y: 原始目标

        返回:
            X_clean: 清洗后的特征
            y_clean: 清洗后的目标
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤2: 数据预处理")
        logger.info("=" * 60)

        # 1. 处理缺失值
        missing_count = X.isna().sum().sum()
        logger.info(f"缺失值数量: {missing_count}")

        if missing_count > 0:
            X_clean = X.fillna(X.mean())
            logger.info("✓ 使用均值填充缺失值")
        else:
            X_clean = X.copy()

        # 2. 处理异常值（使用 3-sigma 规则）
        outlier_threshold = 3
        outliers = (np.abs((X_clean - X_clean.mean()) / X_clean.std()) > outlier_threshold).sum()
        logger.info(f"异常值数量: {outliers.sum()}")

        # Winsorize 异常值
        for col in X_clean.columns:
            lower = X_clean[col].quantile(0.01)
            upper = X_clean[col].quantile(0.99)
            X_clean[col] = X_clean[col].clip(lower, upper)

        logger.info("✓ 异常值处理完成（Winsorize 1%-99%）")

        # 3. 移除 y 的缺失值
        valid_mask = y.notna()
        X_clean = X_clean[valid_mask]
        y_clean = y[valid_mask]

        logger.info(f"✓ 数据预处理完成: {len(X_clean)} 有效样本")

        return X_clean, y_clean

    def split_data(
        self,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Dict[str, Tuple]:
        """
        步骤3: 数据分割

        参数:
            X: 特征
            y: 目标

        返回:
            data_splits: 数据分割字典
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤3: 数据分割")
        logger.info("=" * 60)

        train_ratio = self.config.get('train_ratio', 0.6)
        valid_ratio = self.config.get('valid_ratio', 0.2)
        # test_ratio = 0.2 (剩余)

        n = len(X)
        train_size = int(n * train_ratio)
        valid_size = int(n * (train_ratio + valid_ratio))

        X_train, y_train = X[:train_size], y[:train_size]
        X_valid, y_valid = X[train_size:valid_size], y[train_size:valid_size]
        X_test, y_test = X[valid_size:], y[valid_size:]

        logger.info(f"训练集: {len(X_train)} 样本 ({train_ratio*100:.0f}%)")
        logger.info(f"验证集: {len(X_valid)} 样本 ({valid_ratio*100:.0f}%)")
        logger.info(f"测试集: {len(X_test)} 样本 ({(1-train_ratio-valid_ratio)*100:.0f}%)")

        return {
            'train': (X_train, y_train),
            'valid': (X_valid, y_valid),
            'test': (X_test, y_test)
        }

    def train_models(self, data_splits: Dict) -> Dict:
        """
        步骤4: 训练模型

        参数:
            data_splits: 数据分割

        返回:
            models: 训练好的模型字典
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤4: 训练模型")
        logger.info("=" * 60)

        X_train, y_train = data_splits['train']
        X_valid, y_valid = data_splits['valid']

        models = {}

        # 1. Ridge 模型
        logger.info("\n训练 Ridge 模型...")
        ridge_config = self.config.get('ridge', {})
        ridge = RidgeStockModel(
            alpha=ridge_config.get('alpha', 1.0)
        )

        ridge.train(X_train, y_train)
        models['Ridge'] = ridge
        logger.info("✓ Ridge 训练完成")

        # 2. LightGBM 模型
        logger.info("\n训练 LightGBM 模型...")
        lgb_config = self.config.get('lightgbm', {})
        lgb = LightGBMStockModel(
            n_estimators=lgb_config.get('n_estimators', 100),
            learning_rate=lgb_config.get('learning_rate', 0.05),
            max_depth=lgb_config.get('max_depth', 5),
            num_leaves=lgb_config.get('num_leaves', 31),
            random_state=42
        )

        lgb.train(
            X_train, y_train,
            X_valid, y_valid,
            early_stopping_rounds=20,
            verbose=False
        )
        models['LightGBM'] = lgb
        logger.info("✓ LightGBM 训练完成")

        # 3. LightGBM 模型（深层）
        logger.info("\n训练 LightGBM-Deep 模型...")
        lgb_deep = LightGBMStockModel(
            n_estimators=lgb_config.get('n_estimators', 150),
            learning_rate=0.03,
            max_depth=7,
            num_leaves=63,
            random_state=43
        )

        lgb_deep.train(
            X_train, y_train,
            X_valid, y_valid,
            early_stopping_rounds=20,
            verbose=False
        )
        models['LightGBM-Deep'] = lgb_deep
        logger.info("✓ LightGBM-Deep 训练完成")

        logger.info(f"\n✓ 完成训练 {len(models)} 个模型")

        return models

    def evaluate_models(self, models: Dict, data_splits: Dict) -> Dict:
        """
        步骤5: 评估模型

        参数:
            models: 模型字典
            data_splits: 数据分割

        返回:
            results: 评估结果
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤5: 评估模型")
        logger.info("=" * 60)

        X_train, y_train = data_splits['train']
        X_valid, y_valid = data_splits['valid']
        X_test, y_test = data_splits['test']

        results = {}

        for name, model in models.items():
            logger.info(f"\n评估 {name}...")

            # 预测
            y_pred_train = model.predict(X_train)
            y_pred_valid = model.predict(X_valid)
            y_pred_test = model.predict(X_test)

            # 计算指标
            train_ic = np.corrcoef(y_train, y_pred_train)[0, 1]
            valid_ic = np.corrcoef(y_valid, y_pred_valid)[0, 1]
            test_ic = np.corrcoef(y_test, y_pred_test)[0, 1]

            # Rank IC
            train_rank_ic = pd.Series(y_train.values).corr(
                pd.Series(y_pred_train), method='spearman'
            )
            test_rank_ic = pd.Series(y_test.values).corr(
                pd.Series(y_pred_test), method='spearman'
            )

            results[name] = {
                'train_ic': train_ic,
                'valid_ic': valid_ic,
                'test_ic': test_ic,
                'train_rank_ic': train_rank_ic,
                'test_rank_ic': test_rank_ic
            }

            logger.info(f"  训练集 IC: {train_ic:.6f}")
            logger.info(f"  验证集 IC: {valid_ic:.6f}")
            logger.info(f"  测试集 IC: {test_ic:.6f}")
            logger.info(f"  测试集 Rank IC: {test_rank_ic:.6f}")

        # 保存结果
        self.results = results
        self._save_results(results)

        return results

    def create_ensemble(self, models: Dict, data_splits: Dict) -> WeightedAverageEnsemble:
        """
        步骤6: 创建集成模型

        参数:
            models: 基础模型
            data_splits: 数据分割

        返回:
            ensemble: 集成模型
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤6: 创建集成模型")
        logger.info("=" * 60)

        X_valid, y_valid = data_splits['valid']
        X_test, y_test = data_splits['test']

        # 创建加权平均集成
        ensemble = WeightedAverageEnsemble(
            models=list(models.values()),
            model_names=list(models.keys())
        )

        # 在验证集上优化权重
        logger.info("在验证集上优化权重...")
        optimized_weights = ensemble.optimize_weights(
            X_valid, y_valid,
            metric='ic'
        )

        logger.info(f"优化后权重: {dict(zip(models.keys(), optimized_weights))}")

        # 评估集成模型
        y_pred_test = ensemble.predict(X_test)
        ensemble_ic = np.corrcoef(y_pred_test, y_test)[0, 1]

        logger.info(f"✓ 集成模型测试集 IC: {ensemble_ic:.6f}")

        # 与最佳单模型对比
        best_single_ic = max(r['test_ic'] for r in self.results.values())
        improvement = (ensemble_ic / best_single_ic - 1) * 100

        logger.info(f"相比最佳单模型提升: {improvement:+.2f}%")

        return ensemble

    def select_best_model(self, models: Dict, results: Dict):
        """
        步骤7: 选择最佳模型

        参数:
            models: 模型字典
            results: 评估结果
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤7: 选择最佳模型")
        logger.info("=" * 60)

        # 根据验证集 IC 选择
        best_name = max(results, key=lambda x: results[x]['valid_ic'])
        best_model = models[best_name]

        self.best_model = best_model

        logger.info(f"最佳模型: {best_name}")
        logger.info(f"  验证集 IC: {results[best_name]['valid_ic']:.6f}")
        logger.info(f"  测试集 IC: {results[best_name]['test_ic']:.6f}")

        return best_model

    def save_models(self, models: Dict, ensemble=None):
        """
        步骤8: 保存模型

        参数:
            models: 模型字典
            ensemble: 集成模型（可选）
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤8: 保存模型")
        logger.info("=" * 60)

        models_dir = self.output_dir / 'models'
        models_dir.mkdir(exist_ok=True)

        # 保存所有模型
        for name, model in models.items():
            model_path = models_dir / f'{name.lower().replace(" ", "_")}.pkl'
            model.save(str(model_path))
            logger.info(f"✓ 保存 {name}: {model_path}")

        # 保存集成模型
        if ensemble is not None:
            ensemble_path = models_dir / 'ensemble.pkl'
            ensemble.save(str(ensemble_path))
            logger.info(f"✓ 保存集成模型: {ensemble_path}")

        # 保存元数据
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'config': self.config,
            'results': {
                name: {k: float(v) for k, v in res.items()}
                for name, res in self.results.items()
            },
            'best_model': max(self.results, key=lambda x: self.results[x]['valid_ic'])
        }

        metadata_path = self.output_dir / 'metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"✓ 保存元数据: {metadata_path}")

    def _save_results(self, results: Dict):
        """保存评估结果"""
        results_df = pd.DataFrame(results).T
        results_path = self.output_dir / 'evaluation_results.csv'
        results_df.to_csv(results_path)
        logger.info(f"✓ 保存评估结果: {results_path}")

    def run(self):
        """运行完整流水线"""
        logger.info("=" * 60)
        logger.info("开始运行模型训练流水线")
        logger.info("=" * 60)

        # 1. 加载数据
        X, y = self.load_data()

        # 2. 数据预处理
        X_clean, y_clean = self.preprocess_data(X, y)

        # 3. 数据分割
        data_splits = self.split_data(X_clean, y_clean)

        # 4. 训练模型
        models = self.train_models(data_splits)
        self.models = models

        # 5. 评估模型
        results = self.evaluate_models(models, data_splits)

        # 6. 创建集成
        ensemble = self.create_ensemble(models, data_splits)

        # 7. 选择最佳模型
        best_model = self.select_best_model(models, results)

        # 8. 保存模型
        self.save_models(models, ensemble)

        # 最终总结
        logger.info("\n" + "=" * 60)
        logger.info("流水线运行完成！")
        logger.info("=" * 60)
        logger.info(f"\n输出目录: {self.output_dir}")
        logger.info(f"  - models/             : 模型文件")
        logger.info(f"  - evaluation_results.csv : 评估结果")
        logger.info(f"  - metadata.json       : 元数据")


def main():
    """主函数"""

    # 配置
    config = {
        'output_dir': 'pipeline_outputs',
        'n_samples': 2000,
        'n_features': 50,
        'train_ratio': 0.6,
        'valid_ratio': 0.2,
        'ridge': {
            'alpha': 1.0
        },
        'lightgbm': {
            'n_estimators': 100,
            'learning_rate': 0.05,
            'max_depth': 5,
            'num_leaves': 31
        }
    }

    # 创建并运行流水线
    pipeline = ModelPipeline(config)
    pipeline.run()

    logger.info("\n下一步:")
    logger.info("  1. 查看 pipeline_outputs/ 目录中的输出")
    logger.info("  2. 使用保存的模型进行预测")
    logger.info("  3. 在真实数据上运行流水线")


if __name__ == '__main__':
    main()
