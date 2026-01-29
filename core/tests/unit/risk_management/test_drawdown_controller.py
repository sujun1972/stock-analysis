"""
回撤控制器单元测试
"""

import pytest
import pandas as pd
import numpy as np
from src.risk_management.drawdown_controller import DrawdownController


class TestDrawdownController:
    """回撤控制器测试类"""

    def test_init_valid(self):
        """测试正常初始化"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_threshold=0.80,
            alert_threshold=0.60
        )

        assert controller.max_drawdown == 0.15
        assert controller.warning_threshold == 0.80
        assert controller.alert_threshold == 0.60
        assert controller.peak_value == 0
        assert controller.current_drawdown == 0

    def test_init_invalid_thresholds(self):
        """测试无效阈值"""
        with pytest.raises(ValueError):
            DrawdownController(max_drawdown=1.5)

        with pytest.raises(ValueError):
            DrawdownController(
                max_drawdown=0.15,
                alert_threshold=0.90,  # alert > warning
                warning_threshold=0.80
            )

    def test_update_rising_value(self):
        """测试价值上涨情况"""
        controller = DrawdownController(max_drawdown=0.15)

        # 第一次更新
        result1 = controller.update(1000000)
        assert result1['peak_value'] == 1000000
        assert result1['current_drawdown'] == 0
        assert result1['risk_level'] == 'safe'

        # 价值上涨
        result2 = controller.update(1100000)
        assert result2['peak_value'] == 1100000
        assert result2['current_drawdown'] == 0
        assert result2['risk_level'] == 'safe'

    def test_update_drawdown(self):
        """测试回撤计算"""
        controller = DrawdownController(max_drawdown=0.15)

        # 设置峰值
        controller.update(1000000)

        # 下跌5%
        result = controller.update(950000)
        assert abs(result['current_drawdown'] - 0.05) < 0.001
        assert result['risk_level'] == 'safe'

    def test_alert_levels(self):
        """测试不同警报级别"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_threshold=0.80,
            alert_threshold=0.60
        )

        # 峰值
        controller.update(1000000)

        # Safe: 回撤5% (< 9%)
        result = controller.update(950000)
        assert result['risk_level'] == 'safe'

        # Alert: 回撤10% (> 9%)
        result = controller.update(900000)
        assert result['risk_level'] == 'alert'
        assert result['action'] == 'monitor_closely'

        # Warning: 回撤13% (> 12%)
        result = controller.update(870000)
        assert result['risk_level'] == 'warning'
        assert result['action'] == 'reduce_50%'

        # Critical: 回撤16% (> 15%)
        result = controller.update(840000)
        assert result['risk_level'] == 'critical'
        assert result['action'] == 'stop_trading'

    def test_alert_history(self):
        """测试警报历史记录"""
        controller = DrawdownController(max_drawdown=0.15)

        controller.update(1000000)
        controller.update(950000)  # safe, 不记录
        controller.update(870000)  # warning, 记录
        controller.update(840000)  # critical, 记录

        history = controller.get_alert_history()
        assert len(history) == 2
        assert history['risk_level'].tolist() == ['warning', 'critical']

    def test_drawdown_series(self):
        """测试回撤序列计算"""
        controller = DrawdownController()

        # 生成测试数据
        values = pd.Series([100, 110, 105, 115, 100, 120])
        dd_series = controller.calculate_drawdown_series(values)

        assert len(dd_series) == len(values)
        assert 'portfolio_value' in dd_series.columns
        assert 'peak_value' in dd_series.columns
        assert 'drawdown' in dd_series.columns
        assert 'underwater' in dd_series.columns

        # 检查峰值
        assert dd_series['peak_value'].iloc[-1] == 120

        # 检查回撤
        assert dd_series['drawdown'].iloc[2] > 0  # 从110跌到105

    def test_max_drawdown_period(self):
        """测试最大回撤期间分析"""
        controller = DrawdownController()

        # 创建有明显回撤的序列
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        values = pd.Series([100, 110, 105, 95, 90, 95, 100, 105, 110, 115], index=dates)

        result = controller.get_max_drawdown_period(values)

        assert 'max_drawdown' in result
        assert 'start_date' in result
        assert 'end_date' in result
        assert 'duration_days' in result

        # 最大回撤应该是从110跌到90
        assert result['peak_value'] == 110
        assert result['trough_value'] == 90
        assert abs(result['max_drawdown'] - (110-90)/110) < 0.001

    def test_should_reduce_position(self):
        """测试是否应该减仓"""
        controller = DrawdownController(max_drawdown=0.15)

        controller.update(1000000)

        # 小回撤，不减仓
        controller.update(950000)
        assert not controller.should_reduce_position()

        # 大回撤，应该减仓
        controller.update(870000)
        assert controller.should_reduce_position()

    def test_should_stop_trading(self):
        """测试是否应该停止交易"""
        controller = DrawdownController(max_drawdown=0.15)

        controller.update(1000000)

        # 未超过最大回撤
        controller.update(900000)
        assert not controller.should_stop_trading()

        # 超过最大回撤
        controller.update(840000)
        assert controller.should_stop_trading()

    def test_calculate_recommended_position(self):
        """测试推荐仓位计算"""
        controller = DrawdownController(max_drawdown=0.15)

        controller.update(1000000)

        # 安全范围，保持满仓
        controller.update(950000)
        pos = controller.calculate_recommended_position(1.0)
        assert pos == 1.0

        # 预警范围，开始降低仓位
        controller.update(900000)
        pos = controller.calculate_recommended_position(1.0)
        assert 0 < pos < 1.0

        # 超过最大回撤，仓位降至0
        controller.update(840000)
        pos = controller.calculate_recommended_position(1.0)
        assert pos == 0

    def test_reset(self):
        """测试重置功能"""
        controller = DrawdownController()

        controller.update(1000000)
        controller.update(900000)

        assert controller.peak_value > 0
        assert controller.current_drawdown > 0

        controller.reset()

        assert controller.peak_value == 0
        assert controller.current_drawdown == 0
        assert len(controller.alert_history) == 0

    def test_statistics(self):
        """测试统计信息"""
        controller = DrawdownController(max_drawdown=0.15)

        controller.update(1000000)
        controller.update(900000)  # alert
        controller.update(870000)  # warning
        controller.update(840000)  # critical

        stats = controller.get_statistics()

        assert 'current_drawdown' in stats
        assert 'peak_value' in stats
        assert 'n_total_alerts' in stats
        assert stats['n_total_alerts'] == 2  # warning + critical

    def test_negative_value_error(self):
        """测试负数价值错误"""
        controller = DrawdownController()

        with pytest.raises(ValueError):
            controller.update(-1000)

    def test_empty_series(self):
        """测试空序列"""
        controller = DrawdownController()

        with pytest.raises(ValueError):
            controller.calculate_drawdown_series(pd.Series([]))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
