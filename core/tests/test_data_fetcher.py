"""
数据获取模块测试
测试 data_fetcher.py 中的所有功能
"""
import pytest
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, mock_open

from src.data_fetcher import DataFetcher


@pytest.fixture
def sample_stock_data():
    """创建示例股票数据"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    df = pd.DataFrame({
        'trade_date': dates,
        'open': np.random.uniform(95, 105, 100),
        'close': np.random.uniform(95, 105, 100),
        'high': np.random.uniform(100, 110, 100),
        'low': np.random.uniform(90, 100, 100),
        'vol': np.random.randint(1000000, 10000000, 100),
        'amount': np.random.uniform(1e8, 1e9, 100)
    })
    df.set_index('trade_date', inplace=True)
    return df


class TestDataFetcherInit:
    """测试DataFetcher初始化"""

    def test_init_default_params(self):
        """测试默认参数初始化"""
        fetcher = DataFetcher()
        assert fetcher.data_source is not None

    def test_init_with_tushare_token(self):
        """测试使用Tushare token初始化"""
        with patch('src.data_fetcher.ts.set_token') as mock_set_token:
            with patch('src.data_fetcher.ts.pro_api') as mock_pro_api:
                fetcher = DataFetcher(tushare_token='test_token')
                mock_set_token.assert_called_once_with('test_token')
                assert fetcher.tushare_token == 'test_token'

    def test_init_with_data_source(self):
        """测试指定数据源初始化"""
        fetcher = DataFetcher(data_source='akshare')
        assert fetcher.data_source == 'akshare'

        fetcher = DataFetcher(data_source='yfinance')
        assert fetcher.data_source == 'yfinance'

    def test_init_without_tushare_token(self):
        """测试没有Tushare token的初始化"""
        with patch('src.data_fetcher.settings') as mock_settings:
            mock_settings.data_source.tushare_token = None
            fetcher = DataFetcher()
            assert fetcher.pro is None


class TestFetchYfinanceData:
    """测试yfinance数据获取"""

    @patch('src.data_fetcher.yf.Ticker')
    def test_fetch_yfinance_data_success(self, mock_ticker):
        """测试成功获取yfinance数据"""
        mock_data = pd.DataFrame({
            'Close': [100, 101, 102],
            'High': [101, 102, 103],
            'Low': [99, 100, 101],
            'Volume': [1000000, 1100000, 1200000]
        })
        mock_ticker.return_value.history.return_value = mock_data

        fetcher = DataFetcher()
        result = fetcher.fetch_yfinance_data('AAPL', period='1y', interval='1d')

        assert result is not None
        assert len(result) == 3
        assert 'Close' in result.columns
        mock_ticker.assert_called_once_with('AAPL')

    @patch('src.data_fetcher.yf.Ticker')
    def test_fetch_yfinance_data_default_params(self, mock_ticker):
        """测试使用默认参数"""
        mock_ticker.return_value.history.return_value = pd.DataFrame()

        fetcher = DataFetcher()
        result = fetcher.fetch_yfinance_data('AAPL')

        mock_ticker.return_value.history.assert_called_once_with(period='1y', interval='1d')

    @patch('src.data_fetcher.yf.Ticker')
    def test_fetch_yfinance_data_error(self, mock_ticker):
        """测试获取数据时发生错误"""
        mock_ticker.side_effect = Exception('Network error')

        fetcher = DataFetcher()
        result = fetcher.fetch_yfinance_data('INVALID')

        assert result is None

    @patch('src.data_fetcher.yf.Ticker')
    def test_fetch_yfinance_data_empty(self, mock_ticker):
        """测试返回空数据"""
        mock_ticker.return_value.history.return_value = pd.DataFrame()

        fetcher = DataFetcher()
        result = fetcher.fetch_yfinance_data('AAPL')

        assert result is not None
        assert len(result) == 0


class TestFetchAkshareData:
    """测试akshare数据获取"""

    @patch('src.data_fetcher.ak.stock_zh_a_hist')
    def test_fetch_akshare_data_success(self, mock_ak):
        """测试成功获取akshare数据"""
        mock_data = pd.DataFrame({
            '日期': ['2024-01-01', '2024-01-02', '2024-01-03'],
            '开盘': [100, 101, 102],
            '收盘': [101, 102, 103],
            '最高': [102, 103, 104],
            '最低': [99, 100, 101],
            '成交量': [1000000, 1100000, 1200000],
            '成交额': [1e8, 1.1e8, 1.2e8],
            '振幅': [1.5, 1.6, 1.7],
            '涨跌幅': [1.0, 1.0, 1.0],
            '涨跌额': [1.0, 1.0, 1.0],
            '换手率': [2.0, 2.1, 2.2]
        })
        mock_ak.return_value = mock_data

        fetcher = DataFetcher()
        result = fetcher.fetch_akshare_data('000001', start_date='20240101', end_date='20240331')

        assert result is not None
        assert len(result) == 3
        assert 'close' in result.columns
        assert 'open' in result.columns

    @patch('src.data_fetcher.ak.stock_zh_a_hist')
    def test_fetch_akshare_data_default_dates(self, mock_ak):
        """测试使用默认日期"""
        mock_ak.return_value = pd.DataFrame({
            '日期': ['2024-01-01'],
            '开盘': [100],
            '收盘': [101],
            '最高': [102],
            '最低': [99],
            '成交量': [1000000],
            '成交额': [1e8]
        })

        fetcher = DataFetcher()
        result = fetcher.fetch_akshare_data('000001')

        assert result is not None
        mock_ak.assert_called_once()

    @patch('src.data_fetcher.ak.stock_zh_a_hist')
    def test_fetch_akshare_data_with_exchange_suffix(self, mock_ak):
        """测试带交易所后缀的股票代码"""
        mock_ak.return_value = pd.DataFrame({
            '日期': ['2024-01-01'],
            '开盘': [100],
            '收盘': [101],
            '最高': [102],
            '最低': [99],
            '成交量': [1000000],
            '成交额': [1e8]
        })

        fetcher = DataFetcher()
        result = fetcher.fetch_akshare_data('000001.SZ')

        # 应该去除.SZ后缀
        assert result is not None
        call_args = mock_ak.call_args
        assert '.' not in call_args[1]['symbol']

    @patch('src.data_fetcher.ak.stock_zh_a_hist')
    def test_fetch_akshare_data_date_format_conversion(self, mock_ak):
        """测试日期格式转换"""
        mock_ak.return_value = pd.DataFrame({
            '日期': ['2024-01-01'],
            '开盘': [100],
            '收盘': [101],
            '最高': [102],
            '最低': [99],
            '成交量': [1000000],
            '成交额': [1e8]
        })

        fetcher = DataFetcher()
        # 使用带横线的日期格式
        result = fetcher.fetch_akshare_data('000001', start_date='2024-01-01', end_date='2024-03-31')

        assert result is not None
        # 验证日期格式被转换为YYYYMMDD
        call_args = mock_ak.call_args
        assert '-' not in call_args[1]['start_date']

    @patch('src.data_fetcher.ak.stock_zh_a_hist')
    def test_fetch_akshare_data_error(self, mock_ak):
        """测试获取数据时发生错误"""
        mock_ak.side_effect = Exception('API error')

        fetcher = DataFetcher()
        result = fetcher.fetch_akshare_data('000001')

        assert result is None

    @patch('src.data_fetcher.ak.stock_zh_a_hist')
    def test_fetch_akshare_data_empty(self, mock_ak):
        """测试返回空数据"""
        mock_ak.return_value = None

        fetcher = DataFetcher()
        result = fetcher.fetch_akshare_data('000001')

        assert result is None

    @patch('src.data_fetcher.ak.stock_zh_a_hist')
    def test_fetch_akshare_data_different_adjust(self, mock_ak):
        """测试不同复权类型"""
        mock_ak.return_value = pd.DataFrame({
            '日期': ['2024-01-01'],
            '开盘': [100],
            '收盘': [101],
            '最高': [102],
            '最低': [99],
            '成交量': [1000000],
            '成交额': [1e8]
        })

        fetcher = DataFetcher()

        # 测试前复权
        result = fetcher.fetch_akshare_data('000001', adjust='qfq')
        assert result is not None

        # 测试后复权
        result = fetcher.fetch_akshare_data('000001', adjust='hfq')
        assert result is not None

        # 测试不复权
        result = fetcher.fetch_akshare_data('000001', adjust='')
        assert result is not None


class TestFetchTushareData:
    """测试tushare数据获取"""

    def test_fetch_tushare_data_no_token(self):
        """测试没有token的情况"""
        fetcher = DataFetcher(tushare_token=None)
        result = fetcher.fetch_tushare_data('000001.SZ')

        assert result is None

    @patch('src.data_fetcher.ts.pro_api')
    def test_fetch_tushare_data_success(self, mock_pro_api):
        """测试成功获取tushare数据"""
        mock_df = pd.DataFrame({
            'trade_date': ['20240101', '20240102', '20240103'],
            'open': [100, 101, 102],
            'close': [101, 102, 103],
            'high': [102, 103, 104],
            'low': [99, 100, 101],
            'vol': [1000000, 1100000, 1200000]
        })
        mock_pro_api.return_value.daily.return_value = mock_df

        with patch('src.data_fetcher.ts.set_token'):
            fetcher = DataFetcher(tushare_token='test_token')
            result = fetcher.fetch_tushare_data('000001.SZ')

        assert result is not None
        assert len(result) == 3

    @patch('src.data_fetcher.ts.pro_api')
    def test_fetch_tushare_data_default_dates(self, mock_pro_api):
        """测试使用默认日期"""
        mock_pro_api.return_value.daily.return_value = pd.DataFrame({
            'trade_date': ['20240101'],
            'close': [100]
        })

        with patch('src.data_fetcher.ts.set_token'):
            fetcher = DataFetcher(tushare_token='test_token')
            result = fetcher.fetch_tushare_data('000001.SZ')

        assert result is not None

    @patch('src.data_fetcher.ts.pro_api')
    def test_fetch_tushare_data_error(self, mock_pro_api):
        """测试获取数据时发生错误"""
        mock_pro_api.return_value.daily.side_effect = Exception('API error')

        with patch('src.data_fetcher.ts.set_token'):
            fetcher = DataFetcher(tushare_token='test_token')
            result = fetcher.fetch_tushare_data('000001.SZ')

        assert result is None


class TestFetchData:
    """测试智能数据获取"""

    @patch.object(DataFetcher, 'fetch_akshare_data')
    def test_fetch_data_akshare(self, mock_akshare):
        """测试使用akshare作为主要数据源"""
        mock_akshare.return_value = pd.DataFrame({'close': [100, 101, 102]})

        fetcher = DataFetcher(data_source='akshare')
        result = fetcher.fetch_data('000001')

        assert result is not None
        mock_akshare.assert_called_once()

    @patch.object(DataFetcher, 'fetch_tushare_data')
    @patch.object(DataFetcher, 'fetch_akshare_data')
    def test_fetch_data_akshare_fallback_to_tushare(self, mock_akshare, mock_tushare):
        """测试akshare失败后fallback到tushare"""
        mock_akshare.return_value = None
        mock_tushare.return_value = pd.DataFrame({'close': [100, 101, 102]})

        with patch('src.data_fetcher.ts.set_token'):
            fetcher = DataFetcher(data_source='akshare', tushare_token='test_token')
            result = fetcher.fetch_data('000001')

        assert result is not None
        mock_akshare.assert_called_once()
        mock_tushare.assert_called_once()

    @patch.object(DataFetcher, 'fetch_tushare_data')
    def test_fetch_data_tushare(self, mock_tushare):
        """测试使用tushare作为主要数据源"""
        mock_tushare.return_value = pd.DataFrame({'close': [100, 101, 102]})

        with patch('src.data_fetcher.ts.set_token'):
            fetcher = DataFetcher(data_source='tushare', tushare_token='test_token')
            result = fetcher.fetch_data('000001')

        assert result is not None
        mock_tushare.assert_called_once()

    @patch.object(DataFetcher, 'fetch_akshare_data')
    @patch.object(DataFetcher, 'fetch_tushare_data')
    def test_fetch_data_tushare_fallback_to_akshare(self, mock_tushare, mock_akshare):
        """测试tushare失败后fallback到akshare"""
        mock_tushare.return_value = None
        mock_akshare.return_value = pd.DataFrame({'close': [100, 101, 102]})

        with patch('src.data_fetcher.ts.set_token'):
            fetcher = DataFetcher(data_source='tushare', tushare_token='test_token')
            result = fetcher.fetch_data('000001')

        assert result is not None
        mock_tushare.assert_called_once()
        mock_akshare.assert_called_once()

    @patch.object(DataFetcher, 'fetch_yfinance_data')
    def test_fetch_data_yfinance(self, mock_yfinance):
        """测试使用yfinance作为主要数据源"""
        mock_yfinance.return_value = pd.DataFrame({'Close': [100, 101, 102]})

        fetcher = DataFetcher(data_source='yfinance')
        result = fetcher.fetch_data('AAPL', period='1y', interval='1d')

        assert result is not None
        mock_yfinance.assert_called_once()

    @patch.object(DataFetcher, 'fetch_akshare_data')
    def test_fetch_data_unknown_source(self, mock_akshare):
        """测试未知数据源，默认使用akshare"""
        mock_akshare.return_value = pd.DataFrame({'close': [100, 101, 102]})

        fetcher = DataFetcher(data_source='unknown')
        result = fetcher.fetch_data('000001')

        assert result is not None
        mock_akshare.assert_called_once()


class TestSaveAndLoadData:
    """测试数据保存和加载"""

    @patch('src.data_fetcher.os.path.join')
    def test_save_data_to_csv_success(self, mock_join):
        """测试成功保存CSV"""
        mock_join.return_value = '/tmp/test.csv'

        df = pd.DataFrame({'Close': [100, 101, 102]})

        with patch.object(pd.DataFrame, 'to_csv') as mock_to_csv:
            fetcher = DataFetcher()
            result = fetcher.save_data_to_csv(df, 'test.csv')

        assert result == '/tmp/test.csv'
        mock_to_csv.assert_called_once()

    def test_save_data_to_csv_none_data(self):
        """测试保存None数据"""
        fetcher = DataFetcher()
        result = fetcher.save_data_to_csv(None, 'test.csv')

        assert result is None

    @patch('src.data_fetcher.os.path.exists')
    @patch('src.data_fetcher.pd.read_csv')
    @patch('src.data_fetcher.os.path.join')
    def test_load_data_from_csv_success(self, mock_join, mock_read_csv, mock_exists):
        """测试成功加载CSV"""
        mock_join.return_value = '/tmp/test.csv'
        mock_exists.return_value = True
        mock_read_csv.return_value = pd.DataFrame({'Close': [100, 101, 102]})

        fetcher = DataFetcher()
        result = fetcher.load_data_from_csv('test.csv')

        assert result is not None
        assert len(result) == 3
        mock_read_csv.assert_called_once()

    @patch('src.data_fetcher.os.path.exists')
    @patch('src.data_fetcher.os.path.join')
    def test_load_data_from_csv_file_not_exists(self, mock_join, mock_exists):
        """测试文件不存在"""
        mock_join.return_value = '/tmp/test.csv'
        mock_exists.return_value = False

        fetcher = DataFetcher()
        result = fetcher.load_data_from_csv('test.csv')

        assert result is None


class TestEdgeCases:
    """测试边缘情况"""

    @patch('src.data_fetcher.yf.Ticker')
    def test_fetch_yfinance_special_symbols(self, mock_ticker):
        """测试特殊股票代码"""
        mock_ticker.return_value.history.return_value = pd.DataFrame()

        fetcher = DataFetcher()

        # 测试各种特殊代码
        symbols = ['AAPL', 'BRK-B', '600000.SS', '000001.SZ', '^GSPC']
        for symbol in symbols:
            result = fetcher.fetch_yfinance_data(symbol)
            # 不应该崩溃

    @patch('src.data_fetcher.ak.stock_zh_a_hist')
    def test_fetch_akshare_malformed_data(self, mock_ak):
        """测试格式错误的数据"""
        # 返回列名不匹配的数据
        mock_ak.return_value = pd.DataFrame({
            'unknown_col': [1, 2, 3]
        })

        fetcher = DataFetcher()
        # 不应该崩溃
        result = fetcher.fetch_akshare_data('000001')

    def test_save_data_empty_dataframe(self):
        """测试保存空DataFrame"""
        df = pd.DataFrame()

        with patch.object(pd.DataFrame, 'to_csv') as mock_to_csv:
            with patch('src.data_fetcher.os.path.join', return_value='/tmp/test.csv'):
                fetcher = DataFetcher()
                result = fetcher.save_data_to_csv(df, 'test.csv')

        assert result == '/tmp/test.csv'


class TestIntegration:
    """集成测试"""

    @patch('src.data_fetcher.ak.stock_zh_a_hist')
    def test_full_akshare_workflow(self, mock_ak):
        """测试完整的akshare工作流程"""
        mock_data = pd.DataFrame({
            '日期': ['2024-01-01', '2024-01-02'],
            '开盘': [100, 101],
            '收盘': [101, 102],
            '最高': [102, 103],
            '最低': [99, 100],
            '成交量': [1000000, 1100000],
            '成交额': [1e8, 1.1e8]
        })
        mock_ak.return_value = mock_data

        fetcher = DataFetcher(data_source='akshare')

        # 1. 获取数据
        data = fetcher.fetch_data('000001', start_date='20240101', end_date='20240331')

        # 2. 验证数据
        assert data is not None
        assert len(data) == 2
        assert 'close' in data.columns

        # 3. 保存数据
        with patch.object(pd.DataFrame, 'to_csv'):
            with patch('src.data_fetcher.os.path.join', return_value='/tmp/test.csv'):
                path = fetcher.save_data_to_csv(data, 'test.csv')
                assert path is not None

    @patch('src.data_fetcher.yf.Ticker')
    def test_multiple_fetches_same_fetcher(self, mock_ticker):
        """测试使用同一个fetcher多次获取数据"""
        mock_ticker.return_value.history.return_value = pd.DataFrame({
            'Close': [100, 101, 102]
        })

        fetcher = DataFetcher(data_source='yfinance')

        # 多次获取不同股票
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        for symbol in symbols:
            result = fetcher.fetch_yfinance_data(symbol)
            assert result is not None
            assert len(result) == 3
