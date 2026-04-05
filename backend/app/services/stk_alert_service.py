"""
交易所重点提示证券服务

负责交易所重点提示证券数据的同步和查询业务逻辑
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict
from loguru import logger

from app.repositories.stk_alert_repository import StkAlertRepository
from core.src.providers import DataProviderFactory


class StkAlertService:
    """交易所重点提示证券服务"""

    FULL_HISTORY_LOCK_KEY = "sync:stk_alert:full_history:lock"

    def __init__(self):
        self.stk_alert_repo = StkAlertRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ StkAlertService initialized")

    async def sync_full_history(self, redis_client, start_date: Optional[str] = None, update_state_fn=None) -> Dict:
        """全量同步交易所重点提示证券数据（单次请求，接口不支持日期范围参数）

        stk_alert 接口不支持 start_date/end_date 过滤，不传日期直接返回全量最新数据。
        """
        logger.info("[全量stk_alert] 开始全量同步（接口不支持日期范围，单次拉取全量）")
        try:
            provider = self._get_provider()
            df = await asyncio.to_thread(provider.get_stk_alert)
            records = 0
            if df is not None and not df.empty:
                df = self._validate_and_clean_data(df)
                records = await asyncio.to_thread(self.stk_alert_repo.bulk_upsert, df)
            if update_state_fn:
                update_state_fn(state='PROGRESS', meta={'current': 1, 'total': 1, 'percent': 100.0, 'records': records, 'errors': 0})
            logger.info(f"[全量stk_alert] ✅ 同步完成，入库 {records} 条")
            return {"status": "success", "total": 1, "success": 1, "skipped": 0, "errors": 0,
                    "records": records, "message": f"同步完成，入库 {records} 条"}
        except Exception as e:
            logger.error(f"[全量stk_alert] 同步失败: {e}")
            return {"status": "error", "total": 1, "success": 0, "skipped": 0, "errors": 1,
                    "records": 0, "message": f"同步失败: {str(e)}"}

    async def sync_stk_alert(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        同步交易所重点提示证券数据

        Args:
            trade_date: 单个交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步交易所重点提示证券数据: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, ts_code={ts_code}")

            # 1. 获取Tushare数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_stk_alert,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code
            )

            if df is None or df.empty:
                logger.warning("未获取到数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从Tushare获取到 {len(df)} 条记录")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.stk_alert_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条交易所重点提示证券记录")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条记录"
            }

        except Exception as e:
            logger.error(f"同步交易所重点提示证券数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "error": str(e),
                "message": f"同步失败: {str(e)}"
            }

    async def get_stk_alert_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        获取交易所重点提示证券数据

        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            ts_code: 股票代码（可选）
            limit: 返回记录数限制

        Returns:
            数据字典，包含items和total
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 获取数据
            items, total = await asyncio.gather(
                asyncio.to_thread(
                    self.stk_alert_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.stk_alert_repo.get_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code
                )
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD（用于前端显示）
            for item in items:
                if item['start_date']:
                    item['start_date'] = self._format_date_for_display(item['start_date'])
                if item['end_date']:
                    item['end_date'] = self._format_date_for_display(item['end_date'])

            return {
                "items": items,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取交易所重点提示证券数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）

        Returns:
            统计信息字典
        """
        try:
            # 日期格式转换
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            stats = await asyncio.to_thread(
                self.stk_alert_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    async def get_latest_data(self, limit: int = 20) -> Dict:
        """
        获取最新的重点提示证券数据

        Args:
            limit: 返回记录数限制

        Returns:
            数据字典
        """
        try:
            # 获取最新提示起始日期
            latest_date = await asyncio.to_thread(
                self.stk_alert_repo.get_latest_start_date
            )

            if not latest_date:
                return {"items": [], "total": 0}

            # 获取该日期的数据
            items = await asyncio.to_thread(
                self.stk_alert_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                limit=limit
            )

            # 日期格式转换
            for item in items:
                if item['start_date']:
                    item['start_date'] = self._format_date_for_display(item['start_date'])
                if item['end_date']:
                    item['end_date'] = self._format_date_for_display(item['end_date'])

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            raise

    async def get_active_alerts(self, current_date: Optional[str] = None, limit: int = 100) -> Dict:
        """
        获取当前仍在有效期内的重点提示证券

        Args:
            current_date: 当前日期（YYYY-MM-DD格式），默认为今天
            limit: 返回记录数限制

        Returns:
            数据字典
        """
        try:
            # 如果未提供日期，使用今天
            if not current_date:
                current_date = datetime.now().strftime('%Y-%m-%d')

            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            current_date_fmt = current_date.replace('-', '')

            # 获取当前有效的重点提示证券
            items = await asyncio.to_thread(
                self.stk_alert_repo.get_active_alerts,
                current_date=current_date_fmt,
                limit=limit
            )

            # 日期格式转换
            for item in items:
                if item['start_date']:
                    item['start_date'] = self._format_date_for_display(item['start_date'])
                if item['end_date']:
                    item['end_date'] = self._format_date_for_display(item['end_date'])

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取当前有效的重点提示证券失败: {e}")
            raise

    def _get_provider(self):
        """获取Tushare数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: 原始DataFrame

        Returns:
            清洗后的DataFrame
        """
        # 确保必需列存在
        required_columns = ['ts_code', 'start_date']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需列: {col}")

        # 确保日期格式为 YYYYMMDD（8位）
        for date_col in ['start_date', 'end_date']:
            if date_col in df.columns:
                df[date_col] = df[date_col].astype(str).str.replace('-', '')
                # 验证日期格式
                invalid_dates = df[df[date_col].str.len() != 8]
                if not invalid_dates.empty:
                    logger.warning(f"发现 {len(invalid_dates)} 条无效{date_col}记录，将被过滤")
                    df = df[df[date_col].str.len() == 8]

        # 删除重复记录
        df = df.drop_duplicates(subset=['ts_code', 'start_date'], keep='last')

        # 处理空值
        df = df.fillna({
            'name': '',
            'end_date': '',
            'type': ''
        })

        return df

    def _format_date_for_display(self, date_str: str) -> str:
        """
        格式化日期用于前端显示

        Args:
            date_str: YYYYMMDD格式的日期字符串

        Returns:
            YYYY-MM-DD格式的日期字符串
        """
        if not date_str or len(date_str) != 8:
            return date_str

        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        except Exception:
            return date_str
