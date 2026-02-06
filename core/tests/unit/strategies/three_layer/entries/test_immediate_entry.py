"""
ImmediateEntry 单元测试

测试立即入场策略的各种场景
"""

import pytest
import pandas as pd
import numpy as np

from src.strategies.three_layer.entries import ImmediateEntry


class TestImmediateEntry:
    """ImmediateEntry 测试类"""

    @pytest.fixture
    def entry_strategy(self):
        """创建默认的立即入场策略"""
        return ImmediateEntry(params={
            'max_stocks': 10,
            'min_stocks': 1
        })

    @pytest.fixture
    def sample_data(self):
        """创建测试数据"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        data = {}
        for i, stock in enumerate(['STOCK_A', 'STOCK_B', 'STOCK_C']):
            prices = [100 + i * 10 + j for j in range(30)]
            data[stock] = pd.DataFrame({
                'close': prices,
                'open': prices,
                'high': [p + 1 for p in prices],
                'low': [p - 1 for p in prices],
                'volume': [1000000] * 30
            }, index=dates)

        return data

    def test_initialization(self):
        """测试初始化"""
        entry = ImmediateEntry(params={
            'max_stocks': 10,
            'min_stocks': 1
        })

        assert entry.id == "immediate"
        assert entry.name == "立即入场"
        assert entry.params['max_stocks'] == 10
        assert entry.params['min_stocks'] == 1

    def test_get_parameters(self):
        """测试参数定义获取"""
        params = ImmediateEntry.get_parameters()

        assert len(params) >= 2
        param_names = [p['name'] for p in params]
        assert 'max_stocks' in param_names
        assert 'min_stocks' in param_names
        assert 'validate_data' in param_names

    def test_parameter_validation_invalid_type(self):
        """测试参数类型验证"""
        with pytest.raises(ValueError, match="必须是整数"):
            ImmediateEntry(params={'max_stocks': 10.5})

        with pytest.raises(ValueError, match="必须是布尔值"):
            ImmediateEntry(params={'validate_data': "true"})

    def test_parameter_validation_out_of_range(self):
        """测试参数范围验证"""
        with pytest.raises(ValueError, match="不能小于"):
            ImmediateEntry(params={'max_stocks': 0})

        with pytest.raises(ValueError, match="不能大于"):
            ImmediateEntry(params={'max_stocks': 150})

    def test_immediate_entry_all_stocks(self, entry_strategy, sample_data):
        """测试对所有候选股票立即入场"""
        test_date = pd.Timestamp('2023-01-15')

        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_A', 'STOCK_B', 'STOCK_C'],
            data=sample_data,
            date=test_date
        )

        # 应该生成3个股票的信号
        assert len(signals) == 3
        assert 'STOCK_A' in signals
        assert 'STOCK_B' in signals
        assert 'STOCK_C' in signals

        # 等权分配，每只1/3
        for stock in signals:
            assert abs(signals[stock] - 1.0/3.0) < 0.01

    def test_max_stocks_limit(self, sample_data):
        """测试最大股票数量限制"""
        # 限制最多买2只
        entry = ImmediateEntry(params={
            'max_stocks': 2,
            'min_stocks': 1
        })

        test_date = pd.Timestamp('2023-01-15')

        signals = entry.generate_entry_signals(
            stocks=['STOCK_A', 'STOCK_B', 'STOCK_C'],
            data=sample_data,
            date=test_date
        )

        # 应该只选择前2只
        assert len(signals) == 2

        # 等权分配，每只1/2
        for stock in signals:
            assert abs(signals[stock] - 0.5) < 0.01

    def test_min_stocks_requirement(self, sample_data):
        """测试最小股票数量要求"""
        # 要求至少3只股票
        entry = ImmediateEntry(params={
            'max_stocks': 10,
            'min_stocks': 3
        })

        test_date = pd.Timestamp('2023-01-15')

        # 只提供2只候选股票，少于最小要求
        signals = entry.generate_entry_signals(
            stocks=['STOCK_A', 'STOCK_B'],
            data=sample_data,
            date=test_date
        )

        # 应该不生成信号
        assert len(signals) == 0

    def test_min_stocks_requirement_met(self, sample_data):
        """测试满足最小股票数量要求"""
        entry = ImmediateEntry(params={
            'max_stocks': 10,
            'min_stocks': 2
        })

        test_date = pd.Timestamp('2023-01-15')

        # 提供3只候选股票，满足最小要求
        signals = entry.generate_entry_signals(
            stocks=['STOCK_A', 'STOCK_B', 'STOCK_C'],
            data=sample_data,
            date=test_date
        )

        # 应该生成信号
        assert len(signals) == 3

    def test_equal_weight_distribution(self, entry_strategy, sample_data):
        """测试等权分配"""
        test_date = pd.Timestamp('2023-01-15')

        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_A', 'STOCK_B', 'STOCK_C'],
            data=sample_data,
            date=test_date
        )

        # 权重总和应为1.0
        total_weight = sum(signals.values())
        assert abs(total_weight - 1.0) < 0.01

        # 每只股票权重应该相等
        expected_weight = 1.0 / len(signals)
        for stock in signals:
            assert abs(signals[stock] - expected_weight) < 0.01

    def test_validate_data_enabled(self):
        """测试数据验证功能(启用)"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        # 创建包含无效数据的股票
        data = {
            'STOCK_VALID': pd.DataFrame({
                'close': [100 + i for i in range(30)],
                'open': [100 + i for i in range(30)],
                'high': [101 + i for i in range(30)],
                'low': [99 + i for i in range(30)],
                'volume': [1000000] * 30
            }, index=dates),
            'STOCK_NO_CLOSE': pd.DataFrame({
                'open': [100 + i for i in range(30)],
                'volume': [1000000] * 30
            }, index=dates),
            'STOCK_INVALID_PRICE': pd.DataFrame({
                'close': [0] * 30,  # 无效价格
                'open': [100 + i for i in range(30)],
                'high': [101 + i for i in range(30)],
                'low': [99 + i for i in range(30)],
                'volume': [1000000] * 30
            }, index=dates)
        }

        entry = ImmediateEntry(params={
            'max_stocks': 10,
            'validate_data': True
        })

        test_date = pd.Timestamp('2023-01-15')

        signals = entry.generate_entry_signals(
            stocks=['STOCK_VALID', 'STOCK_NO_CLOSE', 'STOCK_INVALID_PRICE'],
            data=data,
            date=test_date
        )

        # 只有STOCK_VALID应该被选中
        assert len(signals) == 1
        assert 'STOCK_VALID' in signals

    def test_validate_data_disabled(self):
        """测试数据验证功能(禁用)"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        data = {
            'STOCK_A': pd.DataFrame({
                'close': [100 + i for i in range(30)],
                'open': [100 + i for i in range(30)],
                'high': [101 + i for i in range(30)],
                'low': [99 + i for i in range(30)],
                'volume': [1000000] * 30
            }, index=dates)
        }

        entry = ImmediateEntry(params={
            'max_stocks': 10,
            'validate_data': False
        })

        test_date = pd.Timestamp('2023-01-15')

        # 提供的股票不在数据中，但验证被禁用
        signals = entry.generate_entry_signals(
            stocks=['STOCK_A', 'STOCK_B', 'STOCK_C'],
            data=data,
            date=test_date
        )

        # 验证禁用时，直接使用所有候选股票
        assert len(signals) == 3

    def test_missing_stock_data(self, entry_strategy):
        """测试股票数据缺失"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        data = {
            'STOCK_A': pd.DataFrame({
                'close': [100 + i for i in range(30)],
                'open': [100 + i for i in range(30)],
                'high': [101 + i for i in range(30)],
                'low': [99 + i for i in range(30)],
                'volume': [1000000] * 30
            }, index=dates)
        }

        test_date = pd.Timestamp('2023-01-15')

        # STOCK_B和STOCK_C不在数据中
        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_A', 'STOCK_B', 'STOCK_C'],
            data=data,
            date=test_date
        )

        # 只有STOCK_A有效
        assert len(signals) == 1
        assert 'STOCK_A' in signals
        assert signals['STOCK_A'] == 1.0

    def test_date_not_in_data(self, entry_strategy, sample_data):
        """测试日期不在数据范围内"""
        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_A', 'STOCK_B'],
            data=sample_data,
            date=pd.Timestamp('2025-01-01')
        )

        # 日期不在数据范围内，应该被过滤
        assert len(signals) == 0

    def test_nan_in_prices(self):
        """测试价格中包含NaN"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        data = {
            'STOCK_WITH_NAN': pd.DataFrame({
                'close': [100 + i if i != 15 else np.nan for i in range(30)],
                'open': [100 + i for i in range(30)],
                'high': [101 + i for i in range(30)],
                'low': [99 + i for i in range(30)],
                'volume': [1000000] * 30
            }, index=dates)
        }

        entry = ImmediateEntry(params={
            'max_stocks': 10,
            'validate_data': True
        })

        # 在NaN的日期
        test_date = dates[15]

        signals = entry.generate_entry_signals(
            stocks=['STOCK_WITH_NAN'],
            data=data,
            date=test_date
        )

        # 价格为NaN应该被过滤
        assert len(signals) == 0

    def test_empty_stock_list(self, entry_strategy, sample_data):
        """测试空股票列表"""
        test_date = pd.Timestamp('2023-01-15')

        signals = entry_strategy.generate_entry_signals(
            stocks=[],
            data=sample_data,
            date=test_date
        )

        assert len(signals) == 0

    def test_single_stock(self, entry_strategy, sample_data):
        """测试单只股票"""
        test_date = pd.Timestamp('2023-01-15')

        signals = entry_strategy.generate_entry_signals(
            stocks=['STOCK_A'],
            data=sample_data,
            date=test_date
        )

        # 单只股票应该获得100%权重
        assert len(signals) == 1
        assert 'STOCK_A' in signals
        assert abs(signals['STOCK_A'] - 1.0) < 0.01

    def test_many_stocks(self):
        """测试大量股票"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        # 创建50只股票
        data = {}
        stocks = []
        for i in range(50):
            stock_code = f'STOCK_{i:03d}'
            stocks.append(stock_code)
            prices = [100 + i + j for j in range(30)]
            data[stock_code] = pd.DataFrame({
                'close': prices,
                'open': prices,
                'high': [p + 1 for p in prices],
                'low': [p - 1 for p in prices],
                'volume': [1000000] * 30
            }, index=dates)

        entry = ImmediateEntry(params={
            'max_stocks': 20,
            'min_stocks': 1
        })

        test_date = pd.Timestamp('2023-01-15')

        signals = entry.generate_entry_signals(
            stocks=stocks,
            data=data,
            date=test_date
        )

        # 应该只选择前20只
        assert len(signals) == 20

        # 权重总和应为1.0
        total_weight = sum(signals.values())
        assert abs(total_weight - 1.0) < 0.01

    def test_valid_stocks_less_than_min_after_validation(self):
        """测试验证后有效股票少于最小要求"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')

        # 只有1只有效股票
        data = {
            'STOCK_VALID': pd.DataFrame({
                'close': [100 + i for i in range(30)],
                'open': [100 + i for i in range(30)],
                'high': [101 + i for i in range(30)],
                'low': [99 + i for i in range(30)],
                'volume': [1000000] * 30
            }, index=dates)
        }

        entry = ImmediateEntry(params={
            'max_stocks': 10,
            'min_stocks': 3,  # 要求至少3只
            'validate_data': True
        })

        test_date = pd.Timestamp('2023-01-15')

        # 提供3只候选，但只有1只有效
        signals = entry.generate_entry_signals(
            stocks=['STOCK_VALID', 'STOCK_MISSING_1', 'STOCK_MISSING_2'],
            data=data,
            date=test_date
        )

        # 有效股票少于最小要求，不生成信号
        assert len(signals) == 0

    def test_repr(self):
        """测试字符串表示"""
        entry = ImmediateEntry(params={'max_stocks': 10})
        repr_str = repr(entry)

        assert "立即入场" in repr_str
        assert "immediate" in repr_str
