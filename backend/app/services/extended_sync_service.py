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

from app.core.database import get_db
from app.core.config import settings
from loguru import logger
# from app.services.base_service import BaseService
from core.src.providers import DataProviderFactory
from core.src.data.validators.extended_validator import ExtendedDataValidator


class ExtendedDataSyncService:
    """扩展数据同步服务"""

    def __init__(self):
        self.provider_factory = DataProviderFactory()
        self.validator = ExtendedDataValidator()

    def _get_provider(self):
        """获取Tushare数据提供者"""
        return self.provider_factory.create_provider(
            provider_type='tushare',
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
                trade_date = datetime.now().strftime("%Y%m%d")

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
                trade_date = datetime.now().strftime("%Y%m%d")

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

    async def sync_hk_hold(self,
                           trade_date: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        同步北向资金持股数据
        优先级：P1
        调用频率：每日18:00
        积分消耗：300
        """
        task_id = self._generate_task_id("hk_hold")

        try:
            logger.info(f"开始同步北向资金数据: trade_date={trade_date}")

            provider = self._get_provider()

            if not trade_date and not start_date:
                trade_date = datetime.now().strftime("%Y%m%d")

            total_records = 0

            # 分别获取沪股通和深股通数据
            for exchange in ['SH', 'SZ']:
                try:
                    df = provider.get_hk_hold(
                        trade_date=trade_date,
                        start_date=start_date,
                        end_date=end_date,
                        exchange=exchange
                    )

                    if df is not None and len(df) > 0:
                        # 验证数据质量
                        is_valid, errors, warnings = self.validator.validate_hk_hold(df)

                        if errors:
                            logger.warning(f"北向资金数据验证发现错误 [{exchange}]: {errors}")
                            # 尝试修复数据
                            df = self.validator.fix_data(df, 'hk_hold')
                            # 重新验证
                            is_valid, errors, warnings = self.validator.validate_hk_hold(df)

                        if warnings:
                            logger.debug(f"北向资金数据验证警告 [{exchange}]: {warnings}")

                        await self._insert_hk_hold(df)
                        total_records += len(df)
                        logger.info(f"{exchange} 北向资金同步 {len(df)} 条")

                except Exception as e:
                    logger.warning(f"获取 {exchange} 北向资金失败: {e}")
                    continue

            logger.info(f"成功同步北向资金数据 {total_records} 条")
            return {
                "task_id": task_id,
                "status": "success",
                "records": total_records,
                "message": f"成功同步 {total_records} 条北向资金数据"
            }

        except Exception as e:
            logger.error(f"同步北向资金失败: {str(e)}")
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
                trade_date = datetime.now().strftime("%Y%m%d")

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
                trade_date = datetime.now().strftime("%Y%m%d")

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
                trade_date = datetime.now().strftime("%Y%m%d")

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

    async def _insert_hk_hold(self, df: pd.DataFrame):
        """插入北向资金数据"""
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                query = text("""
                    INSERT INTO hk_hold (
                        code, trade_date, ts_code, name, vol, ratio, exchange
                    ) VALUES (
                        :code, :trade_date, :ts_code, :name, :vol, :ratio, :exchange
                    )
                    ON CONFLICT (code, trade_date, exchange) DO UPDATE SET
                        ts_code = EXCLUDED.ts_code,
                        name = EXCLUDED.name,
                        vol = EXCLUDED.vol,
                        ratio = EXCLUDED.ratio
                """)

                await db.execute(query, record)

            await db.commit()

    async def _insert_margin_detail(self, df: pd.DataFrame):
        """插入融资融券数据"""
        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
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