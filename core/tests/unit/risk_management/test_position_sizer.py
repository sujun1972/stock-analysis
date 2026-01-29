"""
仓位计算器单元测试
"""

import pytest
import pandas as pd
import numpy as np
from src.risk_management.position_sizer import PositionSizer


class TestPositionSizer:
    """仓位计算器测试类"""

    @pytest.fixture
    def sample_returns(self):
        """生成测试用收益率数据"""
        np.random.seed(42)
        returns_df = pd.DataFrame({
            'stock_A': np.random.normal(0.001, 0.02, 100),
            'stock_B': np.random.normal(0.0015, 0.03, 100),
            'stock_C': np.random.normal(0.0008, 0.015, 100)
        })
        return returns_df

    def test_init(self):
        """测试初始化"""
        sizer = PositionSizer()
        assert sizer is not None

    def test_equal_weight(self):
        """测试等权重分配"""
        sizer = PositionSizer()

        # 5只股票，无限制
        weights = sizer.calculate_equal_weight(5, max_position=1.0)
        assert len(weights) == 5
        assert all(abs(w - 0.2) < 0.001 for w in weights.values())

        # 5只股票，限制20%
        weights = sizer.calculate_equal_weight(5, max_position=0.2)
        assert all(w <= 0.2 for w in weights.values())

        # 3只股票，限制20%
        weights = sizer.calculate_equal_weight(3, max_position=0.2)
        assert all(w == 0.2 for w in weights.values())

    def test_equal_weight_invalid_inputs(self):
        """测试等权重的无效输入"""
        sizer = PositionSizer()

        with pytest.raises(ValueError):
            sizer.calculate_equal_weight(0)

        with pytest.raises(ValueError):
            sizer.calculate_equal_weight(5, max_position=1.5)

    def test_kelly_position(self):
        """测试凯利公式"""
        sizer = PositionSizer()

        # 胜率60%，平均赚3%，平均亏2%
        position = sizer.calculate_kelly_position(
            win_rate=0.6,
            avg_win=0.03,
            avg_loss=0.02,
            max_position=0.2,
            fractional_kelly=0.5
        )

        assert 0 <= position <= 0.2
        assert position > 0  # 期望为正，应该有仓位

        # 胜率40%，平均赚2%，平均亏3%（期望为负）
        position = sizer.calculate_kelly_position(
            win_rate=0.4,
            avg_win=0.02,
            avg_loss=0.03,
            max_position=0.2,
            fractional_kelly=0.5
        )

        assert position == 0  # 期望为负，不建仓

    def test_kelly_from_trades(self):
        """测试从交易记录计算凯利仓位"""
        sizer = PositionSizer()

        # 构造有明显盈利的交易记录
        trades = pd.Series([0.02, -0.01, 0.03, -0.01, 0.02, 0.015, -0.005])
        position = sizer.calculate_kelly_position_from_trades(trades)

        assert 0 <= position <= 0.2
        assert position > 0

    def test_kelly_invalid_inputs(self):
        """测试凯利公式的无效输入"""
        sizer = PositionSizer()

        with pytest.raises(ValueError):
            sizer.calculate_kelly_position(1.5, 0.03, 0.02)  # 胜率>1

        with pytest.raises(ValueError):
            sizer.calculate_kelly_position(0.6, -0.03, 0.02)  # 平均盈利<0

    def test_risk_parity_weights(self, sample_returns):
        """测试风险平价权重"""
        sizer = PositionSizer()

        weights = sizer.calculate_risk_parity_weights(sample_returns)

        assert len(weights) == 3
        assert abs(weights.sum() - 1.0) < 0.001  # 权重和应该为1

        # 波动率低的股票应该有更高权重
        volatilities = sample_returns.std()
        lowest_vol_stock = volatilities.idxmin()
        assert weights[lowest_vol_stock] == weights.max()

    def test_volatility_target_position(self):
        """测试波动率目标仓位"""
        sizer = PositionSizer()

        # 当前波动率20%，目标15%，满仓
        new_pos = sizer.calculate_volatility_target_position(
            current_volatility=0.20,
            target_volatility=0.15,
            current_position=1.0
        )

        assert abs(new_pos - 0.75) < 0.001  # 应该减仓到75%

        # 当前波动率10%，目标15%，满仓
        new_pos = sizer.calculate_volatility_target_position(
            current_volatility=0.10,
            target_volatility=0.15,
            current_position=1.0
        )

        assert abs(new_pos - 1.5) < 0.001  # 应该加仓到150%（如果允许杠杆）

        # 当前波动率很低，但限制杠杆
        new_pos = sizer.calculate_volatility_target_position(
            current_volatility=0.05,
            target_volatility=0.15,
            current_position=1.0,
            max_leverage=1.5
        )

        assert abs(new_pos - 1.5) < 0.001  # 被限制在最大杠杆

    def test_max_sharpe_weights(self, sample_returns):
        """测试最大夏普比率权重"""
        sizer = PositionSizer()

        try:
            weights = sizer.calculate_max_sharpe_weights(
                sample_returns,
                risk_free_rate=0.03,
                max_position=0.5
            )

            assert len(weights) == 3
            assert abs(weights.sum() - 1.0) < 0.01  # 权重和接近1
            assert all(weights >= 0)  # 无做空
            assert all(weights <= 0.5)  # 满足最大仓位限制

        except ImportError:
            pytest.skip("需要scipy库")

    def test_minimum_variance_weights(self, sample_returns):
        """测试最小方差权重"""
        sizer = PositionSizer()

        try:
            weights = sizer.calculate_minimum_variance_weights(
                sample_returns,
                max_position=0.5
            )

            assert len(weights) == 3
            assert abs(weights.sum() - 1.0) < 0.01
            assert all(weights >= 0)
            assert all(weights <= 0.5)

            # 波动率最低的股票应该有较高权重
            volatilities = sample_returns.std()
            lowest_vol_stock = volatilities.idxmin()
            assert weights[lowest_vol_stock] > weights.mean()

        except ImportError:
            pytest.skip("需要scipy库")

    def test_compare_methods(self, sample_returns):
        """测试方法比较"""
        sizer = PositionSizer()

        comparison = sizer.compare_methods(
            sample_returns,
            methods=['equal_weight', 'risk_parity']
        )

        assert isinstance(comparison, pd.DataFrame)
        assert 'method' in comparison.columns
        assert 'annual_return' in comparison.columns
        assert 'annual_volatility' in comparison.columns
        assert 'sharpe_ratio' in comparison.columns

        assert len(comparison) >= 2

    def test_empty_returns(self):
        """测试空收益率"""
        sizer = PositionSizer()

        with pytest.raises(ValueError):
            sizer.calculate_risk_parity_weights(pd.DataFrame())

    def test_kelly_no_wins_or_losses(self):
        """测试只有盈利或只有亏损的交易"""
        sizer = PositionSizer()

        # 只有盈利
        only_wins = pd.Series([0.01, 0.02, 0.015, 0.03])
        position = sizer.calculate_kelly_position_from_trades(only_wins)
        assert position > 0  # 应该给一个保守仓位

        # 只有亏损
        only_losses = pd.Series([-0.01, -0.02, -0.015, -0.03])
        position = sizer.calculate_kelly_position_from_trades(only_losses)
        # 应该给一个保守仓位或0

    def test_zero_volatility_handling(self):
        """测试零波动率处理"""
        sizer = PositionSizer()

        # 构造一个股票波动率为0的情况
        returns_df = pd.DataFrame({
            'stock_A': np.random.normal(0.001, 0.02, 100),
            'stock_B': [0.001] * 100  # 恒定收益
        })

        # 应该能处理而不报错
        weights = sizer.calculate_risk_parity_weights(returns_df)
        assert len(weights) == 2
        assert abs(weights.sum() - 1.0) < 0.001


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
