"""
扩展数据同步服务
用于同步Tushare扩展数据（资金流向、每日指标、北向资金等）
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
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

    async def sync_daily_basic(self,
                               trade_date: Optional[str] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        同步每日指标数据
        优先级：P0
        调用频率：每日17:00
        积分消耗：120
        """
        task_id = self._generate_task_id("daily_basic")

        try:
            logger.info(f"开始同步每日指标数据: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 获取数据
            provider = self._get_provider()

            # 如果没有指定日期，默认同步最近交易日
            if not trade_date and not start_date:
                # 使用同步版本（兼容Celery任务）
                calculated_date = trading_calendar_service.get_latest_data_date_sync()
                logger.info(f"计算的最近交易日期: {calculated_date}")

                # 根据数据类型判断是否应该使用日期
                trade_date = DataAvailabilityConfig.should_use_date("daily_basic", calculated_date)
                logger.info(DataAvailabilityConfig.get_description("daily_basic", calculated_date))

            df = provider.get_daily_basic(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            # 数据验证和插入
            if df is not None and len(df) > 0:
                # 验证数据质量
                is_valid, errors, warnings = self.validator.validate_daily_basic(df)

                if errors:
                    logger.warning(f"每日指标数据验证发现错误: {errors}")
                    # 尝试修复数据
                    df = self.validator.fix_data(df, 'daily_basic')
                    # 重新验证
                    is_valid, errors, warnings = self.validator.validate_daily_basic(df)

                    if errors:
                        logger.error(f"数据修复后仍有错误: {errors}")

                if warnings:
                    logger.info(f"每日指标数据验证警告: {warnings}")

                await self._insert_daily_basic(df)

                logger.info(f"成功同步每日指标数据 {len(df)} 条")
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": len(df),
                    "validation_errors": len(errors) if errors else 0,
                    "validation_warnings": len(warnings) if warnings else 0,
                    "message": f"成功同步 {len(df)} 条每日指标数据"
                }
            else:
                logger.warning("每日指标数据为空")
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

        except Exception as e:
            logger.error(f"同步每日指标失败: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    async def sync_moneyflow(self,
                             trade_date: Optional[str] = None,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             stock_list: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        同步资金流向数据
        优先级：P0
        调用频率：每日17:30
        积分消耗：2000（高消耗，需要控制调用频率）
        """
        task_id = self._generate_task_id("moneyflow")

        try:
            logger.info(f"开始同步资金流向数据: trade_date={trade_date}")

            provider = self._get_provider()

            # 如果没有指定日期，默认同步最近交易日
            if not trade_date and not start_date:
                # 使用同步版本（兼容Celery任务）
                calculated_date = trading_calendar_service.get_latest_data_date_sync()
                logger.info(f"计算的最近交易日期: {calculated_date}")

                # 根据数据类型判断是否应该使用日期
                trade_date = DataAvailabilityConfig.should_use_date("moneyflow", calculated_date)
                logger.info(DataAvailabilityConfig.get_description("moneyflow", calculated_date))

            # 如果没有指定股票列表，获取活跃股票
            if not stock_list:
                stock_list = await self._get_active_stocks(trade_date)
                logger.info(f"获取到 {len(stock_list)} 只活跃股票")

            total_records = 0
            failed_stocks = []

            # 分批获取，避免单次请求数据量过大
            for i, ts_code in enumerate(stock_list):
                try:
                    df = provider.get_moneyflow(
                        ts_code=ts_code,
                        trade_date=trade_date,
                        start_date=start_date,
                        end_date=end_date
                    )

                    if df is not None and len(df) > 0:
                        # 验证数据质量
                        is_valid, errors, warnings = self.validator.validate_moneyflow(df)

                        if errors:
                            logger.warning(f"资金流向数据验证发现错误 [{ts_code}]: {errors}")
                            # 尝试修复数据
                            df = self.validator.fix_data(df, 'moneyflow')
                            # 重新验证
                            is_valid, errors, warnings = self.validator.validate_moneyflow(df)

                        if warnings:
                            logger.debug(f"资金流向数据验证警告 [{ts_code}]: {warnings}")

                        await self._insert_moneyflow(df)
                        total_records += len(df)

                    # 控制请求频率，避免触发限流
                    if i < len(stock_list) - 1:
                        await asyncio.sleep(0.5)

                except Exception as e:
                    logger.warning(f"获取 {ts_code} 资金流向失败: {e}")
                    failed_stocks.append(ts_code)
                    continue

            message = f"成功同步 {total_records} 条资金流向数据"
            if failed_stocks:
                message += f"，{len(failed_stocks)} 只股票失败"

            logger.info(message)
            return {
                "task_id": task_id,
                "status": "success",
                "records": total_records,
                "failed_stocks": failed_stocks,
                "message": message
            }

        except Exception as e:
            logger.error(f"同步资金流向失败: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "records": 0,
                "error": str(e)
            }


    async def sync_margin_detail(self,
                                 trade_date: Optional[str] = None,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        同步融资融券数据
        优先级：P2
        调用频率：每日18:30
        积分消耗：300
        """
        task_id = self._generate_task_id("margin_detail")

        try:
            logger.info(f"开始同步融资融券数据: trade_date={trade_date}")

            provider = self._get_provider()

            if not trade_date and not start_date:
                # 使用同步版本（兼容Celery任务）
                calculated_date = trading_calendar_service.get_latest_data_date_sync()
                logger.info(f"计算的最近交易日期: {calculated_date}")

                # 根据数据类型判断是否应该使用日期
                trade_date = DataAvailabilityConfig.should_use_date("margin_detail", calculated_date)
                logger.info(DataAvailabilityConfig.get_description("margin_detail", calculated_date))

            df = provider.get_margin_detail(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is not None and len(df) > 0:
                # 验证数据质量
                is_valid, errors, warnings = self.validator.validate_margin_detail(df)

                if errors:
                    logger.warning(f"融资融券数据验证发现错误: {errors}")
                    # 尝试修复数据
                    df = self.validator.fix_data(df, 'margin_detail')
                    # 重新验证
                    is_valid, errors, warnings = self.validator.validate_margin_detail(df)

                if warnings:
                    logger.debug(f"融资融券数据验证警告: {warnings}")

                await self._insert_margin_detail(df)

                logger.info(f"成功同步融资融券数据 {len(df)} 条")
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": len(df),
                    "message": f"成功同步 {len(df)} 条融资融券数据"
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

        except Exception as e:
            logger.error(f"同步融资融券失败: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    async def sync_stk_limit(self,
                             trade_date: Optional[str] = None,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        同步涨跌停价格数据
        优先级：P1
        调用频率：每日9:00
        积分消耗：120
        """
        task_id = self._generate_task_id("stk_limit")

        try:
            logger.info(f"开始同步涨跌停价格数据: trade_date={trade_date}")

            provider = self._get_provider()

            if not trade_date and not start_date:
                # 使用同步版本（兼容Celery任务）
                calculated_date = trading_calendar_service.get_latest_data_date_sync()
                logger.info(f"计算的最近交易日期: {calculated_date}")

                # 根据数据类型判断是否应该使用日期
                trade_date = DataAvailabilityConfig.should_use_date("stk_limit", calculated_date)
                logger.info(DataAvailabilityConfig.get_description("stk_limit", calculated_date))

            df = provider.get_stk_limit(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is not None and len(df) > 0:
                # 验证数据质量
                is_valid, errors, warnings = self.validator.validate_stk_limit(df)

                if errors:
                    logger.warning(f"涨跌停价格数据验证发现错误: {errors}")
                    # 尝试修复数据
                    df = self.validator.fix_data(df, 'stk_limit')
                    # 重新验证
                    is_valid, errors, warnings = self.validator.validate_stk_limit(df)

                if warnings:
                    logger.debug(f"涨跌停价格数据验证警告: {warnings}")

                await self._insert_stk_limit(df)

                logger.info(f"成功同步涨跌停价格数据 {len(df)} 条")
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": len(df),
                    "message": f"成功同步 {len(df)} 条涨跌停价格数据"
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

        except Exception as e:
            logger.error(f"同步涨跌停价格失败: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    async def sync_adj_factor(self,
                              ts_code: Optional[str] = None,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        同步复权因子数据
        优先级：P2
        调用频率：每周一
        积分消耗：120
        """
        task_id = self._generate_task_id("adj_factor")

        try:
            logger.info(f"开始同步复权因子数据: ts_code={ts_code}")

            provider = self._get_provider()

            df = provider.get_adj_factor(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is not None and len(df) > 0:
                await self._insert_adj_factor(df)

                logger.info(f"成功同步复权因子数据 {len(df)} 条")
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": len(df),
                    "message": f"成功同步 {len(df)} 条复权因子数据"
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

        except Exception as e:
            logger.error(f"同步复权因子失败: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    async def sync_block_trade(self,
                               trade_date: Optional[str] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        同步大宗交易数据
        优先级：P3
        调用频率：每日19:00
        积分消耗：300
        """
        task_id = self._generate_task_id("block_trade")

        try:
            logger.info(f"开始同步大宗交易数据: trade_date={trade_date}")

            provider = self._get_provider()

            if not trade_date and not start_date:
                # 使用同步版本（兼容Celery任务）
                calculated_date = trading_calendar_service.get_latest_data_date_sync()
                logger.info(f"计算的最近交易日期: {calculated_date}")

                # 根据数据类型判断是否应该使用日期
                trade_date = DataAvailabilityConfig.should_use_date("block_trade", calculated_date)
                logger.info(DataAvailabilityConfig.get_description("block_trade", calculated_date))

            df = provider.get_block_trade(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is not None and len(df) > 0:
                await self._insert_block_trade(df)

                logger.info(f"成功同步大宗交易数据 {len(df)} 条")
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": len(df),
                    "message": f"成功同步 {len(df)} 条大宗交易数据"
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

        except Exception as e:
            logger.error(f"同步大宗交易失败: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    async def sync_suspend(self,
                           ts_code: Optional[str] = None,
                           suspend_date: Optional[str] = None,
                           resume_date: Optional[str] = None) -> Dict[str, Any]:
        """
        同步停复牌信息
        优先级：P3
        调用频率：每日
        积分消耗：120
        """
        task_id = self._generate_task_id("suspend")

        try:
            logger.info(f"开始同步停复牌信息: ts_code={ts_code}")

            provider = self._get_provider()

            df = provider.get_suspend(
                ts_code=ts_code,
                suspend_date=suspend_date,
                resume_date=resume_date
            )

            if df is not None and len(df) > 0:
                await self._insert_suspend(df)

                logger.info(f"成功同步停复牌信息 {len(df)} 条")
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": len(df),
                    "message": f"成功同步 {len(df)} 条停复牌信息"
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

        except Exception as e:
            logger.error(f"同步停复牌信息失败: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    async def sync_moneyflow_hsgt(self,
                                   trade_date: Optional[str] = None,
                                   start_date: Optional[str] = None,
                                   end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        同步沪深港通资金流向数据

        包含北向资金（沪股通+深股通）和南向资金（港股通上海+港股通深圳）的每日资金流向。
        数据从Tushare获取，支持2026年及以后的最新数据。

        Args:
            trade_date: 单个交易日期 (YYYYMMDD格式)
            start_date: 开始日期 (YYYYMMDD格式)
            end_date: 结束日期 (YYYYMMDD格式)

        Returns:
            同步结果，包含成功/失败状态和记录数

        Note:
            - 优先级：P0
            - 调用频率：每日收盘后
            - 积分消耗：2000
        """
        task_id = self._generate_task_id("moneyflow_hsgt")

        try:
            logger.info(f"开始同步沪深港通资金流向: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            provider = self._get_provider()

            # 如果没有指定日期，默认同步最近交易日
            if not trade_date and not start_date:
                # 使用同步版本（兼容Celery任务）
                calculated_date = trading_calendar_service.get_latest_data_date_sync()
                logger.info(f"计算的最近交易日期: {calculated_date}")

                # moneyflow_hsgt支持当前日期
                trade_date = calculated_date
                logger.info(f"沪深港通资金流向: 使用日期 {trade_date}")

            # 获取数据
            df = provider.get_moneyflow_hsgt(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is not None and len(df) > 0:
                await self._insert_moneyflow_hsgt(df)

                logger.info(f"成功同步沪深港通资金流向数据 {len(df)} 条")
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": len(df),
                    "message": f"成功同步 {len(df)} 条资金流向数据"
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

        except Exception as e:
            logger.error(f"同步沪深港通资金流向失败: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    async def sync_moneyflow_mkt_dc(self,
                                     trade_date: Optional[str] = None,
                                     start_date: Optional[str] = None,
                                     end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        同步大盘资金流向数据（东方财富DC）

        包含大盘主力资金流向、超大单、大单、中单、小单的流入流出情况。
        数据从Tushare获取，每日盘后更新。

        Args:
            trade_date: 单个交易日期 (YYYYMMDD格式)
            start_date: 开始日期 (YYYYMMDD格式)
            end_date: 结束日期 (YYYYMMDD格式)

        Returns:
            同步结果，包含成功/失败状态和记录数

        Note:
            - 优先级：P1
            - 调用频率：每日盘后
            - 积分消耗：120（试用）/ 6000（正式）
        """
        task_id = self._generate_task_id("moneyflow_mkt_dc")

        try:
            logger.info(f"开始同步大盘资金流向: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            provider = self._get_provider()

            # 如果没有指定日期，默认同步最近交易日
            if not trade_date and not start_date:
                # 使用同步版本（兼容Celery任务）
                calculated_date = trading_calendar_service.get_latest_data_date_sync()
                logger.info(f"计算的最近交易日期: {calculated_date}")

                # 大盘资金流向支持当前日期
                trade_date = calculated_date
                logger.info(f"大盘资金流向: 使用日期 {trade_date}")

            # 获取数据
            df = provider.get_moneyflow_mkt_dc(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is not None and len(df) > 0:
                await self._insert_moneyflow_mkt_dc(df)

                logger.info(f"成功同步大盘资金流向数据 {len(df)} 条")
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": len(df),
                    "message": f"成功同步 {len(df)} 条大盘资金流向数据"
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

        except Exception as e:
            logger.error(f"同步大盘资金流向失败: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    async def sync_moneyflow_ind_dc(self,
                                     ts_code: Optional[str] = None,
                                     trade_date: Optional[str] = None,
                                     start_date: Optional[str] = None,
                                     end_date: Optional[str] = None,
                                     content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        同步板块资金流向数据（东财概念及行业板块资金流向 DC）

        包含行业、概念、地域板块的资金流向数据，包括主力资金、超大单、大单、中单、小单的流入流出情况。
        数据从Tushare获取，每天盘后更新。

        Args:
            ts_code: 代码
            trade_date: 单个交易日期 (YYYYMMDD格式)
            start_date: 开始日期 (YYYYMMDD格式)
            end_date: 结束日期 (YYYYMMDD格式)
            content_type: 资金类型(行业、概念、地域)

        Returns:
            同步结果，包含成功/失败状态和记录数

        Note:
            - 优先级：P2
            - 调用频率：每日盘后
            - 积分消耗：6000
            - 单次最大可调取5000条数据
        """
        task_id = self._generate_task_id("moneyflow_ind_dc")

        try:
            logger.info(f"开始同步板块资金流向: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}, content_type={content_type}")

            provider = self._get_provider()

            # 如果没有指定日期，默认同步最近交易日
            if not trade_date and not start_date:
                # 使用同步版本（兼容Celery任务）
                calculated_date = trading_calendar_service.get_latest_data_date_sync()
                logger.info(f"计算的最近交易日期: {calculated_date}")

                # 板块资金流向支持当前日期
                trade_date = calculated_date
                logger.info(f"板块资金流向: 使用日期 {trade_date}")

            # 获取数据
            df = provider.get_moneyflow_ind_dc(
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                content_type=content_type
            )

            if df is not None and len(df) > 0:
                await self._insert_moneyflow_ind_dc(df)

                logger.info(f"成功同步板块资金流向数据 {len(df)} 条")
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": len(df),
                    "message": f"成功同步 {len(df)} 条板块资金流向数据"
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

        except Exception as e:
            logger.error(f"同步板块资金流向失败: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    async def sync_moneyflow_stock_dc(self,
                                      ts_code: Optional[str] = None,
                                      trade_date: Optional[str] = None,
                                      start_date: Optional[str] = None,
                                      end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        同步个股资金流向数据（东方财富DC）

        包含个股主力资金、超大单、大单、中单、小单的流入流出情况。
        数据从Tushare获取，每日盘后更新。数据开始于20230911。

        Args:
            ts_code: 股票代码
            trade_date: 单个交易日期 (YYYYMMDD格式)
            start_date: 开始日期 (YYYYMMDD格式)
            end_date: 结束日期 (YYYYMMDD格式)

        Returns:
            同步结果，包含成功/失败状态和记录数

        Note:
            - 优先级：P2
            - 调用频率：每日盘后
            - 积分消耗：5000
            - 单次最大可调取6000条数据
        """
        task_id = self._generate_task_id("moneyflow_stock_dc")

        try:
            logger.info(f"开始同步个股资金流向: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            provider = self._get_provider()

            # 如果没有指定日期，默认同步最近交易日
            if not trade_date and not start_date:
                # 使用同步版本（兼容Celery任务）
                calculated_date = trading_calendar_service.get_latest_data_date_sync()
                logger.info(f"计算的最近交易日期: {calculated_date}")

                # 个股资金流向支持当前日期
                trade_date = calculated_date
                logger.info(f"个股资金流向: 使用日期 {trade_date}")

            # 获取数据
            df = provider.get_moneyflow_stock_dc(
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is not None and len(df) > 0:
                await self._insert_moneyflow_stock_dc(df)

                logger.info(f"成功同步个股资金流向数据 {len(df)} 条")
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": len(df),
                    "message": f"成功同步 {len(df)} 条个股资金流向数据"
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

        except Exception as e:
            logger.error(f"同步个股资金流向失败: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    # ========== 辅助方法 ==========

    async def _get_active_stocks(self, trade_date: str) -> List[str]:
        """
        获取活跃股票列表（内部方法）
        根据成交额排名获取前100只活跃股票
        """
        async with get_async_db() as db:
            query = text("""
                SELECT ts_code
                FROM stock_daily
                WHERE trade_date = :trade_date
                ORDER BY amount DESC
                LIMIT 100
            """)

            result = await db.execute(query, {"trade_date": trade_date})
            rows = result.fetchall()
            return [row[0] for row in rows]

    async def _insert_daily_basic(self, df: pd.DataFrame):
        """插入每日指标数据"""
        async with get_async_db() as db:
            # 转换DataFrame为records
            records = df.to_dict('records')

            for record in records:
                # 转换日期字符串为日期对象
                if 'trade_date' in record and isinstance(record['trade_date'], str):
                    from datetime import datetime
                    record['trade_date'] = datetime.strptime(record['trade_date'], '%Y%m%d').date()

                # 使用UPSERT避免重复数据
                query = text("""
                    INSERT INTO daily_basic (
                        ts_code, trade_date, close, turnover_rate, turnover_rate_f,
                        volume_ratio, pe, pe_ttm, pb, ps, ps_ttm, dv_ratio, dv_ttm,
                        total_share, float_share, free_share, total_mv, circ_mv
                    ) VALUES (
                        :ts_code, :trade_date, :close, :turnover_rate, :turnover_rate_f,
                        :volume_ratio, :pe, :pe_ttm, :pb, :ps, :ps_ttm, :dv_ratio, :dv_ttm,
                        :total_share, :float_share, :free_share, :total_mv, :circ_mv
                    )
                    ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                        close = EXCLUDED.close,
                        turnover_rate = EXCLUDED.turnover_rate,
                        turnover_rate_f = EXCLUDED.turnover_rate_f,
                        volume_ratio = EXCLUDED.volume_ratio,
                        pe = EXCLUDED.pe,
                        pe_ttm = EXCLUDED.pe_ttm,
                        pb = EXCLUDED.pb,
                        ps = EXCLUDED.ps,
                        ps_ttm = EXCLUDED.ps_ttm,
                        dv_ratio = EXCLUDED.dv_ratio,
                        dv_ttm = EXCLUDED.dv_ttm,
                        total_share = EXCLUDED.total_share,
                        float_share = EXCLUDED.float_share,
                        free_share = EXCLUDED.free_share,
                        total_mv = EXCLUDED.total_mv,
                        circ_mv = EXCLUDED.circ_mv,
                        updated_at = CURRENT_TIMESTAMP
                """)

                await db.execute(query, record)

            await db.commit()

    async def _insert_moneyflow(self, df: pd.DataFrame):
        """插入资金流向数据"""
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # 转换日期字符串为日期对象
                if 'trade_date' in record and isinstance(record['trade_date'], str):
                    from datetime import datetime
                    record['trade_date'] = datetime.strptime(record['trade_date'], '%Y%m%d').date()

                query = text("""
                    INSERT INTO moneyflow (
                        ts_code, trade_date, buy_sm_vol, buy_sm_amount,
                        sell_sm_vol, sell_sm_amount, buy_md_vol, buy_md_amount,
                        sell_md_vol, sell_md_amount, buy_lg_vol, buy_lg_amount,
                        sell_lg_vol, sell_lg_amount, buy_elg_vol, buy_elg_amount,
                        sell_elg_vol, sell_elg_amount, net_mf_vol, net_mf_amount, trade_count
                    ) VALUES (
                        :ts_code, :trade_date, :buy_sm_vol, :buy_sm_amount,
                        :sell_sm_vol, :sell_sm_amount, :buy_md_vol, :buy_md_amount,
                        :sell_md_vol, :sell_md_amount, :buy_lg_vol, :buy_lg_amount,
                        :sell_lg_vol, :sell_lg_amount, :buy_elg_vol, :buy_elg_amount,
                        :sell_elg_vol, :sell_elg_amount, :net_mf_vol, :net_mf_amount, :trade_count
                    )
                    ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                        buy_sm_vol = EXCLUDED.buy_sm_vol,
                        buy_sm_amount = EXCLUDED.buy_sm_amount,
                        sell_sm_vol = EXCLUDED.sell_sm_vol,
                        sell_sm_amount = EXCLUDED.sell_sm_amount,
                        buy_md_vol = EXCLUDED.buy_md_vol,
                        buy_md_amount = EXCLUDED.buy_md_amount,
                        sell_md_vol = EXCLUDED.sell_md_vol,
                        sell_md_amount = EXCLUDED.sell_md_amount,
                        buy_lg_vol = EXCLUDED.buy_lg_vol,
                        buy_lg_amount = EXCLUDED.buy_lg_amount,
                        sell_lg_vol = EXCLUDED.sell_lg_vol,
                        sell_lg_amount = EXCLUDED.sell_lg_amount,
                        buy_elg_vol = EXCLUDED.buy_elg_vol,
                        buy_elg_amount = EXCLUDED.buy_elg_amount,
                        sell_elg_vol = EXCLUDED.sell_elg_vol,
                        sell_elg_amount = EXCLUDED.sell_elg_amount,
                        net_mf_vol = EXCLUDED.net_mf_vol,
                        net_mf_amount = EXCLUDED.net_mf_amount,
                        trade_count = EXCLUDED.trade_count
                """)

                await db.execute(query, record)

            await db.commit()


    async def _insert_moneyflow_hsgt(self, df: pd.DataFrame):
        """
        插入沪深港通资金流向数据到数据库

        使用UPSERT策略，如果数据已存在则更新，避免重复数据。

        Args:
            df: 包含资金流向数据的DataFrame
        """
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # trade_date在这个接口中已经是字符串格式(YYYYMMDD)，直接使用
                query = text("""
                    INSERT INTO moneyflow_hsgt (
                        trade_date, ggt_ss, ggt_sz, hgt, sgt, north_money, south_money
                    ) VALUES (
                        :trade_date, :ggt_ss, :ggt_sz, :hgt, :sgt, :north_money, :south_money
                    )
                    ON CONFLICT (trade_date) DO UPDATE SET
                        ggt_ss = EXCLUDED.ggt_ss,
                        ggt_sz = EXCLUDED.ggt_sz,
                        hgt = EXCLUDED.hgt,
                        sgt = EXCLUDED.sgt,
                        north_money = EXCLUDED.north_money,
                        south_money = EXCLUDED.south_money,
                        updated_at = CURRENT_TIMESTAMP
                """)

                await db.execute(query, record)

            await db.commit()

    async def _insert_moneyflow_mkt_dc(self, df: pd.DataFrame):
        """
        插入大盘资金流向数据到数据库

        使用UPSERT策略，如果数据已存在则更新，避免重复数据。

        Args:
            df: 包含大盘资金流向数据的DataFrame
        """
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # trade_date在这个接口中已经是字符串格式(YYYYMMDD)，直接使用
                query = text("""
                    INSERT INTO moneyflow_mkt_dc (
                        trade_date, close_sh, pct_change_sh, close_sz, pct_change_sz,
                        net_amount, net_amount_rate,
                        buy_elg_amount, buy_elg_amount_rate,
                        buy_lg_amount, buy_lg_amount_rate,
                        buy_md_amount, buy_md_amount_rate,
                        buy_sm_amount, buy_sm_amount_rate
                    ) VALUES (
                        :trade_date, :close_sh, :pct_change_sh, :close_sz, :pct_change_sz,
                        :net_amount, :net_amount_rate,
                        :buy_elg_amount, :buy_elg_amount_rate,
                        :buy_lg_amount, :buy_lg_amount_rate,
                        :buy_md_amount, :buy_md_amount_rate,
                        :buy_sm_amount, :buy_sm_amount_rate
                    )
                    ON CONFLICT (trade_date) DO UPDATE SET
                        close_sh = EXCLUDED.close_sh,
                        pct_change_sh = EXCLUDED.pct_change_sh,
                        close_sz = EXCLUDED.close_sz,
                        pct_change_sz = EXCLUDED.pct_change_sz,
                        net_amount = EXCLUDED.net_amount,
                        net_amount_rate = EXCLUDED.net_amount_rate,
                        buy_elg_amount = EXCLUDED.buy_elg_amount,
                        buy_elg_amount_rate = EXCLUDED.buy_elg_amount_rate,
                        buy_lg_amount = EXCLUDED.buy_lg_amount,
                        buy_lg_amount_rate = EXCLUDED.buy_lg_amount_rate,
                        buy_md_amount = EXCLUDED.buy_md_amount,
                        buy_md_amount_rate = EXCLUDED.buy_md_amount_rate,
                        buy_sm_amount = EXCLUDED.buy_sm_amount,
                        buy_sm_amount_rate = EXCLUDED.buy_sm_amount_rate,
                        updated_at = CURRENT_TIMESTAMP
                """)

                await db.execute(query, record)

            await db.commit()

    async def _insert_moneyflow_ind_dc(self, df: pd.DataFrame):
        """
        插入板块资金流向数据到数据库

        使用UPSERT策略，如果数据已存在则更新，避免重复数据。

        Args:
            df: 包含板块资金流向数据的DataFrame
        """
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # trade_date在这个接口中已经是字符串格式(YYYYMMDD)，直接使用
                query = text("""
                    INSERT INTO moneyflow_ind_dc (
                        trade_date, content_type, ts_code, name, pct_change, close,
                        net_amount, net_amount_rate,
                        buy_elg_amount, buy_elg_amount_rate,
                        buy_lg_amount, buy_lg_amount_rate,
                        buy_md_amount, buy_md_amount_rate,
                        buy_sm_amount, buy_sm_amount_rate,
                        buy_sm_amount_stock, rank
                    ) VALUES (
                        :trade_date, :content_type, :ts_code, :name, :pct_change, :close,
                        :net_amount, :net_amount_rate,
                        :buy_elg_amount, :buy_elg_amount_rate,
                        :buy_lg_amount, :buy_lg_amount_rate,
                        :buy_md_amount, :buy_md_amount_rate,
                        :buy_sm_amount, :buy_sm_amount_rate,
                        :buy_sm_amount_stock, :rank
                    )
                    ON CONFLICT (trade_date, ts_code) DO UPDATE SET
                        content_type = EXCLUDED.content_type,
                        name = EXCLUDED.name,
                        pct_change = EXCLUDED.pct_change,
                        close = EXCLUDED.close,
                        net_amount = EXCLUDED.net_amount,
                        net_amount_rate = EXCLUDED.net_amount_rate,
                        buy_elg_amount = EXCLUDED.buy_elg_amount,
                        buy_elg_amount_rate = EXCLUDED.buy_elg_amount_rate,
                        buy_lg_amount = EXCLUDED.buy_lg_amount,
                        buy_lg_amount_rate = EXCLUDED.buy_lg_amount_rate,
                        buy_md_amount = EXCLUDED.buy_md_amount,
                        buy_md_amount_rate = EXCLUDED.buy_md_amount_rate,
                        buy_sm_amount = EXCLUDED.buy_sm_amount,
                        buy_sm_amount_rate = EXCLUDED.buy_sm_amount_rate,
                        buy_sm_amount_stock = EXCLUDED.buy_sm_amount_stock,
                        rank = EXCLUDED.rank,
                        updated_at = CURRENT_TIMESTAMP
                """)

                await db.execute(query, record)

            await db.commit()

    async def _insert_moneyflow_stock_dc(self, df: pd.DataFrame):
        """
        插入个股资金流向数据到数据库

        使用UPSERT策略，如果数据已存在则更新，避免重复数据。

        Args:
            df: 包含个股资金流向数据的DataFrame
        """
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # trade_date在这个接口中已经是字符串格式(YYYYMMDD)，直接使用
                query = text("""
                    INSERT INTO moneyflow_stock_dc (
                        trade_date, ts_code, name, pct_change, close,
                        net_amount, net_amount_rate,
                        buy_elg_amount, buy_elg_amount_rate,
                        buy_lg_amount, buy_lg_amount_rate,
                        buy_md_amount, buy_md_amount_rate,
                        buy_sm_amount, buy_sm_amount_rate
                    ) VALUES (
                        :trade_date, :ts_code, :name, :pct_change, :close,
                        :net_amount, :net_amount_rate,
                        :buy_elg_amount, :buy_elg_amount_rate,
                        :buy_lg_amount, :buy_lg_amount_rate,
                        :buy_md_amount, :buy_md_amount_rate,
                        :buy_sm_amount, :buy_sm_amount_rate
                    )
                    ON CONFLICT (trade_date, ts_code) DO UPDATE SET
                        name = EXCLUDED.name,
                        pct_change = EXCLUDED.pct_change,
                        close = EXCLUDED.close,
                        net_amount = EXCLUDED.net_amount,
                        net_amount_rate = EXCLUDED.net_amount_rate,
                        buy_elg_amount = EXCLUDED.buy_elg_amount,
                        buy_elg_amount_rate = EXCLUDED.buy_elg_amount_rate,
                        buy_lg_amount = EXCLUDED.buy_lg_amount,
                        buy_lg_amount_rate = EXCLUDED.buy_lg_amount_rate,
                        buy_md_amount = EXCLUDED.buy_md_amount,
                        buy_md_amount_rate = EXCLUDED.buy_md_amount_rate,
                        buy_sm_amount = EXCLUDED.buy_sm_amount,
                        buy_sm_amount_rate = EXCLUDED.buy_sm_amount_rate,
                        updated_at = CURRENT_TIMESTAMP
                """)

                await db.execute(query, record)

            await db.commit()

    async def _insert_margin_detail(self, df: pd.DataFrame):
        """插入融资融券数据"""
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # 转换日期字符串为日期对象
                if 'trade_date' in record and isinstance(record['trade_date'], str):
                    from datetime import datetime
                    record['trade_date'] = datetime.strptime(record['trade_date'], '%Y%m%d').date()

                query = text("""
                    INSERT INTO margin_detail (
                        ts_code, trade_date, rzye, rqye, rzmre, rqyl, rzche, rqchl, rqmcl, rzrqye
                    ) VALUES (
                        :ts_code, :trade_date, :rzye, :rqye, :rzmre, :rqyl, :rzche, :rqchl, :rqmcl, :rzrqye
                    )
                    ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                        rzye = EXCLUDED.rzye,
                        rqye = EXCLUDED.rqye,
                        rzmre = EXCLUDED.rzmre,
                        rqyl = EXCLUDED.rqyl,
                        rzche = EXCLUDED.rzche,
                        rqchl = EXCLUDED.rqchl,
                        rqmcl = EXCLUDED.rqmcl,
                        rzrqye = EXCLUDED.rzrqye
                """)

                await db.execute(query, record)

            await db.commit()

    async def _insert_stk_limit(self, df: pd.DataFrame):
        """插入涨跌停价格数据"""
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # 转换日期字符串为日期对象
                if 'trade_date' in record and isinstance(record['trade_date'], str):
                    from datetime import datetime
                    record['trade_date'] = datetime.strptime(record['trade_date'], '%Y%m%d').date()

                query = text("""
                    INSERT INTO stk_limit (
                        ts_code, trade_date, pre_close, up_limit, down_limit
                    ) VALUES (
                        :ts_code, :trade_date, :pre_close, :up_limit, :down_limit
                    )
                    ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                        pre_close = EXCLUDED.pre_close,
                        up_limit = EXCLUDED.up_limit,
                        down_limit = EXCLUDED.down_limit
                """)

                await db.execute(query, record)

            await db.commit()

    async def _insert_adj_factor(self, df: pd.DataFrame):
        """插入复权因子数据"""
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # 转换日期字符串为日期对象
                if 'trade_date' in record and isinstance(record['trade_date'], str):
                    from datetime import datetime
                    record['trade_date'] = datetime.strptime(record['trade_date'], '%Y%m%d').date()

                query = text("""
                    INSERT INTO adj_factor (
                        ts_code, trade_date, adj_factor
                    ) VALUES (
                        :ts_code, :trade_date, :adj_factor
                    )
                    ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                        adj_factor = EXCLUDED.adj_factor
                """)

                await db.execute(query, record)

            await db.commit()

    async def _insert_block_trade(self, df: pd.DataFrame):
        """插入大宗交易数据"""
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # 转换日期字符串为日期对象
                if 'trade_date' in record and isinstance(record['trade_date'], str):
                    from datetime import datetime
                    record['trade_date'] = datetime.strptime(record['trade_date'], '%Y%m%d').date()

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
                from datetime import datetime
                date_fields = ['suspend_date', 'resume_date', 'ann_date']
                for field in date_fields:
                    if field in record and isinstance(record[field], str) and record[field]:
                        record[field] = datetime.strptime(record[field], '%Y%m%d').date()

                query = text("""
                    INSERT INTO suspend_info (
                        ts_code, suspend_date, resume_date, ann_date, suspend_reason, reason_type
                    ) VALUES (
                        :ts_code, :suspend_date, :resume_date, :ann_date, :suspend_reason, :reason_type
                    )
                """)

                await db.execute(query, record)

            await db.commit()

    def _generate_task_id(self, task_type: str) -> str:
        """生成任务ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{task_type}_{timestamp}"