"""
AkShare Provider 测试配置和公共 fixtures

提供测试所需的公共 fixtures 和配置
"""

import pytest
import pandas as pd
from datetime import datetime, date
from unittest.mock import Mock, patch


@pytest.fixture
def sample_stock_list():
    """示例股票列表数据"""
    return pd.DataFrame({
        'code': ['000001', '600000', '300001', '688001'],
        'name': ['平安银行', '浦发银行', '创业板股', '科创板股']
    })


@pytest.fixture
def sample_daily_data():
    """示例日线数据"""
    return pd.DataFrame({
        '日期': ['2023-01-01', '2023-01-02', '2023-01-03'],
        '开盘': [10.0, 10.5, 10.8],
        '最高': [10.5, 11.0, 11.5],
        '最低': [9.8, 10.3, 10.6],
        '收盘': [10.2, 10.8, 11.2],
        '成交量': [1000000, 1200000, 1500000],
        '成交额': [10200000, 12960000, 16800000],
        '振幅': [7.0, 6.67, 8.33],
        '涨跌幅': [2.0, 5.88, 3.70],
        '涨跌额': [0.2, 0.6, 0.4],
        '换手率': [2.5, 3.0, 3.75]
    })


@pytest.fixture
def sample_minute_data():
    """示例分时数据"""
    return pd.DataFrame({
        '时间': ['2023-01-01 09:30:00', '2023-01-01 09:35:00', '2023-01-01 09:40:00'],
        '开盘': [10.0, 10.1, 10.2],
        '收盘': [10.1, 10.2, 10.3],
        '最高': [10.15, 10.25, 10.35],
        '最低': [9.95, 10.05, 10.15],
        '成交量': [100000, 120000, 150000],
        '成交额': [1010000, 1224000, 1545000]
    })


@pytest.fixture
def sample_realtime_quotes():
    """示例实时行情数据"""
    return pd.DataFrame({
        '代码': ['000001', '600000'],
        '名称': ['平安银行', '浦发银行'],
        '最新价': [10.5, 8.5],
        '开盘': [10.0, 8.0],
        '最高': [10.8, 8.8],
        '最低': [9.8, 7.8],
        '昨收': [10.0, 8.0],
        '成交量': [1000000, 2000000],
        '成交额': [10500000, 17000000],
        '涨跌幅': [5.0, 6.25],
        '涨跌额': [0.5, 0.5],
        '换手率': [2.5, 3.0],
        '振幅': [10.0, 12.5]
    })


@pytest.fixture
def sample_new_stocks():
    """示例新股数据"""
    return pd.DataFrame({
        '代码': ['688001', '688002'],
        '名称': ['科创板新股1', '科创板新股2'],
        '上市日期': ['2023-12-01', '2023-12-15']
    })


@pytest.fixture
def sample_delisted_stocks_sh():
    """示例上交所退市股票数据"""
    return pd.DataFrame({
        '公司代码': ['600001', '600002'],
        '公司简称': ['退市股1', '退市股2'],
        '上市日期': ['2010-01-01', '2015-01-01'],
        '暂停上市日期': ['2023-01-01', '2023-06-01']
    })


@pytest.fixture
def sample_delisted_stocks_sz():
    """示例深交所退市股票数据"""
    return pd.DataFrame({
        '公司代码': ['000001', '000002'],
        '公司简称': ['退市股3', '退市股4'],
        '上市日期': ['2012-01-01', '2016-01-01'],
        '终止上市日期': ['2023-03-01', '2023-09-01']
    })


@pytest.fixture
def mock_akshare_module():
    """Mock AkShare 模块"""
    mock_ak = Mock()

    # 设置默认的模拟方法
    mock_ak.stock_info_a_code_name = Mock()
    mock_ak.stock_zh_a_hist = Mock()
    mock_ak.stock_zh_a_hist_min_em = Mock()
    mock_ak.stock_zh_a_spot_em = Mock()
    mock_ak.stock_bid_ask_em = Mock()
    mock_ak.stock_individual_info_em = Mock()
    mock_ak.stock_new_a_spot_em = Mock()
    mock_ak.stock_info_sh_delist = Mock()
    mock_ak.stock_info_sz_delist = Mock()

    return mock_ak


@pytest.fixture
def mock_logger():
    """Mock logger"""
    with patch('src.providers.akshare.provider.get_logger') as mock_log:
        yield mock_log


@pytest.fixture
def mock_api_client():
    """Mock API 客户端"""
    mock_client = Mock()
    mock_client.execute = Mock()
    return mock_client


@pytest.fixture
def mock_data_converter():
    """Mock 数据转换器"""
    mock_converter = Mock()
    mock_converter.safe_float = Mock(side_effect=lambda x, default=0.0: float(x) if x else default)
    mock_converter.safe_int = Mock(side_effect=lambda x, default=0: int(float(x)) if x else default)
    return mock_converter


@pytest.fixture(autouse=True)
def reset_mocks():
    """每个测试后重置所有 mocks"""
    yield
    # 清理工作在这里进行


# 测试标记
def pytest_configure(config):
    """配置自定义标记"""
    config.addinivalue_line(
        "markers", "slow: 标记为慢速测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记为集成测试"
    )
    config.addinivalue_line(
        "markers", "requires_network: 标记为需要网络的测试"
    )
