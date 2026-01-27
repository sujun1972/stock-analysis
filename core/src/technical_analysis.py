import talib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

try:
    # Prefer package-relative import when used as part of the src package
    from .config.config import DATA_PATH
except ImportError:
    # Fallback for direct script execution
    from config.config import DATA_PATH
from loguru import logger

class TechnicalAnalyzer:
    """技术指标分析器"""
    
    def calculate_trend_indicators(self, df):
        """计算趋势指标"""
        close = self._get_column(df, 'Close')
        high = self._get_column(df, 'High')
        low = self._get_column(df, 'Low')
        
        indicators = {}
        
        # 移动平均线
        indicators['SMA_5'] = talib.SMA(close, timeperiod=5)
        indicators['SMA_20'] = talib.SMA(close, timeperiod=20)
        indicators['SMA_50'] = talib.SMA(close, timeperiod=50)
        indicators['EMA_12'] = talib.EMA(close, timeperiod=12)
        indicators['EMA_26'] = talib.EMA(close, timeperiod=26)
        
        # 布林带
        indicators['BB_upper'], indicators['BB_middle'], indicators['BB_lower'] = \
            talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
        
        return indicators
    
    def calculate_momentum_indicators(self, df):
        """计算动量指标"""
        close = self._get_column(df, 'Close')
        high = self._get_column(df, 'High')
        low = self._get_column(df, 'Low')
        volume = self._get_column(df, 'Volume')
        
        indicators = {}
        
        # MACD
        indicators['MACD'], indicators['MACD_signal'], indicators['MACD_hist'] = \
            talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        
        # RSI
        indicators['RSI_14'] = talib.RSI(close, timeperiod=14)
        
        # 随机指标
        indicators['slowk'], indicators['slowd'] = talib.STOCH(high, low, close)
        
        if volume is not None:
            indicators['OBV'] = talib.OBV(close, volume)
        
        return indicators
    
    def calculate_volatility_indicators(self, df):
        """计算波动率指标"""
        close = self._get_column(df, 'Close')
        high = self._get_column(df, 'High')
        low = self._get_column(df, 'Low')
        
        indicators = {}
        indicators['ATR_14'] = talib.ATR(high, low, close, timeperiod=14)
        return indicators
    
    def _get_column(self, df, column_name):
        """安全获取列数据"""
        if column_name in df.columns:
            return df[column_name]
        # 尝试小写
        column_name_lower = column_name.lower()
        if column_name_lower in df.columns:
            return df[column_name_lower]
        return None
    
    def generate_signals(self, df, indicators):
        """生成交易信号"""
        signals = pd.DataFrame(index=df.index)
        
        close = self._get_column(df, 'Close')
        
        # MACD信号
        if 'MACD' in indicators and 'MACD_signal' in indicators:
            signals['MACD_signal'] = np.where(
                indicators['MACD'] > indicators['MACD_signal'], 1, -1
            )
        
        # RSI信号
        if 'RSI_14' in indicators:
            signals['RSI_signal'] = 0
            rsi = indicators['RSI_14']
            signals.loc[rsi < 30, 'RSI_signal'] = 1    # 超卖，买入信号
            signals.loc[rsi > 70, 'RSI_signal'] = -1   # 超买，卖出信号
        
        # 移动平均线交叉信号
        if 'SMA_20' in indicators and 'SMA_50' in indicators:
            signals['MA_cross_signal'] = np.where(
                indicators['SMA_20'] > indicators['SMA_50'], 1, -1
            )
        
        # 综合信号
        signals['composite_signal'] = signals.sum(axis=1, skipna=True)
        
        return signals
    
    def comprehensive_analysis(self, df):
        """综合技术分析"""
        logger.info("开始技术指标计算...")
        
        trend_indicators = self.calculate_trend_indicators(df)
        momentum_indicators = self.calculate_momentum_indicators(df)
        volatility_indicators = self.calculate_volatility_indicators(df)
        
        # 合并所有指标
        all_indicators = {**trend_indicators, **momentum_indicators, **volatility_indicators}
        
        # 生成信号
        signals = self.generate_signals(df, all_indicators)
        
        # 创建包含所有数据的DataFrame
        result_df = df.copy()
        for name, values in all_indicators.items():
            result_df[name] = values
        
        result_df = pd.concat([result_df, signals], axis=1)
        
        logger.info("技术指标计算完成!")
        return result_df
    
    def plot_analysis(self, df, symbol, save_path=None):
        """绘制分析图表"""
        if 'Close' not in df.columns and 'close' not in df.columns:
            logger.info("无法绘制图表：缺少价格数据")
            return
        
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        close = self._get_column(df, 'Close')
        
        # 价格和移动平均线
        axes[0].plot(close.index, close, label='Close Price', linewidth=1)
        if 'SMA_20' in df.columns:
            axes[0].plot(df.index, df['SMA_20'], label='SMA 20', alpha=0.7)
        if 'SMA_50' in df.columns:
            axes[0].plot(df.index, df['SMA_50'], label='SMA 50', alpha=0.7)
        axes[0].set_title(f'{symbol} - Price Trend')
        axes[0].legend()
        axes[0].grid(True)
        
        # RSI
        if 'RSI_14' in df.columns:
            axes[1].plot(df.index, df['RSI_14'], label='RSI 14', color='orange')
            axes[1].axhline(y=70, color='r', linestyle='--', alpha=0.7, label='Overbought')
            axes[1].axhline(y=30, color='g', linestyle='--', alpha=0.7, label='Oversold')
            axes[1].set_title('RSI Indicator')
            axes[1].legend()
            axes[1].grid(True)
        
        # MACD
        if 'MACD' in df.columns and 'MACD_signal' in df.columns:
            axes[2].plot(df.index, df['MACD'], label='MACD', color='blue')
            axes[2].plot(df.index, df['MACD_signal'], label='MACD Signal', color='red')
            axes[2].bar(df.index, df['MACD_hist'] if 'MACD_hist' in df.columns else df['MACD'] - df['MACD_signal'], 
                       alpha=0.3, label='MACD Hist')
            axes[2].set_title('MACD Indicator')
            axes[2].legend()
            axes[2].grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"图表已保存到: {save_path}")
        
        # 在批量运行场景下不弹出图表窗口，只保存到文件
        # plt.show()