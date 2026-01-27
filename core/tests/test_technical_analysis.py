"""
技术分析模块测试
测试 technical_analysis.py 中的所有功能
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端，避免图表显示问题

from src.technical_analysis import TechnicalAnalyzer


@pytest.fixture
def sample_dataframe():
    """创建用于测试的示例DataFrame"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    np.random.seed(42)

    # 创建真实的价格数据
    close_prices = 100 + np.cumsum(np.random.randn(100) * 2)
    high_prices = close_prices + np.abs(np.random.randn(100) * 1)
    low_prices = close_prices - np.abs(np.random.randn(100) * 1)
    open_prices = close_prices + np.random.randn(100) * 0.5
    volumes = np.random.randint(1000000, 10000000, 100)

    df = pd.DataFrame({
        'Close': close_prices,
        'High': high_prices,
        'Low': low_prices,
        'Open': open_prices,
        'Volume': volumes
    }, index=dates)

    return df


@pytest.fixture
def analyzer():
    """创建TechnicalAnalyzer实例"""
    return TechnicalAnalyzer()


class TestGetColumn:
    """测试_get_column方法"""

    def test_get_column_exact_match(self, analyzer):
        """测试完全匹配的列名"""
        df = pd.DataFrame({'Close': [1, 2, 3], 'Open': [4, 5, 6]})
        result = analyzer._get_column(df, 'Close')
        assert result is not None
        assert len(result) == 3
        assert list(result) == [1, 2, 3]

    def test_get_column_lowercase_fallback(self, analyzer):
        """测试小写列名的fallback"""
        df = pd.DataFrame({'close': [1, 2, 3], 'open': [4, 5, 6]})
        result = analyzer._get_column(df, 'Close')
        assert result is not None
        assert list(result) == [1, 2, 3]

    def test_get_column_not_found(self, analyzer):
        """测试列名不存在的情况"""
        df = pd.DataFrame({'Open': [1, 2, 3]})
        result = analyzer._get_column(df, 'Close')
        assert result is None

    def test_get_column_empty_dataframe(self, analyzer):
        """测试空DataFrame"""
        df = pd.DataFrame()
        result = analyzer._get_column(df, 'Close')
        assert result is None


class TestTrendIndicators:
    """测试趋势指标计算"""

    def test_calculate_trend_indicators_basic(self, analyzer, sample_dataframe):
        """测试基本趋势指标计算"""
        indicators = analyzer.calculate_trend_indicators(sample_dataframe)

        # 验证所有指标都存在
        assert 'SMA_5' in indicators
        assert 'SMA_20' in indicators
        assert 'SMA_50' in indicators
        assert 'EMA_12' in indicators
        assert 'EMA_26' in indicators
        assert 'BB_upper' in indicators
        assert 'BB_middle' in indicators
        assert 'BB_lower' in indicators

        # 验证指标长度与输入数据相同
        assert len(indicators['SMA_5']) == len(sample_dataframe)

        # 验证布林带关系
        last_idx = -1
        assert indicators['BB_upper'].iloc[last_idx] > indicators['BB_middle'].iloc[last_idx]
        assert indicators['BB_middle'].iloc[last_idx] > indicators['BB_lower'].iloc[last_idx]

    def test_calculate_trend_indicators_short_data(self, analyzer):
        """测试数据不足时的情况"""
        df = pd.DataFrame({
            'Close': [100, 101, 102],
            'High': [101, 102, 103],
            'Low': [99, 100, 101]
        })
        indicators = analyzer.calculate_trend_indicators(df)

        # 指标应该存在，但可能包含NaN
        assert 'SMA_5' in indicators
        assert 'SMA_20' in indicators

    def test_calculate_trend_indicators_lowercase_columns(self, analyzer):
        """测试小写列名"""
        df = pd.DataFrame({
            'close': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103]
        })
        indicators = analyzer.calculate_trend_indicators(df)
        assert 'SMA_5' in indicators

    def test_calculate_trend_indicators_missing_columns(self, analyzer):
        """测试缺少必需列"""
        df = pd.DataFrame({'Open': [100, 101, 102]})
        indicators = analyzer.calculate_trend_indicators(df)
        # 不应该抛出异常，但指标可能无法计算


class TestMomentumIndicators:
    """测试动量指标计算"""

    def test_calculate_momentum_indicators_basic(self, analyzer, sample_dataframe):
        """测试基本动量指标计算"""
        indicators = analyzer.calculate_momentum_indicators(sample_dataframe)

        # 验证所有指标都存在
        assert 'MACD' in indicators
        assert 'MACD_signal' in indicators
        assert 'MACD_hist' in indicators
        assert 'RSI_14' in indicators
        assert 'slowk' in indicators
        assert 'slowd' in indicators
        assert 'OBV' in indicators

        # 验证RSI范围 (0-100)
        rsi_valid = indicators['RSI_14'].dropna()
        if len(rsi_valid) > 0:
            assert (rsi_valid >= 0).all() and (rsi_valid <= 100).all()

    def test_calculate_momentum_indicators_no_volume(self, analyzer):
        """测试没有成交量数据的情况"""
        df = pd.DataFrame({
            'Close': np.random.randn(100) + 100,
            'High': np.random.randn(100) + 101,
            'Low': np.random.randn(100) + 99
        })
        indicators = analyzer.calculate_momentum_indicators(df)

        # MACD和RSI应该存在
        assert 'MACD' in indicators
        assert 'RSI_14' in indicators

        # OBV应该不存在或为None
        assert indicators.get('OBV') is None or 'OBV' not in indicators

    def test_calculate_momentum_indicators_with_volume(self, analyzer, sample_dataframe):
        """测试包含成交量数据的情况"""
        indicators = analyzer.calculate_momentum_indicators(sample_dataframe)
        assert 'OBV' in indicators
        assert indicators['OBV'] is not None


class TestVolatilityIndicators:
    """测试波动率指标计算"""

    def test_calculate_volatility_indicators_basic(self, analyzer, sample_dataframe):
        """测试基本波动率指标计算"""
        indicators = analyzer.calculate_volatility_indicators(sample_dataframe)

        # 验证ATR存在
        assert 'ATR_14' in indicators

        # ATR应该是正数
        atr_valid = indicators['ATR_14'].dropna()
        if len(atr_valid) > 0:
            assert (atr_valid >= 0).all()

    def test_calculate_volatility_indicators_minimal_data(self, analyzer):
        """测试最小数据集"""
        df = pd.DataFrame({
            'Close': [100, 101, 102],
            'High': [101, 102, 103],
            'Low': [99, 100, 101]
        })
        indicators = analyzer.calculate_volatility_indicators(df)
        assert 'ATR_14' in indicators


class TestSignalGeneration:
    """测试信号生成"""

    def test_generate_signals_basic(self, analyzer, sample_dataframe):
        """测试基本信号生成"""
        # 先计算指标
        indicators = analyzer.calculate_trend_indicators(sample_dataframe)
        indicators.update(analyzer.calculate_momentum_indicators(sample_dataframe))

        signals = analyzer.generate_signals(sample_dataframe, indicators)

        # 验证信号DataFrame结构
        assert isinstance(signals, pd.DataFrame)
        assert len(signals) == len(sample_dataframe)
        assert 'composite_signal' in signals.columns

    def test_generate_signals_macd(self, analyzer, sample_dataframe):
        """测试MACD信号"""
        indicators = {
            'MACD': pd.Series([1, 2, 3, -1, -2], index=sample_dataframe.index[:5]),
            'MACD_signal': pd.Series([0, 1, 2, -2, -1], index=sample_dataframe.index[:5])
        }

        df_short = sample_dataframe.iloc[:5]
        signals = analyzer.generate_signals(df_short, indicators)

        assert 'MACD_signal' in signals.columns

    def test_generate_signals_rsi(self, analyzer, sample_dataframe):
        """测试RSI信号"""
        indicators = {
            'RSI_14': pd.Series([25, 50, 75, 80, 20], index=sample_dataframe.index[:5])
        }

        df_short = sample_dataframe.iloc[:5]
        signals = analyzer.generate_signals(df_short, indicators)

        assert 'RSI_signal' in signals.columns
        # RSI < 30 应该是买入信号 (1)
        assert signals['RSI_signal'].iloc[0] == 1
        # RSI > 70 应该是卖出信号 (-1)
        assert signals['RSI_signal'].iloc[3] == -1

    def test_generate_signals_ma_cross(self, analyzer, sample_dataframe):
        """测试均线交叉信号"""
        indicators = {
            'SMA_20': pd.Series([100, 101, 102], index=sample_dataframe.index[:3]),
            'SMA_50': pd.Series([99, 100, 103], index=sample_dataframe.index[:3])
        }

        df_short = sample_dataframe.iloc[:3]
        signals = analyzer.generate_signals(df_short, indicators)

        assert 'MA_cross_signal' in signals.columns

    def test_generate_signals_empty_indicators(self, analyzer, sample_dataframe):
        """测试空指标字典"""
        signals = analyzer.generate_signals(sample_dataframe, {})

        # 应该至少有composite_signal
        assert 'composite_signal' in signals.columns


class TestComprehensiveAnalysis:
    """测试综合分析"""

    def test_comprehensive_analysis_basic(self, analyzer, sample_dataframe):
        """测试完整的综合分析"""
        result = analyzer.comprehensive_analysis(sample_dataframe)

        # 验证返回的DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_dataframe)

        # 验证包含原始列
        assert 'Close' in result.columns

        # 验证包含技术指标
        assert 'SMA_20' in result.columns
        assert 'RSI_14' in result.columns
        assert 'MACD' in result.columns
        assert 'ATR_14' in result.columns

        # 验证包含信号
        assert 'composite_signal' in result.columns

    def test_comprehensive_analysis_preserves_index(self, analyzer, sample_dataframe):
        """测试综合分析保持索引"""
        result = analyzer.comprehensive_analysis(sample_dataframe)
        assert result.index.equals(sample_dataframe.index)

    @patch('src.technical_analysis.logger')
    def test_comprehensive_analysis_logging(self, mock_logger, analyzer, sample_dataframe):
        """测试综合分析的日志记录"""
        analyzer.comprehensive_analysis(sample_dataframe)

        # 验证日志调用
        assert mock_logger.info.called
        call_args = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any('开始技术指标计算' in arg for arg in call_args)
        assert any('技术指标计算完成' in arg for arg in call_args)


class TestPlotAnalysis:
    """测试图表绘制"""

    @patch('src.technical_analysis.plt.savefig')
    @patch('src.technical_analysis.plt.tight_layout')
    def test_plot_analysis_with_save_path(self, mock_tight_layout, mock_savefig,
                                          analyzer, sample_dataframe):
        """测试保存图表"""
        # 添加技术指标
        result = analyzer.comprehensive_analysis(sample_dataframe)

        save_path = '/tmp/test_chart.png'
        analyzer.plot_analysis(result, 'TEST', save_path)

        # 验证savefig被调用
        mock_savefig.assert_called_once()
        assert save_path in str(mock_savefig.call_args)

    @patch('src.technical_analysis.logger')
    def test_plot_analysis_missing_close_column(self, mock_logger, analyzer):
        """测试缺少Close列的情况"""
        df = pd.DataFrame({'Open': [1, 2, 3]})
        analyzer.plot_analysis(df, 'TEST')

        # 应该记录错误日志
        mock_logger.info.assert_called()
        call_args = str(mock_logger.info.call_args_list)
        assert '无法绘制图表' in call_args or '缺少价格数据' in call_args

    @patch('src.technical_analysis.plt.savefig')
    def test_plot_analysis_with_all_indicators(self, mock_savefig, analyzer, sample_dataframe):
        """测试包含所有指标的图表"""
        result = analyzer.comprehensive_analysis(sample_dataframe)

        analyzer.plot_analysis(result, 'TEST', '/tmp/test_all.png')

        # 验证图表创建成功
        mock_savefig.assert_called_once()

    @patch('src.technical_analysis.plt.savefig')
    def test_plot_analysis_lowercase_columns(self, mock_savefig, analyzer):
        """测试小写列名"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'close': np.random.randn(100) + 100,
            'high': np.random.randn(100) + 101,
            'low': np.random.randn(100) + 99
        }, index=dates)

        result = analyzer.comprehensive_analysis(df)
        analyzer.plot_analysis(result, 'test', '/tmp/test_lower.png')

        # 不应该抛出异常
        assert True


class TestEdgeCases:
    """测试边缘情况"""

    def test_empty_dataframe(self, analyzer):
        """测试空DataFrame"""
        df = pd.DataFrame()

        # 这些调用不应该崩溃
        indicators = analyzer.calculate_trend_indicators(df)
        assert isinstance(indicators, dict)

    def test_single_row_dataframe(self, analyzer):
        """测试单行DataFrame"""
        df = pd.DataFrame({
            'Close': [100],
            'High': [101],
            'Low': [99],
            'Volume': [1000000]
        })

        # 不应该崩溃
        indicators = analyzer.calculate_trend_indicators(df)
        assert isinstance(indicators, dict)

    def test_dataframe_with_nan(self, analyzer):
        """测试包含NaN的DataFrame"""
        df = pd.DataFrame({
            'Close': [100, np.nan, 102, 103, 104],
            'High': [101, 102, np.nan, 104, 105],
            'Low': [99, 100, 101, np.nan, 103],
            'Volume': [1000000, 1100000, np.nan, 1200000, 1300000]
        })

        # 不应该崩溃
        result = analyzer.comprehensive_analysis(df)
        assert isinstance(result, pd.DataFrame)

    def test_dataframe_with_zeros(self, analyzer):
        """测试包含零值的DataFrame"""
        df = pd.DataFrame({
            'Close': [100, 0, 102, 103, 104],
            'High': [101, 102, 103, 104, 105],
            'Low': [99, 100, 101, 102, 103],
            'Volume': [0, 0, 0, 0, 0]
        })

        # 不应该崩溃
        result = analyzer.comprehensive_analysis(df)
        assert isinstance(result, pd.DataFrame)

    def test_dataframe_with_negative_prices(self, analyzer):
        """测试包含负价格的DataFrame（虽然不现实）"""
        df = pd.DataFrame({
            'Close': [100, -50, 102, 103, 104],
            'High': [101, 102, 103, 104, 105],
            'Low': [99, 100, 101, 102, 103]
        })

        # 不应该崩溃
        result = analyzer.comprehensive_analysis(df)
        assert isinstance(result, pd.DataFrame)


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self, analyzer, sample_dataframe):
        """测试完整的工作流程"""
        # 1. 综合分析
        result = analyzer.comprehensive_analysis(sample_dataframe)

        # 2. 验证结果
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

        # 3. 绘制图表
        with patch('src.technical_analysis.plt.savefig'):
            analyzer.plot_analysis(result, 'TEST', '/tmp/test.png')

        # 工作流应该完整无误
        assert True

    def test_multiple_analyses(self, analyzer):
        """测试多次分析"""
        # 创建多个不同的数据集
        for i in range(3):
            dates = pd.date_range(start=f'2024-0{i+1}-01', periods=50, freq='D')
            df = pd.DataFrame({
                'Close': np.random.randn(50) + 100 + i*10,
                'High': np.random.randn(50) + 101 + i*10,
                'Low': np.random.randn(50) + 99 + i*10,
                'Volume': np.random.randint(1000000, 10000000, 50)
            }, index=dates)

            result = analyzer.comprehensive_analysis(df)
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 50
