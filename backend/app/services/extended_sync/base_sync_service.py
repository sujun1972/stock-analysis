"""
扩展数据同步 - 基础同步服务

提供模板方法模式的基础类，所有同步服务继承此类。
"""

from typing import Optional, Dict, Any, Callable, Tuple
from datetime import datetime
import pandas as pd
from loguru import logger

from app.core.config import settings
from core.src.providers import DataProviderFactory
from core.src.data.validators.extended_validator import ExtendedDataValidator
from app.services.trading_calendar_service import trading_calendar_service
from app.services.data_availability_config import DataAvailabilityConfig

from .common import DataType, SyncResult, generate_task_id


class BaseSyncService:
    """
    扩展数据同步基础服务

    使用模板方法模式统一同步流程:
    1. 获取数据
    2. 验证修复
    3. 插入数据库
    """

    def __init__(self):
        self.provider_factory = DataProviderFactory()
        self.validator = ExtendedDataValidator()

    def _get_provider(self):
        """获取Tushare数据提供者"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

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
        task_id = generate_task_id(data_type.value)

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
                error=str(e),
                message=f"同步失败: {str(e)}"
            ).to_dict()
