import yfinance as yf
import tushare as ts
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import os

try:
    # Prefer package-relative import when used as part of the src package
    from .config.config import DATA_PATH, TUSHARE_TOKEN
except ImportError:
    # Fallback for direct script execution (if src is not treated as a package)
    from config.config import DATA_PATH, TUSHARE_TOKEN
from loguru import logger

class DataFetcher:
    def __init__(self, tushare_token=TUSHARE_TOKEN, data_source='akshare'):
        """
        初始化数据获取器

        参数:
            tushare_token: Tushare Pro的Token（可选）
            data_source: 数据源选择，可选 'akshare', 'tushare', 'yfinance'
                        默认使用 'akshare' 作为主要数据源
        """
        self.data_source = data_source
        self.tushare_token = tushare_token
        if tushare_token:
            ts.set_token(tushare_token)
            self.pro = ts.pro_api()
        else:
            self.pro = None
        logger.info(f"数据获取器初始化完成，当前数据源: {data_source}")
    
    def fetch_yfinance_data(self, symbol, period="1y", interval="1d"):
        """使用 yfinance 获取股票数据"""
        try:
            logger.info(f"正在获取 {symbol} 的数据...")
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            logger.success(f"成功获取 {symbol} 的 {len(data)} 条数据")
            return data
        except Exception as e:
            logger.info(f"获取 {symbol} 数据时出错: {e}")
            return None
    
    def fetch_akshare_data(self, symbol, start_date=None, end_date=None, period="daily", adjust="qfq"):
        """
        使用 AkShare 获取A股数据（主要方法，免费无限制）

        参数:
            symbol: 股票代码，如 '000001' 或 '600000'（6位数字，不需要交易所后缀）
            start_date: 开始日期，格式 'YYYYMMDD' 或 'YYYY-MM-DD'
            end_date: 结束日期，格式 'YYYYMMDD' 或 'YYYY-MM-DD'
            period: 数据周期，可选 'daily'(日线), 'weekly'(周线), 'monthly'(月线)
            adjust: 复权类型，可选 'qfq'(前复权), 'hfq'(后复权), ''(不复权)

        返回:
            DataFrame: 包含日期、开盘、收盘、最高、最低、成交量、成交额等数据
        """
        try:
            # 处理日期格式，确保是YYYYMMDD格式
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            # 统一日期格式为 YYYYMMDD
            start_date = start_date.replace('-', '')
            end_date = end_date.replace('-', '')

            # 去除股票代码中的交易所后缀（如果有）
            if '.' in symbol:
                symbol = symbol.split('.')[0]

            logger.info(f"正在使用AkShare获取 {symbol} 的数据 ({start_date} 至 {end_date})...")

            # 使用AkShare的东方财富数据接口获取历史行情
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )

            if df is not None and not df.empty:
                # 标准化列名，使其与Tushare保持一致
                column_mapping = {
                    '日期': 'trade_date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'vol',
                    '成交额': 'amount',
                    '振幅': 'amplitude',
                    '涨跌幅': 'pct_change',
                    '涨跌额': 'change',
                    '换手率': 'turnover'
                }
                df.rename(columns=column_mapping, inplace=True)

                # 设置日期索引
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df.set_index('trade_date', inplace=True)
                df = df.sort_index()

                logger.success(f"成功获取 {symbol} 的 {len(df)} 条AkShare数据")
                return df
            else:
                logger.info(f"未获取到 {symbol} 的数据")
                return None

        except Exception as e:
            logger.info(f"获取AkShare数据时出错: {e}")
            return None

    def fetch_tushare_data(self, symbol, start_date=None, end_date=None):
        """使用 Tushare 获取A股数据（备用方法，需要Token）"""
        logger.info(f"使用 Tushare token: {self.tushare_token}")
        if not self.pro:
            logger.info("未提供 Tushare token，无法获取数据")
            return None

        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            logger.info(f"正在获取 {symbol} 的Tushare数据...")
            df = self.pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
            df = df.sort_values('trade_date')
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)
            logger.success(f"成功获取 {symbol} 的 {len(df)} 条Tushare数据")
            return df
        except Exception as e:
            logger.info(f"获取Tushare数据时出错: {e}")
            return None

    def fetch_data(self, symbol, start_date=None, end_date=None, **kwargs):
        """
        智能获取股票数据，根据配置的数据源自动选择方法

        参数:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            **kwargs: 其他参数，传递给具体的获取方法

        返回:
            DataFrame: 股票数据，如果主要数据源失败会自动尝试备用数据源
        """
        # 优先使用配置的数据源
        if self.data_source == 'akshare':
            logger.info(f"使用主要数据源: AkShare")
            data = self.fetch_akshare_data(symbol, start_date, end_date, **kwargs)
            # 如果AkShare失败，尝试Tushare作为备用
            if data is None and self.pro:
                logger.error("AkShare获取失败，尝试使用Tushare作为备用数据源...")
                data = self.fetch_tushare_data(symbol, start_date, end_date)
            return data

        elif self.data_source == 'tushare':
            logger.info(f"使用主要数据源: Tushare")
            data = self.fetch_tushare_data(symbol, start_date, end_date)
            # 如果Tushare失败，尝试AkShare作为备用
            if data is None:
                logger.error("Tushare获取失败，尝试使用AkShare作为备用数据源...")
                data = self.fetch_akshare_data(symbol, start_date, end_date, **kwargs)
            return data

        elif self.data_source == 'yfinance':
            logger.info(f"使用主要数据源: yfinance")
            period = kwargs.get('period', '1y')
            interval = kwargs.get('interval', '1d')
            return self.fetch_yfinance_data(symbol, period, interval)

        else:
            logger.info(f"未知的数据源: {self.data_source}，默认使用AkShare")
            return self.fetch_akshare_data(symbol, start_date, end_date, **kwargs)

    def save_data_to_csv(self, data, filename):
        """保存数据到CSV文件"""
        if data is not None:
            filepath = os.path.join(DATA_PATH, filename)
            data.to_csv(filepath)
            logger.info(f"数据已保存到: {filepath}")
            return filepath
        return None
    
    def load_data_from_csv(self, filename):
        """从CSV文件加载数据"""
        filepath = os.path.join(DATA_PATH, filename)
        if os.path.exists(filepath):
            data = pd.read_csv(filepath, index_col=0, parse_dates=True)
            logger.info(f"从 {filepath} 加载了 {len(data)} 条数据")
            return data
        else:
            logger.info(f"文件不存在: {filepath}")
            return None