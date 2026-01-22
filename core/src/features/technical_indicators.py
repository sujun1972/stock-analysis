"""
技术指标计算模块（基于TA-Lib）
包含常用技术指标的封装和扩展
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict
import warnings

# 尝试导入talib，如果不存在则使用纯Python实现
try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    warnings.warn("TA-Lib not installed. Using pure Python implementations.")

    # Fallback implementations using pandas
    class talib:
        """Fallback talib implementation using pandas"""
        @staticmethod
        def SMA(data, timeperiod):
            return data.rolling(window=timeperiod).mean()

        @staticmethod
        def EMA(data, timeperiod):
            return data.ewm(span=timeperiod, adjust=False).mean()

        @staticmethod
        def BBANDS(data, timeperiod=20, nbdevup=2.0, nbdevdn=2.0, matype=0):
            middle = data.rolling(window=timeperiod).mean()
            std = data.rolling(window=timeperiod).std()
            upper = middle + nbdevup * std
            lower = middle - nbdevdn * std
            return upper, middle, lower

        @staticmethod
        def RSI(data, timeperiod=14):
            delta = data.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=timeperiod).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=timeperiod).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))

        @staticmethod
        def MACD(data, fastperiod=12, slowperiod=26, signalperiod=9):
            ema_fast = data.ewm(span=fastperiod, adjust=False).mean()
            ema_slow = data.ewm(span=slowperiod, adjust=False).mean()
            macd = ema_fast - ema_slow
            signal = macd.ewm(span=signalperiod, adjust=False).mean()
            hist = macd - signal
            return macd, signal, hist

        @staticmethod
        def STOCH(high, low, close, fastk_period=5, slowk_period=3, slowd_period=3):
            lowest_low = low.rolling(window=fastk_period).min()
            highest_high = high.rolling(window=fastk_period).max()
            fastk = 100 * (close - lowest_low) / (highest_high - lowest_low)
            slowk = fastk.rolling(window=slowk_period).mean()
            slowd = slowk.rolling(window=slowd_period).mean()
            return slowk, slowd

        @staticmethod
        def CCI(high, low, close, timeperiod=14):
            tp = (high + low + close) / 3
            sma = tp.rolling(window=timeperiod).mean()
            mad = tp.rolling(window=timeperiod).apply(lambda x: np.abs(x - x.mean()).mean())
            return (tp - sma) / (0.015 * mad)

        @staticmethod
        def ATR(high, low, close, timeperiod=14):
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.rolling(window=timeperiod).mean()

        @staticmethod
        def OBV(close, volume):
            obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
            return obv

        @staticmethod
        def ADX(high, low, close, timeperiod=14):
            # Simplified ADX calculation
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=timeperiod).mean()

            up_move = high - high.shift()
            down_move = low.shift() - low

            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

            plus_di = 100 * pd.Series(plus_dm).rolling(window=timeperiod).mean() / atr
            minus_di = 100 * pd.Series(minus_dm).rolling(window=timeperiod).mean() / atr

            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=timeperiod).mean()
            return adx

warnings.filterwarnings('ignore')


class TechnicalIndicators:
    """技术指标计算器"""

    def __init__(self, df: pd.DataFrame):
        """
        初始化技术指标计算器

        参数:
            df: 价格DataFrame，需包含 open, high, low, close, volume 列
        """
        self.df = df.copy()
        self._validate_dataframe()

    def _validate_dataframe(self):
        """验证DataFrame格式"""
        required_cols = ['open', 'high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in self.df.columns]

        if missing_cols:
            raise ValueError(f"DataFrame缺少必需的列: {missing_cols}")

    # ==================== 趋势指标 ====================

    def add_ma(
        self,
        periods: list = [5, 10, 20, 60, 120, 250],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加移动平均线（MA）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加MA列的DataFrame
        """
        for period in periods:
            # 确保period是整数，并将数据转换为数值类型
            period = int(period)
            price_series = pd.to_numeric(self.df[price_col], errors='coerce')
            self.df[f'MA{period}'] = talib.SMA(price_series, timeperiod=period)

        return self.df

    def add_ema(
        self,
        periods: list = [12, 26, 50],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加指数移动平均线（EMA）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加EMA列的DataFrame
        """
        for period in periods:
            self.df[f'EMA{period}'] = talib.EMA(self.df[price_col], timeperiod=period)

        return self.df

    def add_bollinger_bands(
        self,
        period: int = 20,
        nbdevup: float = 2.0,
        nbdevdn: float = 2.0,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加布林带（Bollinger Bands）

        参数:
            period: 周期
            nbdevup: 上轨标准差倍数
            nbdevdn: 下轨标准差倍数
            price_col: 价格列名

        返回:
            添加布林带列的DataFrame
        """
        upper, middle, lower = talib.BBANDS(
            self.df[price_col],
            timeperiod=period,
            nbdevup=nbdevup,
            nbdevdn=nbdevdn,
            matype=0
        )

        self.df['BOLL_UPPER'] = upper
        self.df['BOLL_MIDDLE'] = middle
        self.df['BOLL_LOWER'] = lower

        # 布林带宽度（波动率指标）
        self.df['BOLL_WIDTH'] = (upper - lower) / middle

        # 价格在布林带中的位置 (0-1之间)
        self.df['BOLL_POS'] = (self.df[price_col] - lower) / (upper - lower)

        return self.df

    # ==================== 动量指标 ====================

    def add_rsi(
        self,
        periods: list = [6, 12, 24],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加相对强弱指数（RSI）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加RSI列的DataFrame
        """
        for period in periods:
            self.df[f'RSI{period}'] = talib.RSI(self.df[price_col], timeperiod=period)

        return self.df

    def add_macd(
        self,
        fastperiod: int = 12,
        slowperiod: int = 26,
        signalperiod: int = 9,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加MACD指标

        参数:
            fastperiod: 快线周期
            slowperiod: 慢线周期
            signalperiod: 信号线周期
            price_col: 价格列名

        返回:
            添加MACD列的DataFrame
        """
        macd, signal, hist = talib.MACD(
            self.df[price_col],
            fastperiod=fastperiod,
            slowperiod=slowperiod,
            signalperiod=signalperiod
        )

        self.df['MACD'] = macd
        self.df['MACD_SIGNAL'] = signal
        self.df['MACD_HIST'] = hist

        return self.df

    def add_kdj(
        self,
        fastk_period: int = 9,
        slowk_period: int = 3,
        slowd_period: int = 3
    ) -> pd.DataFrame:
        """
        添加KDJ指标（随机指标）

        参数:
            fastk_period: K线周期
            slowk_period: K线平滑周期
            slowd_period: D线周期

        返回:
            添加KDJ列的DataFrame

        注意:
            移除了slowk_matype和slowd_matype参数，因为某些版本的TA-Lib不支持
        """
        # 调用STOCH计算随机指标（KDJ的K和D值）
        slowk, slowd = talib.STOCH(
            self.df['high'],
            self.df['low'],
            self.df['close'],
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowd_period=slowd_period
        )

        self.df['KDJ_K'] = slowk
        self.df['KDJ_D'] = slowd
        self.df['KDJ_J'] = 3 * slowk - 2 * slowd  # J = 3K - 2D

        return self.df

    def add_cci(
        self,
        periods: list = [14, 28]
    ) -> pd.DataFrame:
        """
        添加CCI指标（商品通道指标）

        参数:
            periods: 周期列表

        返回:
            添加CCI列的DataFrame
        """
        # 支持单个整数或列表
        if isinstance(periods, int):
            periods = [periods]

        for period in periods:
            period = int(period)
            high = pd.to_numeric(self.df['high'], errors='coerce')
            low = pd.to_numeric(self.df['low'], errors='coerce')
            close = pd.to_numeric(self.df['close'], errors='coerce')

            self.df[f'CCI{period}'] = talib.CCI(high, low, close, timeperiod=period)

        return self.df

    # ==================== 波动率指标 ====================

    def add_atr(
        self,
        periods: list = [14, 28]
    ) -> pd.DataFrame:
        """
        添加ATR指标（平均真实波幅）

        参数:
            periods: 周期列表

        返回:
            添加ATR列的DataFrame
        """
        # 支持单个整数或列表
        if isinstance(periods, int):
            periods = [periods]

        for period in periods:
            period = int(period)
            high = pd.to_numeric(self.df['high'], errors='coerce')
            low = pd.to_numeric(self.df['low'], errors='coerce')
            close = pd.to_numeric(self.df['close'], errors='coerce')

            self.df[f'ATR{period}'] = talib.ATR(high, low, close, timeperiod=period)
            # ATR百分比（相对于价格的波动率）
            self.df[f'ATR{period}_PCT'] = self.df[f'ATR{period}'] / close * 100

        return self.df

    def add_volatility(
        self,
        periods: list = [5, 10, 20, 60],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加历史波动率

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加波动率列的DataFrame
        """
        returns = self.df[price_col].pct_change()

        for period in periods:
            self.df[f'VOL{period}'] = returns.rolling(window=period).std() * np.sqrt(252) * 100

        return self.df

    # ==================== 成交量指标 ====================

    def add_obv(
        self,
        price_col: str = 'close',
        volume_col: str = 'vol'
    ) -> pd.DataFrame:
        """
        添加OBV指标（能量潮）

        参数:
            price_col: 价格列名
            volume_col: 成交量列名

        返回:
            添加OBV列的DataFrame
        """
        if volume_col not in self.df.columns:
            print(f"警告: 找不到列'{volume_col}'，跳过OBV计算")
            return self.df

        self.df['OBV'] = talib.OBV(self.df[price_col], self.df[volume_col])

        return self.df

    def add_volume_ma(
        self,
        periods: list = [5, 10, 20],
        volume_col: str = 'vol'
    ) -> pd.DataFrame:
        """
        添加成交量移动平均线

        参数:
            periods: 周期列表
            volume_col: 成交量列名

        返回:
            添加成交量MA列的DataFrame
        """
        if volume_col not in self.df.columns:
            print(f"警告: 找不到列'{volume_col}'，跳过成交量MA计算")
            return self.df

        for period in periods:
            self.df[f'VOL_MA{period}'] = talib.SMA(self.df[volume_col], timeperiod=period)

        return self.df

    # ==================== 价格形态指标 ====================

    def add_price_patterns(self) -> pd.DataFrame:
        """
        添加价格形态特征

        返回:
            添加价格形态列的DataFrame
        """
        # 涨跌幅
        self.df['RETURN'] = self.df['close'].pct_change() * 100

        # 振幅
        self.df['AMPLITUDE'] = (self.df['high'] - self.df['low']) / self.df['close'].shift(1) * 100

        # 上影线长度（相对于实体）
        self.df['UPPER_SHADOW'] = (
            self.df['high'] - self.df[['open', 'close']].max(axis=1)
        ) / self.df['close'] * 100

        # 下影线长度（相对于实体）
        self.df['LOWER_SHADOW'] = (
            self.df[['open', 'close']].min(axis=1) - self.df['low']
        ) / self.df['close'] * 100

        # 实体长度
        self.df['BODY'] = abs(self.df['close'] - self.df['open']) / self.df['close'] * 100

        # 是否为阳线
        self.df['IS_BULL'] = (self.df['close'] > self.df['open']).astype(int)

        return self.df

    # ==================== 综合指标 ====================

    def add_all_indicators(self) -> pd.DataFrame:
        """
        一键添加所有常用技术指标

        返回:
            添加所有指标的DataFrame
        """
        print("正在计算技术指标...")

        # 趋势指标
        self.add_ma([5, 10, 20, 60, 120, 250])
        self.add_ema([12, 26, 50])
        self.add_bollinger_bands()

        # 动量指标
        self.add_rsi([6, 12, 24])
        self.add_macd()
        self.add_kdj()
        self.add_cci()

        # 波动率指标
        self.add_atr()
        self.add_volatility([5, 10, 20, 60])

        # 成交量指标
        self.add_obv()
        self.add_volume_ma([5, 10, 20])

        # 价格形态
        self.add_price_patterns()

        print(f"✓ 技术指标计算完成，共 {len(self.df.columns)} 个特征")

        return self.df

    def get_feature_names(self) -> list:
        """获取所有特征名称列表"""
        # 排除原始OHLCV列
        exclude_cols = ['open', 'high', 'low', 'close', 'vol', 'volume', 'amount']
        return [col for col in self.df.columns if col not in exclude_cols]

    def get_dataframe(self) -> pd.DataFrame:
        """获取包含所有指标的DataFrame"""
        return self.df


# ==================== 便捷函数 ====================

def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    便捷函数：一键计算所有技术指标

    参数:
        df: 价格DataFrame

    返回:
        包含所有技术指标的DataFrame
    """
    ti = TechnicalIndicators(df)
    return ti.add_all_indicators()


def calculate_basic_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    便捷函数：计算基础技术指标（快速模式）

    参数:
        df: 价格DataFrame

    返回:
        包含基础技术指标的DataFrame
    """
    ti = TechnicalIndicators(df)

    ti.add_ma([5, 10, 20, 60])
    ti.add_rsi([14])
    ti.add_macd()
    ti.add_atr()
    ti.add_price_patterns()

    return ti.get_dataframe()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("技术指标模块测试\n")

    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=300, freq='D')

    # 模拟价格数据
    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 300)
    prices = base_price * (1 + returns).cumprod()

    test_df = pd.DataFrame({
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, 300)),
        'high': prices * (1 + np.random.uniform(0, 0.03, 300)),
        'low': prices * (1 + np.random.uniform(-0.03, 0, 300)),
        'close': prices,
        'vol': np.random.uniform(1000000, 10000000, 300)
    }, index=dates)

    print("原始数据:")
    print(test_df.head())
    print(f"\n原始列数: {len(test_df.columns)}")

    # 计算技术指标
    ti = TechnicalIndicators(test_df)
    result_df = ti.add_all_indicators()

    print("\n添加技术指标后:")
    print(result_df.head())
    print(f"\n总列数: {len(result_df.columns)}")
    print(f"特征列数: {len(ti.get_feature_names())}")

    print("\n特征列表:")
    for i, col in enumerate(ti.get_feature_names(), 1):
        print(f"  {i:2d}. {col}")

    print("\n最近5天数据示例:")
    print(result_df[['close', 'MA5', 'MA20', 'RSI14', 'MACD', 'ATR']].tail())
