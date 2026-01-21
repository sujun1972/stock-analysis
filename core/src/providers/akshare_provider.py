"""
AkShare 数据提供者实现
封装 AkShare API，提供统一的数据接口
"""

from typing import Optional, List, Dict
from datetime import datetime, date, timedelta
import time
import pandas as pd
from loguru import logger

try:
    import akshare as ak
except ImportError:
    logger.error("AkShare 未安装，请运行: pip install akshare")
    raise

from .base_provider import BaseDataProvider


class AkShareProvider(BaseDataProvider):
    """
    AkShare 数据提供者

    特点:
    - 免费开源，无需 Token
    - 数据来源稳定（东方财富、新浪财经等）
    - 存在 IP 限流风险

    注意事项:
    - 避免过于频繁的请求
    - 建议请求间隔 >= 0.3秒
    - 实时行情获取较慢（需要爬取多个页面）
    """

    def __init__(self, **kwargs):
        """
        初始化 AkShare 提供者

        Args:
            **kwargs:
                - timeout: 请求超时时间（秒，默认 30）
                - retry_count: 失败重试次数（默认 3）
                - retry_delay: 重试延迟（秒，默认 1）
                - request_delay: 请求间隔（秒，默认 0.3）
        """
        super().__init__(**kwargs)
        self.timeout = kwargs.get('timeout', 30)
        self.retry_count = kwargs.get('retry_count', 3)
        self.retry_delay = kwargs.get('retry_delay', 1)
        self.request_delay = kwargs.get('request_delay', 0.3)

    def _validate_config(self) -> None:
        """验证配置（AkShare 无需特殊配置）"""
        pass

    def _retry_request(self, func, *args, **kwargs):
        """
        带重试机制的请求包装器

        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果

        Raises:
            Exception: 重试次数用尽后抛出最后一次异常
        """
        last_exception = None

        for attempt in range(self.retry_count):
            try:
                result = func(*args, **kwargs)
                time.sleep(self.request_delay)  # 请求间隔
                return result
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"请求失败 (尝试 {attempt + 1}/{self.retry_count}): {e}"
                )
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)

        raise last_exception

    # ========== 股票列表相关 ==========

    def get_stock_list(self) -> pd.DataFrame:
        """
        获取全部 A 股股票列表

        Returns:
            pd.DataFrame: 标准化的股票列表
        """
        try:
            logger.info("正在从 AkShare 获取股票列表...")

            # 获取股票基本信息
            df = self._retry_request(ak.stock_info_a_code_name)

            if df is None or df.empty:
                raise ValueError("获取股票列表失败，返回数据为空")

            # 标准化字段名
            df = df.rename(columns={
                'code': 'code',
                'name': 'name'
            })

            # 添加市场类型
            df['market'] = df['code'].apply(self._parse_market)

            # 添加默认状态
            df['status'] = '正常'

            # 选择标准字段
            df = df[['code', 'name', 'market', 'status']]

            logger.info(f"✓ 成功获取 {len(df)} 只股票")

            return df

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise

    @staticmethod
    def _parse_market(code: str) -> str:
        """
        根据股票代码解析市场类型

        Args:
            code: 股票代码

        Returns:
            str: 市场类型
        """
        if code.startswith('60'):
            return '上海主板'
        elif code.startswith('68'):
            return '上海主板'
        elif code.startswith('000'):
            return '深圳主板'
        elif code.startswith('001'):
            return '深圳主板'
        elif code.startswith('002'):
            return '深圳主板'
        elif code.startswith('300'):
            return '创业板'
        elif code.startswith('688'):
            return '科创板'
        elif code.startswith(('8', '4')):
            return '北交所'
        else:
            return '其他'

    # ========== 日线数据相关 ==========

    def get_daily_data(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = 'qfq'
    ) -> pd.DataFrame:
        """
        获取股票日线数据

        Args:
            code: 股票代码
            start_date: 开始日期 (YYYYMMDD 或 YYYY-MM-DD)
            end_date: 结束日期
            adjust: 复权方式 ('qfq', 'hfq', '')

        Returns:
            pd.DataFrame: 标准化的日线数据
        """
        try:
            # 标准化日期格式
            start = self.normalize_date(start_date) if start_date else \
                (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            end = self.normalize_date(end_date) if end_date else \
                datetime.now().strftime('%Y%m%d')

            logger.debug(f"获取 {code} 日线数据: {start} - {end}")

            # 获取历史数据
            df = self._retry_request(
                ak.stock_zh_a_hist,
                symbol=code,
                period='daily',
                start_date=start,
                end_date=end,
                adjust=adjust
            )

            if df is None or df.empty:
                logger.warning(f"{code}: 无数据")
                return pd.DataFrame()

            # 标准化字段名
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change_amount',
                '换手率': 'turnover'
            })

            # 转换日期类型
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date

            # 选择标准字段
            standard_columns = [
                'trade_date', 'open', 'high', 'low', 'close',
                'volume', 'amount', 'amplitude', 'pct_change',
                'change_amount', 'turnover'
            ]
            df = df[[col for col in standard_columns if col in df.columns]]

            return df

        except Exception as e:
            logger.error(f"获取 {code} 日线数据失败: {e}")
            raise

    def get_daily_batch(
        self,
        codes: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = 'qfq'
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取多只股票的日线数据

        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权方式

        Returns:
            Dict[str, pd.DataFrame]: 股票代码到数据的映射
        """
        result = {}

        for i, code in enumerate(codes, 1):
            try:
                logger.info(f"[{i}/{len(codes)}] 获取 {code} 日线数据")
                df = self.get_daily_data(code, start_date, end_date, adjust)
                if not df.empty:
                    result[code] = df
            except Exception as e:
                logger.error(f"获取 {code} 日线数据失败: {e}")
                continue

        return result

    # ========== 分时数据相关 ==========

    def get_minute_data(
        self,
        code: str,
        period: str = '5',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = ''
    ) -> pd.DataFrame:
        """
        获取股票分时数据

        Args:
            code: 股票代码
            period: 分时周期 ('1', '5', '15', '30', '60')
            start_date: 开始日期时间
            end_date: 结束日期时间
            adjust: 复权方式

        Returns:
            pd.DataFrame: 标准化的分时数据
        """
        try:
            # 标准化日期时间格式
            start = self.normalize_datetime(start_date) if start_date else \
                (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d 09:30:00')
            end = self.normalize_datetime(end_date) if end_date else \
                datetime.now().strftime('%Y-%m-%d 15:00:00')

            logger.debug(f"获取 {code} {period}分钟数据: {start} - {end}")

            # 获取分时数据
            df = self._retry_request(
                ak.stock_zh_a_hist_min_em,
                symbol=code,
                period=period,
                start_date=start,
                end_date=end,
                adjust=adjust
            )

            if df is None or df.empty:
                logger.warning(f"{code}: 无分时数据")
                return pd.DataFrame()

            # 标准化字段名
            df = df.rename(columns={
                '时间': 'trade_time',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change_amount',
                '换手率': 'turnover'
            })

            # 转换时间类型
            df['trade_time'] = pd.to_datetime(df['trade_time'])

            # 添加周期字段
            df['period'] = period

            # 选择标准字段
            standard_columns = [
                'trade_time', 'period', 'open', 'high', 'low', 'close',
                'volume', 'amount', 'amplitude', 'pct_change',
                'change_amount', 'turnover'
            ]
            df = df[[col for col in standard_columns if col in df.columns]]

            return df

        except Exception as e:
            logger.error(f"获取 {code} 分时数据失败: {e}")
            raise

    # ========== 实时行情相关 ==========

    def get_realtime_quotes(
        self,
        codes: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取实时行情数据

        注意: AkShare 实时行情获取较慢（需要爬取多个页面）
        建议用于定时批量更新，不适合高频调用

        Args:
            codes: 股票代码列表 (None 表示获取全部)

        Returns:
            pd.DataFrame: 标准化的实时行情数据
        """
        try:
            logger.info("正在获取实时行情... (此操作可能需要 3-5 分钟，共58个批次)")
            logger.warning("AkShare实时行情接口需要分批次爬取东方财富网数据，请耐心等待...")

            # 获取全部实时行情
            # 注意：此接口会分58个批次请求，每批次约2-3秒，总耗时3-5分钟
            # 由于是爬虫方式，可能会因网络问题超时，建议增加重试次数
            df = self._retry_request(ak.stock_zh_a_spot_em)

            if df is None or df.empty:
                raise ValueError("获取实时行情失败，返回数据为空。可能原因：\n"
                              "1. 网络连接超时（数据获取需3-5分钟）\n"
                              "2. 东方财富网接口限流\n"
                              "3. 非交易时段数据源无响应\n"
                              "建议：稍后重试或使用Tushare数据源")

            # 标准化字段名
            df = df.rename(columns={
                '代码': 'code',
                '名称': 'name',
                '最新价': 'latest_price',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '昨收': 'pre_close',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change_amount',
                '换手率': 'turnover',
                '振幅': 'amplitude'
            })

            # 添加行情时间
            df['trade_time'] = datetime.now()

            # 筛选指定股票
            if codes:
                df = df[df['code'].isin(codes)]

            # 选择标准字段
            standard_columns = [
                'code', 'name', 'latest_price', 'open', 'high', 'low',
                'pre_close', 'volume', 'amount', 'pct_change',
                'change_amount', 'turnover', 'amplitude', 'trade_time'
            ]
            df = df[[col for col in standard_columns if col in df.columns]]

            logger.info(f"✓ 成功获取 {len(df)} 只股票的实时行情")

            return df

        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            raise

    def get_new_stocks(self, days: int = 30) -> pd.DataFrame:
        """
        获取最近 N 天上市的新股

        Args:
            days: 最近天数

        Returns:
            pd.DataFrame: 标准化的新股列表
        """
        try:
            logger.info(f"正在从 AkShare 获取最近 {days} 天的新股...")

            # 获取次新股数据（包含上市日期）
            df = self._retry_request(ak.stock_new_a_spot_em)

            if df is None or df.empty:
                raise ValueError("获取新股列表失败，返回数据为空")

            # 筛选最近 N 天上市的股票
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            df['上市日期'] = pd.to_datetime(df['上市日期'], errors='coerce')
            df = df[df['上市日期'] >= cutoff_date]

            # 标准化字段名
            df = df.rename(columns={
                '代码': 'code',
                '名称': 'name',
                '上市日期': 'list_date'
            })

            # 转换日期为 date 对象（不是 Timestamp）
            df['list_date'] = df['list_date'].dt.date

            # 添加市场类型
            df['market'] = df['code'].apply(self._parse_market)

            # 添加默认状态
            df['status'] = '正常'

            # 选择标准字段
            df = df[['code', 'name', 'market', 'list_date', 'status']]

            logger.info(f"✓ 成功获取 {len(df)} 只新股")

            return df

        except Exception as e:
            logger.error(f"获取新股列表失败: {e}")
            raise

    def get_delisted_stocks(self) -> pd.DataFrame:
        """
        获取退市股票列表

        Returns:
            pd.DataFrame: 标准化的退市股票列表
        """
        try:
            logger.info("正在从 AkShare 获取退市股票列表...")

            # 获取上交所退市股票
            df_sh = self._retry_request(ak.stock_info_sh_delist)
            if df_sh is not None and not df_sh.empty:
                df_sh = df_sh.rename(columns={
                    '公司代码': 'code',
                    '公司简称': 'name',
                    '上市日期': 'list_date',
                    '暂停上市日期': 'delist_date'
                })
                df_sh['market'] = '上海主板'

            # 获取深交所退市股票
            try:
                df_sz = self._retry_request(ak.stock_info_sz_delist)
                if df_sz is not None and not df_sz.empty:
                    # 深交所数据字段可能不同，需要适配
                    if '公司代码' in df_sz.columns:
                        df_sz = df_sz.rename(columns={
                            '公司代码': 'code',
                            '公司简称': 'name',
                            '上市日期': 'list_date',
                            '终止上市日期': 'delist_date'
                        })
                    df_sz['market'] = '深圳主板'
            except:
                logger.warning("深交所退市数据获取失败，仅使用上交所数据")
                df_sz = pd.DataFrame()

            # 合并上深两市数据
            dfs = [df for df in [df_sh, df_sz] if df is not None and not df.empty]
            if not dfs:
                raise ValueError("获取退市股票列表失败，返回数据为空")

            df = pd.concat(dfs, ignore_index=True)

            # 转换日期格式（确保是 date 对象，不是 Timestamp）
            df['list_date'] = pd.to_datetime(df['list_date'], errors='coerce').dt.date
            df['delist_date'] = pd.to_datetime(df['delist_date'], errors='coerce').dt.date

            # 选择标准字段
            df = df[['code', 'name', 'list_date', 'delist_date', 'market']]

            logger.info(f"✓ 成功获取 {len(df)} 只退市股票")

            return df

        except Exception as e:
            logger.error(f"获取退市股票列表失败: {e}")
            raise
