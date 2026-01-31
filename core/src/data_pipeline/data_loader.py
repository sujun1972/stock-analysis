"""
数据加载器 (DataLoader)

负责从数据库加载原始股票数据
"""

import pandas as pd
from typing import Optional
from src.database.db_manager import DatabaseManager, get_database
from src.exceptions import DataError, DataNotFoundError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataLoader:
    """
    数据加载器

    职责：
    - 从数据库加载股票原始数据
    - 验证数据完整性
    - 处理日期索引
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        初始化数据加载器

        Args:
            db_manager: 数据库管理器实例（None则使用全局单例）
        """
        self.db = db_manager if db_manager else get_database()

    def load_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        加载股票数据

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            原始数据 DataFrame，包含 OHLCV 数据，日期作为索引

        Raises:
            DataNotFoundError: 无法获取数据
            DataError: 数据格式错误
        """
        try:
            df = self.db.load_daily_data(symbol, start_date, end_date)

            if df is None or len(df) == 0:
                raise DataNotFoundError(
                    f"无法获取股票数据",
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )

            logger.info(f"加载股票 {symbol} 数据: {len(df)} 条记录 ({start_date} ~ {end_date})")

            # 确保索引是日期类型
            df = self._ensure_datetime_index(df, symbol)

            # 排序
            df = df.sort_index()

            # 验证必要列
            self._validate_columns(df, symbol)

            return df

        except DataNotFoundError:
            raise
        except DataError:
            raise
        except Exception as e:
            logger.error(f"加载数据失败: {symbol}, 错误: {e}")
            raise DataError(f"加载数据失败: {e}", symbol=symbol)

    def _ensure_datetime_index(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """确保DataFrame有日期时间索引"""
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            else:
                raise DataError(
                    "数据缺少日期索引",
                    details={"symbol": symbol}
                )
        return df

    def _validate_columns(self, df: pd.DataFrame, symbol: str):
        """验证必要的列是否存在"""
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            raise DataError(
                f"数据缺少必要列: {missing_cols}",
                symbol=symbol,
                missing_columns=missing_cols
            )
