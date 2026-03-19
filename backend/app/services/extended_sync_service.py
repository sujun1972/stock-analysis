"""
扩展数据同步服务

用于同步Tushare扩展数据(资金流向、每日指标、北向资金等)。
采用模板方法模式统一同步流程,减少代码重复,提高可维护性。
"""

from typing import Optional, Dict, Any, List, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import asyncio
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db, get_async_db
from app.core.config import settings
from loguru import logger
from core.src.providers import DataProviderFactory
from core.src.data.validators.extended_validator import ExtendedDataValidator
from app.services.trading_calendar_service import trading_calendar_service
from app.services.data_availability_config import DataAvailabilityConfig


class DataType(str, Enum):
    """数据类型枚举"""
    DAILY_BASIC = "daily_basic"
    MONEYFLOW = "moneyflow"
    MARGIN_DETAIL = "margin_detail"
    STK_LIMIT = "stk_limit"
    ADJ_FACTOR = "adj_factor"
    BLOCK_TRADE = "block_trade"
    SUSPEND = "suspend"
    MONEYFLOW_HSGT = "moneyflow_hsgt"
    MONEYFLOW_MKT_DC = "moneyflow_mkt_dc"
    MONEYFLOW_IND_DC = "moneyflow_ind_dc"
    MONEYFLOW_STOCK_DC = "moneyflow_stock_dc"


@dataclass
class SyncResult:
    """
    同步结果数据类

    Attributes:
        task_id: 任务唯一标识
        status: 任务状态('success' 或 'error')
        records: 同步的记录数
        validation_errors: 数据验证错误数
        validation_warnings: 数据验证警告数
        message: 结果描述信息
        error: 错误信息(仅在status='error'时有值)
    """
    task_id: str
    status: str
    records: int
    validation_errors: int = 0
    validation_warnings: int = 0
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典,过滤掉默认值"""
        result = {
            "task_id": self.task_id,
            "status": self.status,
            "records": self.records,
            "message": self.message
        }
        if self.validation_errors > 0:
            result["validation_errors"] = self.validation_errors
        if self.validation_warnings > 0:
            result["validation_warnings"] = self.validation_warnings
        if self.error:
            result["error"] = self.error
        return result


class ExtendedDataSyncService:
    """扩展数据同步服务"""

    def __init__(self):
        self.provider_factory = DataProviderFactory()
        self.validator = ExtendedDataValidator()

    def _get_provider(self):
        """获取Tushare数据提供者"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    def _generate_task_id(self, task_type: str) -> str:
        """生成任务ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{task_type}_{timestamp}"

    def _calculate_trade_date(
        self,
        data_type: str,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None
    ) -> Optional[str]:
        """
        根据数据类型和可用性规则计算交易日期

        Args:
            data_type: 数据类型
            trade_date: 已指定的交易日期
            start_date: 已指定的开始日期

        Returns:
            计算后的交易日期,如果已指定日期则返回None
        """
        if trade_date or start_date:
            return None

        calculated_date = trading_calendar_service.get_latest_data_date_sync()
        result_date = DataAvailabilityConfig.should_use_date(data_type, calculated_date)

        logger.info(f"计算交易日期: {calculated_date} -> {result_date}")
        logger.debug(DataAvailabilityConfig.get_description(data_type, calculated_date))

        return result_date

    def _convert_date_string_to_date(self, date_str: str) -> datetime.date:
        """转换YYYYMMDD格式字符串为date对象"""
        return datetime.strptime(date_str, '%Y%m%d').date()

    async def _validate_and_fix_data(
        self,
        df: pd.DataFrame,
        data_type: str,
        validator_method: Callable
    ) -> Tuple[pd.DataFrame, int, int]:
        """
        验证数据质量并尝试自动修复

        Args:
            df: 数据DataFrame
            data_type: 数据类型
            validator_method: 验证方法

        Returns:
            (修复后的DataFrame, 错误数, 警告数)
        """
        is_valid, errors, warnings = validator_method(df)

        if errors:
            logger.warning(f"{data_type}数据验证失败,尝试自动修复: {errors}")
            df = self.validator.fix_data(df, data_type)
            is_valid, errors, warnings = validator_method(df)

            if errors:
                logger.error(f"{data_type}数据修复后仍有错误: {errors}")

        if warnings:
            logger.debug(f"{data_type}数据验证警告: {warnings}")

        return df, len(errors) if errors else 0, len(warnings) if warnings else 0

    async def _sync_data_template(
        self,
        data_type: DataType,
        fetch_method: Callable,
        insert_method: Callable,
        validator_method: Optional[Callable] = None,
        **fetch_params
    ) -> Dict[str, Any]:
        """
        数据同步模板方法(Template Method Pattern)

        统一的同步流程: 获取数据 -> 验证修复 -> 插入数据库

        Args:
            data_type: 数据类型枚举
            fetch_method: 数据获取方法
            insert_method: 数据插入方法
            validator_method: 数据验证方法(可选)
            **fetch_params: 传递给fetch_method的参数

        Returns:
            同步结果字典
        """
        task_id = self._generate_task_id(data_type.value)

        try:
            logger.info(f"开始同步{data_type.value}: {fetch_params}")
            provider = self._get_provider()

            # 步骤1: 获取数据
            df = fetch_method(provider, **fetch_params)

            if df is None or len(df) == 0:
                logger.warning(f"{data_type.value}无可用数据")
                return SyncResult(
                    task_id=task_id,
                    status="success",
                    records=0,
                    message="无数据需要同步"
                ).to_dict()

            # 步骤2: 验证和修复(可选)
            validation_errors = 0
            validation_warnings = 0
            if validator_method:
                df, validation_errors, validation_warnings = await self._validate_and_fix_data(
                    df, data_type.value, validator_method
                )

            # 步骤3: 插入数据库
            await insert_method(df)

            logger.info(f"成功同步{data_type.value}: {len(df)}条记录")
            return SyncResult(
                task_id=task_id,
                status="success",
                records=len(df),
                validation_errors=validation_errors,
                validation_warnings=validation_warnings,
                message=f"成功同步 {len(df)} 条数据"
            ).to_dict()

        except Exception as e:
            logger.error(f"同步{data_type.value}失败: {str(e)}", exc_info=True)
            return SyncResult(
                task_id=task_id,
                status="error",
                records=0,
                error=str(e)
            ).to_dict()

    async def _upsert_records(
        self,
        df: pd.DataFrame,
        table_name: str,
        conflict_columns: List[str],
        update_columns: List[str],
        date_fields: Optional[List[str]] = None,
        keep_date_as_string: bool = False
    ):
        """
        通用UPSERT插入方法(INSERT ... ON CONFLICT DO UPDATE)

        Args:
            df: 数据DataFrame
            table_name: 目标表名
            conflict_columns: 唯一性冲突检测列
            update_columns: 冲突时需要更新的列
            date_fields: 需要转换的日期字段
            keep_date_as_string: 保持日期为字符串(某些表使用VARCHAR存储日期)
        """
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # 转换日期字段
                if date_fields and not keep_date_as_string:
                    for field in date_fields:
                        if field in record and isinstance(record[field], str) and record[field]:
                            record[field] = self._convert_date_string_to_date(record[field])

                # 构建INSERT语句
                columns = list(record.keys())
                placeholders = [f":{col}" for col in columns]

                insert_clause = f"""
                    INSERT INTO {table_name} ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                """

                # 构建ON CONFLICT UPDATE语句
                conflict_clause = f"ON CONFLICT ({', '.join(conflict_columns)})"
                update_clause = ", ".join([
                    f"{col} = EXCLUDED.{col}" for col in update_columns
                ])

                # 添加updated_at字段(如果存在)
                if 'updated_at' not in update_columns:
                    update_clause += ", updated_at = CURRENT_TIMESTAMP"

                query = text(f"""
                    {insert_clause}
                    {conflict_clause} DO UPDATE SET
                    {update_clause}
                """)

                await db.execute(query, record)

            await db.commit()

    # ========== 公共同步方法 ==========

    async def sync_daily_basic(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步每日指标数据
        优先级: P0
        调用频率: 每日17:00
        积分消耗: 120
        """
        # 计算交易日期
        if not trade_date and not start_date:
            trade_date = self._calculate_trade_date("daily_basic", trade_date, start_date)

        return await self._sync_data_template(
            data_type=DataType.DAILY_BASIC,
            fetch_method=lambda p, **kw: p.get_daily_basic(**kw),
            insert_method=self._insert_daily_basic,
            validator_method=self.validator.validate_daily_basic,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_moneyflow(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        stock_list: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        同步资金流向数据(Tushare标准接口)

        数据源: pro.moneyflow() - 基于主动买卖单统计的资金流向
        优先级: P0
        调用频率: 每日17:30
        积分消耗: 2000(高消耗,需要控制调用频率)

        Note:
            - 不指定股票代码时,直接使用日期参数查询,Tushare会返回该日期所有有数据的股票
            - 单次最大提取6000行记录
            - 股票和时间参数至少输入一个
        """
        # 资金流向支持当前日期
        if not trade_date and not start_date:
            trade_date = trading_calendar_service.get_latest_data_date_sync()
            logger.info(f"资金流向: 使用日期 {trade_date}")

        return await self._sync_data_template(
            data_type=DataType.MONEYFLOW,
            fetch_method=lambda p, **kw: p.get_moneyflow(**kw),
            insert_method=self._insert_moneyflow,
            validator_method=self.validator.validate_moneyflow,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_margin_detail(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步融资融券数据
        优先级: P2
        调用频率: 每日18:30
        积分消耗: 300
        """
        if not trade_date and not start_date:
            trade_date = self._calculate_trade_date("margin_detail", trade_date, start_date)

        return await self._sync_data_template(
            data_type=DataType.MARGIN_DETAIL,
            fetch_method=lambda p, **kw: p.get_margin_detail(**kw),
            insert_method=self._insert_margin_detail,
            validator_method=self.validator.validate_margin_detail,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_stk_limit(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步涨跌停价格数据
        优先级: P1
        调用频率: 每日9:00
        积分消耗: 120
        """
        if not trade_date and not start_date:
            trade_date = self._calculate_trade_date("stk_limit", trade_date, start_date)

        return await self._sync_data_template(
            data_type=DataType.STK_LIMIT,
            fetch_method=lambda p, **kw: p.get_stk_limit(**kw),
            insert_method=self._insert_stk_limit,
            validator_method=self.validator.validate_stk_limit,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_adj_factor(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步复权因子数据
        优先级: P2
        调用频率: 每周一
        积分消耗: 120
        """
        return await self._sync_data_template(
            data_type=DataType.ADJ_FACTOR,
            fetch_method=lambda p, **kw: p.get_adj_factor(**kw),
            insert_method=self._insert_adj_factor,
            validator_method=None,  # 复权因子不需要验证
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_block_trade(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步大宗交易数据
        优先级: P3
        调用频率: 每日19:00
        积分消耗: 300
        """
        if not trade_date and not start_date:
            trade_date = self._calculate_trade_date("block_trade", trade_date, start_date)

        return await self._sync_data_template(
            data_type=DataType.BLOCK_TRADE,
            fetch_method=lambda p, **kw: p.get_block_trade(**kw),
            insert_method=self._insert_block_trade,
            validator_method=None,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_suspend(
        self,
        ts_code: Optional[str] = None,
        suspend_date: Optional[str] = None,
        resume_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步停复牌信息
        优先级: P3
        调用频率: 每日
        积分消耗: 120
        """
        return await self._sync_data_template(
            data_type=DataType.SUSPEND,
            fetch_method=lambda p, **kw: p.get_suspend(**kw),
            insert_method=self._insert_suspend,
            validator_method=None,
            ts_code=ts_code,
            suspend_date=suspend_date,
            resume_date=resume_date
        )

    async def sync_moneyflow_hsgt(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步沪深港通资金流向数据

        包含北向资金(沪股通+深股通)和南向资金(港股通上海+港股通深圳)的每日资金流向。
        数据从Tushare获取,支持2026年及以后的最新数据。

        优先级: P0
        调用频率: 每日收盘后
        积分消耗: 2000
        """
        if not trade_date and not start_date:
            trade_date = trading_calendar_service.get_latest_data_date_sync()
            logger.info(f"沪深港通资金流向: 使用日期 {trade_date}")

        return await self._sync_data_template(
            data_type=DataType.MONEYFLOW_HSGT,
            fetch_method=lambda p, **kw: p.get_moneyflow_hsgt(**kw),
            insert_method=self._insert_moneyflow_hsgt,
            validator_method=None,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_moneyflow_mkt_dc(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步大盘资金流向数据(东方财富DC)

        包含大盘主力资金流向、超大单、大单、中单、小单的流入流出情况。
        数据从Tushare获取,每日盘后更新。

        优先级: P1
        调用频率: 每日盘后
        积分消耗: 120(试用) / 6000(正式)
        """
        if not trade_date and not start_date:
            trade_date = trading_calendar_service.get_latest_data_date_sync()
            logger.info(f"大盘资金流向: 使用日期 {trade_date}")

        return await self._sync_data_template(
            data_type=DataType.MONEYFLOW_MKT_DC,
            fetch_method=lambda p, **kw: p.get_moneyflow_mkt_dc(**kw),
            insert_method=self._insert_moneyflow_mkt_dc,
            validator_method=None,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_moneyflow_ind_dc(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步板块资金流向数据(东财概念及行业板块资金流向 DC)

        包含行业、概念、地域板块的资金流向数据,包括主力资金、超大单、大单、中单、小单的流入流出情况。
        数据从Tushare获取,每天盘后更新。

        优先级: P2
        调用频率: 每日盘后
        积分消耗: 6000
        单次最大: 5000条数据
        """
        if not trade_date and not start_date:
            trade_date = trading_calendar_service.get_latest_data_date_sync()
            logger.info(f"板块资金流向: 使用日期 {trade_date}")

        return await self._sync_data_template(
            data_type=DataType.MONEYFLOW_IND_DC,
            fetch_method=lambda p, **kw: p.get_moneyflow_ind_dc(**kw),
            insert_method=self._insert_moneyflow_ind_dc,
            validator_method=None,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            content_type=content_type
        )

    async def sync_moneyflow_stock_dc(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步个股资金流向数据(东方财富DC)

        包含个股主力资金、超大单、大单、中单、小单的流入流出情况。
        数据从Tushare获取,每日盘后更新。数据开始于20230911。

        优先级: P2
        调用频率: 每日盘后
        积分消耗: 5000
        单次最大: 6000条数据
        """
        if not trade_date and not start_date:
            trade_date = trading_calendar_service.get_latest_data_date_sync()
            logger.info(f"个股资金流向: 使用日期 {trade_date}")

        return await self._sync_data_template(
            data_type=DataType.MONEYFLOW_STOCK_DC,
            fetch_method=lambda p, **kw: p.get_moneyflow_stock_dc(**kw),
            insert_method=self._insert_moneyflow_stock_dc,
            validator_method=None,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    # ========== 辅助方法 ==========

    async def _get_active_stocks(self, trade_date: str) -> List[str]:
        """
        获取活跃股票列表

        根据成交额排序,返回指定日期的前100只活跃股票。

        Args:
            trade_date: 交易日期(YYYYMMDD格式)

        Returns:
            股票代码列表(TS格式,如000001.SZ)
        """
        async with get_async_db() as db:
            date_obj = self._convert_date_string_to_date(trade_date)

            query = text("""
                SELECT code
                FROM stock_daily
                WHERE date = :date
                  AND code NOT LIKE 'TEST%'
                  AND amount > 0
                ORDER BY amount DESC
                LIMIT 100
            """)

            result = await db.execute(query, {"date": date_obj})
            rows = result.fetchall()
            return [row[0] for row in rows]

    # ========== 私有数据插入方法 ==========

    async def _insert_daily_basic(self, df: pd.DataFrame):
        """插入每日指标数据"""
        await self._upsert_records(
            df=df,
            table_name="daily_basic",
            conflict_columns=["ts_code", "trade_date"],
            update_columns=[
                "close", "turnover_rate", "turnover_rate_f", "volume_ratio",
                "pe", "pe_ttm", "pb", "ps", "ps_ttm", "dv_ratio", "dv_ttm",
                "total_share", "float_share", "free_share", "total_mv", "circ_mv"
            ],
            date_fields=["trade_date"]
        )

    async def _insert_moneyflow(self, df: pd.DataFrame):
        """插入资金流向数据(Tushare标准接口)"""
        # moneyflow表的trade_date使用VARCHAR(8)存储YYYYMMDD格式
        await self._upsert_records(
            df=df,
            table_name="moneyflow",
            conflict_columns=["ts_code", "trade_date"],
            update_columns=[
                "buy_sm_vol", "buy_sm_amount", "sell_sm_vol", "sell_sm_amount",
                "buy_md_vol", "buy_md_amount", "sell_md_vol", "sell_md_amount",
                "buy_lg_vol", "buy_lg_amount", "sell_lg_vol", "sell_lg_amount",
                "buy_elg_vol", "buy_elg_amount", "sell_elg_vol", "sell_elg_amount",
                "net_mf_vol", "net_mf_amount"
            ],
            keep_date_as_string=True  # 保持字符串格式
        )

    async def _insert_moneyflow_hsgt(self, df: pd.DataFrame):
        """插入沪深港通资金流向数据"""
        await self._upsert_records(
            df=df,
            table_name="moneyflow_hsgt",
            conflict_columns=["trade_date"],
            update_columns=[
                "ggt_ss", "ggt_sz", "hgt", "sgt", "north_money", "south_money"
            ],
            keep_date_as_string=True
        )

    async def _insert_moneyflow_mkt_dc(self, df: pd.DataFrame):
        """插入大盘资金流向数据"""
        await self._upsert_records(
            df=df,
            table_name="moneyflow_mkt_dc",
            conflict_columns=["trade_date"],
            update_columns=[
                "close_sh", "pct_change_sh", "close_sz", "pct_change_sz",
                "net_amount", "net_amount_rate",
                "buy_elg_amount", "buy_elg_amount_rate",
                "buy_lg_amount", "buy_lg_amount_rate",
                "buy_md_amount", "buy_md_amount_rate",
                "buy_sm_amount", "buy_sm_amount_rate"
            ],
            keep_date_as_string=True
        )

    async def _insert_moneyflow_ind_dc(self, df: pd.DataFrame):
        """插入板块资金流向数据"""
        await self._upsert_records(
            df=df,
            table_name="moneyflow_ind_dc",
            conflict_columns=["trade_date", "ts_code"],
            update_columns=[
                "content_type", "name", "pct_change", "close",
                "net_amount", "net_amount_rate",
                "buy_elg_amount", "buy_elg_amount_rate",
                "buy_lg_amount", "buy_lg_amount_rate",
                "buy_md_amount", "buy_md_amount_rate",
                "buy_sm_amount", "buy_sm_amount_rate",
                "buy_sm_amount_stock", "rank"
            ],
            keep_date_as_string=True
        )

    async def _insert_moneyflow_stock_dc(self, df: pd.DataFrame):
        """插入个股资金流向数据"""
        await self._upsert_records(
            df=df,
            table_name="moneyflow_stock_dc",
            conflict_columns=["trade_date", "ts_code"],
            update_columns=[
                "name", "pct_change", "close",
                "net_amount", "net_amount_rate",
                "buy_elg_amount", "buy_elg_amount_rate",
                "buy_lg_amount", "buy_lg_amount_rate",
                "buy_md_amount", "buy_md_amount_rate",
                "buy_sm_amount", "buy_sm_amount_rate"
            ],
            keep_date_as_string=True
        )

    async def _insert_margin_detail(self, df: pd.DataFrame):
        """插入融资融券数据"""
        await self._upsert_records(
            df=df,
            table_name="margin_detail",
            conflict_columns=["ts_code", "trade_date"],
            update_columns=[
                "rzye", "rqye", "rzmre", "rqyl", "rzche", "rqchl", "rqmcl", "rzrqye"
            ],
            date_fields=["trade_date"]
        )

    async def _insert_stk_limit(self, df: pd.DataFrame):
        """插入涨跌停价格数据"""
        await self._upsert_records(
            df=df,
            table_name="stk_limit",
            conflict_columns=["ts_code", "trade_date"],
            update_columns=["pre_close", "up_limit", "down_limit"],
            date_fields=["trade_date"]
        )

    async def _insert_adj_factor(self, df: pd.DataFrame):
        """插入复权因子数据"""
        await self._upsert_records(
            df=df,
            table_name="adj_factor",
            conflict_columns=["ts_code", "trade_date"],
            update_columns=["adj_factor"],
            date_fields=["trade_date"]
        )

    async def _insert_block_trade(self, df: pd.DataFrame):
        """插入大宗交易数据"""
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # 转换日期字符串为日期对象
                if 'trade_date' in record and isinstance(record['trade_date'], str):
                    record['trade_date'] = self._convert_date_string_to_date(record['trade_date'])

                # 大宗交易数据不使用UPSERT,直接插入
                query = text("""
                    INSERT INTO block_trade (
                        ts_code, trade_date, price, vol, amount, buyer, seller
                    ) VALUES (
                        :ts_code, :trade_date, :price, :vol, :amount, :buyer, :seller
                    )
                """)

                await db.execute(query, record)

            await db.commit()

    async def _insert_suspend(self, df: pd.DataFrame):
        """插入停复牌信息"""
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # 转换所有日期字符串为日期对象
                date_fields = ['suspend_date', 'resume_date', 'ann_date']
                for field in date_fields:
                    if field in record and isinstance(record[field], str) and record[field]:
                        record[field] = self._convert_date_string_to_date(record[field])

                # 停复牌信息不使用UPSERT,直接插入
                query = text("""
                    INSERT INTO suspend_info (
                        ts_code, suspend_date, resume_date, ann_date, suspend_reason, reason_type
                    ) VALUES (
                        :ts_code, :suspend_date, :resume_date, :ann_date, :suspend_reason, :reason_type
                    )
                """)

                await db.execute(query, record)

            await db.commit()


# 创建全局单例
extended_sync_service = ExtendedDataSyncService()
