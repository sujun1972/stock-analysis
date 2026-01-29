"""
回撤控制器

实时监控组合回撤，自动触发风控措施
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from datetime import datetime


class DrawdownController:
    """
    回撤控制器

    功能：
        1. 实时监控最大回撤
        2. 多级警报机制（预警、警告、严重）
        3. 自动触发风控动作（减仓、停止交易）
        4. 回撤恢复监控

    风险等级：
        - safe: 回撤 < 最大回撤 × 60% → 安全，继续交易
        - alert: 回撤 ≥ 最大回撤 × 60% → 预警，密切监控
        - warning: 回撤 ≥ 最大回撤 × 80% → 警告，建议减仓50%
        - critical: 回撤 ≥ 最大回撤 × 100% → 严重，立即停止交易
    """

    def __init__(
        self,
        max_drawdown: float = 0.15,      # 最大允许回撤（15%）
        warning_threshold: float = 0.80,  # 警告阈值（最大回撤的80%）
        alert_threshold: float = 0.60     # 预警阈值（最大回撤的60%）
    ):
        """
        初始化回撤控制器

        参数:
            max_drawdown: 最大允许回撤（触发停止交易）
            warning_threshold: 警告阈值（触发减仓，相对于最大回撤的比例）
            alert_threshold: 预警阈值（触发提醒，相对于最大回撤的比例）

        示例:
            >>> # 最大回撤15%，警告阈值80%（即12%），预警阈值60%（即9%）
            >>> controller = DrawdownController(
            ...     max_drawdown=0.15,
            ...     warning_threshold=0.80,
            ...     alert_threshold=0.60
            ... )
        """
        if not 0 < max_drawdown <= 1:
            raise ValueError("最大回撤必须在0和1之间")
        if not 0 < alert_threshold < warning_threshold < 1:
            raise ValueError("阈值必须满足: 0 < alert < warning < 1")

        self.max_drawdown = max_drawdown
        self.warning_threshold = warning_threshold
        self.alert_threshold = alert_threshold

        self.peak_value = 0  # 历史峰值
        self.current_drawdown = 0  # 当前回撤
        self.alert_history: List[Dict] = []  # 警报历史

        logger.info(
            f"回撤控制器初始化，最大回撤: {max_drawdown:.1%}, "
            f"警告阈值: {warning_threshold:.1%}, 预警阈值: {alert_threshold:.1%}"
        )

    def update(self, current_value: float) -> Dict[str, Any]:
        """
        更新组合价值，计算回撤

        参数:
            current_value: 当前组合价值

        返回:
            {
                'current_value': 当前价值,
                'peak_value': 峰值,
                'current_drawdown': 当前回撤（正数表示回撤）,
                'risk_level': 风险等级 ('safe'/'alert'/'warning'/'critical'),
                'action': 建议动作 ('continue'/'monitor_closely'/'reduce_50%'/'stop_trading'),
                'message': 详细说明,
                'timestamp': 时间戳
            }

        示例:
            >>> controller = DrawdownController(max_drawdown=0.15)
            >>> result = controller.update(1000000)
            >>> print(result['risk_level'])
            safe
            >>> result = controller.update(870000)  # 下跌13%
            >>> print(result['risk_level'])
            warning
        """
        if current_value < 0:
            raise ValueError("组合价值不能为负数")

        # 更新峰值
        if current_value > self.peak_value:
            self.peak_value = current_value
            logger.debug(f"组合价值创新高: {current_value:,.2f}")

        # 计算回撤
        if self.peak_value > 0:
            self.current_drawdown = (self.peak_value - current_value) / self.peak_value
        else:
            self.current_drawdown = 0

        # 评估风险等级
        risk_level, action, message = self._assess_risk()

        # 记录警报
        if risk_level in ['warning', 'critical']:
            alert = {
                'timestamp': pd.Timestamp.now(),
                'risk_level': risk_level,
                'drawdown': self.current_drawdown,
                'value': current_value,
                'peak': self.peak_value
            }
            self.alert_history.append(alert)
            logger.warning(f"触发警报: {risk_level}, 回撤: {self.current_drawdown:.2%}")

        return {
            'current_value': current_value,
            'peak_value': self.peak_value,
            'current_drawdown': self.current_drawdown,
            'risk_level': risk_level,
            'action': action,
            'message': message,
            'timestamp': pd.Timestamp.now()
        }

    def _assess_risk(self) -> Tuple[str, str, str]:
        """
        评估风险等级并推荐动作

        返回:
            (risk_level, action, message)
        """
        dd = abs(self.current_drawdown)

        if dd >= self.max_drawdown:
            # 严重：超过最大回撤
            return (
                'critical',
                'stop_trading',
                f'🚨 严重：回撤达到 {dd:.2%}，已超过限制 {self.max_drawdown:.2%}！'
                f'建议立即停止交易并清仓。'
            )
        elif dd >= self.max_drawdown * self.warning_threshold:
            # 警告：接近最大回撤
            return (
                'warning',
                'reduce_50%',
                f'⚠️ 警告：回撤达到 {dd:.2%}，接近限制 {self.max_drawdown:.2%}。'
                f'建议减仓50%降低风险。'
            )
        elif dd >= self.max_drawdown * self.alert_threshold:
            # 预警：回撤较大
            return (
                'alert',
                'monitor_closely',
                f'⚡ 预警：回撤达到 {dd:.2%}，需密切监控。'
            )
        else:
            # 安全：回撤在控制范围内
            return (
                'safe',
                'continue',
                f'✓ 安全：回撤 {dd:.2%}，风险可控。'
            )

    def calculate_drawdown_series(
        self,
        portfolio_values: pd.Series
    ) -> pd.DataFrame:
        """
        计算完整的回撤序列（用于回测分析）

        参数:
            portfolio_values: 组合价值序列

        返回:
            DataFrame with columns:
                - portfolio_value: 组合价值
                - peak_value: 滚动峰值
                - drawdown: 回撤（正数表示回撤）
                - underwater: 是否在水下（True=回撤中，False=创新高）

        示例:
            >>> values = pd.Series([100, 110, 105, 115, 100],
            ...                    index=pd.date_range('2024-01-01', periods=5))
            >>> dd_series = controller.calculate_drawdown_series(values)
            >>> print(dd_series)
        """
        if portfolio_values.empty:
            raise ValueError("组合价值序列不能为空")

        df = pd.DataFrame()
        df['portfolio_value'] = portfolio_values
        df['peak_value'] = portfolio_values.expanding().max()
        df['drawdown'] = (df['peak_value'] - df['portfolio_value']) / df['peak_value']
        df['underwater'] = df['drawdown'] > 0

        return df

    def get_max_drawdown_period(
        self,
        portfolio_values: pd.Series
    ) -> Dict[str, Any]:
        """
        找出最大回撤期间的详细信息

        参数:
            portfolio_values: 组合价值序列

        返回:
            {
                'max_drawdown': 最大回撤,
                'start_date': 峰值日期,
                'end_date': 谷底日期,
                'recovery_date': 恢复日期（如果已恢复）,
                'duration_days': 持续天数,
                'peak_value': 峰值,
                'trough_value': 谷底值
            }

        示例:
            >>> result = controller.get_max_drawdown_period(portfolio_values)
            >>> print(f"最大回撤: {result['max_drawdown']:.2%}")
            >>> print(f"持续天数: {result['duration_days']}")
        """
        dd_series = self.calculate_drawdown_series(portfolio_values)

        max_dd = dd_series['drawdown'].max()
        max_dd_date = dd_series['drawdown'].idxmax()

        # 找到峰值日期（最大回撤之前的最高点）
        peak_date = dd_series.loc[:max_dd_date, 'peak_value'].idxmax()
        peak_value = dd_series.loc[peak_date, 'peak_value']
        trough_value = dd_series.loc[max_dd_date, 'portfolio_value']

        # 找到恢复日期（最大回撤之后第一次回到峰值）
        recovery_dates = dd_series.loc[max_dd_date:][dd_series['drawdown'] <= 0]
        recovery_date = recovery_dates.index[0] if len(recovery_dates) > 0 else None

        # 计算持续天数
        duration = (max_dd_date - peak_date).days if hasattr(max_dd_date, 'days') else 0

        logger.info(
            f"最大回撤分析: {max_dd:.2%}, "
            f"开始: {peak_date}, 谷底: {max_dd_date}, "
            f"持续: {duration}天"
        )

        return {
            'max_drawdown': max_dd,
            'start_date': peak_date,
            'end_date': max_dd_date,
            'recovery_date': recovery_date,
            'duration_days': duration,
            'peak_value': peak_value,
            'trough_value': trough_value
        }

    def get_alert_history(self) -> pd.DataFrame:
        """
        获取警报历史记录

        返回:
            DataFrame with alert history
        """
        if not self.alert_history:
            return pd.DataFrame()

        df = pd.DataFrame(self.alert_history)
        return df

    def reset(self):
        """
        重置回撤控制器状态

        用于开始新的回测或实盘周期
        """
        self.peak_value = 0
        self.current_drawdown = 0
        self.alert_history = []
        logger.info("回撤控制器已重置")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取回撤统计信息

        返回:
            {
                'current_drawdown': 当前回撤,
                'peak_value': 峰值,
                'n_alerts': 警报次数,
                'n_warnings': 警告次数,
                'n_criticals': 严重警报次数
            }
        """
        n_alerts = sum(1 for a in self.alert_history if a['risk_level'] == 'alert')
        n_warnings = sum(1 for a in self.alert_history if a['risk_level'] == 'warning')
        n_criticals = sum(1 for a in self.alert_history if a['risk_level'] == 'critical')

        return {
            'current_drawdown': self.current_drawdown,
            'peak_value': self.peak_value,
            'n_total_alerts': len(self.alert_history),
            'n_alerts': n_alerts,
            'n_warnings': n_warnings,
            'n_criticals': n_criticals
        }

    def should_reduce_position(self) -> bool:
        """
        判断是否应该减仓

        返回:
            True if should reduce position
        """
        dd = abs(self.current_drawdown)
        return dd >= self.max_drawdown * self.warning_threshold

    def should_stop_trading(self) -> bool:
        """
        判断是否应该停止交易

        返回:
            True if should stop trading
        """
        dd = abs(self.current_drawdown)
        return dd >= self.max_drawdown

    def calculate_recommended_position(
        self,
        current_position: float = 1.0
    ) -> float:
        """
        根据当前回撤计算推荐仓位

        方法：
            - 回撤 < 60%阈值: 保持当前仓位
            - 回撤 ≥ 60%阈值: 线性降低仓位
            - 回撤 ≥ 100%: 仓位降至0

        参数:
            current_position: 当前仓位（1.0=满仓）

        返回:
            推荐仓位（0-1）

        示例:
            >>> controller = DrawdownController(max_drawdown=0.15)
            >>> controller.current_drawdown = 0.10  # 回撤10%
            >>> pos = controller.calculate_recommended_position(1.0)
            >>> print(f"推荐仓位: {pos:.1%}")
        """
        dd = abs(self.current_drawdown)

        if dd >= self.max_drawdown:
            # 超过最大回撤，仓位降至0
            return 0.0

        elif dd >= self.max_drawdown * self.alert_threshold:
            # 在预警阈值以上，线性降低仓位
            # 从预警阈值的100%仓位降至最大回撤的0%仓位
            alert_dd = self.max_drawdown * self.alert_threshold
            max_dd = self.max_drawdown

            # 线性插值
            factor = 1.0 - (dd - alert_dd) / (max_dd - alert_dd)
            recommended = current_position * factor

            return max(0.0, min(recommended, current_position))

        else:
            # 安全范围，保持当前仓位
            return current_position
