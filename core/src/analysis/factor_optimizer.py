"""
因子组合优化器

优化多因子组合的权重：
- 等权重
- IC加权
- IC_IR加权
- 最大化IC_IR（优化算法）
- 最小相关性约束
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from loguru import logger
from dataclasses import dataclass
import warnings

# 导入异常类
try:
    from ..exceptions import (
        AnalysisError,
        DataValidationError,
        InsufficientDataError,
        FeatureCalculationError
    )
except ImportError:
    from src.exceptions import (
        AnalysisError,
        DataValidationError,
        InsufficientDataError,
        FeatureCalculationError
    )

warnings.filterwarnings('ignore')


@dataclass
class OptimizationResult:
    """优化结果数据类"""
    weights: pd.Series  # 优化后的权重
    objective_value: float  # 目标函数值
    ic_mean: float  # 组合IC均值
    ic_ir: float  # 组合ICIR
    method: str  # 优化方法

    def to_dict(self) -> Dict:
        return {
            '权重': self.weights.to_dict(),
            '目标函数值': self.objective_value,
            'IC均值': self.ic_mean,
            'ICIR': self.ic_ir,
            '方法': self.method
        }

    def __str__(self) -> str:
        weights_str = '\n'.join([f"  {k}: {v:.4f}" for k, v in self.weights.items()])
        return (
            f"优化结果 ({self.method}):\n"
            f"权重:\n{weights_str}\n"
            f"IC均值: {self.ic_mean:.4f}\n"
            f"ICIR: {self.ic_ir:.4f}\n"
            f"目标函数值: {self.objective_value:.4f}"
        )


class FactorOptimizer:
    """
    因子组合优化器

    目标：
    - 最大化组合IC或ICIR
    - 考虑因子相关性约束
    - 生成稳定的因子权重
    """

    def __init__(self):
        """初始化因子优化器"""
        logger.info("初始化因子组合优化器")

    def equal_weight(
        self,
        factor_names: List[str]
    ) -> pd.Series:
        """
        等权重分配

        Args:
            factor_names: 因子名称列表

        Returns:
            权重Series
        """
        n = len(factor_names)
        weights = pd.Series([1/n] * n, index=factor_names)

        logger.info(f"等权重分配: {n}个因子，每个{1/n:.4f}")

        return weights

    def ic_weight(
        self,
        ic_stats: pd.DataFrame
    ) -> pd.Series:
        """
        IC加权（按IC绝对值加权）

        Args:
            ic_stats: IC统计表 (index=因子名, columns=['IC均值', ...])

        Returns:
            权重Series
        """
        logger.info("计算IC加权...")

        # 取IC均值的绝对值
        ic_abs = ic_stats['IC均值'].abs()

        # 归一化为权重
        weights = ic_abs / ic_abs.sum()

        logger.success(f"IC加权完成，最高权重: {weights.max():.4f}")

        return weights

    def ic_ir_weight(
        self,
        ic_stats: pd.DataFrame
    ) -> pd.Series:
        """
        ICIR加权（按ICIR加权）

        Args:
            ic_stats: IC统计表 (columns=['ICIR', ...])

        Returns:
            权重Series
        """
        logger.info("计算ICIR加权...")

        # 取ICIR（可能为负，需要处理）
        ic_ir = ic_stats['ICIR']

        # 只保留正值ICIR
        ic_ir_positive = ic_ir[ic_ir > 0]

        if len(ic_ir_positive) == 0:
            logger.warning("所有因子的ICIR <= 0，使用等权重")
            return self.equal_weight(ic_stats.index.tolist())

        # 归一化为权重
        weights = ic_ir_positive / ic_ir_positive.sum()

        # 填充未选中的因子为0
        full_weights = pd.Series(0.0, index=ic_stats.index)
        full_weights[weights.index] = weights

        logger.success(f"ICIR加权完成，{len(weights)}个因子被选中")

        return full_weights

    def optimize_max_icir(
        self,
        ic_series_dict: Dict[str, pd.Series],
        method: str = 'SLSQP',
        max_weight: float = 0.5,
        min_weight: float = 0.0
    ) -> OptimizationResult:
        """
        优化最大化ICIR（使用scipy优化器）

        Args:
            ic_series_dict: IC时间序列字典 {因子名: IC序列}
            method: 优化算法 ('SLSQP', 'trust-constr')
            max_weight: 单因子最大权重
            min_weight: 单因子最小权重

        Returns:
            OptimizationResult对象
        """
        try:
            from scipy.optimize import minimize

            logger.info(f"优化最大化ICIR（算法={method}）...")

            # 对齐所有IC序列
            ic_df = pd.DataFrame(ic_series_dict)
            ic_df = ic_df.dropna()

            if len(ic_df) < 20:
                raise ValueError(f"有效IC序列太短({len(ic_df)})，无法优化")

            factor_names = ic_df.columns.tolist()
            n_factors = len(factor_names)

            # 目标函数：最大化ICIR = -min(-ICIR)
            def objective(weights):
                # 计算组合IC
                combined_ic = (ic_df * weights).sum(axis=1)

                # 计算ICIR
                ic_mean = combined_ic.mean()
                ic_std = combined_ic.std()

                if ic_std == 0:
                    return 0

                ic_ir = ic_mean / ic_std

                # 返回负值（minimize函数求最小值）
                return -ic_ir

            # 约束条件
            constraints = [
                {'type': 'eq', 'fun': lambda w: w.sum() - 1.0}  # 权重和为1
            ]

            # 边界条件
            bounds = [(min_weight, max_weight) for _ in range(n_factors)]

            # 初始值：等权重
            x0 = np.array([1/n_factors] * n_factors)

            # 执行优化
            # 注意：L-BFGS-B方法不支持等式约束，自动切换到SLSQP
            if method == 'L-BFGS-B':
                logger.warning(f"优化方法 '{method}' 不支持等式约束，自动切换到 'SLSQP'")
                method = 'SLSQP'

            result = minimize(
                objective,
                x0,
                method=method,
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000}
            )

            if not result.success:
                logger.warning(f"优化未完全收敛: {result.message}")

            # 提取结果
            optimal_weights = pd.Series(result.x, index=factor_names)

            # 计算最终IC统计
            combined_ic = (ic_df * optimal_weights).sum(axis=1)
            ic_mean = combined_ic.mean()
            ic_std = combined_ic.std()
            ic_ir = ic_mean / ic_std if ic_std > 0 else 0

            opt_result = OptimizationResult(
                weights=optimal_weights,
                objective_value=-result.fun,  # 转回正值
                ic_mean=ic_mean,
                ic_ir=ic_ir,
                method=f'MaxICIR_{method}'
            )

            logger.success(f"优化完成: ICIR={ic_ir:.4f}")

            return opt_result

        except ImportError:
            logger.error("scipy未安装，无法执行优化")
            raise
        except (DataValidationError, InsufficientDataError, FeatureCalculationError, AnalysisError) as e:
            logger.warning(f"优化失败(已知异常): {e}")
            raise
        except Exception as e:
            logger.warning(f"优化失败(未预期异常): {e}", exc_info=True)
            raise

    def optimize_min_correlation(
        self,
        ic_series_dict: Dict[str, pd.Series],
        corr_matrix: pd.DataFrame,
        max_avg_corr: float = 0.3
    ) -> OptimizationResult:
        """
        优化：最小化因子相关性，同时保持ICIR

        Args:
            ic_series_dict: IC时间序列字典
            corr_matrix: 因子相关性矩阵
            max_avg_corr: 最大平均相关性约束

        Returns:
            OptimizationResult对象
        """
        try:
            from scipy.optimize import minimize

            logger.info(f"优化最小相关性（约束平均相关性<{max_avg_corr}）...")

            # 对齐IC序列
            ic_df = pd.DataFrame(ic_series_dict).dropna()
            factor_names = ic_df.columns.tolist()
            n_factors = len(factor_names)

            # 目标函数：加权平均相关性
            def objective(weights):
                # 计算加权平均相关性
                weighted_corr = 0
                for i in range(n_factors):
                    for j in range(i+1, n_factors):
                        weighted_corr += weights[i] * weights[j] * abs(corr_matrix.iloc[i, j])

                return weighted_corr

            # 约束条件
            constraints = [
                {'type': 'eq', 'fun': lambda w: w.sum() - 1.0},  # 权重和为1

                # ICIR约束：组合ICIR > 0.3
                {'type': 'ineq', 'fun': lambda w: self._calculate_icir(ic_df, w) - 0.3}
            ]

            # 边界条件
            bounds = [(0.0, 1.0) for _ in range(n_factors)]

            # 初始值：等权重
            x0 = np.array([1/n_factors] * n_factors)

            # 执行优化
            result = minimize(
                objective,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000}
            )

            # 提取结果
            optimal_weights = pd.Series(result.x, index=factor_names)

            # 计算最终统计
            combined_ic = (ic_df * optimal_weights).sum(axis=1)
            ic_mean = combined_ic.mean()
            ic_std = combined_ic.std()
            ic_ir = ic_mean / ic_std if ic_std > 0 else 0

            opt_result = OptimizationResult(
                weights=optimal_weights,
                objective_value=result.fun,
                ic_mean=ic_mean,
                ic_ir=ic_ir,
                method='MinCorrelation'
            )

            logger.success(f"最小相关性优化完成: 平均相关性={result.fun:.4f}")

            return opt_result

        except (DataValidationError, InsufficientDataError, FeatureCalculationError, AnalysisError) as e:
            logger.warning(f"优化失败(已知异常): {e}")
            raise

        except Exception as e:
            logger.warning(f"优化失败(未预期异常): {e}", exc_info=True)
            raise

    def _calculate_icir(self, ic_df: pd.DataFrame, weights: np.ndarray) -> float:
        """辅助函数：计算组合ICIR"""
        combined_ic = (ic_df.values * weights).sum(axis=1)
        ic_mean = combined_ic.mean()
        ic_std = combined_ic.std()
        return ic_mean / ic_std if ic_std > 0 else 0

    def combine_factors(
        self,
        factor_dict: Dict[str, pd.DataFrame],
        weights: pd.Series,
        normalize: bool = True
    ) -> pd.DataFrame:
        """
        根据权重组合因子

        Args:
            factor_dict: 因子DataFrame字典
            weights: 因子权重Series
            normalize: 是否标准化组合因子

        Returns:
            组合因子DataFrame
        """
        logger.info("组合因子...")

        # 确保权重和因子对齐
        common_factors = list(set(factor_dict.keys()) & set(weights.index))

        if len(common_factors) == 0:
            raise ValueError("因子字典和权重没有公共因子")

        # 计算加权和
        combined_factor = None

        for factor_name in common_factors:
            factor_df = factor_dict[factor_name]
            weight = weights[factor_name]

            if combined_factor is None:
                combined_factor = factor_df * weight
            else:
                # 对齐索引和列
                combined_factor = combined_factor.add(factor_df * weight, fill_value=0)

        # 标准化（可选）
        if normalize:
            combined_factor = (combined_factor - combined_factor.mean()) / combined_factor.std()

        logger.success(f"因子组合完成，使用{len(common_factors)}个因子")

        return combined_factor


