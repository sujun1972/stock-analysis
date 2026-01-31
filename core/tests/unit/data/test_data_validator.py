"""
数据验证器单元测试

测试覆盖：
- 必需字段验证
- 数据类型验证
- 价格逻辑验证
- 日期连续性验证
- 数值范围验证
- 缺失值验证

更新日志：
- 2026-01-31: 更新所有测试以适配Response返回格式（任务3.5）
"""

import pytest
import pandas as pd
import numpy as np

from data.data_validator import DataValidator, validate_stock_data
from utils.response import Response


@pytest.fixture
def valid_data():
    """创建有效的测试数据"""
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    np.random.seed(42)

    base_price = 100
    returns = np.random.normal(0.001, 0.02, 50)
    prices = base_price * (1 + returns).cumprod()

    return pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(1000000, 10000000, 50)
    }, index=dates)


@pytest.fixture
def invalid_data():
    """创建包含问题的测试数据"""
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    np.random.seed(42)

    prices = 100 + np.random.normal(0, 5, 50)

    df = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(1000000, 10000000, 50)
    }, index=dates)

    # 注入问题
    df.loc[dates[10], 'high'] = df.loc[dates[10], 'low'] - 1  # high < low
    df.loc[dates[20], 'close'] = df.loc[dates[20], 'high'] + 10  # close > high
    df.loc[dates[30], 'close'] = -10  # 负价格
    df.loc[dates[40:45], 'close'] = np.nan  # 缺失值

    return df


class TestDataValidator:
    """数据验证器测试类"""

    def test_initialization(self, valid_data):
        """测试初始化"""
        validator = DataValidator(valid_data)

        assert validator.df is not None
        assert len(validator.required_fields) == 1  # 默认只需要close
        assert validator.required_fields[0] == 'close'

    def test_validate_required_fields_pass(self, valid_data):
        """测试必需字段验证通过"""
        validator = DataValidator(valid_data, required_fields=['close'])
        response = validator.validate_required_fields()

        assert isinstance(response, Response)
        assert response.is_success()
        assert response.data['passed'] is True
        assert len(validator.validation_results['errors']) == 0

    def test_validate_required_fields_fail(self, valid_data):
        """测试必需字段验证失败"""
        validator = DataValidator(valid_data, required_fields=['close', 'missing_column'])
        response = validator.validate_required_fields()

        assert isinstance(response, Response)
        assert response.is_error()
        assert response.error_code == "MISSING_REQUIRED_FIELDS"
        assert 'missing_fields' in response.metadata
        assert len(validator.validation_results['errors']) > 0

    def test_validate_data_types_pass(self, valid_data):
        """测试数据类型验证通过"""
        validator = DataValidator(valid_data)
        response = validator.validate_data_types()

        assert isinstance(response, Response)
        assert response.is_success()
        assert response.data['passed'] is True

    def test_validate_data_types_fail(self, valid_data):
        """测试数据类型验证失败"""
        df = valid_data.copy()
        df['close'] = df['close'].astype(str)  # 转为字符串类型

        validator = DataValidator(df)
        response = validator.validate_data_types()

        assert isinstance(response, Response)
        assert response.is_error()
        assert response.error_code == "INVALID_DATA_TYPES"
        assert 'type_errors' in response.metadata
        assert len(validator.validation_results['errors']) > 0

    def test_validate_price_logic_pass(self, valid_data):
        """测试价格逻辑验证通过"""
        validator = DataValidator(valid_data)
        response = validator.validate_price_logic()

        assert isinstance(response, Response)
        assert response.is_success()
        assert response.data['passed'] is True
        assert sum(response.data['error_stats'].values()) == 0  # 没有错误

    def test_validate_price_logic_fail(self, invalid_data):
        """测试价格逻辑验证失败"""
        validator = DataValidator(invalid_data)
        response = validator.validate_price_logic()

        assert isinstance(response, Response)
        assert response.is_warning()  # 价格逻辑问题返回警告
        assert response.data['passed'] is False
        error_stats = response.data['error_stats']

        # 应该检测到多个问题
        assert error_stats['high_less_than_low'] >= 1
        assert error_stats['close_out_of_range'] >= 1
        assert error_stats['negative_price'] >= 1

    def test_validate_date_continuity(self, valid_data):
        """测试日期连续性验证"""
        validator = DataValidator(valid_data)
        response = validator.validate_date_continuity(allow_gaps=True, max_gap_days=10)

        assert isinstance(response, Response)
        assert response.is_success() or response.is_warning()
        assert response.data['passed'] is True
        assert 'gaps' in response.data
        assert isinstance(response.data['gaps'], list)

    def test_validate_date_continuity_with_gaps(self):
        """测试有间隔的日期序列"""
        dates = pd.date_range('2023-01-01', periods=20, freq='D').tolist()
        dates += pd.date_range('2023-02-01', periods=20, freq='D').tolist()  # 中间有间隔

        df = pd.DataFrame({
            'close': np.random.uniform(90, 110, 40)
        }, index=pd.DatetimeIndex(dates))

        validator = DataValidator(df)
        response = validator.validate_date_continuity(max_gap_days=10)

        assert isinstance(response, Response)
        assert response.is_warning()  # 有间隔但允许，返回警告
        gaps = response.data['gaps']
        assert len(gaps) >= 1  # 应该检测到间隔
        assert gaps[0]['gap_days'] > 10  # 间隔天数 > 10

    def test_validate_value_ranges_pass(self, valid_data):
        """测试数值范围验证通过"""
        validator = DataValidator(valid_data)
        response = validator.validate_value_ranges(
            price_min=0.01,
            price_max=10000.0
        )

        assert isinstance(response, Response)
        assert response.is_success()
        assert response.data['passed'] is True
        assert len(response.data['range_errors']) == 0

    def test_validate_value_ranges_fail(self):
        """测试数值范围验证失败"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')

        df = pd.DataFrame({
            'close': np.random.uniform(0.001, 0.01, 50),  # 价格过低
            'volume': np.random.uniform(1e13, 2e13, 50)    # 成交量过大
        }, index=dates)

        validator = DataValidator(df)
        response = validator.validate_value_ranges(
            price_min=0.01,
            price_max=10000.0,
            volume_max=1e12
        )

        assert isinstance(response, Response)
        assert response.is_warning()  # 超范围返回警告
        assert response.data['passed'] is False
        range_errors = response.data['range_errors']
        assert len(range_errors) >= 2  # 价格和成交量都超范围

    def test_validate_missing_values_pass(self, valid_data):
        """测试缺失值验证通过"""
        validator = DataValidator(valid_data)
        response = validator.validate_missing_values(max_missing_rate=0.5)

        assert isinstance(response, Response)
        assert response.is_success()
        assert response.data['passed'] is True
        missing_stats = response.data['missing_stats']
        assert all(stats['rate'] == 0 for stats in missing_stats.values())

    def test_validate_missing_values_fail(self, invalid_data):
        """测试缺失值验证失败"""
        validator = DataValidator(invalid_data)
        response = validator.validate_missing_values(max_missing_rate=0.05)

        assert isinstance(response, Response)
        assert response.is_warning()  # 缺失值过多返回警告
        assert response.data['passed'] is False
        missing_stats = response.data['missing_stats']

        # close列有缺失值
        assert missing_stats['close']['count'] > 0
        assert missing_stats['close']['rate'] > 0

    def test_validate_duplicates_no_dup(self, valid_data):
        """测试无重复记录"""
        validator = DataValidator(valid_data)
        response = validator.validate_duplicates()

        assert isinstance(response, Response)
        assert response.is_success()
        assert response.data['passed'] is True
        assert response.data['duplicate_count'] == 0

    def test_validate_duplicates_with_dup(self, valid_data):
        """测试有重复记录"""
        df = pd.concat([valid_data, valid_data.iloc[[0, 1, 2]]])  # 添加3条重复记录

        validator = DataValidator(df)
        response = validator.validate_duplicates()

        assert isinstance(response, Response)
        assert response.is_warning()  # 有重复记录返回警告
        assert response.data['passed'] is False
        assert response.data['duplicate_count'] == 3

    def test_validate_all_pass(self, valid_data):
        """测试全面验证通过"""
        validator = DataValidator(valid_data)
        response = validator.validate_all(strict_mode=False)

        assert isinstance(response, Response)
        assert response.is_success()
        assert response.data['passed'] is True
        assert response.data['summary']['error_count'] == 0

    def test_validate_all_fail(self, invalid_data):
        """测试全面验证失败"""
        validator = DataValidator(invalid_data)
        response = validator.validate_all(strict_mode=False)

        assert isinstance(response, Response)
        # 非严格模式下，只有警告不会导致失败，返回warning状态
        assert response.is_warning()
        assert response.data['passed'] is True  # 非严格模式下只有警告不算失败
        assert response.data['summary']['error_count'] == 0  # 只有警告，没有错误
        assert response.data['summary']['warning_count'] > 0

    def test_validate_all_strict_mode(self, invalid_data):
        """测试严格模式"""
        validator = DataValidator(invalid_data)
        response = validator.validate_all(strict_mode=True)

        assert isinstance(response, Response)
        # 严格模式下，警告也算失败，返回error状态
        assert response.is_error()
        assert response.data['passed'] is False
        assert response.data['summary']['warning_count'] > 0

    def test_get_validation_report(self, invalid_data):
        """测试验证报告生成"""
        validator = DataValidator(invalid_data)
        validator.validate_all()

        report = validator.get_validation_report()

        assert isinstance(report, str)
        assert '数据验证报告' in report
        assert '验证结果' in report

    def test_get_validation_report_before_validate(self, valid_data):
        """测试验证前获取报告"""
        validator = DataValidator(valid_data)
        report = validator.get_validation_report()

        assert '尚未执行验证' in report


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_validate_stock_data(self, valid_data):
        """测试快速验证函数"""
        response = validate_stock_data(valid_data, strict_mode=False)

        assert isinstance(response, Response)
        assert response.is_success() or response.is_warning()
        assert 'passed' in response.data
        assert 'summary' in response.data


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_dataframe(self):
        """测试空DataFrame"""
        df = pd.DataFrame()

        validator = DataValidator(df, required_fields=[])
        response = validator.validate_all()

        assert isinstance(response, Response)

    def test_single_row(self):
        """测试单行数据"""
        df = pd.DataFrame({
            'close': [100.0],
            'volume': [1000000]
        })

        validator = DataValidator(df)
        response = validator.validate_all()

        assert isinstance(response, Response)
        assert response.data['summary']['total_records'] == 1

    def test_single_column(self):
        """测试单列数据"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')

        df = pd.DataFrame({
            'close': np.random.uniform(90, 110, 50)
        }, index=dates)

        validator = DataValidator(df)
        response = validator.validate_all()

        assert isinstance(response, Response)
        assert response.data['summary']['total_columns'] == 1

    def test_non_datetime_index(self):
        """测试非日期索引"""
        df = pd.DataFrame({
            'close': np.random.uniform(90, 110, 50),
            'volume': np.random.uniform(1000000, 10000000, 50)
        })  # 默认整数索引

        validator = DataValidator(df)
        response = validator.validate_all()

        # 应该跳过日期连续性检查
        assert isinstance(response, Response)

    def test_all_missing(self):
        """测试全部缺失的列"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')

        df = pd.DataFrame({
            'close': np.full(50, np.nan),
            'volume': np.random.uniform(1000000, 10000000, 50)
        }, index=dates)

        validator = DataValidator(df)
        response = validator.validate_missing_values(max_missing_rate=0.5)

        assert isinstance(response, Response)
        assert response.is_warning()  # 缺失率过高返回警告
        assert response.data['passed'] is False
        missing_stats = response.data['missing_stats']
        assert missing_stats['close']['rate'] == 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
