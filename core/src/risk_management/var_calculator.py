"""
VaR（风险价值）计算器

计算组合在给定置信水平下的潜在最大损失
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from loguru import logger


class VaRCalculator:
    """
    风险价值(Value at Risk)计算器

    VaR = 在给定置信水平下，组合在一定时间内的最大潜在损失

    示例：
        95%置信水平、1日VaR = -2.5%
        含义：有95%的把握，组合在1天内的损失不会超过2.5%

    支持的计算方法：
        - historical: 历史模拟法
        - parametric: 方差-协方差法（假设正态分布）
        - monte_carlo: 蒙特卡洛模拟法
    """

    def __init__(self, confidence_level: float = 0.95):
        """
        初始化VaR计算器

        参数:
            confidence_level: 置信水平（默认95%）
        """
        if not 0 < confidence_level < 1:
            raise ValueError("置信水平必须在0和1之间")

        self.confidence_level = confidence_level
        logger.info(f"VaR计算器初始化，置信水平: {confidence_level:.1%}")

    def calculate_historical_var(
        self,
        returns: pd.Series,
        holding_period: int = 1
    ) -> Dict[str, float]:
        """
        历史模拟法计算VaR

        方法：
            1. 使用历史收益率分布
            2. 计算分位数作为VaR

        参数:
            returns: 历史收益率序列
            holding_period: 持有期（天数，默认1天）

        返回:
            {
                'var': VaR值（负数表示损失）,
                'cvar': 条件VaR（超过VaR的平均损失）,
                'confidence_level': 置信水平,
                'holding_period': 持有期,
                'method': 计算方法
            }

        示例:
            >>> calc = VaRCalculator(confidence_level=0.95)
            >>> returns = pd.Series([0.01, -0.02, 0.015, -0.005, ...])
            >>> result = calc.calculate_historical_var(returns)
            >>> print(f"95% VaR: {result['var']:.2%}")
            95% VaR: -2.50%
        """
        if returns.empty:
            raise ValueError("收益率序列不能为空")

        returns = returns.dropna()

        if len(returns) < 30:
            logger.warning(f"收益率样本较少（{len(returns)}个），VaR估计可能不准确")

        # 计算VaR（分位数）
        var = returns.quantile(1 - self.confidence_level)

        # 计算CVaR（VaR之下的平均损失）
        tail_returns = returns[returns <= var]
        cvar = tail_returns.mean() if len(tail_returns) > 0 else var

        # 调整持有期（假设收益率独立同分布）
        if holding_period > 1:
            var = var * np.sqrt(holding_period)
            cvar = cvar * np.sqrt(holding_period)

        logger.debug(
            f"历史模拟法VaR: {var:.4f}, CVaR: {cvar:.4f}, "
            f"持有期: {holding_period}天"
        )

        return {
            'var': var,
            'cvar': cvar,
            'confidence_level': self.confidence_level,
            'holding_period': holding_period,
            'method': 'historical'
        }

    def calculate_parametric_var(
        self,
        returns: pd.Series,
        holding_period: int = 1
    ) -> Dict[str, float]:
        """
        方差-协方差法计算VaR（参数法）

        方法：
            假设收益率服从正态分布
            VaR = μ - z * σ
            其中 z 是标准正态分布的分位数

        适用场景：
            - 收益率接近正态分布
            - 计算速度快
            - 适合大样本

        参数:
            returns: 历史收益率序列
            holding_period: 持有期（天数）

        返回:
            同 calculate_historical_var()
        """
        if returns.empty:
            raise ValueError("收益率序列不能为空")

        returns = returns.dropna()

        # 计算均值和标准差
        mean = returns.mean()
        std = returns.std()

        # 标准正态分布的分位数
        from scipy.stats import norm
        z_score = norm.ppf(1 - self.confidence_level)

        # 计算VaR
        var = mean + z_score * std  # z_score是负数

        # 正态分布下的CVaR
        # CVaR = μ - σ * φ(z) / α
        # 其中 φ(z) 是标准正态分布的概率密度函数
        cvar = mean - std * norm.pdf(z_score) / (1 - self.confidence_level)

        # 调整持有期
        if holding_period > 1:
            var = mean * holding_period + z_score * std * np.sqrt(holding_period)
            cvar = mean * holding_period - std * np.sqrt(holding_period) * \
                   norm.pdf(z_score) / (1 - self.confidence_level)

        logger.debug(
            f"参数法VaR: {var:.4f}, CVaR: {cvar:.4f}, "
            f"均值: {mean:.4f}, 标准差: {std:.4f}"
        )

        return {
            'var': var,
            'cvar': cvar,
            'confidence_level': self.confidence_level,
            'holding_period': holding_period,
            'method': 'parametric'
        }

    def calculate_monte_carlo_var(
        self,
        returns: pd.Series,
        holding_period: int = 1,
        n_simulations: int = 10000
    ) -> Dict[str, float]:
        """
        蒙特卡洛模拟法计算VaR

        方法：
            1. 根据历史收益率拟合分布
            2. 模拟大量未来收益路径
            3. 计算模拟收益的分位数

        参数:
            returns: 历史收益率序列
            holding_period: 持有期（天数）
            n_simulations: 模拟次数（默认10000次）

        返回:
            同 calculate_historical_var()
        """
        if returns.empty:
            raise ValueError("收益率序列不能为空")

        returns = returns.dropna()

        # 计算参数
        mean = returns.mean()
        std = returns.std()

        # 蒙特卡洛模拟
        np.random.seed(42)  # 固定随机种子以便复现

        # 生成模拟收益
        simulated_returns = np.random.normal(
            mean * holding_period,
            std * np.sqrt(holding_period),
            n_simulations
        )

        # 计算VaR和CVaR
        var = np.percentile(simulated_returns, (1 - self.confidence_level) * 100)
        tail_returns = simulated_returns[simulated_returns <= var]
        cvar = tail_returns.mean() if len(tail_returns) > 0 else var

        logger.debug(
            f"蒙特卡洛VaR: {var:.4f}, CVaR: {cvar:.4f}, "
            f"模拟次数: {n_simulations}"
        )

        return {
            'var': var,
            'cvar': cvar,
            'confidence_level': self.confidence_level,
            'holding_period': holding_period,
            'method': 'monte_carlo',
            'n_simulations': n_simulations
        }

    def calculate_portfolio_var(
        self,
        portfolio_values: pd.Series,
        method: str = 'historical'
    ) -> Dict[str, Any]:
        """
        计算组合VaR（多个持有期）

        参数:
            portfolio_values: 组合价值序列
            method: 计算方法 ('historical' | 'parametric' | 'monte_carlo')

        返回:
            {
                'var_1day': 1日VaR,
                'var_5day': 5日VaR,
                'var_20day': 20日VaR,
                'cvar_1day': 1日CVaR,
                'cvar_5day': 5日CVaR,
                'cvar_20day': 20日CVaR,
                'max_loss_historical': 历史最大单日损失,
                'method': 计算方法
            }

        示例:
            >>> portfolio_values = pd.Series([100000, 102000, 99000, ...])
            >>> results = calc.calculate_portfolio_var(portfolio_values)
            >>> print(f"1日VaR: {results['var_1day']:.2%}")
            >>> print(f"5日VaR: {results['var_5day']:.2%}")
        """
        if portfolio_values.empty:
            raise ValueError("组合价值序列不能为空")

        # 计算收益率
        returns = portfolio_values.pct_change().dropna()

        if returns.empty:
            raise ValueError("无法计算收益率，请检查数据")

        # 选择计算方法
        if method == 'historical':
            calc_func = self.calculate_historical_var
        elif method == 'parametric':
            calc_func = self.calculate_parametric_var
        elif method == 'monte_carlo':
            calc_func = self.calculate_monte_carlo_var
        else:
            raise ValueError(f"不支持的计算方法: {method}")

        # 计算不同持有期的VaR
        results = {'method': method}
        for period in [1, 5, 20]:
            var_result = calc_func(returns, period)
            results[f'var_{period}day'] = var_result['var']
            results[f'cvar_{period}day'] = var_result['cvar']

        # 历史最大损失
        results['max_loss_historical'] = returns.min()

        # 统计信息
        results['mean_return'] = returns.mean()
        results['std_return'] = returns.std()
        results['n_observations'] = len(returns)

        logger.info(
            f"组合VaR计算完成，方法: {method}, "
            f"1日VaR: {results['var_1day']:.4f}"
        )

        return results

    def compare_methods(
        self,
        returns: pd.Series,
        holding_period: int = 1
    ) -> pd.DataFrame:
        """
        比较不同VaR计算方法的结果

        参数:
            returns: 收益率序列
            holding_period: 持有期

        返回:
            DataFrame with methods comparison
        """
        methods = ['historical', 'parametric', 'monte_carlo']
        results = []

        for method in methods:
            try:
                if method == 'historical':
                    result = self.calculate_historical_var(returns, holding_period)
                elif method == 'parametric':
                    result = self.calculate_parametric_var(returns, holding_period)
                elif method == 'monte_carlo':
                    result = self.calculate_monte_carlo_var(returns, holding_period)

                results.append({
                    'method': method,
                    'var': result['var'],
                    'cvar': result['cvar']
                })
            except Exception as e:
                logger.warning(f"方法 {method} 计算失败: {e}")

        df = pd.DataFrame(results)
        return df

    def backtest_var(
        self,
        returns: pd.Series,
        window_size: int = 252,
        holding_period: int = 1,
        method: str = 'historical'
    ) -> Dict[str, Any]:
        """
        回测VaR模型的准确性

        方法：
            滚动窗口计算VaR，检查实际损失超过VaR的次数

        参数:
            returns: 收益率序列
            window_size: 滚动窗口大小（默认252个交易日）
            holding_period: 持有期
            method: 计算方法

        返回:
            {
                'violation_rate': 违约率（实际损失超过VaR的比例）,
                'expected_rate': 期望违约率（1 - 置信水平）,
                'n_violations': 违约次数,
                'n_tests': 测试次数,
                'pass_backtest': 是否通过回测
            }
        """
        returns = returns.dropna()

        if len(returns) < window_size + holding_period:
            raise ValueError(f"数据不足，至少需要 {window_size + holding_period} 个观测值")

        violations = 0
        n_tests = 0

        # 滚动窗口回测
        for i in range(window_size, len(returns) - holding_period + 1):
            # 训练窗口
            train_returns = returns.iloc[i - window_size:i]

            # 计算VaR
            if method == 'historical':
                var_result = self.calculate_historical_var(train_returns, holding_period)
            elif method == 'parametric':
                var_result = self.calculate_parametric_var(train_returns, holding_period)
            else:
                raise ValueError(f"回测不支持方法: {method}")

            var = var_result['var']

            # 实际收益
            actual_return = returns.iloc[i:i + holding_period].sum()

            # 检查是否违约
            if actual_return < var:
                violations += 1

            n_tests += 1

        # 计算违约率
        violation_rate = violations / n_tests if n_tests > 0 else 0
        expected_rate = 1 - self.confidence_level

        # Kupiec检验：违约率是否显著偏离期望值
        # 简化判断：违约率在期望值±2个标准差内
        std_error = np.sqrt(expected_rate * (1 - expected_rate) / n_tests)
        pass_backtest = abs(violation_rate - expected_rate) <= 2 * std_error

        logger.info(
            f"VaR回测完成，违约率: {violation_rate:.2%}, "
            f"期望违约率: {expected_rate:.2%}, "
            f"通过: {pass_backtest}"
        )

        return {
            'violation_rate': violation_rate,
            'expected_rate': expected_rate,
            'n_violations': violations,
            'n_tests': n_tests,
            'pass_backtest': pass_backtest,
            'method': method
        }
