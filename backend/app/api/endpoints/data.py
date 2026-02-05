"""
股票数据下载和查询API (重构版本)

✅ 任务 0.5: 重写 Data API
- 使用 Core Adapters 代替 DatabaseService/DataDownloadService
- Backend 只负责：参数验证、响应格式化
- 业务逻辑全部由 Core 处理

作者: Backend Team
创建日期: 2026-02-02
版本: 2.0.0 (架构修正版)
"""

from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Query
from loguru import logger

from app.core.exceptions import DataNotFoundError, DataSyncError, ExternalAPIError
from app.core_adapters.data_adapter import DataAdapter
from app.models.api_response import ApiResponse

router = APIRouter()

# 全局 Data Adapter 实例
data_adapter = DataAdapter()


@router.get("/daily/{code}")
async def get_daily_data(
    code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(500, ge=1, le=5000, description="最大返回记录数"),
):
    """
    获取股票日线数据

    ✅ 架构修正版：
    - Backend 只负责：参数验证、调用 Core Adapter、响应格式化
    - Core 负责：数据库查询、数据处理

    参数:
    - code: 股票代码（如 000001.SZ）
    - start_date: 开始日期（YYYY-MM-DD 格式）
    - end_date: 结束日期（YYYY-MM-DD 格式）
    - limit: 最大返回记录数（1-5000，默认 500）

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "code": "000001.SZ",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "count": 244,
            "data": [
                {
                    "date": "2023-01-03",
                    "open": 13.50,
                    "high": 13.80,
                    "low": 13.40,
                    "close": 13.75,
                    "volume": 123456789,
                    "amount": 1700000000
                },
                ...
            ]
        }
    }
    """
    try:
        # 1. 参数处理：设置默认日期范围（最近一年）
        if not end_date:
            end_date = datetime.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=365)

        # 2. 调用 Core Adapter（业务逻辑在 Core）
        df = await data_adapter.get_daily_data(code=code, start_date=start_date, end_date=end_date)

        # 3. Backend 职责：数据验证
        if df is None or df.empty:
            return ApiResponse.not_found(
                message=f"股票 {code} 在指定日期范围内无数据",
                data={
                    "code": code,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "count": 0,
                },
            ).to_dict()

        # 4. Backend 职责：限制返回数量
        if len(df) > limit:
            df = df.tail(limit)
            logger.warning(f"数据量超过限制 {limit}，仅返回最新 {limit} 条记录")

        # 5. Backend 职责：格式化数据
        df_reset = df.reset_index()

        # 将日期列转换为字符串格式
        if "date" in df_reset.columns:
            df_reset["date"] = df_reset["date"].astype(str)

        # 6. Backend 职责：响应格式化
        return ApiResponse.success(
            data={
                "code": code,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "count": len(df),
                "data": df_reset.to_dict("records"),
            },
            message=f"获取股票 {code} 日线数据成功",
        ).to_dict()

    except DataNotFoundError:
        raise
    except Exception as e:
        logger.exception(f"未预期的错误 {code}: {e}")
        return ApiResponse.internal_error(
            message=f"获取日线数据失败: {str(e)}", data={"code": code, "error": str(e)}
        ).to_dict()


@router.post("/download")
async def download_data(
    codes: Optional[List[str]] = Query(None, description="股票代码列表（不指定则下载全部）"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    years: Optional[int] = Query(None, ge=1, le=20, description="下载年数（与日期范围二选一）"),
    max_stocks: Optional[int] = Query(None, ge=1, le=10000, description="最大下载数量"),
    batch_size: int = Query(50, ge=1, le=200, description="批量下载大小"),
):
    """
    批量下载股票数据

    ✅ 架构修正版：
    - Backend 只负责：参数验证、调用 Core Adapter、响应格式化
    - Core 负责：数据下载、批量处理、数据存储

    参数:
    - codes: 股票代码列表（不指定则下载全部股票）
    - start_date: 开始日期（YYYY-MM-DD）
    - end_date: 结束日期（YYYY-MM-DD）
    - years: 下载年数（如果指定，则忽略 start_date/end_date）
    - max_stocks: 最大下载数量（用于测试或限流）
    - batch_size: 批量下载大小（默认 50）

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "status": "completed",
            "total": 100,
            "success": 95,
            "failed": 5,
            "duration_seconds": 120.5,
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "failed_codes": ["600001.SH", "600002.SH"]
        }
    }
    """
    try:
        # 1. 参数处理：计算日期范围
        if years:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=years * 365)
            logger.info(f"根据 years={years} 计算日期范围: {start_date} ~ {end_date}")
        else:
            if not end_date:
                end_date = datetime.now().date()
            if not start_date:
                start_date = end_date - timedelta(days=365)

        # 2. 参数处理：获取股票列表
        if not codes:
            # 调用 Core 获取所有股票列表
            stock_list = await data_adapter.get_stock_list(status="正常")
            codes = [stock["code"] for stock in stock_list]
            logger.info(f"未指定股票代码，将下载全部 {len(codes)} 只股票")

        # 3. 限制下载数量
        if max_stocks and len(codes) > max_stocks:
            codes = codes[:max_stocks]
            logger.info(f"限制下载数量为 {max_stocks}")

        # 4. 调用 Core Adapter 批量下载（业务逻辑在 Core）
        start_time = datetime.now()

        total = len(codes)
        success = 0
        failed = 0
        failed_codes = []

        # 批量下载逻辑
        for i in range(0, total, batch_size):
            batch = codes[i : i + batch_size]
            logger.info(
                f"下载批次 {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}: {len(batch)} 只股票"
            )

            for code in batch:
                try:
                    # 下载单只股票数据
                    df = await data_adapter.download_daily_data(
                        code=code, start_date=start_date, end_date=end_date
                    )

                    if df is not None and not df.empty:
                        # 插入数据库
                        await data_adapter.insert_daily_data(df, code)
                        success += 1
                        logger.info(f"✅ {code}: 下载并保存 {len(df)} 条记录")
                    else:
                        failed += 1
                        failed_codes.append(code)
                        logger.warning(f"⚠️  {code}: 无数据")

                except ExternalAPIError as e:
                    failed += 1
                    failed_codes.append(code)
                    logger.error(f"❌ {code}: 数据源API错误 - {e}")
                except Exception as e:
                    failed += 1
                    failed_codes.append(code)
                    logger.error(f"❌ {code}: 下载失败 - {e}")

        duration = (datetime.now() - start_time).total_seconds()

        # 5. Backend 职责：响应格式化
        return ApiResponse.success(
            data={
                "status": "completed",
                "total": total,
                "success": success,
                "failed": failed,
                "duration_seconds": round(duration, 2),
                "start_date": str(start_date),
                "end_date": str(end_date),
                "failed_codes": failed_codes[:20] if len(failed_codes) > 20 else failed_codes,
                "message": f"下载完成: 成功 {success}/{total}, 失败 {failed}/{total}",
            },
            message=f"数据下载完成，成功率: {success/total*100:.1f}%",
        ).to_dict()

    except DataSyncError as e:
        logger.error(f"数据同步失败: {e}")
        return ApiResponse.internal_error(
            message=f"数据下载失败: {str(e)}", data={"error": str(e)}
        ).to_dict()
    except Exception as e:
        logger.exception(f"未预期的错误: {e}")
        return ApiResponse.internal_error(
            message=f"数据下载失败: {str(e)}", data={"error": str(e)}
        ).to_dict()


@router.get("/minute/{code}")
async def get_minute_data(
    code: str,
    trade_date: Optional[date] = Query(None, description="交易日期"),
    period: str = Query("1min", description="周期（1min/5min/15min/30min/60min）"),
    limit: int = Query(240, ge=1, le=1000, description="最大返回记录数"),
):
    """
    获取股票分钟数据

    ✅ 架构修正版：
    - Backend 只负责：参数验证、调用 Core Adapter、响应格式化
    - Core 负责：数据库查询、数据处理

    参数:
    - code: 股票代码（如 000001.SZ）
    - trade_date: 交易日期（YYYY-MM-DD 格式，默认今天）
    - period: 周期（1min/5min/15min/30min/60min）
    - limit: 最大返回记录数（1-1000，默认 240）

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "code": "000001.SZ",
            "trade_date": "2023-12-29",
            "period": "1min",
            "count": 240,
            "data": [
                {
                    "time": "09:31:00",
                    "open": 13.50,
                    "high": 13.52,
                    "low": 13.48,
                    "close": 13.51,
                    "volume": 1234567,
                    "amount": 16700000
                },
                ...
            ]
        }
    }
    """
    try:
        # 1. 参数处理：设置默认日期
        if not trade_date:
            trade_date = datetime.now().date()

        # 2. 参数验证：周期
        valid_periods = ["1min", "5min", "15min", "30min", "60min"]
        if period not in valid_periods:
            return ApiResponse.bad_request(
                message=f"无效的周期参数: {period}", data={"valid_periods": valid_periods}
            ).to_dict()

        # 3. 调用 Core Adapter（业务逻辑在 Core）
        df = await data_adapter.get_minute_data(code=code, period=period, trade_date=trade_date)

        # 4. Backend 职责：数据验证
        if df is None or df.empty:
            return ApiResponse.not_found(
                message=f"股票 {code} 在 {trade_date} 无分钟数据",
                data={"code": code, "trade_date": str(trade_date), "period": period, "count": 0},
            ).to_dict()

        # 5. Backend 职责：限制返回数量
        if len(df) > limit:
            df = df.tail(limit)
            logger.warning(f"数据量超过限制 {limit}，仅返回最新 {limit} 条记录")

        # 6. Backend 职责：格式化数据
        df_reset = df.reset_index()

        # 将时间列转换为字符串格式
        if "time" in df_reset.columns:
            df_reset["time"] = df_reset["time"].astype(str)

        # 7. Backend 职责：响应格式化
        return ApiResponse.success(
            data={
                "code": code,
                "trade_date": str(trade_date),
                "period": period,
                "count": len(df),
                "data": df_reset.to_dict("records"),
            },
            message=f"获取股票 {code} 分钟数据成功",
        ).to_dict()

    except DataNotFoundError:
        raise
    except Exception as e:
        logger.exception(f"未预期的错误 {code}: {e}")
        return ApiResponse.internal_error(
            message=f"获取分钟数据失败: {str(e)}", data={"code": code, "error": str(e)}
        ).to_dict()


@router.get("/check/{code}")
async def check_data_integrity(
    code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
):
    """
    检查股票数据完整性

    ✅ 新增端点：数据质量检查

    参数:
    - code: 股票代码
    - start_date: 开始日期（可选）
    - end_date: 结束日期（可选）

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "code": "000001.SZ",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "expected_trading_days": 244,
            "actual_data_count": 242,
            "missing_count": 2,
            "data_completeness": 99.18,
            "missing_dates": ["2023-03-15", "2023-08-22"]
        }
    }
    """
    try:
        # 1. 参数处理：设置默认日期范围
        if not end_date:
            end_date = datetime.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=365)

        # 2. 调用 Core Adapter 检查数据完整性
        integrity_result = await data_adapter.check_data_integrity(
            code=code, start_date=start_date, end_date=end_date
        )

        # 3. Backend 职责：响应格式化
        return ApiResponse.success(data=integrity_result, message="数据完整性检查完成").to_dict()

    except DataNotFoundError:
        raise
    except Exception as e:
        logger.exception(f"未预期的错误 {code}: {e}")
        return ApiResponse.internal_error(
            message=f"数据完整性检查失败: {str(e)}", data={"code": code, "error": str(e)}
        ).to_dict()
