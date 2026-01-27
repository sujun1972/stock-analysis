"""
主程序模块测试
测试 main.py 中的所有功能
"""
import pytest
import pandas as pd
import numpy as np
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, mock_open
from io import StringIO

from src.main import (
    get_safe_value,
    generate_trading_signal,
    generate_report,
    analyze_symbol,
    load_stock_symbols,
    main,
    get_ai_analysis
)
from src.data_fetcher import DataFetcher
from src.technical_analysis import TechnicalAnalyzer


@pytest.fixture
def sample_analysis_df():
    """创建用于测试的分析结果DataFrame"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    np.random.seed(42)

    df = pd.DataFrame({
        'Close': 100 + np.cumsum(np.random.randn(100) * 2),
        'High': 101 + np.cumsum(np.random.randn(100) * 2),
        'Low': 99 + np.cumsum(np.random.randn(100) * 2),
        'Volume': np.random.randint(1000000, 10000000, 100),
        'SMA_20': 100 + np.cumsum(np.random.randn(100) * 1.5),
        'SMA_50': 100 + np.cumsum(np.random.randn(100) * 1.2),
        'RSI_14': np.random.uniform(30, 70, 100),
        'MACD': np.random.randn(100),
        'MACD_signal': np.random.randn(100),
        'BB_upper': 105 + np.cumsum(np.random.randn(100) * 2),
        'BB_lower': 95 + np.cumsum(np.random.randn(100) * 2),
        'composite_signal': np.random.randint(-3, 4, 100)
    }, index=dates)

    return df


class TestGetSafeValue:
    """测试 get_safe_value 函数"""

    def test_get_safe_value_normal(self):
        """测试正常情况"""
        df = pd.DataFrame({'Close': [100, 101, 102, 103, 104]})
        value = get_safe_value(df, 'Close')
        assert value == 104

    def test_get_safe_value_with_nan(self):
        """测试包含NaN的情况"""
        df = pd.DataFrame({'Close': [100, 101, np.nan, 103, 104]})
        value = get_safe_value(df, 'Close')
        assert value == 104

    def test_get_safe_value_all_nan(self):
        """测试全是NaN的情况"""
        df = pd.DataFrame({'Close': [np.nan, np.nan, np.nan]})
        value = get_safe_value(df, 'Close')
        assert value is None

    def test_get_safe_value_column_not_exist(self):
        """测试列不存在的情况"""
        df = pd.DataFrame({'Open': [100, 101, 102]})
        value = get_safe_value(df, 'Close')
        assert value is None

    def test_get_safe_value_empty_dataframe(self):
        """测试空DataFrame"""
        df = pd.DataFrame()
        value = get_safe_value(df, 'Close')
        assert value is None

    def test_get_safe_value_single_value(self):
        """测试单个值"""
        df = pd.DataFrame({'Close': [100]})
        value = get_safe_value(df, 'Close')
        assert value == 100

    def test_get_safe_value_numpy_types(self):
        """测试numpy类型"""
        df = pd.DataFrame({'Close': np.array([100.5, 101.5, 102.5])})
        value = get_safe_value(df, 'Close')
        assert isinstance(value, (int, float))
        assert abs(value - 102.5) < 0.01


class TestGenerateTradingSignal:
    """测试交易信号生成"""

    def test_generate_trading_signal_bullish(self):
        """测试看涨信号"""
        df = pd.DataFrame({
            'Close': [100],
            'SMA_20': [102],  # SMA20 > SMA50
            'SMA_50': [98],
            'RSI_14': [25],   # RSI < 30
            'MACD': [1],      # MACD > signal
            'MACD_signal': [0],
            'BB_upper': [110],
            'BB_lower': [90]  # Close <= BB_lower
        })

        signal = generate_trading_signal(df, 'TEST')

        assert signal is not None
        assert signal['buy_signals'] > signal['sell_signals']
        assert 'recommendation' in signal
        assert signal['confidence'] in ['低', '中', '高']

    def test_generate_trading_signal_bearish(self):
        """测试看跌信号"""
        df = pd.DataFrame({
            'Close': [110],   # Close >= BB_upper
            'SMA_20': [98],   # SMA20 < SMA50
            'SMA_50': [102],
            'RSI_14': [75],   # RSI > 70
            'MACD': [0],      # MACD < signal
            'MACD_signal': [1],
            'BB_upper': [110],
            'BB_lower': [90]
        })

        signal = generate_trading_signal(df, 'TEST')

        assert signal is not None
        assert signal['sell_signals'] > signal['buy_signals']
        assert 'SELL' in signal['recommendation'] or 'HOLD' in signal['recommendation']

    def test_generate_trading_signal_neutral(self):
        """测试中性信号"""
        df = pd.DataFrame({
            'Close': [100],
            'SMA_20': [100],
            'SMA_50': [100],
            'RSI_14': [50],   # RSI在正常区域
            'MACD': [0],
            'MACD_signal': [0],
            'BB_upper': [110],
            'BB_lower': [90]
        })

        signal = generate_trading_signal(df, 'TEST')

        assert signal is not None
        # 中性信号较多
        assert signal['neutral_signals'] >= 0

    def test_generate_trading_signal_missing_indicators(self):
        """测试缺少指标的情况"""
        df = pd.DataFrame({
            'Close': [100]
        })

        signal = generate_trading_signal(df, 'TEST')
        # 可能返回None或信号数为0

    @patch('src.main.logger')
    def test_generate_trading_signal_logging(self, mock_logger):
        """测试日志记录"""
        df = pd.DataFrame({
            'Close': [100],
            'SMA_20': [102],
            'SMA_50': [98],
            'RSI_14': [50],
            'MACD': [1],
            'MACD_signal': [0],
            'BB_upper': [110],
            'BB_lower': [90]
        })

        generate_trading_signal(df, 'TEST')

        # 验证日志调用
        assert mock_logger.info.called or mock_logger.success.called

    def test_generate_trading_signal_empty_df(self):
        """测试空DataFrame"""
        df = pd.DataFrame()
        signal = generate_trading_signal(df, 'TEST')
        # 不应该崩溃


class TestGenerateReport:
    """测试报告生成"""

    def test_generate_report_normal(self, sample_analysis_df):
        """测试正常报告生成"""
        # 不应该抛出异常
        generate_report(sample_analysis_df, 'TEST')
        assert True

    def test_generate_report_empty_df(self):
        """测试空DataFrame"""
        df = pd.DataFrame()
        generate_report(df, 'TEST')
        # 不应该抛出异常

    def test_generate_report_minimal_data(self):
        """测试最小数据集"""
        df = pd.DataFrame({
            'Close': [100]
        })
        generate_report(df, 'TEST')
        # 不应该抛出异常

    def test_generate_report_with_lowercase_columns(self):
        """测试小写列名"""
        df = pd.DataFrame({
            'close': [100],
            'open': [99]
        })
        generate_report(df, 'TEST')
        # 不应该抛出异常

    @patch('src.main.logger')
    def test_generate_report_logging(self, mock_logger, sample_analysis_df):
        """测试日志记录"""
        generate_report(sample_analysis_df, 'TEST')

        # 验证日志调用
        assert mock_logger.info.called

    def test_generate_report_all_indicators(self, sample_analysis_df):
        """测试包含所有指标的报告"""
        generate_report(sample_analysis_df, 'TEST')
        # 验证不崩溃


class TestAnalyzeSymbol:
    """测试单个股票分析"""

    @patch.object(TechnicalAnalyzer, 'plot_analysis')
    @patch.object(DataFetcher, 'save_data_to_csv')
    @patch.object(TechnicalAnalyzer, 'comprehensive_analysis')
    @patch.object(DataFetcher, 'fetch_yfinance_data')
    def test_analyze_symbol_yfinance(self, mock_fetch, mock_analysis,
                                     mock_save, mock_plot):
        """测试使用yfinance分析股票"""
        # 设置mock返回值
        mock_df = pd.DataFrame({
            'Close': [100, 101, 102],
            'High': [101, 102, 103],
            'Low': [99, 100, 101],
            'Volume': [1000000, 1100000, 1200000]
        })
        mock_fetch.return_value = mock_df
        mock_analysis.return_value = mock_df
        mock_save.return_value = '/tmp/test.csv'

        fetcher = DataFetcher()
        analyzer = TechnicalAnalyzer()

        result = analyze_symbol('AAPL', fetcher, analyzer, period='6mo', use_tushare=False)

        assert result is not None
        assert result['symbol'] == 'AAPL'
        assert 'csv_path' in result
        assert 'chart_path' in result
        assert 'trading_signal' in result
        mock_fetch.assert_called_once()
        mock_analysis.assert_called_once()

    @patch.object(TechnicalAnalyzer, 'plot_analysis')
    @patch.object(DataFetcher, 'save_data_to_csv')
    @patch.object(TechnicalAnalyzer, 'comprehensive_analysis')
    @patch.object(DataFetcher, 'fetch_tushare_data')
    def test_analyze_symbol_tushare(self, mock_fetch, mock_analysis,
                                    mock_save, mock_plot):
        """测试使用tushare分析股票"""
        mock_df = pd.DataFrame({
            'close': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'vol': [1000000, 1100000, 1200000]
        })
        mock_fetch.return_value = mock_df
        mock_analysis.return_value = mock_df
        mock_save.return_value = '/tmp/test.csv'

        fetcher = DataFetcher()
        analyzer = TechnicalAnalyzer()

        result = analyze_symbol('000001.SZ', fetcher, analyzer, period='6mo', use_tushare=True)

        assert result is not None
        mock_fetch.assert_called_once()

    @patch.object(DataFetcher, 'fetch_yfinance_data')
    def test_analyze_symbol_no_data(self, mock_fetch):
        """测试无法获取数据的情况"""
        mock_fetch.return_value = None

        fetcher = DataFetcher()
        analyzer = TechnicalAnalyzer()

        result = analyze_symbol('INVALID', fetcher, analyzer)

        assert result is None

    @patch.object(DataFetcher, 'fetch_yfinance_data')
    def test_analyze_symbol_empty_data(self, mock_fetch):
        """测试空数据的情况"""
        mock_fetch.return_value = pd.DataFrame()

        fetcher = DataFetcher()
        analyzer = TechnicalAnalyzer()

        result = analyze_symbol('TEST', fetcher, analyzer)

        assert result is None

    @patch.object(DataFetcher, 'save_data_to_csv')
    @patch.object(TechnicalAnalyzer, 'comprehensive_analysis')
    @patch.object(DataFetcher, 'fetch_yfinance_data')
    def test_analyze_symbol_save_fails(self, mock_fetch, mock_analysis, mock_save):
        """测试保存CSV失败的情况"""
        mock_df = pd.DataFrame({'Close': [100, 101, 102]})
        mock_fetch.return_value = mock_df
        mock_analysis.return_value = mock_df
        mock_save.return_value = None  # 保存失败

        fetcher = DataFetcher()
        analyzer = TechnicalAnalyzer()

        result = analyze_symbol('TEST', fetcher, analyzer)

        assert result is None

    @patch.object(TechnicalAnalyzer, 'comprehensive_analysis')
    @patch.object(DataFetcher, 'fetch_yfinance_data')
    def test_analyze_symbol_empty_analysis(self, mock_fetch, mock_analysis):
        """测试分析结果为空的情况"""
        mock_df = pd.DataFrame({'Close': [100, 101, 102]})
        mock_fetch.return_value = mock_df
        mock_analysis.return_value = pd.DataFrame()  # 空分析结果

        fetcher = DataFetcher()
        analyzer = TechnicalAnalyzer()

        result = analyze_symbol('TEST', fetcher, analyzer)

        assert result is None


class TestLoadStockSymbols:
    """测试股票代码列表加载"""

    @patch('src.main.pd.read_csv')
    @patch('src.main.os.path.join')
    def test_load_stock_symbols_success(self, mock_join, mock_read_csv):
        """测试成功加载股票代码"""
        mock_join.return_value = '/tmp/a_stock_list.csv'
        mock_read_csv.return_value = pd.DataFrame({
            'code': ['000001', '000002', '600000']
        })

        symbols = load_stock_symbols()

        assert len(symbols) == 3
        assert '000001' in symbols
        assert '000002' in symbols
        assert '600000' in symbols

    @patch('src.main.pd.read_csv')
    @patch('src.main.os.path.join')
    def test_load_stock_symbols_with_nan(self, mock_join, mock_read_csv):
        """测试包含NaN的情况"""
        mock_join.return_value = '/tmp/a_stock_list.csv'
        mock_read_csv.return_value = pd.DataFrame({
            'code': ['000001', np.nan, '600000']
        })

        symbols = load_stock_symbols()

        assert len(symbols) == 2
        assert '000001' in symbols
        assert '600000' in symbols

    @patch('src.main.pd.read_csv')
    @patch('src.main.os.path.join')
    def test_load_stock_symbols_file_not_found(self, mock_join, mock_read_csv):
        """测试文件不存在"""
        mock_join.return_value = '/tmp/a_stock_list.csv'
        mock_read_csv.side_effect = FileNotFoundError('File not found')

        symbols = load_stock_symbols()

        assert symbols == []

    @patch('src.main.pd.read_csv')
    @patch('src.main.os.path.join')
    def test_load_stock_symbols_empty_file(self, mock_join, mock_read_csv):
        """测试空文件"""
        mock_join.return_value = '/tmp/a_stock_list.csv'
        mock_read_csv.return_value = pd.DataFrame()

        symbols = load_stock_symbols()

        assert symbols == []

    @patch('src.main.pd.read_csv')
    @patch('src.main.os.path.join')
    def test_load_stock_symbols_all_nan(self, mock_join, mock_read_csv):
        """测试全是NaN的情况"""
        mock_join.return_value = '/tmp/a_stock_list.csv'
        mock_read_csv.return_value = pd.DataFrame({
            'code': [np.nan, np.nan, np.nan]
        })

        symbols = load_stock_symbols()

        assert symbols == []


class TestGetAiAnalysis:
    """测试AI分析功能"""

    @patch('src.main.deepseek_client')
    def test_get_ai_analysis_success(self, mock_client):
        """测试成功获取AI分析"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "这是AI分析报告"

        mock_client.chat.completions.create.return_value = mock_response

        df = pd.DataFrame({'Close': [100, 101, 102]})
        trading_signal = {'recommendation': 'BUY'}

        result = get_ai_analysis('TEST', df, trading_signal)

        assert result == "这是AI分析报告"

    @patch('src.main.deepseek_client', None)
    def test_get_ai_analysis_no_client(self):
        """测试没有配置API Key的情况"""
        df = pd.DataFrame({'Close': [100, 101, 102]})
        trading_signal = {'recommendation': 'BUY'}

        result = get_ai_analysis('TEST', df, trading_signal)

        assert result is None

    @patch('src.main.deepseek_client')
    def test_get_ai_analysis_api_error(self, mock_client):
        """测试API调用失败"""
        mock_client.chat.completions.create.side_effect = Exception('API Error')

        df = pd.DataFrame({'Close': [100, 101, 102]})
        trading_signal = {'recommendation': 'BUY'}

        result = get_ai_analysis('TEST', df, trading_signal)

        assert result is None


class TestMain:
    """测试主函数"""

    @patch('src.main.analyze_symbol')
    @patch('src.main.load_stock_symbols')
    @patch('src.main.TechnicalAnalyzer')
    @patch('src.main.DataFetcher')
    def test_main_success(self, mock_fetcher, mock_analyzer,
                         mock_load, mock_analyze):
        """测试主函数成功执行"""
        mock_load.return_value = ['000001', '000002']
        mock_analyze.return_value = {
            'symbol': '000001',
            'csv_path': '/tmp/test.csv',
            'chart_path': '/tmp/test.png',
            'trading_signal': {'recommendation': 'BUY'},
            'analysis_df': pd.DataFrame({'Close': [100]})
        }

        # 不应该抛出异常
        main()

        assert mock_load.called
        assert mock_fetcher.called
        assert mock_analyzer.called

    @patch('src.main.load_stock_symbols')
    @patch('src.main.TechnicalAnalyzer')
    @patch('src.main.DataFetcher')
    def test_main_no_symbols(self, mock_fetcher, mock_analyzer, mock_load):
        """测试没有股票代码的情况"""
        mock_load.return_value = []

        # 不应该抛出异常
        main()

        assert mock_load.called

    @patch('src.main.analyze_symbol')
    @patch('src.main.load_stock_symbols')
    @patch('src.main.TechnicalAnalyzer')
    @patch('src.main.DataFetcher')
    def test_main_analyze_fails(self, mock_fetcher, mock_analyzer,
                                mock_load, mock_analyze):
        """测试分析失败的情况"""
        mock_load.return_value = ['000001']
        mock_analyze.return_value = None  # 分析失败

        # 不应该抛出异常
        main()

        assert mock_analyze.called

    @patch('src.main.analyze_symbol')
    @patch('src.main.load_stock_symbols')
    @patch('src.main.TechnicalAnalyzer')
    @patch('src.main.DataFetcher')
    def test_main_multiple_symbols(self, mock_fetcher, mock_analyzer,
                                   mock_load, mock_analyze):
        """测试多个股票的情况"""
        mock_load.return_value = ['000001', '000002', '600000']
        mock_analyze.return_value = {
            'symbol': '000001',
            'csv_path': '/tmp/test.csv',
            'chart_path': '/tmp/test.png',
            'trading_signal': {'recommendation': 'BUY'},
            'analysis_df': pd.DataFrame({'Close': [100]})
        }

        main()

        # 应该调用3次analyze_symbol
        assert mock_analyze.call_count == 3


class TestIntegration:
    """集成测试"""

    @patch('src.main.plt.savefig')
    @patch('src.main.os.path.join')
    def test_full_analysis_workflow(self, mock_join, mock_savefig):
        """测试完整的分析工作流程"""
        # 创建测试数据
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'Close': np.random.randn(100) + 100,
            'High': np.random.randn(100) + 101,
            'Low': np.random.randn(100) + 99,
            'Volume': np.random.randint(1000000, 10000000, 100)
        }, index=dates)

        analyzer = TechnicalAnalyzer()

        # 1. 综合分析
        result = analyzer.comprehensive_analysis(df)

        # 2. 生成报告
        generate_report(result, 'TEST')

        # 3. 生成交易信号
        signal = generate_trading_signal(result, 'TEST')

        # 验证
        assert result is not None
        assert len(result) == 100
        assert signal is not None

    def test_get_safe_value_with_real_dataframe(self):
        """测试get_safe_value处理真实DataFrame"""
        df = pd.DataFrame({
            'Close': [100.5, 101.2, np.nan, 103.7, 104.1],
            'Open': [100.0, 101.0, 102.0, 103.0, 104.0]
        })

        close_value = get_safe_value(df, 'Close')
        open_value = get_safe_value(df, 'Open')

        assert close_value == 104.1
        assert open_value == 104.0


class TestEdgeCases:
    """测试边缘情况"""

    def test_generate_trading_signal_with_inf(self):
        """测试包含无穷大值的情况"""
        df = pd.DataFrame({
            'Close': [100],
            'SMA_20': [np.inf],
            'SMA_50': [100],
            'RSI_14': [50],
            'MACD': [1],
            'MACD_signal': [0]
        })

        # 不应该崩溃
        signal = generate_trading_signal(df, 'TEST')

    def test_generate_report_with_negative_values(self):
        """测试包含负值的情况"""
        df = pd.DataFrame({
            'Close': [-100],
            'RSI_14': [-10],
            'MACD': [-5]
        })

        # 不应该崩溃
        generate_report(df, 'TEST')

    def test_get_safe_value_with_series(self):
        """测试返回Series的情况"""
        df = pd.DataFrame({
            'Close': [[1, 2, 3], [4, 5, 6]]
        })

        # 不应该崩溃
        value = get_safe_value(df, 'Close')

    @patch('src.main.logger')
    def test_analyze_symbol_logs_errors(self, mock_logger):
        """测试analyze_symbol记录错误"""
        fetcher = DataFetcher()
        analyzer = TechnicalAnalyzer()

        with patch.object(fetcher, 'fetch_yfinance_data', side_effect=Exception('Test error')):
            result = analyze_symbol('TEST', fetcher, analyzer)

        # 可能返回None或记录错误
