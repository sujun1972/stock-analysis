"""
压力测试模块

测试组合在极端市场情景下的表现
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from loguru import logger


class StressTest:
    """
    压力测试

    功能：
        1. 历史情景测试（2015股灾、2020疫情等）
        2. 假设情景测试（市场暴跌X%）
        3. 敏感性分析
        4. 蒙特卡洛压力测试
    """

    def __init__(self):
        """初始化压力测试"""
        logger.info("压力测试模块初始化")

        # 预定义历史极端事件
        self.historical_scenarios = {
            '2015_stock_crash': {
                'name': '2015年股灾',
                'period': ('2015-06-15', '2015-08-26'),
                'market_return': -0.40,  # 市场下跌40%
                'description': 'A股杠杆牛市崩盘'
            },
            '2018_trade_war': {
                'name': '2018年中美贸易战',
                'period': ('2018-01-01', '2018-12-31'),
                'market_return': -0.25,
                'description': '中美贸易摩擦导致市场下跌'
            },
            '2020_covid': {
                'name': '2020年新冠疫情',
                'period': ('2020-01-20', '2020-03-23'),
                'market_return': -0.30,
                'description': '新冠疫情全球爆发'
            },
            '2008_financial_crisis': {
                'name': '2008年金融危机',
                'period': ('2008-09-15', '2009-03-09'),
                'market_return': -0.50,
                'description': '全球金融危机'
            }
        }

    def test_historical_scenario(
        self,
        portfolio_returns: pd.Series,
        market_returns: pd.Series,
        scenario: str = '2015_stock_crash'
    ) -> Dict[str, Any]:
        """
        历史情景测试

        使用历史极端事件测试组合表现

        参数:
            portfolio_returns: 组合历史收益率序列
            market_returns: 市场收益率序列（如沪深300）
            scenario: 情景名称

        返回:
            {
                'scenario_name': 情景名称,
                'portfolio_return': 组合收益率,
                'market_return': 市场收益率,
                'relative_return': 相对收益,
                'max_drawdown': 最大回撤,
                'var_95': 95% VaR,
                'days_to_recovery': 恢复天数
            }

        示例:
            >>> tester = StressTest()
            >>> result = tester.test_historical_scenario(
            ...     portfolio_returns, market_returns, '2015_stock_crash'
            ... )
            >>> print(f"组合损失: {result['portfolio_return']:.2%}")
        """
        if scenario not in self.historical_scenarios:
            raise ValueError(f"未知情景: {scenario}")

        scenario_info = self.historical_scenarios[scenario]
        start_date, end_date = scenario_info['period']

        # 过滤该时期的收益率
        try:
            portfolio_period = portfolio_returns.loc[start_date:end_date]
            market_period = market_returns.loc[start_date:end_date]

            if portfolio_period.empty:
                logger.warning(f"情景 {scenario} 期间无组合数据")
                return None

        except Exception as e:
            logger.error(f"提取情景数据失败: {e}")
            return None

        # 计算指标
        portfolio_ret = (1 + portfolio_period).prod() - 1
        market_ret = (1 + market_period).prod() - 1
        relative_ret = portfolio_ret - market_ret

        # 计算最大回撤
        cum_returns = (1 + portfolio_period).cumprod()
        running_max = cum_returns.expanding().max()
        drawdown = (cum_returns - running_max) / running_max
        max_dd = drawdown.min()

        # 计算VaR
        var_95 = portfolio_period.quantile(0.05)

        # 恢复天数（简化：假设之后都恢复了）
        days_to_recovery = len(portfolio_period)

        result = {
            'scenario_name': scenario_info['name'],
            'period': scenario_info['period'],
            'portfolio_return': portfolio_ret,
            'market_return': market_ret,
            'relative_return': relative_ret,
            'max_drawdown': max_dd,
            'var_95': var_95,
            'days_to_recovery': days_to_recovery,
            'n_days': len(portfolio_period)
        }

        logger.info(
            f"历史情景测试 '{scenario_info['name']}': "
            f"组合收益 {portfolio_ret:.2%}, 市场收益 {market_ret:.2%}"
        )

        return result

    def test_hypothetical_scenario(
        self,
        positions: Dict[str, Dict],
        prices: Dict[str, float],
        portfolio_value: float,
        market_shock: float = -0.20,
        stock_betas: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        假设情景测试

        假设市场下跌X%，测试组合损失

        参数:
            positions: 持仓信息
            prices: 当前价格
            portfolio_value: 组合价值
            market_shock: 市场冲击（如-0.20表示市场下跌20%）
            stock_betas: 各股票Beta值（可选，默认=1）

        返回:
            {
                'market_shock': 市场冲击,
                'portfolio_loss': 组合损失,
                'portfolio_loss_pct': 组合损失比例,
                'new_portfolio_value': 冲击后组合价值,
                'stock_impacts': 各股票影响
            }

        示例:
            >>> # 测试市场下跌20%的影响
            >>> result = tester.test_hypothetical_scenario(
            ...     positions, prices, portfolio_value, market_shock=-0.20
            ... )
            >>> print(f"组合损失: {result['portfolio_loss_pct']:.2%}")
        """
        if not positions:
            return {
                'market_shock': market_shock,
                'portfolio_loss': 0,
                'portfolio_loss_pct': 0,
                'new_portfolio_value': portfolio_value
            }

        # 如果没有提供Beta，假设全部为1
        if stock_betas is None:
            stock_betas = {stock: 1.0 for stock in positions.keys()}

        stock_impacts = {}
        total_loss = 0

        for stock, pos in positions.items():
            # 当前市值
            shares = pos.get('shares', 0)
            current_price = prices.get(stock, 0)
            current_value = shares * current_price

            # 股票Beta
            beta = stock_betas.get(stock, 1.0)

            # 预期损失 = Beta × 市场冲击
            expected_shock = beta * market_shock
            expected_loss = current_value * expected_shock

            stock_impacts[stock] = {
                'current_value': current_value,
                'beta': beta,
                'expected_shock': expected_shock,
                'expected_loss': expected_loss,
                'new_value': current_value * (1 + expected_shock)
            }

            total_loss += expected_loss

        portfolio_loss_pct = total_loss / portfolio_value if portfolio_value > 0 else 0
        new_portfolio_value = portfolio_value + total_loss

        result = {
            'market_shock': market_shock,
            'portfolio_loss': total_loss,
            'portfolio_loss_pct': portfolio_loss_pct,
            'new_portfolio_value': new_portfolio_value,
            'stock_impacts': stock_impacts
        }

        logger.info(
            f"假设情景测试，市场冲击: {market_shock:.1%}, "
            f"组合损失: {portfolio_loss_pct:.2%}"
        )

        return result

    def sensitivity_analysis(
        self,
        positions: Dict,
        prices: Dict,
        portfolio_value: float,
        shock_range: List[float] = None,
        stock_betas: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """
        敏感性分析

        测试不同市场冲击下的组合损失

        参数:
            positions: 持仓信息
            prices: 当前价格
            portfolio_value: 组合价值
            shock_range: 冲击范围列表（如[-0.30, -0.20, -0.10, 0, 0.10]）
            stock_betas: Beta值

        返回:
            DataFrame with sensitivity results

        示例:
            >>> results = tester.sensitivity_analysis(
            ...     positions, prices, portfolio_value,
            ...     shock_range=[-0.40, -0.30, -0.20, -0.10, 0, 0.10]
            ... )
            >>> print(results)
        """
        if shock_range is None:
            shock_range = [-0.40, -0.30, -0.20, -0.10, -0.05, 0, 0.05, 0.10]

        results = []

        for shock in shock_range:
            result = self.test_hypothetical_scenario(
                positions, prices, portfolio_value, shock, stock_betas
            )

            results.append({
                'market_shock': shock,
                'portfolio_loss_pct': result['portfolio_loss_pct'],
                'new_portfolio_value': result['new_portfolio_value']
            })

        df = pd.DataFrame(results)

        logger.info(f"敏感性分析完成，测试 {len(shock_range)} 个情景")

        return df

    def monte_carlo_stress_test(
        self,
        returns: pd.Series,
        portfolio_value: float,
        n_simulations: int = 10000,
        holding_period: int = 20,
        confidence_levels: List[float] = None
    ) -> Dict[str, Any]:
        """
        蒙特卡洛压力测试

        模拟大量未来路径，计算极端损失

        参数:
            returns: 历史收益率序列
            portfolio_value: 组合价值
            n_simulations: 模拟次数
            holding_period: 持有期（天数）
            confidence_levels: 置信水平列表

        返回:
            {
                'var_95': 95% VaR,
                'var_99': 99% VaR,
                'cvar_95': 95% CVaR,
                'expected_loss': 平均损失,
                'worst_case': 最坏情况损失,
                'simulated_returns': 模拟收益率分布
            }

        示例:
            >>> result = tester.monte_carlo_stress_test(
            ...     returns, portfolio_value=1000000, n_simulations=10000
            ... )
            >>> print(f"99% VaR: {result['var_99']:.2%}")
        """
        if confidence_levels is None:
            confidence_levels = [0.90, 0.95, 0.99]

        returns = returns.dropna()

        # 计算参数
        mean = returns.mean()
        std = returns.std()

        # 蒙特卡洛模拟
        np.random.seed(42)

        # 生成模拟路径
        simulated_returns = np.random.normal(
            mean * holding_period,
            std * np.sqrt(holding_period),
            n_simulations
        )

        # 计算损失分布
        losses = -simulated_returns  # 负收益 = 损失

        # 计算VaR和CVaR
        var_results = {}
        cvar_results = {}

        for cl in confidence_levels:
            var = np.percentile(losses, cl * 100)
            cvar = losses[losses >= var].mean()

            var_results[f'var_{int(cl*100)}'] = var
            cvar_results[f'cvar_{int(cl*100)}'] = cvar

        # 统计信息
        expected_loss = losses.mean()
        worst_case = losses.max()
        median_loss = np.median(losses)

        result = {
            **var_results,
            **cvar_results,
            'expected_loss': expected_loss,
            'worst_case': worst_case,
            'median_loss': median_loss,
            'holding_period': holding_period,
            'n_simulations': n_simulations,
            'simulated_returns': simulated_returns
        }

        logger.info(
            f"蒙特卡洛压力测试完成，{n_simulations}次模拟, "
            f"99% VaR: {var_results.get('var_99', 0):.2%}"
        )

        return result

    def run_comprehensive_stress_test(
        self,
        portfolio_returns: pd.Series,
        market_returns: pd.Series,
        positions: Dict,
        prices: Dict,
        portfolio_value: float,
        stock_betas: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        综合压力测试

        运行所有压力测试并生成综合报告

        返回:
            {
                'historical_scenarios': 历史情景测试结果,
                'hypothetical_scenarios': 假设情景测试结果,
                'sensitivity_analysis': 敏感性分析,
                'monte_carlo': 蒙特卡洛测试,
                'summary': 综合评估
            }
        """
        logger.info("开始综合压力测试")

        results = {}

        # 1. 历史情景测试
        historical_results = []
        for scenario in ['2015_stock_crash', '2020_covid', '2018_trade_war']:
            try:
                result = self.test_historical_scenario(
                    portfolio_returns, market_returns, scenario
                )
                if result:
                    historical_results.append(result)
            except Exception as e:
                logger.warning(f"历史情景 {scenario} 测试失败: {e}")

        results['historical_scenarios'] = historical_results

        # 2. 假设情景测试
        hypothetical_shocks = [-0.40, -0.30, -0.20, -0.10]
        hypothetical_results = []

        for shock in hypothetical_shocks:
            result = self.test_hypothetical_scenario(
                positions, prices, portfolio_value, shock, stock_betas
            )
            hypothetical_results.append(result)

        results['hypothetical_scenarios'] = hypothetical_results

        # 3. 敏感性分析
        sensitivity = self.sensitivity_analysis(
            positions, prices, portfolio_value, stock_betas=stock_betas
        )
        results['sensitivity_analysis'] = sensitivity

        # 4. 蒙特卡洛测试
        mc_result = self.monte_carlo_stress_test(
            portfolio_returns, portfolio_value
        )
        results['monte_carlo'] = mc_result

        # 5. 综合评估
        summary = self._generate_stress_test_summary(results)
        results['summary'] = summary

        logger.info("综合压力测试完成")

        return results

    def _generate_stress_test_summary(self, results: Dict) -> Dict[str, Any]:
        """生成压力测试综合评估"""
        summary = {}

        # 最坏历史情景
        if results.get('historical_scenarios'):
            worst_historical = min(
                results['historical_scenarios'],
                key=lambda x: x['portfolio_return']
            )
            summary['worst_historical_scenario'] = worst_historical['scenario_name']
            summary['worst_historical_loss'] = worst_historical['portfolio_return']

        # 最坏假设情景
        if results.get('hypothetical_scenarios'):
            worst_hypo = min(
                results['hypothetical_scenarios'],
                key=lambda x: x['portfolio_loss_pct']
            )
            summary['worst_hypothetical_shock'] = worst_hypo['market_shock']
            summary['worst_hypothetical_loss'] = worst_hypo['portfolio_loss_pct']

        # 蒙特卡洛99% VaR
        if results.get('monte_carlo'):
            summary['monte_carlo_var_99'] = results['monte_carlo'].get('var_99', 0)
            summary['monte_carlo_worst_case'] = results['monte_carlo'].get('worst_case', 0)

        # 风险评估
        mc_var_99 = summary.get('monte_carlo_var_99', 0)
        if mc_var_99 > 0.30:
            summary['risk_assessment'] = 'high'
        elif mc_var_99 > 0.20:
            summary['risk_assessment'] = 'medium'
        else:
            summary['risk_assessment'] = 'low'

        return summary

    def generate_stress_test_report(self, results: Dict) -> str:
        """
        生成压力测试报告（文本格式）

        参数:
            results: 综合压力测试结果

        返回:
            格式化的报告字符串
        """
        lines = []
        lines.append("=" * 60)
        lines.append("压力测试报告")
        lines.append("=" * 60)
        lines.append("")

        # 历史情景
        if results.get('historical_scenarios'):
            lines.append("历史情景测试:")
            for scenario in results['historical_scenarios']:
                lines.append(f"  {scenario['scenario_name']}:")
                lines.append(f"    组合收益: {scenario['portfolio_return']:.2%}")
                lines.append(f"    市场收益: {scenario['market_return']:.2%}")
                lines.append(f"    相对表现: {scenario['relative_return']:.2%}")
                lines.append(f"    最大回撤: {scenario['max_drawdown']:.2%}")
            lines.append("")

        # 假设情景
        if results.get('hypothetical_scenarios'):
            lines.append("假设情景测试:")
            for scenario in results['hypothetical_scenarios']:
                lines.append(
                    f"  市场冲击 {scenario['market_shock']:.0%}: "
                    f"组合损失 {scenario['portfolio_loss_pct']:.2%}"
                )
            lines.append("")

        # 蒙特卡洛
        if results.get('monte_carlo'):
            mc = results['monte_carlo']
            lines.append("蒙特卡洛压力测试:")
            lines.append(f"  95% VaR: {mc.get('var_95', 0):.2%}")
            lines.append(f"  99% VaR: {mc.get('var_99', 0):.2%}")
            lines.append(f"  最坏情况: {mc.get('worst_case', 0):.2%}")
            lines.append("")

        # 综合评估
        if results.get('summary'):
            summary = results['summary']
            lines.append("综合评估:")
            lines.append(f"  风险等级: {summary.get('risk_assessment', 'unknown').upper()}")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)
