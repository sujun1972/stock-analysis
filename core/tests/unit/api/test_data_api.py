"""
数据加载API单元测试

测试 src/api/data_api.py 中的三个核心函数:
- load_stock_data()
- validate_stock_data()
- clean_stock_data()
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from src.api.data_api import (
    load_stock_data,
    validate_stock_data,
    clean_stock_data
)
from src.utils.response import Response
from src.exceptions import DataError, DataNotFoundError


# ==================== Fixtures ====================

@pytest.fixture
def valid_stock_data():
    """创建有效的股票数据"""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)

    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, 100)
    prices = base_price * (1 + returns).cumprod()

    df = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)

    return df


@pytest.fixture
def problematic_stock_data():
    """创建有问题的股票数据（用于测试清洗）"""
    dates = pd.date_range('2024-01-01', periods=50, freq='D')
    np.random.seed(42)

    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, 50)
    prices = base_price * (1 + returns).cumprod()

    df = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(1000000, 10000000, 50)
    }, index=dates)

    # 添加问题数据
    df.loc[dates[10], 'close'] = np.nan  # 缺失值
    df.loc[dates[20], 'high'] = df.loc[dates[20], 'low'] - 1  # OHLC逻辑错误
    df.loc[dates[30]:dates[32], 'volume'] = np.nan  # 连续缺失

    # 添加重复行
    df = pd.concat([df, df.iloc[[5]]])

    return df


@pytest.fixture
def empty_dataframe():
    """创建空DataFrame"""
    return pd.DataFrame()


@pytest.fixture
def mock_data_loader():
    """Mock DataLoader"""
    with patch('src.data_pipeline.data_loader.DataLoader') as mock:
        yield mock


@pytest.fixture
def mock_data_validator():
    """Mock DataValidator"""
    with patch('src.data.data_validator.DataValidator') as mock:
        yield mock


@pytest.fixture
def mock_data_cleaner():
    """Mock DataCleaner"""
    with patch('src.data.data_cleaner.DataCleaner') as mock:
        yield mock


# ==================== load_stock_data 测试 ====================

class TestLoadStockData:
    """load_stock_data() 测试套件"""

    def test_load_success(self, valid_stock_data, mock_data_loader):
        """测试成功加载数据"""
        # 配置Mock
        mock_loader_instance = Mock()
        mock_loader_instance.load_data.return_value = valid_stock_data
        mock_data_loader.return_value = mock_loader_instance

        # 执行
        response = load_stock_data('000001', '20240101', '20241231', validate=False)

        # 验证
        assert response.is_success()
        assert isinstance(response.data, pd.DataFrame)
        assert len(response.data) == 100
        assert response.metadata['symbol'] == '000001'
        assert response.metadata['n_records'] == 100
        assert 'elapsed_time' in response.metadata

    def test_load_with_validation_success(self, valid_stock_data, mock_data_loader, mock_data_validator):
        """测试加载数据并验证通过"""
        # 配置Mock
        mock_loader_instance = Mock()
        mock_loader_instance.load_data.return_value = valid_stock_data
        mock_data_loader.return_value = mock_loader_instance

        mock_validator_instance = Mock()
        mock_validator_instance.validate_all.return_value = {
            'passed': True,
            'errors': [],
            'warnings': [],
            'summary': {'error_count': 0, 'warning_count': 0}
        }
        mock_data_validator.return_value = mock_validator_instance

        # 执行
        response = load_stock_data('000001', '20240101', '20241231', validate=True)

        # 验证
        assert response.is_success()
        assert response.metadata['validation_passed'] is True
        assert response.metadata['validation_warnings'] == 0

    def test_load_with_validation_warning(self, valid_stock_data, mock_data_loader, mock_data_validator):
        """测试加载数据但验证有警告"""
        # 配置Mock
        mock_loader_instance = Mock()
        mock_loader_instance.load_data.return_value = valid_stock_data
        mock_data_loader.return_value = mock_loader_instance

        mock_validator_instance = Mock()
        mock_validator_instance.validate_all.return_value = {
            'passed': False,
            'errors': ['缺少数据'],
            'warnings': ['存在缺失值'],
            'summary': {'error_count': 1, 'warning_count': 1}
        }
        mock_data_validator.return_value = mock_validator_instance

        # 执行
        response = load_stock_data('000001', '20240101', '20241231', validate=True)

        # 验证
        assert response.is_warning()
        assert 'validation_errors' in response.metadata
        assert 'validation_warnings' in response.metadata

    def test_load_empty_symbol(self):
        """测试空股票代码"""
        response = load_stock_data('', '20240101', '20241231')

        assert response.is_error()
        assert response.error_code == 'EMPTY_SYMBOL'

    def test_load_empty_dates(self):
        """测试空日期"""
        response = load_stock_data('000001', '', '')

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATE'

    def test_load_invalid_date_format(self):
        """测试无效日期格式"""
        response = load_stock_data('000001', '2024-01-01', '2024-12-31')

        assert response.is_error()
        assert response.error_code == 'INVALID_DATE_FORMAT'

    def test_load_data_not_found(self, mock_data_loader):
        """测试数据未找到"""
        # 配置Mock
        mock_loader_instance = Mock()
        mock_loader_instance.load_data.side_effect = DataNotFoundError("数据未找到")
        mock_data_loader.return_value = mock_loader_instance

        # 执行
        response = load_stock_data('999999', '20240101', '20241231')

        # 验证
        assert response.is_error()
        assert response.error_code == 'DATA_NOT_FOUND'
        assert response.metadata['symbol'] == '999999'

    def test_load_data_error(self, mock_data_loader):
        """测试数据加载错误"""
        # 配置Mock
        mock_loader_instance = Mock()
        mock_loader_instance.load_data.side_effect = DataError("数据库连接失败")
        mock_data_loader.return_value = mock_loader_instance

        # 执行
        response = load_stock_data('000001', '20240101', '20241231')

        # 验证
        assert response.is_error()
        assert response.error_code == 'DATA_LOAD_ERROR'

    def test_load_unexpected_error(self, mock_data_loader):
        """测试未预期错误"""
        # 配置Mock
        mock_loader_instance = Mock()
        mock_loader_instance.load_data.side_effect = Exception("未知错误")
        mock_data_loader.return_value = mock_loader_instance

        # 执行
        response = load_stock_data('000001', '20240101', '20241231')

        # 验证
        assert response.is_error()
        assert response.error_code == 'UNEXPECTED_ERROR'
        assert response.metadata['exception_type'] == 'Exception'


# ==================== validate_stock_data 测试 ====================

class TestValidateStockData:
    """validate_stock_data() 测试套件"""

    def test_validate_success(self, valid_stock_data, mock_data_validator):
        """测试验证成功"""
        # 配置Mock
        mock_validator_instance = Mock()
        mock_validator_instance.validate_all.return_value = {
            'passed': True,
            'errors': [],
            'warnings': [],
            'stats': {},
            'summary': {
                'total_records': 100,
                'total_columns': 5,
                'error_count': 0,
                'warning_count': 0
            }
        }
        mock_data_validator.return_value = mock_validator_instance

        # 执行
        response = validate_stock_data(valid_stock_data)

        # 验证
        assert response.is_success()
        assert response.data['passed'] is True
        assert response.metadata['n_records'] == 100
        assert response.metadata['error_count'] == 0

    def test_validate_with_warnings(self, valid_stock_data, mock_data_validator):
        """测试验证有警告"""
        # 配置Mock
        mock_validator_instance = Mock()
        mock_validator_instance.validate_all.return_value = {
            'passed': True,
            'errors': [],
            'warnings': ['存在缺失值', '存在常数列'],
            'stats': {},
            'summary': {
                'total_records': 100,
                'total_columns': 5,
                'error_count': 0,
                'warning_count': 2
            }
        }
        mock_data_validator.return_value = mock_validator_instance

        # 执行
        response = validate_stock_data(valid_stock_data)

        # 验证
        assert response.is_warning()
        assert len(response.metadata['warnings']) == 2
        assert response.metadata['warning_count'] == 2

    def test_validate_failed(self, valid_stock_data, mock_data_validator):
        """测试验证失败"""
        # 配置Mock
        mock_validator_instance = Mock()
        mock_validator_instance.validate_all.return_value = {
            'passed': False,
            'errors': ['缺少必需字段', 'OHLC逻辑错误'],
            'warnings': [],
            'stats': {},
            'summary': {
                'total_records': 100,
                'total_columns': 5,
                'error_count': 2,
                'warning_count': 0
            }
        }
        mock_data_validator.return_value = mock_validator_instance

        # 执行
        response = validate_stock_data(valid_stock_data)

        # 验证
        assert response.is_error()
        assert response.error_code == 'DATA_VALIDATION_FAILED'
        assert len(response.metadata['errors']) == 2

    def test_validate_empty_data(self, empty_dataframe):
        """测试验证空数据"""
        response = validate_stock_data(empty_dataframe)

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'

    def test_validate_none_data(self):
        """测试验证None数据"""
        response = validate_stock_data(None)

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'

    def test_validate_strict_mode(self, valid_stock_data, mock_data_validator):
        """测试严格模式验证"""
        # 配置Mock
        mock_validator_instance = Mock()
        mock_validator_instance.validate_all.return_value = {
            'passed': False,  # 严格模式下，有警告就失败
            'errors': [],
            'warnings': ['轻微问题'],
            'stats': {},
            'summary': {
                'total_records': 100,
                'total_columns': 5,
                'error_count': 0,
                'warning_count': 1
            }
        }
        mock_data_validator.return_value = mock_validator_instance

        # 执行
        response = validate_stock_data(valid_stock_data, strict_mode=True)

        # 验证
        assert response.is_error()
        assert response.metadata['strict_mode'] is True

    def test_validate_with_required_fields(self, valid_stock_data, mock_data_validator):
        """测试指定必需字段验证"""
        # 配置Mock
        mock_validator_instance = Mock()
        mock_validator_instance.validate_all.return_value = {
            'passed': True,
            'errors': [],
            'warnings': [],
            'stats': {},
            'summary': {
                'total_records': 100,
                'total_columns': 5,
                'error_count': 0,
                'warning_count': 0
            }
        }
        mock_data_validator.return_value = mock_validator_instance

        # 执行
        required_fields = ['open', 'high', 'low', 'close', 'volume']
        response = validate_stock_data(valid_stock_data, required_fields=required_fields)

        # 验证
        assert response.is_success()
        mock_data_validator.assert_called_once()


# ==================== clean_stock_data 测试 ====================

class TestCleanStockData:
    """clean_stock_data() 测试套件"""

    def test_clean_success(self, problematic_stock_data, mock_data_cleaner):
        """测试清洗成功"""
        # 准备清洗后的数据
        cleaned_data = problematic_stock_data.dropna().drop_duplicates()

        # 配置Mock
        mock_cleaner_instance = Mock()
        mock_cleaner_instance.clean_price_data.return_value = cleaned_data
        mock_cleaner_instance.validate_ohlc.return_value = cleaned_data
        mock_cleaner_instance.get_stats.return_value = {
            'total_rows': 51,
            'missing_filled': 4,
            'outliers_removed': 1,
            'duplicates_removed': 1,
            'final_rows': 45
        }
        mock_data_cleaner.return_value = mock_cleaner_instance

        # 执行
        response = clean_stock_data(problematic_stock_data, '000001')

        # 验证
        assert response.is_success()
        assert isinstance(response.data, pd.DataFrame)
        assert response.metadata['symbol'] == '000001'
        assert 'cleaning_stats' in response.metadata
        assert 'removal_rate' in response.metadata

    def test_clean_high_removal_rate(self, problematic_stock_data, mock_data_cleaner):
        """测试清洗时移除了大量数据"""
        # 准备清洗后的数据（移除了35%）
        cleaned_data = problematic_stock_data.iloc[:33]

        # 配置Mock
        mock_cleaner_instance = Mock()
        mock_cleaner_instance.clean_price_data.return_value = cleaned_data
        mock_cleaner_instance.validate_ohlc.return_value = cleaned_data
        mock_cleaner_instance.get_stats.return_value = {
            'total_rows': 51,
            'missing_filled': 4,
            'outliers_removed': 10,
            'duplicates_removed': 4,
            'final_rows': 33
        }
        mock_data_cleaner.return_value = mock_cleaner_instance

        # 执行
        response = clean_stock_data(problematic_stock_data, '000001')

        # 验证
        assert response.is_warning()
        assert '移除了' in response.message
        assert isinstance(response.data, pd.DataFrame)

    def test_clean_too_few_rows(self, valid_stock_data, mock_data_cleaner):
        """测试清洗后剩余数据太少"""
        # 准备清洗后的数据（仅剩5行）
        cleaned_data = valid_stock_data.iloc[:5]

        # 配置Mock
        mock_cleaner_instance = Mock()
        mock_cleaner_instance.clean_price_data.return_value = cleaned_data
        mock_cleaner_instance.validate_ohlc.return_value = cleaned_data
        mock_cleaner_instance.get_stats.return_value = {
            'total_rows': 100,
            'missing_filled': 0,
            'outliers_removed': 90,
            'duplicates_removed': 5,
            'final_rows': 5
        }
        mock_data_cleaner.return_value = mock_cleaner_instance

        # 执行
        response = clean_stock_data(valid_stock_data, '000001')

        # 验证 - 可能是高移除率警告或少行数警告
        assert response.is_warning()
        assert ('仅有 5 行' in response.message or '移除了' in response.message)

    def test_clean_empty_data(self, empty_dataframe):
        """测试清洗空数据"""
        response = clean_stock_data(empty_dataframe, '000001')

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'

    def test_clean_none_data(self):
        """测试清洗None数据"""
        response = clean_stock_data(None, '000001')

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'

    def test_clean_with_ohlc_fix(self, problematic_stock_data, mock_data_cleaner):
        """测试清洗并修复OHLC"""
        cleaned_data = problematic_stock_data.dropna()

        # 配置Mock
        mock_cleaner_instance = Mock()
        mock_cleaner_instance.clean_price_data.return_value = cleaned_data
        mock_cleaner_instance.validate_ohlc.return_value = cleaned_data
        mock_cleaner_instance.get_stats.return_value = {
            'total_rows': 51,
            'final_rows': 47
        }
        mock_data_cleaner.return_value = mock_cleaner_instance

        # 执行
        response = clean_stock_data(problematic_stock_data, '000001', fix_ohlc=True)

        # 验证
        assert response.is_success() or response.is_warning()
        assert response.metadata['ohlc_fixed'] is True
        mock_cleaner_instance.validate_ohlc.assert_called_once()

    def test_clean_with_features(self, valid_stock_data, mock_data_cleaner):
        """测试清洗并添加特征"""
        # 准备带特征的数据
        cleaned_data = valid_stock_data.copy()
        cleaned_data['pct_change'] = cleaned_data['close'].pct_change() * 100

        # 配置Mock
        mock_cleaner_instance = Mock()
        mock_cleaner_instance.clean_price_data.return_value = valid_stock_data
        mock_cleaner_instance.validate_ohlc.return_value = valid_stock_data
        mock_cleaner_instance.add_basic_features.return_value = cleaned_data
        mock_cleaner_instance.get_stats.return_value = {
            'total_rows': 100,
            'final_rows': 100
        }
        mock_data_cleaner.return_value = mock_cleaner_instance

        # 执行
        response = clean_stock_data(valid_stock_data, '000001', add_features=True)

        # 验证
        assert response.is_success()
        assert response.metadata['features_added'] is True
        mock_cleaner_instance.add_basic_features.assert_called_once()

    def test_clean_data_error(self, valid_stock_data, mock_data_cleaner):
        """测试清洗时发生DataError"""
        # 配置Mock
        mock_cleaner_instance = Mock()
        mock_cleaner_instance.clean_price_data.side_effect = DataError("清洗失败")
        mock_data_cleaner.return_value = mock_cleaner_instance

        # 执行
        response = clean_stock_data(valid_stock_data, '000001')

        # 验证
        assert response.is_error()
        assert response.error_code == 'DATA_CLEANING_ERROR'

    def test_clean_unexpected_error(self, valid_stock_data, mock_data_cleaner):
        """测试清洗时发生未预期错误"""
        # 配置Mock
        mock_cleaner_instance = Mock()
        mock_cleaner_instance.clean_price_data.side_effect = Exception("未知错误")
        mock_data_cleaner.return_value = mock_cleaner_instance

        # 执行
        response = clean_stock_data(valid_stock_data, '000001')

        # 验证
        assert response.is_error()
        assert response.error_code == 'UNEXPECTED_ERROR'


# ==================== 集成测试 ====================

class TestDataAPIIntegration:
    """数据API集成测试"""

    def test_complete_workflow_mock(self, valid_stock_data, mock_data_loader,
                                   mock_data_validator, mock_data_cleaner):
        """测试完整工作流：加载 -> 验证 -> 清洗"""
        # 配置Mock
        mock_loader_instance = Mock()
        mock_loader_instance.load_data.return_value = valid_stock_data
        mock_data_loader.return_value = mock_loader_instance

        mock_validator_instance = Mock()
        mock_validator_instance.validate_all.return_value = {
            'passed': True,
            'errors': [],
            'warnings': ['轻微问题'],
            'stats': {},
            'summary': {
                'total_records': 100,
                'total_columns': 5,
                'error_count': 0,
                'warning_count': 1
            }
        }
        mock_data_validator.return_value = mock_validator_instance

        cleaned_data = valid_stock_data.copy()
        mock_cleaner_instance = Mock()
        mock_cleaner_instance.clean_price_data.return_value = cleaned_data
        mock_cleaner_instance.validate_ohlc.return_value = cleaned_data
        mock_cleaner_instance.get_stats.return_value = {
            'total_rows': 100,
            'final_rows': 100
        }
        mock_data_cleaner.return_value = mock_cleaner_instance

        # 1. 加载数据
        load_resp = load_stock_data('000001', '20240101', '20241231', validate=False)
        assert load_resp.is_success()
        data = load_resp.data

        # 2. 验证数据
        validate_resp = validate_stock_data(data)
        assert validate_resp.is_warning()  # 有警告

        # 3. 清洗数据
        clean_resp = clean_stock_data(data, '000001')
        assert clean_resp.is_success()

        # 验证整体流程
        assert isinstance(clean_resp.data, pd.DataFrame)

    def test_error_handling_chain(self, mock_data_loader):
        """测试错误处理链"""
        # 配置Mock - 加载失败
        mock_loader_instance = Mock()
        mock_loader_instance.load_data.side_effect = DataNotFoundError("数据未找到")
        mock_data_loader.return_value = mock_loader_instance

        # 执行加载
        load_resp = load_stock_data('999999', '20240101', '20241231')

        # 验证错误被正确处理
        assert load_resp.is_error()
        assert load_resp.error_code == 'DATA_NOT_FOUND'
        assert 'elapsed_time' in load_resp.metadata


# ==================== Response格式验证 ====================

class TestResponseFormat:
    """验证Response格式一致性"""

    def test_load_response_format(self, valid_stock_data, mock_data_loader):
        """测试load_stock_data返回格式"""
        mock_loader_instance = Mock()
        mock_loader_instance.load_data.return_value = valid_stock_data
        mock_data_loader.return_value = mock_loader_instance

        response = load_stock_data('000001', '20240101', '20241231', validate=False)

        # 验证Response对象
        assert isinstance(response, Response)
        assert hasattr(response, 'status')
        assert hasattr(response, 'data')
        assert hasattr(response, 'message')
        assert hasattr(response, 'metadata')

        # 验证to_dict方法
        response_dict = response.to_dict()
        assert isinstance(response_dict, dict)
        assert 'status' in response_dict

    def test_validate_response_format(self, valid_stock_data, mock_data_validator):
        """测试validate_stock_data返回格式"""
        mock_validator_instance = Mock()
        mock_validator_instance.validate_all.return_value = {
            'passed': True,
            'errors': [],
            'warnings': [],
            'stats': {},
            'summary': {
                'total_records': 100,
                'total_columns': 5,
                'error_count': 0,
                'warning_count': 0
            }
        }
        mock_data_validator.return_value = mock_validator_instance

        response = validate_stock_data(valid_stock_data)

        # 验证Response对象
        assert isinstance(response, Response)
        assert response.is_success()

        # 验证metadata包含预期字段
        assert 'n_records' in response.metadata
        assert 'n_columns' in response.metadata
        assert 'error_count' in response.metadata

    def test_clean_response_format(self, valid_stock_data, mock_data_cleaner):
        """测试clean_stock_data返回格式"""
        mock_cleaner_instance = Mock()
        mock_cleaner_instance.clean_price_data.return_value = valid_stock_data
        mock_cleaner_instance.validate_ohlc.return_value = valid_stock_data
        mock_cleaner_instance.get_stats.return_value = {
            'total_rows': 100,
            'final_rows': 100
        }
        mock_data_cleaner.return_value = mock_cleaner_instance

        response = clean_stock_data(valid_stock_data, '000001')

        # 验证Response对象
        assert isinstance(response, Response)
        assert response.is_success()

        # 验证metadata包含预期字段
        assert 'symbol' in response.metadata
        assert 'original_rows' in response.metadata
        assert 'final_rows' in response.metadata
        assert 'cleaning_stats' in response.metadata


# ==================== Lazy Import 测试 ====================

class TestLazyImport:
    """测试Lazy Import机制"""

    def test_load_stock_data_lazy_import(self):
        """测试load_stock_data的lazy import - 参数验证不触发导入"""
        # 参数错误应该在导入之前就返回
        response = load_stock_data('', '20240101', '20241231')

        # 验证错误被正确处理，没有因为导入失败而抛出异常
        assert response.is_error()
        assert response.error_code == 'EMPTY_SYMBOL'

    def test_validate_stock_data_lazy_import_empty(self):
        """测试validate_stock_data的lazy import - 空数据不触发导入"""
        response = validate_stock_data(None)

        # 验证空数据检查在导入之前
        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'

    def test_clean_stock_data_lazy_import_empty(self):
        """测试clean_stock_data的lazy import - 空数据不触发导入"""
        response = clean_stock_data(None, '000001')

        # 验证空数据检查在导入之前
        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'


# ==================== 参数验证增强测试 ====================

class TestEnhancedParameterValidation:
    """增强的参数验证测试"""

    def test_load_stock_data_whitespace_symbol(self):
        """测试仅包含空格的股票代码"""
        response = load_stock_data('   ', '20240101', '20241231')

        assert response.is_error()
        assert response.error_code == 'EMPTY_SYMBOL'

    def test_load_stock_data_short_date(self):
        """测试日期格式太短"""
        response = load_stock_data('000001', '2024', '20241231')

        assert response.is_error()
        assert response.error_code == 'INVALID_DATE_FORMAT'

    def test_load_stock_data_long_date(self):
        """测试日期格式太长"""
        response = load_stock_data('000001', '202401011', '20241231')

        assert response.is_error()
        assert response.error_code == 'INVALID_DATE_FORMAT'

    def test_validate_stock_data_with_empty_dataframe(self, empty_dataframe):
        """测试验证空DataFrame"""
        response = validate_stock_data(empty_dataframe)

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'

    def test_clean_stock_data_with_empty_dataframe(self, empty_dataframe):
        """测试清洗空DataFrame"""
        response = clean_stock_data(empty_dataframe, '000001')

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'


# ==================== Metadata 完整性测试 ====================

class TestMetadataCompleteness:
    """测试Response metadata的完整性"""

    def test_load_stock_data_metadata_keys(self, valid_stock_data, mock_data_loader):
        """测试load_stock_data返回的metadata包含所有必需键"""
        # 配置Mock
        mock_loader_instance = Mock()
        mock_loader_instance.load_data.return_value = valid_stock_data
        mock_data_loader.return_value = mock_loader_instance

        response = load_stock_data('000001', '20240101', '20241231', validate=False)

        # 验证metadata包含所有预期键
        if response.is_success():
            assert 'symbol' in response.metadata
            assert 'n_records' in response.metadata
            assert 'date_range' in response.metadata
            assert 'columns' in response.metadata
            assert 'elapsed_time' in response.metadata

    def test_validate_stock_data_metadata_keys(self, valid_stock_data, mock_data_validator):
        """测试validate_stock_data返回的metadata包含所有必需键"""
        # 配置Mock
        mock_validator_instance = Mock()
        mock_validator_instance.validate_all.return_value = {
            'passed': True,
            'errors': [],
            'warnings': [],
            'stats': {},
            'summary': {
                'total_records': 100,
                'total_columns': 5,
                'error_count': 0,
                'warning_count': 0
            }
        }
        mock_data_validator.return_value = mock_validator_instance

        response = validate_stock_data(valid_stock_data)

        # 验证metadata包含所有预期键
        if response.is_success():
            assert 'n_records' in response.metadata
            assert 'n_columns' in response.metadata
            assert 'error_count' in response.metadata
            assert 'warning_count' in response.metadata
            assert 'strict_mode' in response.metadata

    def test_clean_stock_data_metadata_keys(self, valid_stock_data, mock_data_cleaner):
        """测试clean_stock_data返回的metadata包含所有必需键"""
        # 配置Mock
        mock_cleaner_instance = Mock()
        mock_cleaner_instance.clean_price_data.return_value = valid_stock_data
        mock_cleaner_instance.validate_ohlc.return_value = valid_stock_data
        mock_cleaner_instance.get_stats.return_value = {
            'total_rows': 100,
            'final_rows': 100
        }
        mock_data_cleaner.return_value = mock_cleaner_instance

        response = clean_stock_data(valid_stock_data, '000001')

        # 验证metadata包含所有预期键
        if response.is_success():
            assert 'symbol' in response.metadata
            assert 'original_rows' in response.metadata
            assert 'original_columns' in response.metadata
            assert 'final_rows' in response.metadata
            assert 'final_columns' in response.metadata
            assert 'rows_removed' in response.metadata
            assert 'removal_rate' in response.metadata
            assert 'cleaning_stats' in response.metadata
            assert 'ohlc_fixed' in response.metadata
            assert 'features_added' in response.metadata
            assert 'elapsed_time' in response.metadata


# ==================== 边界条件测试 ====================

class TestEdgeCases:
    """边界条件测试"""

    def test_load_stock_data_with_special_characters(self):
        """测试包含特殊字符的股票代码"""
        response = load_stock_data('000001.SZ', '20240101', '20241231', validate=False)

        # 应该能正常处理（具体结果取决于DataLoader实现）
        assert isinstance(response, Response)

    def test_validate_stock_data_single_row(self, valid_stock_data, mock_data_validator):
        """测试验证单行数据"""
        single_row_data = valid_stock_data.iloc[:1]

        # 配置Mock
        mock_validator_instance = Mock()
        mock_validator_instance.validate_all.return_value = {
            'passed': True,
            'errors': [],
            'warnings': [],
            'stats': {},
            'summary': {
                'total_records': 1,
                'total_columns': 5,
                'error_count': 0,
                'warning_count': 0
            }
        }
        mock_data_validator.return_value = mock_validator_instance

        response = validate_stock_data(single_row_data)

        assert isinstance(response, Response)
        if response.is_success():
            assert response.metadata['n_records'] == 1

    def test_clean_stock_data_all_removed(self, valid_stock_data, mock_data_cleaner):
        """测试清洗后所有数据都被移除的情况"""
        # 准备空的清洗结果
        empty_result = pd.DataFrame()

        # 配置Mock
        mock_cleaner_instance = Mock()
        mock_cleaner_instance.clean_price_data.return_value = empty_result
        mock_cleaner_instance.validate_ohlc.return_value = empty_result
        mock_cleaner_instance.get_stats.return_value = {
            'total_rows': 100,
            'final_rows': 0
        }
        mock_data_cleaner.return_value = mock_cleaner_instance

        response = clean_stock_data(valid_stock_data, '000001')

        # 应该返回警告
        assert response.is_warning()
        assert response.metadata['final_rows'] == 0


# ==================== 错误消息完整性测试 ====================

class TestErrorMessages:
    """测试错误消息的完整性和可读性"""

    def test_error_messages_have_codes(self):
        """测试所有错误都有error_code"""
        # 测试各种错误场景
        test_cases = [
            (load_stock_data('', '20240101', '20241231'), 'EMPTY_SYMBOL'),
            (load_stock_data('000001', '', ''), 'EMPTY_DATE'),
            (load_stock_data('000001', '2024', '20241231'), 'INVALID_DATE_FORMAT'),
            (validate_stock_data(None), 'EMPTY_DATA'),
            (clean_stock_data(None, '000001'), 'EMPTY_DATA'),
        ]

        for response, expected_code in test_cases:
            assert response.is_error()
            assert response.error_code == expected_code
            assert response.error_message is not None
            assert len(response.error_message) > 0

    def test_error_messages_contain_context(self):
        """测试错误消息包含上下文信息"""
        # 空股票代码错误应包含symbol
        response = load_stock_data('', '20240101', '20241231')
        assert 'symbol' in response.metadata

        # 空日期错误应包含start_date和end_date
        response = load_stock_data('000001', '', '')
        assert 'start_date' in response.metadata
        assert 'end_date' in response.metadata


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
