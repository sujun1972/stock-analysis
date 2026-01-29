"""
仓位计算器

根据不同的风险管理策略，计算合理的仓位大小
"""

import pandas as pd
import numpy as np
from typing import Dict, Union, List, Optional
from loguru import logger


class PositionSizer:
    """
    仓位计算器

    支持多种仓位计算方法：
        1. 等权重（Equal Weight）
        2. 凯利公式（Kelly Criterion）
        3. 风险平价（Risk Parity）
        4. 波动率目标（Volatility Target）
        5. 最大夏普比率（Max Sharpe Ratio）
    """

    def __init__(self):
        """初始化仓位计算器"""
        logger.info("仓位计算器初始化")

    def calculate_equal_weight(
        self,
        n_stocks: int,
        max_position: float = 0.2
    ) -> Dict[str, float]:
        """
        等权重分配

        最简单的方法：每只股票分配相同权重

        参数:
            n_stocks: 股票数量
            max_position: 单只股票最大仓位限制（默认20%）

        返回:
            {stock_id: weight}

        示例:
            >>> sizer = PositionSizer()
            >>> weights = sizer.calculate_equal_weight(5, max_position=0.25)
            >>> print(weights)
            {'stock_0': 0.2, 'stock_1': 0.2, ...}
        """
        if n_stocks <= 0:
            raise ValueError("股票数量必须大于0")
        if not 0 < max_position <= 1:
            raise ValueError("最大仓位必须在0和1之间")

        equal_weight = 1.0 / n_stocks
        weight = min(equal_weight, max_position)

        # 如果受到max_position限制，重新归一化
        if weight < equal_weight:
            # 超过限制的部分均分给其他股票
            total_weight = weight * n_stocks
            if total_weight < 1.0:
                logger.warning(
                    f"等权重受限，总仓位: {total_weight:.1%}，"
                    f"建议增加股票数量或提高最大仓位限制"
                )

        weights = {f'stock_{i}': weight for i in range(n_stocks)}

        logger.debug(f"等权重分配: {n_stocks}只股票，每只权重: {weight:.2%}")

        return weights

    def calculate_kelly_position(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        max_position: float = 0.2,
        fractional_kelly: float = 0.5
    ) -> float:
        """
        凯利公式计算仓位

        Kelly % = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

        参数:
            win_rate: 胜率（0-1）
            avg_win: 平均盈利（正数，如0.03表示平均赚3%）
            avg_loss: 平均亏损（正数，如0.02表示平均亏2%）
            max_position: 最大仓位限制（默认20%）
            fractional_kelly: 凯利系数（0.5=半凯利，更保守）

        返回:
            建议仓位比例（0-1）

        示例:
            >>> sizer = PositionSizer()
            >>> # 胜率60%，平均赚3%，平均亏2%
            >>> pos = sizer.calculate_kelly_position(0.6, 0.03, 0.02)
            >>> print(f"建议仓位: {pos:.1%}")
            建议仓位: 16.7%  # (0.6*3 - 0.4*2)/3 * 0.5 = 16.7%
        """
        # 参数验证
        if not 0 <= win_rate <= 1:
            raise ValueError("胜率必须在0和1之间")
        if avg_win <= 0 or avg_loss <= 0:
            raise ValueError("平均盈利和平均亏损必须大于0")
        if not 0 < fractional_kelly <= 1:
            raise ValueError("凯利系数必须在0和1之间")

        # 凯利公式
        # f = (p * b - q) / b
        # 其中 p=胜率, q=1-胜率, b=盈亏比
        win_loss_ratio = avg_win / avg_loss
        kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio

        # 使用部分凯利（更保守）
        kelly = kelly * fractional_kelly

        # 限制范围 [0, max_position]
        position = max(0, min(kelly, max_position))

        logger.debug(
            f"凯利仓位: {position:.2%}, "
            f"胜率: {win_rate:.1%}, 盈亏比: {win_loss_ratio:.2f}, "
            f"系数: {fractional_kelly}"
        )

        return position

    def calculate_kelly_position_from_trades(
        self,
        trade_returns: pd.Series,
        max_position: float = 0.2,
        fractional_kelly: float = 0.5
    ) -> float:
        """
        从历史交易记录计算凯利仓位

        自动计算胜率、平均盈利和平均亏损

        参数:
            trade_returns: 历史交易收益率序列
            max_position: 最大仓位限制
            fractional_kelly: 凯利系数

        返回:
            建议仓位比例

        示例:
            >>> returns = pd.Series([0.02, -0.01, 0.03, -0.01, 0.02])
            >>> pos = sizer.calculate_kelly_position_from_trades(returns)
        """
        if trade_returns.empty:
            raise ValueError("交易收益序列不能为空")

        # 分离盈利和亏损交易
        wins = trade_returns[trade_returns > 0]
        losses = trade_returns[trade_returns < 0]

        if len(wins) == 0 or len(losses) == 0:
            logger.warning("缺少盈利或亏损交易，使用保守仓位")
            return max_position * 0.3  # 保守的30%仓位

        # 计算胜率
        win_rate = len(wins) / len(trade_returns)

        # 计算平均盈利和亏损
        avg_win = wins.mean()
        avg_loss = abs(losses.mean())

        return self.calculate_kelly_position(
            win_rate, avg_win, avg_loss, max_position, fractional_kelly
        )

    def calculate_risk_parity_weights(
        self,
        returns: pd.DataFrame,
        risk_target: Optional[float] = None
    ) -> pd.Series:
        """
        风险平价权重

        方法：
            每只股票的风险贡献相等
            权重 ∝ 1 / 波动率

        参数:
            returns: 股票收益率DataFrame (columns=stocks)
            risk_target: 目标风险水平（年化波动率，可选）

        返回:
            各股票权重Series

        示例:
            >>> returns_df = pd.DataFrame({
            ...     'stock_A': [0.01, 0.02, -0.01, 0.015],
            ...     'stock_B': [0.03, 0.01, -0.02, 0.01]
            ... })
            >>> weights = sizer.calculate_risk_parity_weights(returns_df)
            >>> print(weights)
            stock_A    0.55
            stock_B    0.45
        """
        if returns.empty:
            raise ValueError("收益率DataFrame不能为空")

        # 计算各股票的波动率（年化）
        volatilities = returns.std() * np.sqrt(252)

        if (volatilities == 0).any():
            logger.warning("某些股票波动率为0，使用等权重")
            return pd.Series(1.0 / len(returns.columns), index=returns.columns)

        # 风险平价：权重与波动率成反比
        inv_vol = 1 / volatilities
        weights = inv_vol / inv_vol.sum()

        # 如果指定了目标风险水平，进行缩放
        if risk_target is not None:
            portfolio_vol = self._calculate_portfolio_volatility(returns, weights)
            scale_factor = risk_target / portfolio_vol
            logger.debug(
                f"风险平价权重已缩放至目标波动率 {risk_target:.2%}, "
                f"缩放因子: {scale_factor:.2f}"
            )

        logger.debug(
            f"风险平价权重计算完成，波动率范围: "
            f"{volatilities.min():.2%} - {volatilities.max():.2%}"
        )

        return weights

    def calculate_volatility_target_position(
        self,
        current_volatility: float,
        target_volatility: float = 0.15,
        current_position: float = 1.0,
        max_leverage: float = 1.5
    ) -> float:
        """
        波动率目标仓位调整

        方法：
            根据当前波动率动态调整仓位
            new_position = (target_vol / current_vol) * current_position

        参数:
            current_volatility: 当前组合波动率（年化）
            target_volatility: 目标波动率（默认15%）
            current_position: 当前仓位（1.0=满仓）
            max_leverage: 最大杠杆（默认1.5，即允许150%仓位）

        返回:
            调整后的仓位（0 - max_leverage）

        示例:
            >>> # 当前波动率20%，目标15%，当前满仓
            >>> new_pos = sizer.calculate_volatility_target_position(0.20, 0.15, 1.0)
            >>> print(f"建议仓位: {new_pos:.1%}")
            建议仓位: 75.0%  # 波动率高，减仓到75%
        """
        if current_volatility <= 0:
            logger.warning("当前波动率为0，保持原仓位")
            return current_position

        if target_volatility <= 0:
            raise ValueError("目标波动率必须大于0")

        # 计算调整因子
        adjustment_factor = target_volatility / current_volatility
        new_position = current_position * adjustment_factor

        # 限制范围 [0, max_leverage]
        new_position = max(0, min(new_position, max_leverage))

        logger.debug(
            f"波动率目标调整: {current_position:.1%} → {new_position:.1%}, "
            f"当前波动率: {current_volatility:.2%}, 目标: {target_volatility:.2%}"
        )

        return new_position

    def calculate_max_sharpe_weights(
        self,
        returns: pd.DataFrame,
        risk_free_rate: float = 0.03,
        max_position: float = 0.3
    ) -> pd.Series:
        """
        最大夏普比率权重

        使用均值-方差优化求解最大夏普比率的权重

        参数:
            returns: 股票收益率DataFrame
            risk_free_rate: 无风险利率（年化，默认3%）
            max_position: 单只股票最大仓位（默认30%）

        返回:
            各股票权重Series

        注意：
            需要安装 scipy 库

        示例:
            >>> returns_df = pd.DataFrame({...})
            >>> weights = sizer.calculate_max_sharpe_weights(returns_df)
        """
        try:
            from scipy.optimize import minimize
        except ImportError:
            logger.error("需要安装scipy库: pip install scipy")
            raise

        if returns.empty:
            raise ValueError("收益率DataFrame不能为空")

        n_assets = len(returns.columns)

        # 计算期望收益率和协方差矩阵（年化）
        mean_returns = returns.mean() * 252
        cov_matrix = returns.cov() * 252

        # 目标函数：负夏普比率（最小化 = 最大化正夏普比率）
        def negative_sharpe(weights):
            portfolio_return = np.sum(mean_returns * weights)
            portfolio_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

            if portfolio_std == 0:
                return 1e10  # 避免除零

            sharpe = (portfolio_return - risk_free_rate) / portfolio_std
            return -sharpe

        # 约束条件
        constraints = (
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # 权重和=1
        )

        # 边界条件
        bounds = tuple((0, max_position) for _ in range(n_assets))

        # 初始猜测（等权重）
        initial_guess = np.array([1 / n_assets] * n_assets)

        # 优化
        result = minimize(
            negative_sharpe,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )

        if not result.success:
            logger.warning(f"优化未收敛: {result.message}，使用等权重")
            return pd.Series(1.0 / n_assets, index=returns.columns)

        weights = pd.Series(result.x, index=returns.columns)

        # 计算最优组合的夏普比率
        optimal_sharpe = -result.fun
        logger.info(f"最大夏普比率权重计算完成，夏普比率: {optimal_sharpe:.2f}")

        return weights

    def calculate_inverse_volatility_weights(
        self,
        returns: pd.DataFrame
    ) -> pd.Series:
        """
        反波动率权重

        简化版的风险平价，不考虑相关性

        参数:
            returns: 股票收益率DataFrame

        返回:
            各股票权重Series
        """
        return self.calculate_risk_parity_weights(returns)

    def calculate_minimum_variance_weights(
        self,
        returns: pd.DataFrame,
        max_position: float = 0.3
    ) -> pd.Series:
        """
        最小方差权重

        寻找波动率最小的组合

        参数:
            returns: 股票收益率DataFrame
            max_position: 单只股票最大仓位

        返回:
            各股票权重Series
        """
        try:
            from scipy.optimize import minimize
        except ImportError:
            logger.error("需要安装scipy库")
            raise

        if returns.empty:
            raise ValueError("收益率DataFrame不能为空")

        n_assets = len(returns.columns)
        cov_matrix = returns.cov() * 252  # 年化

        # 目标函数：组合方差
        def portfolio_variance(weights):
            return np.dot(weights.T, np.dot(cov_matrix, weights))

        # 约束和边界
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, max_position) for _ in range(n_assets))
        initial_guess = np.array([1 / n_assets] * n_assets)

        # 优化
        result = minimize(
            portfolio_variance,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if not result.success:
            logger.warning("最小方差优化未收敛，使用风险平价")
            return self.calculate_risk_parity_weights(returns)

        weights = pd.Series(result.x, index=returns.columns)
        min_vol = np.sqrt(result.fun)

        logger.info(f"最小方差权重计算完成，组合波动率: {min_vol:.2%}")

        return weights

    def _calculate_portfolio_volatility(
        self,
        returns: pd.DataFrame,
        weights: pd.Series
    ) -> float:
        """
        计算组合波动率

        参数:
            returns: 收益率DataFrame
            weights: 权重Series

        返回:
            年化波动率
        """
        cov_matrix = returns.cov() * 252
        portfolio_variance = np.dot(weights.values.T,
                                   np.dot(cov_matrix, weights.values))
        portfolio_volatility = np.sqrt(portfolio_variance)

        return portfolio_volatility

    def compare_methods(
        self,
        returns: pd.DataFrame,
        methods: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        比较不同仓位计算方法

        参数:
            returns: 收益率DataFrame
            methods: 要比较的方法列表（None=全部）

        返回:
            比较结果DataFrame
        """
        if methods is None:
            methods = ['equal_weight', 'risk_parity', 'max_sharpe', 'min_variance']

        results = []

        for method in methods:
            try:
                if method == 'equal_weight':
                    weights = pd.Series(
                        1.0 / len(returns.columns),
                        index=returns.columns
                    )
                elif method == 'risk_parity':
                    weights = self.calculate_risk_parity_weights(returns)
                elif method == 'max_sharpe':
                    weights = self.calculate_max_sharpe_weights(returns)
                elif method == 'min_variance':
                    weights = self.calculate_minimum_variance_weights(returns)
                else:
                    continue

                # 计算该权重下的组合指标
                portfolio_vol = self._calculate_portfolio_volatility(returns, weights)
                portfolio_ret = (returns.mean() * 252 * weights).sum()

                results.append({
                    'method': method,
                    'annual_return': portfolio_ret,
                    'annual_volatility': portfolio_vol,
                    'sharpe_ratio': portfolio_ret / portfolio_vol if portfolio_vol > 0 else 0,
                    'max_position': weights.max(),
                    'min_position': weights.min()
                })

            except Exception as e:
                logger.warning(f"方法 {method} 计算失败: {e}")

        df = pd.DataFrame(results)
        return df
