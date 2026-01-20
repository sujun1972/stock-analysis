"""
数据同步 API
管理数据同步任务
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from loguru import logger
import asyncio

from app.services.config_service import ConfigService
from app.services.data_service import DataDownloadService
from src.providers import DataProviderFactory

router = APIRouter()


class SyncDailyBatchRequest(BaseModel):
    """批量同步日线数据请求"""
    codes: Optional[List[str]] = None
    years: Optional[int] = 5
    max_stocks: Optional[int] = None


class SyncMinuteRequest(BaseModel):
    """同步分时数据请求"""
    period: Optional[str] = "5"
    days: Optional[int] = 5


class SyncRealtimeRequest(BaseModel):
    """同步实时行情请求"""
    codes: Optional[List[str]] = None


class SyncNewStocksRequest(BaseModel):
    """同步新股列表请求"""
    days: Optional[int] = 30


@router.get("/status")
async def get_sync_status():
    """
    获取同步状态（全局，已废弃，建议使用模块化接口）

    Returns:
        当前同步状态信息
    """
    try:
        config_service = ConfigService()
        status = await config_service.get_sync_status()

        return {
            "code": 200,
            "message": "success",
            "data": status
        }
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{module}")
async def get_module_sync_status(module: str):
    """
    获取特定模块的同步状态

    Args:
        module: 模块名称 (stock_list, daily, minute, realtime)

    Returns:
        模块同步状态信息，包含错误信息和重试次数
    """
    try:
        # 验证模块名称
        valid_modules = ['stock_list', 'new_stocks', 'delisted_stocks', 'daily', 'minute', 'realtime']
        if module not in valid_modules:
            raise HTTPException(
                status_code=400,
                detail=f"无效的模块名称，支持: {', '.join(valid_modules)}"
            )

        config_service = ConfigService()
        status = await config_service.get_module_sync_status(module)

        return {
            "code": 200,
            "message": "success",
            "data": status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模块同步状态失败 ({module}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stock-list")
async def sync_stock_list():
    """
    同步股票列表

    从当前配置的数据源获取最新的股票列表

    Returns:
        同步结果，包含获取的股票总数
    """
    config_service = ConfigService()
    task_id = f"stock_list_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    try:
        # 获取数据源配置
        config = await config_service.get_data_source_config()

        # 创建同步任务记录
        await config_service.create_sync_task(
            task_id=task_id,
            module='stock_list',
            data_source=config['data_source']
        )

        # 创建数据提供者（禁用内部重试，由外层控制）
        provider = DataProviderFactory.create_provider(
            source=config['data_source'],
            token=config.get('tushare_token', ''),
            retry_count=1  # 禁用 Provider 内部重试，由外层控制
        )

        # 获取股票列表（带重试逻辑和状态更新）
        logger.info(f"使用 {config['data_source']} 获取股票列表...")

        max_retries = 3
        retry_count = 0
        stock_list = None
        last_error = None

        while retry_count < max_retries:
            try:
                stock_list = await asyncio.to_thread(provider.get_stock_list)
                break  # 成功则退出循环
            except Exception as e:
                retry_count += 1
                last_error = str(e)

                # 更新任务状态，记录重试信息
                error_with_retry = f"重试 {retry_count}/{max_retries}: {last_error}"
                await config_service.update_sync_task(
                    task_id=task_id,
                    error_message=error_with_retry,
                    progress=int((retry_count / max_retries) * 50)  # 重试进度占 50%
                )

                logger.warning(f"获取股票列表失败 (尝试 {retry_count}/{max_retries}): {last_error}")

                if retry_count >= max_retries:
                    raise  # 重试次数用尽，抛出异常

                # 等待后重试（线性增长，更均匀）
                await asyncio.sleep(retry_count * 3)  # 3, 6, 9 秒

        if stock_list is None:
            raise Exception(last_error or "获取股票列表失败")

        # 保存到数据库
        data_service = DataDownloadService()
        count = await asyncio.to_thread(
            data_service.db.save_stock_list,
            stock_list,
            config['data_source']
        )

        # 更新任务状态为完成
        await config_service.update_sync_task(
            task_id=task_id,
            status='completed',
            total_count=count,
            success_count=count,
            failed_count=0,
            progress=100,
            error_message=''  # 清空错误信息
        )

        # 同时更新全局状态（兼容旧接口）
        await config_service.update_sync_status(
            status='completed',
            last_sync_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            progress=100,
            total=count,
            completed=count
        )

        logger.info(f"✓ 股票列表同步完成: {count} 只")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "total": count
            }
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"同步股票列表失败: {error_msg}")

        # 更新任务状态为失败
        await config_service.update_sync_task(
            task_id=task_id,
            status='failed',
            error_message=error_msg
        )

        # 同时更新全局状态（兼容旧接口）
        await config_service.update_sync_status(status='failed')

        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/new-stocks")
async def sync_new_stocks(request: SyncNewStocksRequest):
    """
    同步新股列表

    获取最近 N 天上市的新股信息

    Args:
        request: 新股同步请求
            - days: 最近天数 (默认 30 天)

    Returns:
        同步结果，包含获取的新股总数
    """
    config_service = ConfigService()
    task_id = f"new_stocks_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    try:
        # 获取数据源配置
        config = await config_service.get_data_source_config()

        # 创建同步任务记录
        await config_service.create_sync_task(
            task_id=task_id,
            module='new_stocks',
            data_source=config['data_source']
        )

        # 创建数据提供者（禁用内部重试，由外层控制）
        provider = DataProviderFactory.create_provider(
            source=config['data_source'],
            token=config.get('tushare_token', ''),
            retry_count=1
        )

        # 获取新股列表（带重试逻辑和状态更新）
        logger.info(f"使用 {config['data_source']} 获取最近 {request.days} 天的新股...")

        max_retries = 3
        retry_count = 0
        new_stocks = None
        last_error = None

        while retry_count < max_retries:
            try:
                new_stocks = await asyncio.to_thread(provider.get_new_stocks, request.days)
                break
            except Exception as e:
                retry_count += 1
                last_error = str(e)

                error_with_retry = f"重试 {retry_count}/{max_retries}: {last_error}"
                await config_service.update_sync_task(
                    task_id=task_id,
                    error_message=error_with_retry,
                    progress=int((retry_count / max_retries) * 50)
                )

                logger.warning(f"获取新股列表失败 (尝试 {retry_count}/{max_retries}): {last_error}")

                if retry_count >= max_retries:
                    raise

                await asyncio.sleep(retry_count * 3)

        if new_stocks is None:
            raise Exception(last_error or "获取新股列表失败")

        # 保存到数据库（新股自动添加到股票基础表）
        data_service = DataDownloadService()
        count = await asyncio.to_thread(
            data_service.db.save_stock_list,
            new_stocks,
            config['data_source']
        )

        # 更新任务状态为完成
        await config_service.update_sync_task(
            task_id=task_id,
            status='completed',
            total_count=count,
            success_count=count,
            failed_count=0,
            progress=100,
            error_message=''
        )

        logger.info(f"✓ 新股列表同步完成: {count} 只")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "total": count
            }
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"同步新股列表失败: {error_msg}")

        await config_service.update_sync_task(
            task_id=task_id,
            status='failed',
            error_message=error_msg
        )

        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/delisted-stocks")
async def sync_delisted_stocks():
    """
    同步退市股票列表

    获取已退市股票信息，并更新数据库中相应股票的状态

    Returns:
        同步结果，包含退市股票总数
    """
    config_service = ConfigService()
    task_id = f"delisted_stocks_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    try:
        # 获取数据源配置
        config = await config_service.get_data_source_config()

        # 创建同步任务记录
        await config_service.create_sync_task(
            task_id=task_id,
            module='delisted_stocks',
            data_source=config['data_source']
        )

        # 创建数据提供者（禁用内部重试，由外层控制）
        provider = DataProviderFactory.create_provider(
            source=config['data_source'],
            token=config.get('tushare_token', ''),
            retry_count=1
        )

        # 获取退市股票列表（带重试逻辑和状态更新）
        logger.info(f"使用 {config['data_source']} 获取退市股票列表...")

        max_retries = 3
        retry_count = 0
        delisted_stocks = None
        last_error = None

        while retry_count < max_retries:
            try:
                delisted_stocks = await asyncio.to_thread(provider.get_delisted_stocks)
                break
            except Exception as e:
                retry_count += 1
                last_error = str(e)

                error_with_retry = f"重试 {retry_count}/{max_retries}: {last_error}"
                await config_service.update_sync_task(
                    task_id=task_id,
                    error_message=error_with_retry,
                    progress=int((retry_count / max_retries) * 50)
                )

                logger.warning(f"获取退市股票列表失败 (尝试 {retry_count}/{max_retries}): {last_error}")

                if retry_count >= max_retries:
                    raise

                await asyncio.sleep(retry_count * 3)

        if delisted_stocks is None:
            raise Exception(last_error or "获取退市股票列表失败")

        # 更新数据库中股票的状态为"退市"
        data_service = DataDownloadService()
        count = 0

        for _, row in delisted_stocks.iterrows():
            code = row['code']
            try:
                # 使用 save_stock_list 保存，但状态设为"退市"
                stock_df = delisted_stocks[delisted_stocks['code'] == code].copy()
                stock_df['status'] = '退市'

                await asyncio.to_thread(
                    data_service.db.save_stock_list,
                    stock_df,
                    config['data_source']
                )
                count += 1
            except Exception as e:
                logger.warning(f"更新退市股票 {code} 失败: {e}")

        # 更新任务状态为完成
        await config_service.update_sync_task(
            task_id=task_id,
            status='completed',
            total_count=len(delisted_stocks),
            success_count=count,
            failed_count=len(delisted_stocks) - count,
            progress=100,
            error_message=''
        )

        logger.info(f"✓ 退市股票列表同步完成: {count} 只")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "total": count
            }
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"同步退市股票列表失败: {error_msg}")

        await config_service.update_sync_task(
            task_id=task_id,
            status='failed',
            error_message=error_msg
        )

        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/daily/batch")
async def sync_daily_batch(request: SyncDailyBatchRequest):
    """
    批量同步日线数据

    Args:
        request: 批量同步请求
            - codes: 股票代码列表 (None 表示全部)
            - years: 历史年数 (默认 5 年)
            - max_stocks: 最大同步数量 (限制批量大小)

    Returns:
        同步结果统计
    """
    try:
        config_service = ConfigService()
        data_service = DataDownloadService()

        # 获取数据源配置
        config = await config_service.get_data_source_config()

        # 创建数据提供者
        provider = DataProviderFactory.create_provider(
            source=config['data_source'],
            token=config.get('tushare_token', '')
        )

        # 获取要同步的股票代码
        if request.codes is None:
            stock_list_df = await asyncio.to_thread(
                data_service.db.get_stock_list
            )
            codes = stock_list_df['code'].tolist()
        else:
            codes = request.codes

        # 限制数量
        if request.max_stocks:
            codes = codes[:request.max_stocks]

        total = len(codes)
        success_count = 0
        failed_count = 0

        # 更新同步状态
        await config_service.update_sync_status(
            status='running',
            progress=0,
            total=total,
            completed=0
        )

        logger.info(f"开始批量同步 {total} 只股票的日线数据 (近 {request.years} 年)")

        # 计算日期范围
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=request.years * 365)).strftime('%Y%m%d')

        # 批量同步
        for idx, code in enumerate(codes, 1):
            try:
                logger.info(f"[{idx}/{total}] 同步 {code}")

                # 获取日线数据 (添加30秒超时)
                try:
                    df = await asyncio.wait_for(
                        asyncio.to_thread(
                            provider.get_daily_data,
                            code=code,
                            start_date=start_date,
                            end_date=end_date,
                            adjust='qfq'
                        ),
                        timeout=30.0  # 单个股票数据获取超时30秒
                    )
                except asyncio.TimeoutError:
                    logger.error(f"  ✗ {code}: 数据获取超时 (30秒)")
                    failed_count += 1
                    continue

                if not df.empty:
                    # 保存到数据库
                    count = await asyncio.to_thread(
                        data_service.db.save_daily_data,
                        df,
                        code
                    )
                    logger.info(f"  ✓ {code}: {count} 条记录")
                    success_count += 1
                else:
                    logger.warning(f"  {code}: 无数据")
                    failed_count += 1

                # 更新进度
                progress = int((idx / total) * 100)
                await config_service.update_sync_status(
                    progress=progress,
                    completed=idx
                )

                # 请求间隔
                await asyncio.sleep(0.3)

            except Exception as e:
                logger.error(f"  ✗ {code}: {e}")
                failed_count += 1

        # 更新同步状态为完成
        await config_service.update_sync_status(
            status='completed',
            last_sync_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            progress=100
        )

        logger.info(f"✓ 批量同步完成: 成功 {success_count}, 失败 {failed_count}")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "success": success_count,
                "failed": failed_count,
                "total": total
            }
        }
    except Exception as e:
        logger.error(f"批量同步失败: {e}")

        config_service = ConfigService()
        await config_service.update_sync_status(status='failed')

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daily/{code}")
async def sync_daily_stock(code: str, years: int = 5):
    """
    同步单只股票日线数据

    Args:
        code: 股票代码
        years: 历史年数

    Returns:
        同步结果
    """
    try:
        config_service = ConfigService()
        data_service = DataDownloadService()

        # 获取数据源配置
        config = await config_service.get_data_source_config()

        # 创建数据提供者
        provider = DataProviderFactory.create_provider(
            source=config['data_source'],
            token=config.get('tushare_token', '')
        )

        # 计算日期范围
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y%m%d')

        logger.info(f"同步 {code} 日线数据 ({start_date} - {end_date})")

        # 获取日线数据 (添加30秒超时)
        try:
            df = await asyncio.wait_for(
                asyncio.to_thread(
                    provider.get_daily_data,
                    code=code,
                    start_date=start_date,
                    end_date=end_date,
                    adjust='qfq'
                ),
                timeout=30.0  # 30秒超时
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail=f"{code}: 数据获取超时")

        if df.empty:
            raise HTTPException(status_code=404, detail=f"{code}: 无数据")

        # 保存到数据库
        count = await asyncio.to_thread(
            data_service.db.save_daily_data,
            df,
            code
        )

        logger.info(f"✓ {code}: {count} 条记录")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "code": code,
                "records": count
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"同步 {code} 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/minute/{code}")
async def sync_minute_data(code: str, request: SyncMinuteRequest):
    """
    同步分时数据

    Args:
        code: 股票代码
        request: 分时同步请求
            - period: 分时周期 ('1', '5', '15', '30', '60')
            - days: 同步天数

    Returns:
        同步结果
    """
    try:
        config_service = ConfigService()
        data_service = DataDownloadService()

        # 获取数据源配置
        config = await config_service.get_data_source_config()

        # 创建数据提供者
        provider = DataProviderFactory.create_provider(
            source=config['data_source'],
            token=config.get('tushare_token', '')
        )

        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        start_date = (datetime.now() - timedelta(days=request.days)).strftime('%Y-%m-%d 09:30:00')

        logger.info(f"同步 {code} {request.period}分钟数据")

        # 获取分时数据
        df = await asyncio.to_thread(
            provider.get_minute_data,
            code=code,
            period=request.period,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            raise HTTPException(status_code=404, detail=f"{code}: 无分时数据")

        # TODO: 保存分时数据到数据库
        # count = await asyncio.to_thread(
        #     data_service.db.save_minute_data,
        #     df,
        #     code
        # )

        logger.info(f"✓ {code}: {len(df)} 条分时记录")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "code": code,
                "period": request.period,
                "records": len(df)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"同步 {code} 分时数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/realtime")
async def sync_realtime_quotes(request: SyncRealtimeRequest):
    """
    更新实时行情

    Args:
        request: 实时行情请求
            - codes: 股票代码列表 (None 表示全部)

    Returns:
        更新结果
    """
    try:
        config_service = ConfigService()

        # 获取数据源配置
        config = await config_service.get_data_source_config()

        # 创建数据提供者
        provider = DataProviderFactory.create_provider(
            source=config['data_source'],
            token=config.get('tushare_token', '')
        )

        logger.info("更新实时行情...")

        # 获取实时行情
        df = await asyncio.to_thread(
            provider.get_realtime_quotes,
            codes=request.codes
        )

        if df.empty:
            raise HTTPException(status_code=404, detail="无实时行情数据")

        # TODO: 保存实时行情到数据库
        # await asyncio.to_thread(
        #     data_service.db.save_realtime_quotes,
        #     df
        # )

        logger.info(f"✓ 实时行情更新完成: {len(df)} 只股票")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "total": len(df),
                "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新实时行情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_sync_history(limit: int = 20, offset: int = 0):
    """
    获取同步历史记录

    Args:
        limit: 返回记录数
        offset: 跳过记录数

    Returns:
        同步历史记录列表
    """
    try:
        # TODO: 从 sync_log 表查询历史记录
        history = []

        return {
            "code": 200,
            "message": "success",
            "data": history
        }
    except Exception as e:
        logger.error(f"获取同步历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
