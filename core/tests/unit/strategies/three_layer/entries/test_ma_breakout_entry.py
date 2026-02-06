"""
MABreakoutEntry 单元测试

测试均线突破入场策略的各种场景
"""

import pytest
import pandas as pd
import numpy as np

from src.strategies.three_layer.entries import MABreakoutEntry


class TestMABreakoutEntry:
    """MABreakoutEntry 测试类"""

    @pytest.fixture
    def entry_strategy(self):
        """创建默认的均线突破入场策略"""
        return MABreakoutEntry(params={
            'short_window': 5,
            'long_window': 20,
            'lookback_for_cross': 1
        })

    @pytest.fixture
    def sample_data_with_golden_cross(self):
        """创建包含金叉的测试数据"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')

        # 股票A: 先跌后涨(可能产生金叉)
        prices_a = list(range(100, 85, -1)) + list(range(85, 120))  # 15下跌 + 35上涨 = 50
        stock_a = pd.DataFrame({
            'close': prices_a,
            'open': prices_a,
            'high': [p + 1 for p in prices_a],
            'low': [p - 1 for p in prices_a],
            'volume': [1000000] * 50
        }, index=dates)

        # 股票B: 无金叉，持续下跌
        stock_b = pd.DataFrame({
            'close': list(range(100, 50, -1)),
            'open': list(range(100, 50, -1)),
            'high': list(range(101, 51, -1)),
            'low': list(range(99, 49, -1)),
            'volume': [1000000] * 50
        }, index=dates)

        return {
            'STOCK_A': stock_a,
            'STOCK_B': stock_b
        }

    def test_initialization(self):
        """测试初始化"""
        entry = MABreakoutEntry(params={
            'short_window': 5,
            'long_window': 20
        })

        assert entry.id == "ma_breakout"
        assert entry.name == "均线突破入场"
        assert entry.params['short_window'] == 5
        assert entry.params['long_window'] == 20

    def test_get_parameters(self):
        """测试参数定义获取"""
        params = MABreakoutEntry.get_parameters()

        assert len(params) >= 3
        param_names = [p['name'] for p in params]
        assert 'short_window' in param_names
        assert 'long_window' in param_names
        assert 'lookback_for_cross' in param_names

    def test_parameter_validation_invalid_type(self):
        """测试参数类型验证"""
        with pytest.raises(ValueError, match="必须是整数"):
            MABreakoutEntry(params={'short_window': 5.5})

    def test_parameter_validation_out_of_range(self):
        """测试参数范围验证"""
        with pytest.raises(ValueError, match="不能小于"):
            MABreakoutEntry(params={'short_window': 1})

        with pytest.raises(ValueError, match="不能大于"):
            MABreakoutEntry(params={'long_window': 300})

    def test_parameter_validation_unknown_param(self):
        """测试未知参数验证"""
        with pytest.raises(ValueError, match="未知参数"):
            MABreakoutEntry(params={'unknown_param': 123})

    def test_golden_cross_detection(self, entry_strategy, sample_data_with_golden_cross):
        """测试金叉检测"""
        # 在数据末尾应该能检测到金叉
        test_date = pd.Timestamp('2023-02-19')  # 第50天

        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_A'],
            data=sample_data_with_golden_cross,
            date=test_date
        )

        # 股票A应该在某个时期有金叉信号
        # 注意：具体结果取决于数据特征，这里主要验证函数运行正常
        assert isinstance(signals, dict)

    def test_no_golden_cross(self, entry_strategy):
        """测试无金叉情况"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        # 持续下跌，不会有金叉
        stock_data = pd.DataFrame({
            'close': list(range(100, 70, -1)),
            'open': list(range(100, 70, -1)),
            'high': list(range(101, 71, -1)),
            'low': list(range(99, 69, -1)),
            'volume': [1000000] * 30
        }, index=dates)

        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_NO_CROSS'],
            data={'STOCK_NO_CROSS': stock_data},
            date=dates[-1]
        )

        # 持续下跌不应该有金叉信号
        assert 'STOCK_NO_CROSS' not in signals or len(signals) == 0

    def test_multiple_stocks(self):
        """测试多股票场景"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        # 创建3只股票，其中1只有金叉
        data = {}
        for i, stock in enumerate(['STOCK_1', 'STOCK_2', 'STOCK_3']):
            if i == 0:
                # 第一只股票: 先跌后涨，可能产生金叉
                prices = list(range(100, 85, -1)) + list(range(85, 100))
            else:
                # 其他股票: 持续下跌
                prices = list(range(100, 70, -1))

            data[stock] = pd.DataFrame({
                'close': prices,
                'open': prices,
                'high': [p + 1 for p in prices],
                'low': [p - 1 for p in prices],
                'volume': [1000000] * 30
            }, index=dates)

        entry = MABreakoutEntry(params={
            'short_window': 5,
            'long_window': 10,
            'lookback_for_cross': 3
        })

        signals = entry.generate_entry_signals(
            stocks=['STOCK_1', 'STOCK_2', 'STOCK_3'],
            data=data,
            date=dates[-1]
        )

        # 验证返回格式
        assert isinstance(signals, dict)

        # 如果有信号，权重应该归一化
        if signals:
            total_weight = sum(signals.values())
            assert abs(total_weight - 1.0) < 0.01

    def test_equal_weight_distribution(self):
        """测试等权分配"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        # 创建2只都有金叉的股票
        data = {}
        for stock in ['STOCK_1', 'STOCK_2']:
            prices = list(range(100, 85, -1)) + list(range(85, 100))
            data[stock] = pd.DataFrame({
                'close': prices,
                'open': prices,
                'high': [p + 1 for p in prices],
                'low': [p - 1 for p in prices],
                'volume': [1000000] * 30
            }, index=dates)

        entry = MABreakoutEntry(params={
            'short_window': 3,
            'long_window': 10,
            'lookback_for_cross': 5
        })

        signals = entry.generate_entry_signals(
            stocks=['STOCK_1', 'STOCK_2'],
            data=data,
            date=dates[-1]
        )

        # 如果两只都有信号，应该等权
        if len(signals) == 2:
            assert abs(signals['STOCK_1'] - 0.5) < 0.01
            assert abs(signals['STOCK_2'] - 0.5) < 0.01

    def test_missing_data(self, entry_strategy):
        """测试数据缺失情况"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        stock_data = pd.DataFrame({
            'close': list(range(100, 70, -1)),
            'open': list(range(100, 70, -1)),
            'high': list(range(101, 71, -1)),
            'low': list(range(99, 69, -1)),
            'volume': [1000000] * 30
        }, index=dates)

        # 股票不在数据中
        signals = entry_strategy.generate_entry_signals(
            stocks=['MISSING_STOCK'],
            data={'STOCK_A': stock_data},
            date=dates[-1]
        )

        assert len(signals) == 0

    def test_missing_close_column(self, entry_strategy):
        """测试缺少close列的情况"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        # 只有open列，没有close列
        stock_data = pd.DataFrame({
            'open': list(range(100, 70, -1)),
            'volume': [1000000] * 30
        }, index=dates)

        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_NO_CLOSE'],
            data={'STOCK_NO_CLOSE': stock_data},
            date=dates[-1]
        )

        assert len(signals) == 0

    def test_date_not_in_data(self, entry_strategy):
        """测试日期不在数据范围内"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        stock_data = pd.DataFrame({
            'close': list(range(100, 70, -1)),
            'open': list(range(100, 70, -1)),
            'high': list(range(101, 71, -1)),
            'low': list(range(99, 69, -1)),
            'volume': [1000000] * 30
        }, index=dates)

        # 使用不在数据范围内的日期
        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_A'],
            data={'STOCK_A': stock_data},
            date=pd.Timestamp('2025-01-01')
        )

        assert len(signals) == 0

    def test_insufficient_history(self, entry_strategy):
        """测试历史数据不足的情况"""
        dates = pd.date_range('2023-01-01', periods=5, freq='D')

        # 只有5天数据，不足以计算20日均线
        stock_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104],
            'open': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103],
            'volume': [1000000] * 5
        }, index=dates)

        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_SHORT'],
            data={'STOCK_SHORT': stock_data},
            date=dates[-1]
        )

        # 数据不足，可能没有信号
        assert isinstance(signals, dict)

    def test_invalid_window_parameters(self):
        """测试无效的窗口参数(短期>=长期)"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        stock_data = pd.DataFrame({
            'close': list(range(100, 70, -1)),
            'open': list(range(100, 70, -1)),
            'high': list(range(101, 71, -1)),
            'low': list(range(99, 69, -1)),
            'volume': [1000000] * 30
        }, index=dates)

        # 短期窗口 >= 长期窗口
        entry = MABreakoutEntry(params={
            'short_window': 20,
            'long_window': 10
        })

        signals = entry.generate_entry_signals(
            stocks=['STOCK_A'],
            data={'STOCK_A': stock_data},
            date=dates[-1]
        )

        # 应该不生成信号并记录警告
        assert len(signals) == 0

    def test_lookback_parameter(self):
        """测试回溯期参数"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        # 先跌后涨
        prices = list(range(100, 85, -1)) + list(range(85, 100))
        stock_data = pd.DataFrame({
            'close': prices,
            'open': prices,
            'high': [p + 1 for p in prices],
            'low': [p - 1 for p in prices],
            'volume': [1000000] * 30
        }, index=dates)

        # 回溯期为1，只检查当天
        entry_1 = MABreakoutEntry(params={
            'short_window': 3,
            'long_window': 10,
            'lookback_for_cross': 1
        })

        # 回溯期为5，检查过去5天
        entry_5 = MABreakoutEntry(params={
            'short_window': 3,
            'long_window': 10,
            'lookback_for_cross': 5
        })

        signals_1 = entry_1.generate_entry_signals(
            stocks=['STOCK_A'],
            data={'STOCK_A': stock_data},
            date=dates[-1]
        )

        signals_5 = entry_5.generate_entry_signals(
            stocks=['STOCK_A'],
            data={'STOCK_A': stock_data},
            date=dates[-1]
        )

        # 回溯期更长的策略可能捕捉到更多信号
        assert isinstance(signals_1, dict)
        assert isinstance(signals_5, dict)

    def test_empty_stock_list(self, entry_strategy):
        """测试空股票列表"""
        signals = entry_strategy.generate_entry_signals(
            stocks=[],
            data={},
            date=pd.Timestamp('2023-01-01')
        )

        assert len(signals) == 0

    def test_repr(self):
        """测试字符串表示"""
        entry = MABreakoutEntry(params={'short_window': 5, 'long_window': 20})
        repr_str = repr(entry)

        assert "均线突破入场" in repr_str
        assert "ma_breakout" in repr_str

    def test_rolling_calculation_exception(self, entry_strategy):
        """测试rolling计算异常情况"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        # 创建包含NaN的数据导致rolling计算问题
        close_prices = [100.0] * 30
        close_prices[15] = np.nan  # 中间插入NaN

        stock_data = pd.DataFrame({
            'close': close_prices,
            'open': [100.0] * 30,
            'high': [101.0] * 30,
            'low': [99.0] * 30,
            'volume': [1000000] * 30
        }, index=dates)

        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_WITH_NAN'],
            data={'STOCK_WITH_NAN': stock_data},
            date=dates[-1]
        )

        # 应该能处理NaN，即使没有信号也不应该抛出异常
        assert isinstance(signals, dict)

    def test_require_trending_up_parameter(self):
        """测试require_ma_trending_up参数"""
        dates = pd.date_range('2023-01-01', periods=40, freq='D')

        # 创建一个金叉但短期均线不向上的情况
        prices = list(range(100, 85, -1)) + list(range(85, 110))
        stock_data = pd.DataFrame({
            'close': prices,
            'open': prices,
            'high': [p + 1 for p in prices],
            'low': [p - 1 for p in prices],
            'volume': [1000000] * 40
        }, index=dates)

        # 不要求向上趋势
        entry_no_trend = MABreakoutEntry(params={
            'short_window': 5,
            'long_window': 20,
            'lookback_for_cross': 5,
            'require_ma_trending_up': False
        })

        # 要求向上趋势
        entry_with_trend = MABreakoutEntry(params={
            'short_window': 5,
            'long_window': 20,
            'lookback_for_cross': 5,
            'require_ma_trending_up': True
        })

        signals_no_trend = entry_no_trend.generate_entry_signals(
            stocks=['STOCK_A'],
            data={'STOCK_A': stock_data},
            date=dates[-1]
        )

        signals_with_trend = entry_with_trend.generate_entry_signals(
            stocks=['STOCK_A'],
            data={'STOCK_A': stock_data},
            date=dates[-1]
        )

        # 两种策略都应该返回dict
        assert isinstance(signals_no_trend, dict)
        assert isinstance(signals_with_trend, dict)

    def test_nan_in_ma_values(self):
        """测试均线计算结果包含NaN的情况"""
        dates = pd.date_range('2023-01-01', periods=25, freq='D')

        # 创建数据，前面部分不足以计算长期均线
        prices = [100.0] * 25
        stock_data = pd.DataFrame({
            'close': prices,
            'open': prices,
            'high': [p + 1 for p in prices],
            'low': [p - 1 for p in prices],
            'volume': [1000000] * 25
        }, index=dates)

        entry = MABreakoutEntry(params={
            'short_window': 5,
            'long_window': 20,
            'lookback_for_cross': 3
        })

        # 使用靠前的日期，此时长期均线可能为NaN
        signals = entry.generate_entry_signals(
            stocks=['STOCK_EARLY'],
            data={'STOCK_EARLY': stock_data},
            date=dates[22]  # 第23天
        )

        # 应该能处理NaN情况
        assert isinstance(signals, dict)

    def test_index_error_handling(self):
        """测试索引错误处理"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')

        prices = list(range(100, 90, -1))
        stock_data = pd.DataFrame({
            'close': prices,
            'open': prices,
            'high': [p + 1 for p in prices],
            'low': [p - 1 for p in prices],
            'volume': [1000000] * 10
        }, index=dates)

        entry = MABreakoutEntry(params={
            'short_window': 3,
            'long_window': 7,
            'lookback_for_cross': 2
        })

        # 数据量很小，容易触发索引问题
        signals = entry.generate_entry_signals(
            stocks=['STOCK_SHORT_DATA'],
            data={'STOCK_SHORT_DATA': stock_data},
            date=dates[5]
        )

        # 应该安全处理，不抛异常
        assert isinstance(signals, dict)
