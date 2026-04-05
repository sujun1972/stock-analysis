"""
神奇九转指标数据服务
"""

import traceback
from typing import Optional, Dict, List
import asyncio
from datetime import datetime, timedelta
from loguru import logger

from app.repositories import StkNineturnRepository
from app.services.stock_quote_cache import stock_quote_cache
from core.src.providers import DataProviderFactory
from app.core.config import settings


class StkNineturnService:
    """神奇九转指标数据服务"""

    def __init__(self):
        self.stk_nineturn_repo = StkNineturnRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def sync_stk_nineturn(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        freq: str = 'daily',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步神奇九转指标数据

        Args:
            ts_code: 股票代码
            trade_date: 交易日期，格式：YYYYMMDD
            freq: 频率，默认daily
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            同步结果字典
        """
        try:
            # 参数验证：至少提供一个参数
            if not any([ts_code, trade_date, start_date, end_date]):
                # 默认同步最近30天数据
                end_date_dt = datetime.now()
                start_date_dt = end_date_dt - timedelta(days=30)
                start_date = start_date_dt.strftime('%Y%m%d')
                end_date = end_date_dt.strftime('%Y%m%d')
                logger.info(f"未指定参数，默认同步最近30天: {start_date} ~ {end_date}")

            # 从 Tushare 获取数据
            provider = self._get_provider()
            logger.info(f"开始从 Tushare 获取神奇九转数据: ts_code={ts_code}, trade_date={trade_date}, freq={freq}")

            df = await asyncio.to_thread(
                provider.get_stk_nineturn,
                ts_code=ts_code,
                trade_date=trade_date,
                freq=freq,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到神奇九转数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"获取到 {len(df)} 条神奇九转数据")

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.stk_nineturn_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条神奇九转数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步神奇九转数据失败: {e}\n{traceback.format_exc()}")
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: 原始DataFrame

        Returns:
            清洗后的DataFrame
        """
        try:
            # 删除重复记录（基于 ts_code + trade_date + freq）
            initial_count = len(df)
            df = df.drop_duplicates(subset=['ts_code', 'trade_date', 'freq'], keep='last')
            if len(df) < initial_count:
                logger.info(f"删除了 {initial_count - len(df)} 条重复记录")

            # 确保必需字段不为空
            required_fields = ['ts_code', 'trade_date']
            for field in required_fields:
                if field in df.columns:
                    df = df[df[field].notna()]

            # 设置默认值
            if 'freq' not in df.columns or df['freq'].isna().any():
                df['freq'] = 'daily'

            # 处理日期格式 (Tushare返回的是datetime字符串)
            if 'trade_date' in df.columns:
                # trade_date 已经是 datetime 格式，无需转换
                pass

            logger.info(f"数据验证完成，有效记录数: {len(df)}")
            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise

    async def resolve_default_date_range(self):
        """
        解析默认日期范围：返回表中最新日期（作为 end_date），往前30天作为 start_date。
        用于查询端点在用户未传日期时自动回填。

        Returns:
            (start_date_str, end_date_str) YYYY-MM-DD 格式，或 (None, None)
        """
        try:
            latest = await asyncio.to_thread(self.stk_nineturn_repo.get_latest_trade_date)
            if latest:
                end_dt = datetime.strptime(latest, '%Y-%m-%d')
                start_dt = end_dt - timedelta(days=30)
                return start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d')
            return None, None
        except Exception as e:
            logger.error(f"解析默认日期范围失败: {e}")
            return None, None

    async def get_stk_nineturn_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        freq: str = 'daily',
        limit: int = 100,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict:
        """
        获取神奇九转数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            freq: 频率，默认daily
            limit: 返回记录数限制
            offset: 偏移量
            sort_by: 排序字段
            sort_order: 排序方向 asc/desc

        Returns:
            包含数据列表和统计信息的字典
        """
        try:
            # 未传日期时自动回填默认日期范围
            resolved_start = start_date
            resolved_end = end_date
            if not start_date and not end_date and not ts_code:
                resolved_start, resolved_end = await self.resolve_default_date_range()

            # 并发查询数据、总数、统计
            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.stk_nineturn_repo.get_by_date_range,
                    start_date=resolved_start,
                    end_date=resolved_end,
                    ts_code=ts_code,
                    freq=freq,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.stk_nineturn_repo.get_record_count,
                    start_date=resolved_start,
                    end_date=resolved_end,
                    ts_code=ts_code,
                    freq=freq
                ),
                asyncio.to_thread(
                    self.stk_nineturn_repo.get_statistics,
                    start_date=resolved_start,
                    end_date=resolved_end,
                    ts_code=ts_code,
                    freq=freq
                )
            )

            # 注入股票名称
            if items:
                ts_codes = list(dict.fromkeys(item['ts_code'] for item in items))
                quotes = await asyncio.to_thread(stock_quote_cache._repo.get_quotes, ts_codes)
                for item in items:
                    item['name'] = quotes.get(item['ts_code'], {}).get('name', '')

            return {
                "items": items,
                "statistics": statistics,
                "total": total,
                "start_date": resolved_start,
                "end_date": resolved_end
            }

        except Exception as e:
            logger.error(f"获取神奇九转数据失败: {e}")
            raise

    async def get_turn_signals(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        signal_type: str = 'all',
        limit: int = 50
    ) -> List[Dict]:
        """
        获取九转信号

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            signal_type: 信号类型 ('up': 上九转, 'down': 下九转, 'all': 全部)
            limit: 返回记录数限制

        Returns:
            九转信号列表
        """
        try:
            signals = await asyncio.to_thread(
                self.stk_nineturn_repo.get_turn_signals,
                start_date=start_date,
                end_date=end_date,
                signal_type=signal_type,
                limit=limit
            )

            return signals

        except Exception as e:
            logger.error(f"获取九转信号失败: {e}")
            raise

    async def get_latest_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新交易日期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新交易日期字符串（YYYY-MM-DD）
        """
        try:
            latest_date = await asyncio.to_thread(
                self.stk_nineturn_repo.get_latest_trade_date,
                ts_code=ts_code
            )
            return latest_date

        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            raise
