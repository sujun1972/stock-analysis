"""
LightGBM模型（基线模型）
用于股票收益率预测和排名
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from typing import Optional, Dict, List, Tuple
import warnings
import pickle
from pathlib import Path
from loguru import logger

warnings.filterwarnings('ignore')


class LightGBMStockModel:
    """LightGBM股票预测模型"""

    def __init__(
        self,
        objective: str = 'regression',
        metric: str = 'rmse',
        num_leaves: int = 15,
        learning_rate: float = 0.05,
        n_estimators: int = 500,
        max_depth: int = 4,
        min_child_samples: int = 30,
        subsample: float = 0.8,
        colsample_bytree: float = 0.6,
        reg_alpha: float = 0.1,
        reg_lambda: float = 0.1,
        random_state: int = 42,
        verbose: int = -1,
        use_gpu: bool = True,
        gpu_platform_id: int = 0,
        gpu_device_id: int = 0
    ):
        """
        初始化LightGBM模型（支持GPU加速）

        参数:
            objective: 目标函数 ('regression', 'lambdarank')
            metric: 评估指标
            num_leaves: 叶子节点数
            learning_rate: 学习率
            n_estimators: 树的数量
            max_depth: 最大深度 (-1表示不限制)
            min_child_samples: 叶子节点最小样本数
            subsample: 行采样比例
            colsample_bytree: 列采样比例
            reg_alpha: L1正则化系数
            reg_lambda: L2正则化系数
            random_state: 随机种子
            verbose: 训练输出详细程度
            use_gpu: 是否使用GPU加速（默认True）
            gpu_platform_id: GPU平台ID（默认0）
            gpu_device_id: GPU设备ID（默认0）
        """
        # 尝试导入GPU管理器
        try:
            from src.utils.gpu_utils import gpu_manager
            gpu_available = gpu_manager.cuda_available
        except ImportError:
            gpu_available = False
            logger.warning("GPU管理器未安装，将使用CPU模式")

        # 基础参数
        self.params = {
            'objective': objective,
            'metric': metric,
            'num_leaves': num_leaves,
            'learning_rate': learning_rate,
            'n_estimators': n_estimators,
            'max_depth': max_depth,
            'min_child_samples': min_child_samples,
            'min_gain_to_split': 0.01,  # 添加分裂增益阈值，防止过拟合
            'subsample': subsample,
            'colsample_bytree': colsample_bytree,
            'reg_alpha': reg_alpha,
            'reg_lambda': reg_lambda,
            'random_state': random_state,
            'verbose': verbose,
        }

        # GPU配置
        self.use_gpu = use_gpu and gpu_available
        if self.use_gpu:
            try:
                # 检查LightGBM GPU支持
                from src.utils.gpu_utils import gpu_manager
                if gpu_manager.check_lightgbm_gpu():
                    self.params.update({
                        'device': 'gpu',
                        'gpu_platform_id': gpu_platform_id,
                        'gpu_device_id': gpu_device_id,
                        'gpu_use_dp': False,  # 使用单精度
                    })
                    logger.info("🚀 LightGBM将使用GPU训练")
                else:
                    self.use_gpu = False
                    self.params['force_col_wise'] = True
                    logger.warning("⚠️  LightGBM GPU不可用，降级为CPU模式")
            except Exception as e:
                logger.warning(f"GPU初始化失败: {e}，使用CPU模式")
                self.use_gpu = False
                self.params['force_col_wise'] = True
        else:
            self.params['force_col_wise'] = True

        self.model = None
        self.feature_names = None
        self.feature_importance = None

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame] = None,
        y_valid: Optional[pd.Series] = None,
        early_stopping_rounds: int = 50,
        verbose_eval: int = 50
    ) -> Dict:
        """
        训练模型

        参数:
            X_train: 训练特征
            y_train: 训练标签
            X_valid: 验证特征
            y_valid: 验证标签
            early_stopping_rounds: 早停轮数
            verbose_eval: 训练输出间隔

        返回:
            训练历史字典
        """
        logger.info(f"\n开始训练LightGBM模型...")
        logger.info(f"训练集: {len(X_train)} 样本 × {len(X_train.columns)} 特征")

        # 保存特征名
        self.feature_names = list(X_train.columns)

        # 创建数据集
        train_data = lgb.Dataset(X_train, label=y_train)

        # 验证集
        valid_sets = [train_data]
        valid_names = ['train']

        if X_valid is not None and y_valid is not None:
            valid_data = lgb.Dataset(X_valid, label=y_valid, reference=train_data)
            valid_sets.append(valid_data)
            valid_names.append('valid')
            logger.info(f"验证集: {len(X_valid)} 样本")

        # 训练模型
        callbacks = []
        if verbose_eval > 0:
            callbacks.append(lgb.log_evaluation(period=verbose_eval))
        if early_stopping_rounds > 0 and X_valid is not None:
            callbacks.append(lgb.early_stopping(stopping_rounds=early_stopping_rounds))

        self.model = lgb.train(
            self.params,
            train_data,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=callbacks
        )

        # 计算特征重要性
        self._compute_feature_importance()

        logger.success(f"✓ 训练完成，最佳迭代: {self.model.best_iteration}")

        # 返回训练历史
        history = {
            'best_iteration': self.model.best_iteration,
            'best_score': self.model.best_score
        }

        return history

    def predict(
        self,
        X: pd.DataFrame,
        num_iteration: int = None
    ) -> np.ndarray:
        """
        预测

        参数:
            X: 特征DataFrame
            num_iteration: 使用的迭代次数（None表示最佳迭代）

        返回:
            预测值数组
        """
        if self.model is None:
            raise ValueError("模型未训练，请先调用train()方法")

        # 检查特征名是否匹配
        if list(X.columns) != self.feature_names:
            logger.warning("警告: 特征名不匹配，尝试重新排序...")
            X = X[self.feature_names]

        predictions = self.model.predict(
            X,
            num_iteration=num_iteration
        )

        return predictions

    def predict_rank(
        self,
        X: pd.DataFrame,
        num_iteration: int = None,
        ascending: bool = False
    ) -> np.ndarray:
        """
        预测并返回排名（用于选股）

        参数:
            X: 特征DataFrame
            num_iteration: 使用的迭代次数
            ascending: 是否升序排名

        返回:
            排名数组（1表示最高/最低）
        """
        predictions = self.predict(X, num_iteration)
        ranks = pd.Series(predictions).rank(ascending=ascending).values
        return ranks

    def _compute_feature_importance(self):
        """计算特征重要性"""
        if self.model is None:
            return

        importance_gain = self.model.feature_importance(importance_type='gain')
        importance_split = self.model.feature_importance(importance_type='split')

        self.feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'gain': importance_gain,
            'split': importance_split
        }).sort_values('gain', ascending=False)

    def get_feature_importance(
        self,
        importance_type: str = 'gain',
        top_n: int = None
    ) -> pd.DataFrame:
        """
        获取特征重要性

        参数:
            importance_type: 重要性类型 ('gain', 'split')
            top_n: 返回前N个重要特征

        返回:
            特征重要性DataFrame
        """
        if self.feature_importance is None:
            raise ValueError("特征重要性未计算")

        df = self.feature_importance.copy()
        df = df.sort_values(importance_type, ascending=False)

        if top_n is not None:
            df = df.head(top_n)

        return df

    def plot_feature_importance(
        self,
        importance_type: str = 'gain',
        top_n: int = 20,
        figsize: tuple = (10, 8)
    ):
        """
        绘制特征重要性图

        参数:
            importance_type: 重要性类型
            top_n: 显示前N个特征
            figsize: 图片大小
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.info("需要安装matplotlib: pip install matplotlib")
            return

        importance_df = self.get_feature_importance(importance_type, top_n)

        plt.figure(figsize=figsize)
        plt.barh(range(len(importance_df)), importance_df[importance_type])
        plt.yticks(range(len(importance_df)), importance_df['feature'])
        plt.xlabel(f'Feature Importance ({importance_type})')
        plt.title(f'Top {top_n} Important Features')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.show()

    def save_model(
        self,
        model_path: str,
        save_importance: bool = True
    ):
        """
        保存模型

        参数:
            model_path: 模型保存路径
            save_importance: 是否保存特征重要性
        """
        if self.model is None:
            raise ValueError("模型未训练")

        model_path = Path(model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存模型
        self.model.save_model(str(model_path))

        # 保存特征名和参数
        meta_path = model_path.with_suffix('.meta.pkl')
        meta_data = {
            'params': self.params,
            'feature_names': self.feature_names,
            'feature_importance': self.feature_importance if save_importance else None
        }

        with open(meta_path, 'wb') as f:
            pickle.dump(meta_data, f)

        logger.success(f"✓ 模型已保存至: {model_path}")
        logger.success(f"✓ 元数据已保存至: {meta_path}")

    def load_model(
        self,
        model_path: str
    ):
        """
        加载模型

        参数:
            model_path: 模型路径
        """
        model_path = Path(model_path)

        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

        # 加载模型
        self.model = lgb.Booster(model_file=str(model_path))

        # 加载元数据
        meta_path = model_path.with_suffix('.meta.pkl')
        if meta_path.exists():
            with open(meta_path, 'rb') as f:
                meta_data = pickle.load(f)

            self.params = meta_data.get('params', self.params)
            self.feature_names = meta_data.get('feature_names')
            self.feature_importance = meta_data.get('feature_importance')

        logger.success(f"✓ 模型已加载: {model_path}")

    def get_params(self) -> dict:
        """获取模型参数"""
        return self.params.copy()

    def auto_tune(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: pd.DataFrame,
        y_valid: pd.Series,
        param_grid: Optional[Dict] = None,
        metric: str = 'ic',
        n_trials: int = 20,
        method: str = 'grid'
    ) -> Tuple['LightGBMStockModel', Dict]:
        """
        自动调优超参数

        参数:
            X_train: 训练特征
            y_train: 训练标签
            X_valid: 验证特征
            y_valid: 验证标签
            param_grid: 参数搜索空间（None=使用默认）
            metric: 优化指标 ('ic', 'rank_ic', 'mse')
            n_trials: 搜索次数
            method: 搜索方法 ('grid', 'random')

        返回:
            (best_model, results): 最佳模型和调优结果
        """
        from itertools import product
        import random

        logger.info(f"开始自动调优 (方法={method}, 指标={metric})...")

        # 默认搜索空间
        if param_grid is None:
            param_grid = {
                'learning_rate': [0.03, 0.05, 0.1],
                'num_leaves': [15, 31, 63],
                'max_depth': [3, 5, 7],
                'n_estimators': [100, 200],
                'min_child_samples': [20, 30]
            }

        # 生成参数组合
        keys = list(param_grid.keys())
        values = list(param_grid.values())

        if method == 'grid':
            # 网格搜索：所有组合
            param_combinations = [dict(zip(keys, v)) for v in product(*values)]
            logger.info(f"网格搜索: {len(param_combinations)} 种组合")
        else:
            # 随机搜索：随机采样
            all_combinations = [dict(zip(keys, v)) for v in product(*values)]
            param_combinations = random.sample(
                all_combinations,
                min(n_trials, len(all_combinations))
            )
            logger.info(f"随机搜索: {len(param_combinations)} 种组合")

        best_score = -float('inf') if metric != 'mse' else float('inf')
        best_params = None
        best_model = None
        all_results = []

        for i, params in enumerate(param_combinations, 1):
            # 创建并训练模型
            model = LightGBMStockModel(**params, random_state=42, verbose=-1)
            model.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)

            # 评估
            y_pred = model.predict(X_valid)
            score = self._calculate_metric(y_valid, y_pred, metric)

            all_results.append({'params': params, 'score': score})

            # 更新最佳
            is_better = (score > best_score) if metric != 'mse' else (score < best_score)
            if is_better:
                best_score = score
                best_params = params
                best_model = model

            if i % 5 == 0:
                logger.info(f"进度: {i}/{len(param_combinations)}, 最佳{metric}={best_score:.6f}")

        logger.info(f"✓ 调优完成！最佳{metric}={best_score:.6f}")
        logger.info(f"最佳参数: {best_params}")

        return best_model, {
            'best_params': best_params,
            'best_score': best_score,
            'all_results': all_results
        }

    def _calculate_metric(self, y_true: pd.Series, y_pred: np.ndarray, metric: str) -> float:
        """计算评估指标"""
        if metric == 'ic':
            return np.corrcoef(y_true, y_pred)[0, 1]
        elif metric == 'rank_ic':
            return pd.Series(y_true.values).corr(pd.Series(y_pred), method='spearman')
        elif metric == 'mse':
            return np.mean((y_true - y_pred) ** 2)
        else:
            raise ValueError(f"未知指标: {metric}")


# ==================== 便捷函数 ====================

def train_lightgbm_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_valid: pd.DataFrame = None,
    y_valid: pd.Series = None,
    params: dict = None,
    early_stopping_rounds: int = 50
) -> LightGBMStockModel:
    """
    便捷函数：训练LightGBM模型

    参数:
        X_train: 训练特征
        y_train: 训练标签
        X_valid: 验证特征
        y_valid: 验证标签
        params: 模型参数字典
        early_stopping_rounds: 早停轮数

    返回:
        训练好的模型
    """
    # 默认参数
    default_params = {
        'objective': 'regression',
        'metric': 'rmse',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'n_estimators': 500,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42
    }

    if params:
        default_params.update(params)

    # 创建模型
    model = LightGBMStockModel(**default_params)

    # 训练模型
    model.train(
        X_train, y_train,
        X_valid, y_valid,
        early_stopping_rounds=early_stopping_rounds
    )

    return model


# ==================== 使用示例 ====================

if __name__ == "__main__":
    logger.info("LightGBM模型测试\n")

    # 创建测试数据
    np.random.seed(42)
    n_samples = 1000
    n_features = 20

    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )

    # 模拟股票收益率（带噪声）
    y = (
        X['feature_0'] * 0.5 +
        X['feature_1'] * 0.3 +
        X['feature_2'] * -0.2 +
        np.random.randn(n_samples) * 0.1
    )

    # 分割训练集和验证集
    split_idx = int(n_samples * 0.8)
    X_train, X_valid = X[:split_idx], X[split_idx:]
    y_train, y_valid = y[:split_idx], y[split_idx:]

    logger.info("数据准备:")
    logger.info(f"  训练集: {len(X_train)} 样本")
    logger.info(f"  验证集: {len(X_valid)} 样本")
    logger.info(f"  特征数: {len(X.columns)}")

    # 训练模型
    logger.info("\n训练LightGBM模型:")
    model = LightGBMStockModel(
        objective='regression',
        learning_rate=0.1,
        n_estimators=100,
        num_leaves=31,
        verbose=-1
    )

    history = model.train(
        X_train, y_train,
        X_valid, y_valid,
        early_stopping_rounds=10,
        verbose_eval=20
    )

    # 预测
    logger.info("\n预测:")
    y_pred_train = model.predict(X_train)
    y_pred_valid = model.predict(X_valid)

    # 计算指标
    from sklearn.metrics import mean_squared_error, r2_score

    train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
    valid_rmse = np.sqrt(mean_squared_error(y_valid, y_pred_valid))
    train_r2 = r2_score(y_train, y_pred_train)
    valid_r2 = r2_score(y_valid, y_pred_valid)

    logger.info(f"\n训练集 RMSE: {train_rmse:.4f}, R²: {train_r2:.4f}")
    logger.info(f"验证集 RMSE: {valid_rmse:.4f}, R²: {valid_r2:.4f}")

    # 特征重要性
    logger.info("\n特征重要性 (Top 10):")
    importance_df = model.get_feature_importance('gain', top_n=10)
    logger.info(f"{importance_df}")

    # 保存和加载模型
    logger.info("\n保存模型:")
    model.save_model('test_lgb_model.txt')

    logger.info("\n加载模型:")
    new_model = LightGBMStockModel()
    new_model.load_model('test_lgb_model.txt')

    y_pred_new = new_model.predict(X_valid)
    logger.info(f"加载后预测一致性: {np.allclose(y_pred_valid, y_pred_new)}")

    logger.success("\n✓ LightGBM模型测试完成")
