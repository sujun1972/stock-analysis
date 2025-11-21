import yfinance as yf
import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
import os

try:
    # Prefer package-relative import when used as part of the src package
    from .config.config import DATA_PATH, TUSHARE_TOKEN
except ImportError:
    # Fallback for direct script execution (if src is not treated as a package)
    from config.config import DATA_PATH, TUSHARE_TOKEN

class DataFetcher:
    def __init__(self, tushare_token=TUSHARE_TOKEN):
        self.tushare_token = tushare_token
        if tushare_token:
            ts.set_token(tushare_token)
            self.pro = ts.pro_api()
        else:
            self.pro = None
        print("数据获取器初始化完成")
    
    def fetch_yfinance_data(self, symbol, period="1y", interval="1d"):
        """使用 yfinance 获取股票数据"""
        try:
            print(f"正在获取 {symbol} 的数据...")
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            print(f"成功获取 {symbol} 的 {len(data)} 条数据")
            return data
        except Exception as e:
            print(f"获取 {symbol} 数据时出错: {e}")
            return None
    
    def fetch_tushare_data(self, symbol, start_date=None, end_date=None):
        print(f"使用 Tushare token: {self.tushare_token}")
        """使用 Tushare 获取A股数据"""
        if not self.pro:
            print("未提供 Tushare token，无法获取数据")
            return None
        
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            
            print(f"正在获取 {symbol} 的Tushare数据...")
            df = self.pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
            df = df.sort_values('trade_date')
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)
            print(f"成功获取 {symbol} 的 {len(df)} 条Tushare数据")
            return df
        except Exception as e:
            print(f"获取Tushare数据时出错: {e}")
            return None
    
    def save_data_to_csv(self, data, filename):
        """保存数据到CSV文件"""
        if data is not None:
            filepath = os.path.join(DATA_PATH, filename)
            data.to_csv(filepath)
            print(f"数据已保存到: {filepath}")
            return filepath
        return None
    
    def load_data_from_csv(self, filename):
        """从CSV文件加载数据"""
        filepath = os.path.join(DATA_PATH, filename)
        if os.path.exists(filepath):
            data = pd.read_csv(filepath, index_col=0, parse_dates=True)
            print(f"从 {filepath} 加载了 {len(data)} 条数据")
            return data
        else:
            print(f"文件不存在: {filepath}")
            return None