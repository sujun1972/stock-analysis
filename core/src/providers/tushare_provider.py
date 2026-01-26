"""
Tushare 数据提供者实现
封装 Tushare Pro API，提供统一的数据接口
"""

from typing import Optional, List, Dict, Callable, Any
from datetime import datetime, date, timedelta
import time
import pandas as pd
from loguru import logger

try:
    import tushare as ts
except ImportError:
    logger.warning("Tushare 未安装，请运行: pip install tushare")
    ts = None

from .base_provider import BaseDataProvider


class TushareProvider(BaseDataProvider):
    """
    Tushare Pro 数据提供者

    特点:
    - 数据质量高，覆盖全面
    - 需要积分和 Token
    - 有积分限制和频率限制

    积分要求:
    - 日线数据: 120 积分
    - 分钟数据: 2000 积分
    - 实时行情: 5000 积分

    注意事项:
    - 每分钟调用次数有限制（与积分等级相关）
    - 建议请求间隔 >= 0.2秒
    - 超出限制会返回错误
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        初始化 Tushare 提供者

        Args:
            **kwargs:
                - token: Tushare API Token (必需)
                - timeout: 请求超时时间（秒，默认 30）
                - retry_count: 失败重试次数（默认 3）
                - retry_delay: 重试延迟（秒，默认 1）
                - request_delay: 请求间隔（秒，默认 0.2）
        """
        if ts is None:
            raise ImportError("Tushare 未安装，请运行: pip install tushare")

        # 先设置属性，再调用父类初始化（因为父类会调用 _validate_config）
        self.token: str = kwargs.get('token', '')
        self.timeout: int = kwargs.get('timeout', 30)
        self.retry_count: int = kwargs.get('retry_count', 3)
        self.retry_delay: int = kwargs.get('retry_delay', 1)
        self.request_delay: float = kwargs.get('request_delay', 0.2)

        # 初始化 Tushare Pro API
        if self.token:
            ts.set_token(self.token)
            self.pro: Any = ts.pro_api(self.token)
        else:
            self.pro: Any = None

        # 最后调用父类初始化（会调用 _validate_config）
        super().__init__(**kwargs)

    def _validate_config(self) -> None:
        """验证配置"""
        if not self.token:
            raise ValueError("Tushare Token 未配置，请在系统设置中配置 Token")

        if self.pro is None:
            raise ValueError("Tushare Pro API 初始化失败")

    def _retry_request(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
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
                error_msg = str(e)

                # 检查是否是积分不足或权限限制（直接抛出，不重试）
                if '积分不足' in error_msg or '权限不足' in error_msg:
                    logger.error(f"Tushare 积分不足或权限不足: {e}")
                    raise

                # 检查是否是频率限制（直接抛出，由外层决定是否重试）
                if '抱歉，您每分钟最多访问' in error_msg or '抱歉，您每小时最多访问' in error_msg:
                    logger.warning(f"Tushare 访问频率限制: {e}")
                    raise

                # 其他错误才进行重试
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
            logger.info("正在从 Tushare 获取股票列表...")

            # 获取股票基本信息
            df = self._retry_request(
                self.pro.stock_basic,
                exchange='',
                list_status='L',  # L: 上市, D: 退市, P: 暂停上市
                fields='ts_code,symbol,name,area,industry,market,list_date'
            )

            if df is None or df.empty:
                raise ValueError("获取股票列表失败，返回数据为空")

            # 标准化字段名和格式
            df = df.rename(columns={
                'symbol': 'code',
                'name': 'name',
                'area': 'area',
                'industry': 'industry',
                'market': 'market',
                'list_date': 'list_date'
            })

            # 处理市场类型映射
            market_map = {
                '主板': '上海主板',
                '创业板': '创业板',
                '科创板': '科创板',
                '北交所': '北交所'
            }
            df['market'] = df['market'].map(market_map).fillna('其他')

            # 转换上市日期
            df['list_date'] = pd.to_datetime(df['list_date'], format='%Y%m%d', errors='coerce')

            # 添加默认状态
            df['status'] = '正常'

            # 选择标准字段
            df = df[['code', 'name', 'market', 'industry', 'area', 'list_date', 'status']]

            logger.info(f"✓ 成功获取 {len(df)} 只股票")

            return df

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise

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
            code: 股票代码 (不含后缀)
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

            # 转换为 Tushare 格式的股票代码
            ts_code = self._to_ts_code(code)

            logger.debug(f"获取 {ts_code} 日线数据: {start} - {end}")

            # 根据复权类型选择接口
            if adjust == 'qfq':
                # 前复权
                df = self._retry_request(
                    self.pro.daily,
                    ts_code=ts_code,
                    start_date=start,
                    end_date=end,
                    adj='qfq'
                )
            elif adjust == 'hfq':
                # 后复权
                df = self._retry_request(
                    self.pro.daily,
                    ts_code=ts_code,
                    start_date=start,
                    end_date=end,
                    adj='hfq'
                )
            else:
                # 不复权
                df = self._retry_request(
                    self.pro.daily,
                    ts_code=ts_code,
                    start_date=start,
                    end_date=end
                )

            if df is None or df.empty:
                logger.warning(f"{code}: 无数据")
                return pd.DataFrame()

            # 标准化字段名
            df = df.rename(columns={
                'trade_date': 'trade_date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount',
                'pct_chg': 'pct_change'
            })

            # 转换日期类型
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d').dt.date

            # 计算其他字段
            if 'pre_close' in df.columns and 'close' in df.columns:
                df['change_amount'] = df['close'] - df['pre_close']
                df['amplitude'] = ((df['high'] - df['low']) / df['pre_close'] * 100)

            # 成交量单位转换（手 -> 股）
            if 'volume' in df.columns:
                df['volume'] = df['volume'] * 100

            # 成交额单位转换（千元 -> 元）
            if 'amount' in df.columns:
                df['amount'] = df['amount'] * 1000

            # 选择标准字段
            standard_columns = [
                'trade_date', 'open', 'high', 'low', 'close',
                'volume', 'amount', 'amplitude', 'pct_change',
                'change_amount', 'turnover'
            ]
            df = df[[col for col in standard_columns if col in df.columns]]

            # 按日期升序排序
            df = df.sort_values('trade_date')

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

        注意: Tushare 分时数据需要 2000 积分

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
            # 标准化日期格式
            start = self.normalize_date(start_date) if start_date else \
                (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
            end = self.normalize_date(end_date) if end_date else \
                datetime.now().strftime('%Y%m%d')

            # 转换为 Tushare 格式的股票代码
            ts_code = self._to_ts_code(code)

            logger.debug(f"获取 {ts_code} {period}分钟数据: {start} - {end}")

            # 映射周期
            freq_map = {
                '1': '1min',
                '5': '5min',
                '15': '15min',
                '30': '30min',
                '60': '60min'
            }
            freq = freq_map.get(period, '5min')

            # 获取分时数据（需要高积分）
            df = self._retry_request(
                self.pro.stk_mins,
                ts_code=ts_code,
                start_date=start,
                end_date=end,
                freq=freq,
                adj=adjust
            )

            if df is None or df.empty:
                logger.warning(f"{code}: 无分时数据")
                return pd.DataFrame()

            # 标准化字段名
            df = df.rename(columns={
                'trade_time': 'trade_time',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount'
            })

            # 转换时间类型
            df['trade_time'] = pd.to_datetime(df['trade_time'])

            # 添加周期字段
            df['period'] = period

            # 成交量单位转换
            if 'volume' in df.columns:
                df['volume'] = df['volume'] * 100

            # 选择标准字段
            standard_columns = [
                'trade_time', 'period', 'open', 'high', 'low', 'close',
                'volume', 'amount'
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

        注意: Tushare 实时行情需要 5000 积分

        Args:
            codes: 股票代码列表 (None 表示获取全部)

        Returns:
            pd.DataFrame: 标准化的实时行情数据
        """
        try:
            logger.info("正在获取实时行情...")

            # 如果指定了代码列表，转换格式
            ts_codes = None
            if codes:
                ts_codes = ','.join([self._to_ts_code(code) for code in codes])

            # 获取实时行情（需要高积分）
            df = self._retry_request(
                self.pro.realtime_quotes,
                ts_code=ts_codes
            )

            if df is None or df.empty:
                raise ValueError("获取实时行情失败，返回数据为空")

            # 标准化字段名
            df = df.rename(columns={
                'ts_code': 'ts_code_raw',
                'name': 'name',
                'price': 'latest_price',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'pre_close': 'pre_close',
                'volume': 'volume',
                'amount': 'amount',
                'pct_chg': 'pct_change',
                'change': 'change_amount'
            })

            # 提取股票代码（去除后缀）
            df['code'] = df['ts_code_raw'].apply(lambda x: x.split('.')[0])

            # 计算换手率和振幅
            if all(col in df.columns for col in ['pre_close', 'high', 'low']):
                df['amplitude'] = ((df['high'] - df['low']) / df['pre_close'] * 100)

            # 添加行情时间
            df['trade_time'] = datetime.now()

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

    # ========== 工具方法 ==========

    @staticmethod
    def _to_ts_code(code: str) -> str:
        """
        转换为 Tushare 格式的股票代码

        Args:
            code: 股票代码 (如 '000001')

        Returns:
            str: Tushare 格式代码 (如 '000001.SZ')
        """
        if '.' in code:
            return code

        # 根据代码前缀判断交易所
        if code.startswith(('6', '68', '688')):
            return f"{code}.SH"  # 上海
        elif code.startswith(('0', '2', '3', '8', '4')):
            return f"{code}.SZ"  # 深圳
        else:
            return f"{code}.SH"  # 默认上海

    def get_new_stocks(self, days: int = 30) -> pd.DataFrame:
        """
        获取最近 N 天上市的新股

        Args:
            days: 最近天数

        Returns:
            pd.DataFrame: 标准化的新股列表
        """
        try:
            logger.info(f"正在从 Tushare 获取最近 {days} 天的新股...")

            # 计算日期范围
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            # 使用 new_share 接口获取新股上市日历
            df = self._retry_request(
                self.pro.new_share,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到新股数据，尝试使用 stock_basic 接口")
                # 备用方案：从 stock_basic 筛选最近上市的股票
                df_all = self._retry_request(
                    self.pro.stock_basic,
                    exchange='',
                    list_status='L',
                    fields='ts_code,symbol,name,area,industry,market,list_date'
                )
                df_all['list_date'] = pd.to_datetime(df_all['list_date'], format='%Y%m%d', errors='coerce')
                cutoff_date = datetime.now() - timedelta(days=days)
                df = df_all[df_all['list_date'] >= cutoff_date]

            # 标准化字段（避免重复映射到同一列）
            rename_map = {
                'ts_code': 'ts_code',
                'name': 'name'
            }
            # ipo_date 和 issue_date 只能有一个，优先使用 ipo_date
            if 'ipo_date' in df.columns:
                rename_map['ipo_date'] = 'list_date'
            elif 'issue_date' in df.columns:
                rename_map['issue_date'] = 'list_date'

            df = df.rename(columns=rename_map)

            if 'symbol' in df.columns:
                df = df.rename(columns={'symbol': 'code'})
            elif 'ts_code' in df.columns:
                df['code'] = df['ts_code'].str[:6]

            # 添加市场类型
            if 'market' not in df.columns:
                df['market'] = df['code'].apply(lambda x: self._parse_market(x) if pd.notna(x) else '其他')

            # 转换日期格式（确保是 date 对象，不是 Timestamp）
            if 'list_date' in df.columns:
                df['list_date'] = pd.to_datetime(df['list_date'], format='%Y%m%d', errors='coerce').dt.date

            # 添加状态
            df['status'] = '正常'

            # 选择标准字段
            df = df[['code', 'name', 'market', 'list_date', 'status']].copy()

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
            logger.info("正在从 Tushare 获取退市股票列表...")

            # 使用 stock_basic 接口，list_status='D' 获取退市股票
            df = self._retry_request(
                self.pro.stock_basic,
                exchange='',
                list_status='D',  # 退市
                fields='ts_code,symbol,name,area,industry,market,list_date,delist_date'
            )

            if df is None or df.empty:
                raise ValueError("获取退市股票列表失败，返回数据为空")

            # 标准化字段
            df = df.rename(columns={
                'symbol': 'code',
                'name': 'name',
                'list_date': 'list_date',
                'delist_date': 'delist_date',
                'market': 'market'
            })

            # 转换日期格式（确保是 date 对象，不是 Timestamp）
            df['list_date'] = pd.to_datetime(df['list_date'], format='%Y%m%d', errors='coerce').dt.date
            df['delist_date'] = pd.to_datetime(df['delist_date'], format='%Y%m%d', errors='coerce').dt.date

            # 处理市场类型映射
            market_map = {
                '主板': '上海主板',
                '创业板': '创业板',
                '科创板': '科创板',
                '北交所': '北交所'
            }
            df['market'] = df['market'].map(market_map).fillna('其他')

            # 选择标准字段
            df = df[['code', 'name', 'list_date', 'delist_date', 'market']].copy()

            logger.info(f"✓ 成功获取 {len(df)} 只退市股票")
            return df

        except Exception as e:
            logger.error(f"获取退市股票列表失败: {e}")
            raise

    @staticmethod
    def _parse_market(code: str) -> str:
        """根据股票代码解析市场类型"""
        if not isinstance(code, str):
            return '其他'
        if code.startswith('60') or code.startswith('68'):
            return '上海主板'
        elif code.startswith('000') or code.startswith('001') or code.startswith('002'):
            return '深圳主板'
        elif code.startswith('300'):
            return '创业板'
        elif code.startswith('688'):
            return '科创板'
        elif code.startswith(('8', '4')):
            return '北交所'
        else:
            return '其他'
