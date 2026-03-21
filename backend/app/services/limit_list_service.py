"""
涨跌停列表服务层

负责涨跌停列表数据的业务逻辑处理
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from loguru import logger

from app.repositories import LimitListRepository
from core.src.providers import DataProviderFactory


class LimitListService:
    """涨跌停列表服务类"""

    def __init__(self):
        """初始化涨跌停列表服务"""
        self.limit_list_repo = LimitListRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ LimitListService initialized")

    def _get_provider(self):
        """获取Tushare数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_limit_list(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit_type: Optional[str] = None
    ) -> Dict:
        """
        同步涨跌停列表数据

        Args:
            trade_date: 单个交易日期，格式：YYYYMMDD
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit_type: 涨跌停类型（U涨停D跌停Z炸板）（可选）

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步涨跌停列表数据: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, limit_type={limit_type}")

            # 1. 获取Tushare数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_limit_list_d,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                limit_type=limit_type
            )

            if df is None or df.empty:
                logger.warning("未获取到涨跌停列表数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从Tushare获取到 {len(df)} 条涨跌停列表数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.limit_list_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条涨跌停列表数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步涨跌停列表数据失败: {str(e)}")
            return {
                "status": "error",
                "records": 0,
                "error": str(e),
                "message": "同步失败"
            }

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: pandas DataFrame

        Returns:
            清洗后的 DataFrame
        """
        # 确保必需字段存在
        required_fields = ['trade_date', 'ts_code']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 移除空值记录
        df = df.dropna(subset=['trade_date', 'ts_code'])

        # 数据类型转换
        if 'trade_date' in df.columns:
            df['trade_date'] = df['trade_date'].astype(str)

        if 'ts_code' in df.columns:
            df['ts_code'] = df['ts_code'].astype(str)

        # 移除重复记录
        df = df.drop_duplicates(subset=['trade_date', 'ts_code'], keep='last')

        logger.debug(f"数据清洗完成，剩余 {len(df)} 条记录")
        return df

    async def get_limit_list_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit_type: Optional[str] = None,
        limit: int = 100
    ) -> Dict:
        """
        获取涨跌停列表数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit_type: 涨跌停类型（U涨停D跌停Z炸板）（可选）
            limit: 返回记录数限制

        Returns:
            数据字典
        """
        try:
            # 设置默认日期范围
            if not start_date:
                start_date = '20200101'  # 涨跌停数据从2020年开始
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            # 获取数据
            items = await asyncio.to_thread(
                self.limit_list_repo.get_by_date_range,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                limit_type=limit_type,
                limit=limit
            )

            # 获取统计信息
            statistics = await asyncio.to_thread(
                self.limit_list_repo.get_statistics,
                start_date=start_date,
                end_date=end_date,
                limit_type=limit_type
            )

            # 数据格式转换
            formatted_items = []
            for item in items:
                formatted_items.append({
                    'trade_date': item[0],
                    'ts_code': item[1],
                    'industry': item[2],
                    'name': item[3],
                    'close': float(item[4]) if item[4] else None,
                    'pct_chg': float(item[5]) if item[5] else None,
                    'amount': float(item[6]) if item[6] else None,
                    'limit_amount': float(item[7]) if item[7] else None,
                    'float_mv': float(item[8]) if item[8] else None,
                    'total_mv': float(item[9]) if item[9] else None,
                    'turnover_ratio': float(item[10]) if item[10] else None,
                    'fd_amount': float(item[11]) if item[11] else None,
                    'first_time': item[12],
                    'last_time': item[13],
                    'open_times': item[14],
                    'up_stat': item[15],
                    'limit_times': item[16],
                    'limit_type': item[17],
                })

            return {
                'items': formatted_items,
                'statistics': statistics,
                'total': len(formatted_items)
            }

        except Exception as e:
            logger.error(f"获取涨跌停列表数据失败: {str(e)}")
            raise

    async def get_latest_data(self, limit_type: Optional[str] = None) -> Dict:
        """
        获取最新涨跌停列表数据

        Args:
            limit_type: 涨跌停类型（U涨停D跌停Z炸板）（可选）

        Returns:
            最新数据字典
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(
                self.limit_list_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    'items': [],
                    'statistics': {},
                    'total': 0,
                    'trade_date': None
                }

            # 获取最新数据
            items = await asyncio.to_thread(
                self.limit_list_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                limit_type=limit_type,
                limit=1000
            )

            # 获取统计信息
            statistics = await asyncio.to_thread(
                self.limit_list_repo.get_statistics,
                start_date=latest_date,
                end_date=latest_date,
                limit_type=limit_type
            )

            # 数据格式转换
            formatted_items = []
            for item in items:
                formatted_items.append({
                    'trade_date': item[0],
                    'ts_code': item[1],
                    'industry': item[2],
                    'name': item[3],
                    'close': float(item[4]) if item[4] else None,
                    'pct_chg': float(item[5]) if item[5] else None,
                    'amount': float(item[6]) if item[6] else None,
                    'limit_amount': float(item[7]) if item[7] else None,
                    'float_mv': float(item[8]) if item[8] else None,
                    'total_mv': float(item[9]) if item[9] else None,
                    'turnover_ratio': float(item[10]) if item[10] else None,
                    'fd_amount': float(item[11]) if item[11] else None,
                    'first_time': item[12],
                    'last_time': item[13],
                    'open_times': item[14],
                    'up_stat': item[15],
                    'limit_times': item[16],
                    'limit_type': item[17],
                })

            return {
                'items': formatted_items,
                'statistics': statistics,
                'total': len(formatted_items),
                'trade_date': latest_date
            }

        except Exception as e:
            logger.error(f"获取最新涨跌停列表数据失败: {str(e)}")
            raise

    async def get_top_limit_up_stocks(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取涨停股票排行

        Args:
            trade_date: 交易日期，格式：YYYYMMDD（None表示最新日期）
            limit: 返回记录数限制

        Returns:
            涨停股票列表
        """
        try:
            # 如果未指定日期，获取最新日期
            if not trade_date:
                trade_date = await asyncio.to_thread(
                    self.limit_list_repo.get_latest_trade_date
                )
                if not trade_date:
                    return []

            # 获取涨停股票排行
            items = await asyncio.to_thread(
                self.limit_list_repo.get_top_limit_up_stocks,
                trade_date=trade_date,
                limit=limit
            )

            # 数据格式转换
            formatted_items = []
            for item in items:
                formatted_items.append({
                    'trade_date': item[0],
                    'ts_code': item[1],
                    'industry': item[2],
                    'name': item[3],
                    'close': float(item[4]) if item[4] else None,
                    'pct_chg': float(item[5]) if item[5] else None,
                    'amount': float(item[6]) if item[6] else None,
                    'fd_amount': float(item[7]) if item[7] else None,
                    'first_time': item[8],
                    'last_time': item[9],
                    'open_times': item[10],
                    'up_stat': item[11],
                    'limit_times': item[12],
                    'limit_type': item[13],
                })

            return formatted_items

        except Exception as e:
            logger.error(f"获取涨停股票排行失败: {str(e)}")
            raise
