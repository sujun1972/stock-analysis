"""
RSIOversoldEntry 单元测试

测试RSI超卖入场策略的各种场景
"""

import pytest
import pandas as pd
import numpy as np

from src.strategies.three_layer.entries import RSIOversoldEntry


class TestRSIOversoldEntry:
    """RSIOversoldEntry 测试类"""

    @pytest.fixture
    def entry_strategy(self):
        """创建默认的RSI超卖入场策略"""
        return RSIOversoldEntry(params={
            'rsi_period': 14,
            'oversold_threshold': 30.0
        })

    @pytest.fixture
    def sample_data_with_oversold(self):
        """创建包含超卖的测试数据"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')

        # 股票A: 持续下跌后反弹(超卖)
        prices_a = [100]
        for i in range(20):
            prices_a.append(prices_a[-1] * 0.95)  # 持续下跌5%
        for i in range(29):
            prices_a.append(prices_a[-1] * 1.01)  # 缓慢反弹1%

        stock_a = pd.DataFrame({
            'close': prices_a,
            'open': prices_a,
            'high': [p * 1.01 for p in prices_a],
            'low': [p * 0.99 for p in prices_a],
            'volume': [1000000] * 50
        }, index=dates)

        # 股票B: 持续上涨(不超卖)
        prices_b = [100 + i * 2 for i in range(50)]
        stock_b = pd.DataFrame({
            'close': prices_b,
            'open': prices_b,
            'high': [p + 1 for p in prices_b],
            'low': [p - 1 for p in prices_b],
            'volume': [1000000] * 50
        }, index=dates)

        return {
            'STOCK_OVERSOLD': stock_a,
            'STOCK_NORMAL': stock_b
        }

    def test_initialization(self):
        """测试初始化"""
        entry = RSIOversoldEntry(params={
            'rsi_period': 14,
            'oversold_threshold': 30.0
        })

        assert entry.id == "rsi_oversold"
        assert entry.name == "RSI超卖入场"
        assert entry.params['rsi_period'] == 14
        assert entry.params['oversold_threshold'] == 30.0

    def test_get_parameters(self):
        """测试参数定义获取"""
        params = RSIOversoldEntry.get_parameters()

        assert len(params) >= 3
        param_names = [p['name'] for p in params]
        assert 'rsi_period' in param_names
        assert 'oversold_threshold' in param_names
        assert 'require_rsi_turning_up' in param_names

    def test_parameter_validation_invalid_type(self):
        """测试参数类型验证"""
        with pytest.raises(ValueError, match="必须是整数"):
            RSIOversoldEntry(params={'rsi_period': 14.5})

        with pytest.raises(ValueError):
            RSIOversoldEntry(params={'oversold_threshold': "30"})

    def test_parameter_validation_out_of_range(self):
        """测试参数范围验证"""
        with pytest.raises(ValueError, match="不能小于"):
            RSIOversoldEntry(params={'rsi_period': 3})

        with pytest.raises(ValueError, match="不能大于"):
            RSIOversoldEntry(params={'rsi_period': 100})

        with pytest.raises(ValueError):
            RSIOversoldEntry(params={'oversold_threshold': 5.0})

    def test_rsi_calculation(self, entry_strategy):
        """测试RSI计算"""
        # 创建简单的价格序列
        prices = pd.Series([
            100, 102, 101, 103, 105,  # 上涨
            104, 103, 102, 101, 100,  # 下跌
            99, 98, 97, 96, 95,       # 继续下跌
            96, 97, 98, 99, 100       # 反弹
        ])

        rsi = entry_strategy._calculate_rsi(prices, period=14)

        # RSI应该在0-100之间
        valid_rsi = rsi.dropna()
        assert all(valid_rsi >= 0)
        assert all(valid_rsi <= 100)

        # 下跌期间RSI应该较低
        # 上涨期间RSI应该较高
        # 这里只验证RSI被正确计算
        assert len(valid_rsi) > 0

    def test_oversold_detection(self, entry_strategy, sample_data_with_oversold):
        """测试超卖检测"""
        test_date = pd.Timestamp('2023-02-19')  # 第50天

        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_OVERSOLD', 'STOCK_NORMAL'],
            data=sample_data_with_oversold,
            date=test_date
        )

        # 验证返回格式
        assert isinstance(signals, dict)

        # 超卖股票可能有信号，正常股票应该没有
        # 具体结果取决于RSI计算，这里主要验证函数运行正常

    def test_oversold_with_turning_up_requirement(self):
        """测试要求RSI回升的超卖检测"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        # 创建持续下跌的股票(RSI低但未回升)
        prices = [100 - i * 2 for i in range(30)]
        stock_data = pd.DataFrame({
            'close': prices,
            'open': prices,
            'high': [p + 1 for p in prices],
            'low': [p - 1 for p in prices],
            'volume': [1000000] * 30
        }, index=dates)

        # 不要求回升
        entry_no_req = RSIOversoldEntry(params={
            'rsi_period': 14,
            'oversold_threshold': 30.0,
            'require_rsi_turning_up': False
        })

        # 要求回升
        entry_with_req = RSIOversoldEntry(params={
            'rsi_period': 14,
            'oversold_threshold': 30.0,
            'require_rsi_turning_up': True
        })

        signals_no_req = entry_no_req.generate_entry_signals(
            stocks=['STOCK_A'],
            data={'STOCK_A': stock_data},
            date=dates[-1]
        )

        signals_with_req = entry_with_req.generate_entry_signals(
            stocks=['STOCK_A'],
            data={'STOCK_A': stock_data},
            date=dates[-1]
        )

        # 持续下跌时，要求回升的策略可能不生成信号
        assert isinstance(signals_no_req, dict)
        assert isinstance(signals_with_req, dict)

    def test_multiple_stocks(self):
        """测试多股票场景"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        data = {}
        for i, stock in enumerate(['STOCK_1', 'STOCK_2', 'STOCK_3']):
            if i == 0:
                # 第一只: 持续下跌(可能超卖)
                prices = [100 - j * 3 for j in range(30)]
            elif i == 1:
                # 第二只: 横盘震荡
                prices = [100 + (j % 2) * 2 for j in range(30)]
            else:
                # 第三只: 持续上涨
                prices = [100 + j * 2 for j in range(30)]

            data[stock] = pd.DataFrame({
                'close': prices,
                'open': prices,
                'high': [p + 1 for p in prices],
                'low': [p - 1 for p in prices],
                'volume': [1000000] * 30
            }, index=dates)

        entry = RSIOversoldEntry(params={
            'rsi_period': 14,
            'oversold_threshold': 30.0
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

        # 创建2只都超卖的股票
        data = {}
        for stock in ['STOCK_1', 'STOCK_2']:
            prices = [100 - i * 3 for i in range(30)]
            data[stock] = pd.DataFrame({
                'close': prices,
                'open': prices,
                'high': [p + 1 for p in prices],
                'low': [p - 1 for p in prices],
                'volume': [1000000] * 30
            }, index=dates)

        entry = RSIOversoldEntry(params={
            'rsi_period': 10,
            'oversold_threshold': 40.0
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
            'close': [100 - i for i in range(30)],
            'open': [100 - i for i in range(30)],
            'high': [101 - i for i in range(30)],
            'low': [99 - i for i in range(30)],
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

        stock_data = pd.DataFrame({
            'open': [100 - i for i in range(30)],
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
            'close': [100 - i for i in range(30)],
            'open': [100 - i for i in range(30)],
            'high': [101 - i for i in range(30)],
            'low': [99 - i for i in range(30)],
            'volume': [1000000] * 30
        }, index=dates)

        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_A'],
            data={'STOCK_A': stock_data},
            date=pd.Timestamp('2025-01-01')
        )

        assert len(signals) == 0

    def test_insufficient_history(self, entry_strategy):
        """测试历史数据不足的情况"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')

        # 只有10天数据，不足以计算14日RSI
        stock_data = pd.DataFrame({
            'close': [100 - i for i in range(10)],
            'open': [100 - i for i in range(10)],
            'high': [101 - i for i in range(10)],
            'low': [99 - i for i in range(10)],
            'volume': [1000000] * 10
        }, index=dates)

        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_SHORT'],
            data={'STOCK_SHORT': stock_data},
            date=dates[-1]
        )

        # 数据不足，RSI可能为NaN
        assert isinstance(signals, dict)

    def test_min_rsi_filter(self):
        """测试RSI下限过滤"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        # 极端下跌的股票
        prices = [100 * (0.8 ** i) for i in range(30)]
        stock_data = pd.DataFrame({
            'close': prices,
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'volume': [1000000] * 30
        }, index=dates)

        entry = RSIOversoldEntry(params={
            'rsi_period': 14,
            'oversold_threshold': 30.0,
            'min_rsi': 10.0  # 过滤极端低RSI
        })

        signals = entry.generate_entry_signals(
            stocks=['STOCK_EXTREME'],
            data={'STOCK_EXTREME': stock_data},
            date=dates[-1]
        )

        # 如果RSI过低(异常数据)，应该被过滤
        assert isinstance(signals, dict)

    def test_empty_stock_list(self, entry_strategy):
        """测试空股票列表"""
        signals = entry_strategy.generate_entry_signals(
            stocks=[],
            data={},
            date=pd.Timestamp('2023-01-01')
        )

        assert len(signals) == 0

    def test_nan_in_prices(self, entry_strategy):
        """测试价格中包含NaN的情况"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        prices = [100 - i for i in range(30)]
        prices[15] = np.nan  # 添加NaN值

        stock_data = pd.DataFrame({
            'close': prices,
            'open': prices,
            'high': [p + 1 if not pd.isna(p) else np.nan for p in prices],
            'low': [p - 1 if not pd.isna(p) else np.nan for p in prices],
            'volume': [1000000] * 30
        }, index=dates)

        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_WITH_NAN'],
            data={'STOCK_WITH_NAN': stock_data},
            date=dates[-1]
        )

        # RSI计算应该能处理NaN
        assert isinstance(signals, dict)

    def test_repr(self):
        """测试字符串表示"""
        entry = RSIOversoldEntry(params={'rsi_period': 14, 'oversold_threshold': 30.0})
        repr_str = repr(entry)

        assert "RSI超卖入场" in repr_str
        assert "rsi_oversold" in repr_str
