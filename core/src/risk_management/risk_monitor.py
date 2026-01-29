"""
综合风险监控器

整合所有风险管理模块，提供实时风险监控
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from loguru import logger

from .var_calculator import VaRCalculator
from .drawdown_controller import DrawdownController
from .position_sizer import PositionSizer


class RiskMonitor:
    """
    综合风险监控器

    功能：
        1. 整合VaR、回撤、仓位管理等所有风险模块
        2. 提供统一的风险监控接口
        3. 实时风险评级（low/medium/high/critical）
        4. 自动生成风控建议
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化风险监控器

        参数:
            config: 配置字典
                {
                    'max_drawdown': 0.15,           # 最大回撤
                    'var_confidence': 0.95,          # VaR置信水平
                    'max_position_pct': 0.20,        # 单只股票最大仓位
                    'max_sector_pct': 0.30,          # 单个行业最大仓位
                    'target_volatility': 0.15,       # 目标波动率
                    'enable_var': True,              # 是否启用VaR监控
                    'enable_drawdown': True,         # 是否启用回撤监控
                    'enable_concentration': True     # 是否启用集中度监控
                }

        示例:
            >>> config = {'max_drawdown': 0.15, 'var_confidence': 0.95}
            >>> monitor = RiskMonitor(config)
        """
        self.config = config or {}

        # 初始化子模块
        self.var_calc = VaRCalculator(
            confidence_level=self.config.get('var_confidence', 0.95)
        )

        self.dd_controller = DrawdownController(
            max_drawdown=self.config.get('max_drawdown', 0.15),
            warning_threshold=self.config.get('dd_warning_threshold', 0.80),
            alert_threshold=self.config.get('dd_alert_threshold', 0.60)
        )

        self.position_sizer = PositionSizer()

        # 监控开关
        self.enable_var = self.config.get('enable_var', True)
        self.enable_drawdown = self.config.get('enable_drawdown', True)
        self.enable_concentration = self.config.get('enable_concentration', True)

        # 警报历史
        self.alerts: List[Dict] = []

        logger.info(f"风险监控器初始化完成，配置: {self.config}")

    def monitor(
        self,
        portfolio_value: float,
        portfolio_returns: pd.Series,
        positions: Dict[str, Dict[str, float]],
        prices: Dict[str, float],
        sector_map: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        执行完整的风险监控

        参数:
            portfolio_value: 当前组合总价值
            portfolio_returns: 组合历史收益率序列
            positions: 持仓信息
                {
                    'stock_code': {
                        'shares': 1000,      # 持仓股数
                        'cost': 10.5,        # 成本价
                        'value': 12000       # 当前市值（可选，会自动计算）
                    }
                }
            prices: 当前价格 {stock_code: current_price}
            sector_map: 行业映射（可选）{stock_code: sector_name}

        返回:
            {
                'timestamp': 监控时间,
                'portfolio_value': 组合价值,
                'risk_metrics': {
                    'var': VaR指标,
                    'drawdown': 回撤信息,
                    'concentration': 集中度信息,
                    'volatility': 波动率信息
                },
                'alerts': 警报列表,
                'recommendations': 建议动作列表,
                'overall_risk_level': 'low'/'medium'/'high'/'critical'
            }

        示例:
            >>> result = monitor.monitor(
            ...     portfolio_value=1000000,
            ...     portfolio_returns=pd.Series([...]),
            ...     positions={'000001': {'shares': 10000, 'cost': 10.0}},
            ...     prices={'000001': 11.5}
            ... )
            >>> print(f"风险等级: {result['overall_risk_level']}")
        """
        risk_metrics = {}
        self.alerts = []

        # ===== 1. VaR监控 =====
        if self.enable_var and len(portfolio_returns) >= 30:
            try:
                var_metrics = self.var_calc.calculate_portfolio_var(
                    pd.Series(portfolio_returns),
                    method='historical'
                )
                risk_metrics['var'] = var_metrics

                # 检查VaR是否过高
                var_1day = abs(var_metrics['var_1day'])
                if var_1day > 0.03:  # 单日VaR > 3%
                    self.alerts.append({
                        'level': 'warning',
                        'type': 'var',
                        'message': f"单日VaR过高: {var_1day:.2%}，存在较大风险暴露",
                        'value': var_1day
                    })
                    logger.warning(f"VaR警报: {var_1day:.2%}")

            except Exception as e:
                logger.error(f"VaR计算失败: {e}")
                risk_metrics['var'] = None
        else:
            risk_metrics['var'] = None

        # ===== 2. 回撤监控 =====
        if self.enable_drawdown:
            try:
                dd_result = self.dd_controller.update(portfolio_value)
                risk_metrics['drawdown'] = dd_result

                if dd_result['risk_level'] in ['alert', 'warning', 'critical']:
                    self.alerts.append({
                        'level': dd_result['risk_level'],
                        'type': 'drawdown',
                        'message': dd_result['message'],
                        'action': dd_result['action'],
                        'value': dd_result['current_drawdown']
                    })
                    logger.warning(f"回撤警报: {dd_result['risk_level']}")

            except Exception as e:
                logger.error(f"回撤计算失败: {e}")
                risk_metrics['drawdown'] = None
        else:
            risk_metrics['drawdown'] = None

        # ===== 3. 仓位集中度监控 =====
        if self.enable_concentration:
            try:
                concentration = self._check_concentration(
                    positions, prices, portfolio_value, sector_map
                )
                risk_metrics['concentration'] = concentration

                # 检查单只股票集中度
                max_pos_pct = concentration['max_position_pct']
                max_pos_limit = self.config.get('max_position_pct', 0.20)

                if max_pos_pct > max_pos_limit:
                    self.alerts.append({
                        'level': 'warning',
                        'type': 'position_concentration',
                        'message': f"仓位过于集中: {concentration['max_stock']} "
                                 f"占比 {max_pos_pct:.1%}，超过限制 {max_pos_limit:.1%}",
                        'value': max_pos_pct
                    })

                # 检查行业集中度
                if sector_map and 'max_sector_pct' in concentration:
                    max_sector_pct = concentration['max_sector_pct']
                    max_sector_limit = self.config.get('max_sector_pct', 0.30)

                    if max_sector_pct > max_sector_limit:
                        self.alerts.append({
                            'level': 'alert',
                            'type': 'sector_concentration',
                            'message': f"行业集中度过高: {concentration['max_sector']} "
                                     f"占比 {max_sector_pct:.1%}",
                            'value': max_sector_pct
                        })

            except Exception as e:
                logger.error(f"集中度计算失败: {e}")
                risk_metrics['concentration'] = None
        else:
            risk_metrics['concentration'] = None

        # ===== 4. 波动率监控 =====
        if len(portfolio_returns) >= 20:
            try:
                volatility_metrics = self._calculate_volatility_metrics(portfolio_returns)
                risk_metrics['volatility'] = volatility_metrics

                # 检查波动率是否过高
                current_vol = volatility_metrics['current_volatility']
                target_vol = self.config.get('target_volatility', 0.15)

                if current_vol > target_vol * 1.5:  # 超过目标的150%
                    self.alerts.append({
                        'level': 'alert',
                        'type': 'volatility',
                        'message': f"组合波动率过高: {current_vol:.2%}，"
                                 f"目标: {target_vol:.2%}",
                        'value': current_vol
                    })

            except Exception as e:
                logger.error(f"波动率计算失败: {e}")
                risk_metrics['volatility'] = None
        else:
            risk_metrics['volatility'] = None

        # ===== 5. 评估整体风险等级 =====
        overall_risk = self._assess_overall_risk(risk_metrics)

        # ===== 6. 生成建议 =====
        recommendations = self._generate_recommendations(risk_metrics, overall_risk)

        result = {
            'timestamp': pd.Timestamp.now(),
            'portfolio_value': portfolio_value,
            'risk_metrics': risk_metrics,
            'alerts': self.alerts,
            'recommendations': recommendations,
            'overall_risk_level': overall_risk
        }

        logger.info(
            f"风险监控完成，等级: {overall_risk}, "
            f"警报数: {len(self.alerts)}"
        )

        return result

    def _check_concentration(
        self,
        positions: Dict,
        prices: Dict,
        total_value: float,
        sector_map: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        检查仓位集中度

        返回:
            {
                'max_stock': 最大持仓股票,
                'max_position_pct': 最大持仓比例,
                'top5_concentration': 前5大持仓集中度,
                'n_positions': 持仓数量,
                'max_sector': 最大行业（如果提供sector_map）,
                'max_sector_pct': 最大行业比例
            }
        """
        if not positions or total_value <= 0:
            return {
                'max_position_pct': 0,
                'max_stock': None,
                'top5_concentration': 0,
                'n_positions': 0
            }

        # 计算各持仓市值
        position_values = {}
        for stock, pos in positions.items():
            if 'value' in pos:
                market_value = pos['value']
            else:
                shares = pos.get('shares', 0)
                price = prices.get(stock, 0)
                market_value = shares * price

            position_values[stock] = market_value

        # 最大持仓
        if position_values:
            max_stock = max(position_values, key=position_values.get)
            max_value = position_values[max_stock]
            max_pct = max_value / total_value
        else:
            max_stock = None
            max_pct = 0

        # 前5大持仓集中度
        sorted_values = sorted(position_values.values(), reverse=True)
        top5_value = sum(sorted_values[:5])
        top5_pct = top5_value / total_value

        result = {
            'max_stock': max_stock,
            'max_position_pct': max_pct,
            'top5_concentration': top5_pct,
            'n_positions': len(positions),
            'position_values': position_values
        }

        # 行业集中度
        if sector_map:
            sector_values = {}
            for stock, value in position_values.items():
                sector = sector_map.get(stock, 'Unknown')
                sector_values[sector] = sector_values.get(sector, 0) + value

            if sector_values:
                max_sector = max(sector_values, key=sector_values.get)
                max_sector_pct = sector_values[max_sector] / total_value

                result['max_sector'] = max_sector
                result['max_sector_pct'] = max_sector_pct
                result['sector_distribution'] = sector_values

        return result

    def _calculate_volatility_metrics(
        self,
        returns: pd.Series
    ) -> Dict[str, float]:
        """
        计算波动率指标

        返回:
            {
                'current_volatility': 当前波动率（年化）,
                'rolling_volatility_20d': 20日滚动波动率,
                'volatility_trend': 波动率趋势（增加/稳定/减少）
            }
        """
        returns = pd.Series(returns).dropna()

        # 当前波动率（全样本）
        current_vol = returns.std() * np.sqrt(252)

        # 20日滚动波动率
        if len(returns) >= 20:
            recent_returns = returns.iloc[-20:]
            rolling_vol_20d = recent_returns.std() * np.sqrt(252)
        else:
            rolling_vol_20d = current_vol

        # 波动率趋势
        if len(returns) >= 40:
            vol_prev = returns.iloc[-40:-20].std() * np.sqrt(252)
            vol_recent = rolling_vol_20d

            if vol_recent > vol_prev * 1.2:
                trend = 'increasing'
            elif vol_recent < vol_prev * 0.8:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'unknown'

        return {
            'current_volatility': current_vol,
            'rolling_volatility_20d': rolling_vol_20d,
            'volatility_trend': trend
        }

    def _assess_overall_risk(self, risk_metrics: Dict) -> str:
        """
        评估整体风险等级

        风险评分规则：
            - 回撤: critical=3, warning=2, alert=1
            - VaR: >5%=3, >3%=2, >2%=1
            - 集中度: >30%=2, >20%=1
            - 波动率: >目标1.5倍=2, >目标1.2倍=1

        总分: >=6=critical, >=4=high, >=2=medium, <2=low
        """
        risk_score = 0

        # 回撤风险
        if risk_metrics.get('drawdown'):
            dd_level = risk_metrics['drawdown']['risk_level']
            if dd_level == 'critical':
                risk_score += 3
            elif dd_level == 'warning':
                risk_score += 2
            elif dd_level == 'alert':
                risk_score += 1

        # VaR风险
        if risk_metrics.get('var'):
            var_1day = abs(risk_metrics['var']['var_1day'])
            if var_1day > 0.05:
                risk_score += 3
            elif var_1day > 0.03:
                risk_score += 2
            elif var_1day > 0.02:
                risk_score += 1

        # 集中度风险
        if risk_metrics.get('concentration'):
            max_pos = risk_metrics['concentration']['max_position_pct']
            if max_pos > 0.30:
                risk_score += 2
            elif max_pos > 0.20:
                risk_score += 1

        # 波动率风险
        if risk_metrics.get('volatility'):
            current_vol = risk_metrics['volatility']['current_volatility']
            target_vol = self.config.get('target_volatility', 0.15)

            if current_vol > target_vol * 1.5:
                risk_score += 2
            elif current_vol > target_vol * 1.2:
                risk_score += 1

        # 评级
        if risk_score >= 6:
            return 'critical'
        elif risk_score >= 4:
            return 'high'
        elif risk_score >= 2:
            return 'medium'
        else:
            return 'low'

    def _generate_recommendations(
        self,
        risk_metrics: Dict,
        overall_risk: str
    ) -> List[str]:
        """生成风险管理建议"""
        recommendations = []

        # 整体风险建议
        if overall_risk == 'critical':
            recommendations.append(
                "🚨 风险极高，建议立即停止交易并减仓至50%以下"
            )
        elif overall_risk == 'high':
            recommendations.append(
                "⚠️ 风险较高，建议减仓30%并暂停新开仓"
            )
        elif overall_risk == 'medium':
            recommendations.append(
                "⚡ 风险中等，建议密切监控，谨慎操作"
            )

        # 回撤建议
        if risk_metrics.get('drawdown'):
            dd_info = risk_metrics['drawdown']
            if dd_info['action'] == 'reduce_50%':
                recommendations.append(
                    f"建议减仓50%，当前回撤: {dd_info['current_drawdown']:.2%}"
                )
            elif dd_info['action'] == 'stop_trading':
                recommendations.append(
                    f"建议立即停止交易，当前回撤: {dd_info['current_drawdown']:.2%}"
                )

        # 集中度建议
        if risk_metrics.get('concentration'):
            conc = risk_metrics['concentration']
            max_pos_limit = self.config.get('max_position_pct', 0.20)

            if conc['max_position_pct'] > max_pos_limit:
                recommendations.append(
                    f"建议降低 {conc['max_stock']} 的仓位至 "
                    f"{max_pos_limit:.0%} 以下"
                )

        # VaR建议
        if risk_metrics.get('var'):
            var_1day = abs(risk_metrics['var']['var_1day'])
            if var_1day > 0.03:
                recommendations.append(
                    "VaR过高，建议增加对冲或降低整体仓位"
                )

        # 波动率建议
        if risk_metrics.get('volatility'):
            vol = risk_metrics['volatility']
            target_vol = self.config.get('target_volatility', 0.15)

            if vol['current_volatility'] > target_vol * 1.5:
                # 计算建议仓位
                suggested_position = self.position_sizer.calculate_volatility_target_position(
                    vol['current_volatility'],
                    target_vol,
                    1.0
                )
                recommendations.append(
                    f"波动率过高，建议降低仓位至 {suggested_position:.0%}"
                )

        # 如果没有建议，说明风险可控
        if not recommendations:
            recommendations.append("✓ 风险可控，可以继续按策略执行")

        return recommendations

    def get_risk_report(
        self,
        portfolio_value: float,
        portfolio_returns: pd.Series,
        positions: Dict,
        prices: Dict
    ) -> str:
        """
        生成风险报告（文本格式）

        返回:
            格式化的风险报告字符串
        """
        result = self.monitor(portfolio_value, portfolio_returns, positions, prices)

        lines = []
        lines.append("=" * 60)
        lines.append("风险监控报告")
        lines.append("=" * 60)
        lines.append(f"时间: {result['timestamp']}")
        lines.append(f"组合价值: {result['portfolio_value']:,.2f}")
        lines.append(f"整体风险等级: {result['overall_risk_level'].upper()}")
        lines.append("")

        # VaR
        if result['risk_metrics'].get('var'):
            var = result['risk_metrics']['var']
            lines.append("VaR指标:")
            lines.append(f"  1日VaR: {var['var_1day']:.2%}")
            lines.append(f"  5日VaR: {var['var_5day']:.2%}")
            lines.append(f"  历史最大损失: {var['max_loss_historical']:.2%}")
            lines.append("")

        # 回撤
        if result['risk_metrics'].get('drawdown'):
            dd = result['risk_metrics']['drawdown']
            lines.append("回撤指标:")
            lines.append(f"  当前回撤: {dd['current_drawdown']:.2%}")
            lines.append(f"  峰值: {dd['peak_value']:,.2f}")
            lines.append(f"  风险等级: {dd['risk_level']}")
            lines.append("")

        # 集中度
        if result['risk_metrics'].get('concentration'):
            conc = result['risk_metrics']['concentration']
            lines.append("集中度指标:")
            lines.append(f"  持仓数量: {conc['n_positions']}")
            lines.append(f"  最大持仓: {conc['max_stock']} ({conc['max_position_pct']:.1%})")
            lines.append(f"  前5集中度: {conc['top5_concentration']:.1%}")
            lines.append("")

        # 警报
        if result['alerts']:
            lines.append("警报:")
            for alert in result['alerts']:
                lines.append(f"  [{alert['level'].upper()}] {alert['message']}")
            lines.append("")

        # 建议
        lines.append("建议:")
        for rec in result['recommendations']:
            lines.append(f"  - {rec}")

        lines.append("=" * 60)

        return "\n".join(lines)

    def reset(self):
        """重置监控器状态"""
        self.dd_controller.reset()
        self.alerts = []
        logger.info("风险监控器已重置")
