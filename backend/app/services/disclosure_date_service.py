"""
财报披露计划服务

负责财报披露计划数据的业务逻辑处理
"""

from typing import Optional, Dict
import asyncio
from loguru import logger

from app.repositories.disclosure_date_repository import DisclosureDateRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class DisclosureDateService:
    """财报披露计划服务"""

    def __init__(self):
        self.disclosure_date_repo = DisclosureDateRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取 Tushare Provider"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def get_disclosure_date_data(
        self,
        ts_code: Optional[str] = None,
        end_date: Optional[str] = None,
        start_date: Optional[str] = None,
        limit: int = 30
    ) -> Dict:
        """
        获取财报披露计划数据

        Args:
            ts_code: 股票代码
            end_date: 截止日期（报告期），格式：YYYY-MM-DD
            start_date: 开始日期（报告期），格式：YYYY-MM-DD
            limit: 限制返回记录数

        Returns:
            包含数据列表和统计信息的字典
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 查询数据
            if ts_code:
                items = await asyncio.to_thread(
                    self.disclosure_date_repo.get_by_ts_code,
                    ts_code,
                    limit
                )
            else:
                items = await asyncio.to_thread(
                    self.disclosure_date_repo.get_by_date_range,
                    start_date_fmt,
                    end_date_fmt,
                    None,
                    limit
                )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD（用于前端显示）
            for item in items:
                for field in ['ann_date', 'end_date', 'pre_date', 'actual_date', 'modify_date']:
                    if item.get(field) and len(str(item[field])) == 8:
                        date_str = str(item[field])
                        item[field] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            # 获取统计信息
            statistics = await asyncio.to_thread(
                self.disclosure_date_repo.get_statistics,
                start_date_fmt,
                end_date_fmt
            )

            return {
                "items": items,
                "statistics": statistics,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取财报披露计划数据失败: {e}")
            raise

    async def sync_disclosure_date(
        self,
        ts_code: Optional[str] = None,
        end_date: Optional[str] = None,
        pre_date: Optional[str] = None,
        ann_date: Optional[str] = None,
        actual_date: Optional[str] = None
    ) -> Dict:
        """
        同步财报披露计划数据

        Args:
            ts_code: 股票代码
            end_date: 报告期（每个季度最后一天），格式：YYYYMMDD
            pre_date: 计划披露日期，格式：YYYYMMDD
            ann_date: 最新披露公告日，格式：YYYYMMDD
            actual_date: 实际披露日期，格式：YYYYMMDD

        Returns:
            同步结果
        """
        try:
            # 获取 Tushare Provider
            provider = self._get_provider()

            # 调用 Tushare API 获取数据
            logger.info(f"开始从Tushare获取财报披露计划数据: ts_code={ts_code}, end_date={end_date}")
            df = await asyncio.to_thread(
                provider.get_disclosure_date,
                ts_code=ts_code,
                end_date=end_date,
                pre_date=pre_date,
                ann_date=ann_date,
                actual_date=actual_date
            )

            if df is None or df.empty:
                logger.warning("未获取到财报披露计划数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"获取到 {len(df)} 条财报披露计划数据")

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.disclosure_date_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条财报披露计划数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步财报披露计划数据失败: {e}")
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
            # 确保必需字段存在（只有ts_code和end_date是必需的）
            required_fields = ['ts_code', 'end_date']
            for field in required_fields:
                if field not in df.columns:
                    raise ValueError(f"缺少必需字段: {field}")

            # 移除重复记录（根据主键：ts_code + end_date）
            df = df.drop_duplicates(subset=['ts_code', 'end_date'], keep='last')

            # 填充可选字段的None值
            optional_fields = ['ann_date', 'pre_date', 'actual_date', 'modify_date']
            for field in optional_fields:
                if field not in df.columns:
                    df[field] = None

            logger.debug(f"数据验证完成，共 {len(df)} 条有效记录")
            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise
