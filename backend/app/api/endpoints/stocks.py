"""
股票列表相关API (重构版本)

✅ 任务 0.3: 重写 Stocks API
- 使用 Core Adapters 代替 DatabaseService
- Backend 只负责：参数验证、分页、响应格式化
- 业务逻辑全部由 Core 处理

作者: Backend Team
创建日期: 2026-02-01
版本: 2.0.0 (架构修正版)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import sys
from pathlib import Path

from fastapi import APIRouter, Query, Depends
from loguru import logger

from app.core_adapters.data_adapter import DataAdapter
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User
from app.services.realtime_sync_service import RealtimeSyncService

router = APIRouter()

# 全局 Data Adapter 实例
data_adapter = DataAdapter()

@router.get(
    "/list",
    summary="获取股票列表",
    description="分页获取A股市场的股票列表，支持按市场类型、状态筛选和关键词搜索",
    tags=["股票管理"],
    responses={
        200: {
            "description": "成功获取股票列表",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "获取股票列表成功",
                        "data": {
                            "items": [
                                {
                                    "code": "000001.SZ",
                                    "name": "平安银行",
                                    "market": "深圳主板",
                                    "industry": "银行",
                                    "list_date": "1991-04-03",
                                    "status": "正常"
                                },
                                {
                                    "code": "600000.SH",
                                    "name": "浦发银行",
                                    "market": "上海主板",
                                    "industry": "银行",
                                    "list_date": "1999-11-10",
                                    "status": "正常"
                                }
                            ],
                            "total": 5000,
                            "page": 1,
                            "page_size": 20,
                            "total_pages": 250
                        }
                    }
                }
            }
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "参数验证失败",
                        "error": "page 必须大于等于 1"
                    }
                }
            }
        },
        500: {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "获取股票列表失败",
                        "error": "数据库连接失败"
                    }
                }
            }
        }
    }
)
async def get_stock_list(
    market: Optional[str] = Query(None, description="市场类型筛选，如: 深圳主板、上海主板、创业板、科创板、北交所"),
    industry: Optional[str] = Query(None, description="行业筛选，如: 银行、医药、计算机"),
    status_filter: str = Query("正常", description="股票状态筛选，如: 正常、退市、暂停上市", alias="status"),
    search: Optional[str] = Query(None, description="搜索关键词，支持股票代码或名称的模糊匹配，如: 平安、000001"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数，范围: 1-100"),
):
    """
    获取股票列表（分页）

    ✅ 架构修正版：
    - Backend 只负责：参数验证（Pydantic 自动）、调用 Core Adapter、分页、响应格式化
    - Core 负责：数据库查询、业务逻辑

    ## 功能说明
    - 支持按市场类型筛选（深圳主板/上海主板/创业板/科创板/北交所）
    - 支持按行业筛选（银行/医药/计算机等）
    - 支持按股票状态筛选（正常/退市/暂停上市等）
    - 支持股票代码和名称的模糊搜索
    - 支持分页查询，避免一次返回大量数据

    ## 使用场景
    1. 获取全部正常上市的股票列表
    2. 筛选特定市场的股票（如只看创业板）
    3. 搜索特定股票（输入代码或名称关键词）
    4. 前端表格分页展示

    ## 错误码说明
    - 200: 成功
    - 400: 参数错误（如 page < 1 或 page_size > 100）
    - 500: 服务器内部错误（如数据库连接失败）
    """
    # 直接调用，让异常传播到全局处理器
    # 1. 调用 Core Adapter（业务逻辑在 Core）
    stocks = await data_adapter.get_stock_list(market=market, status=status_filter)

    # 2. Backend 职责：行业过滤
    if industry:
        stocks = [
            stock
            for stock in stocks
            if stock.get("industry") == industry
        ]

    # 3. Backend 职责：搜索过滤（前端功能）
    if search:
        search_lower = search.lower()
        stocks = [
            stock
            for stock in stocks
            if search_lower in stock.get("code", "").lower()
            or search_lower in stock.get("name", "").lower()
        ]

    # 4. Backend 职责：分页
    total = len(stocks)
    start = (page - 1) * page_size
    end = start + page_size
    items = stocks[start:end]

    # 6. Backend 职责：响应格式化
    return ApiResponse.paginated(
        items=items, total=total, page=page, page_size=page_size, message="获取股票列表成功"
    ).to_dict()


@router.get(
    "/codes/filtered",
    summary="获取股票代码列表（筛选后）",
    description="根据筛选条件获取股票代码列表，用于批量选择场景（如回测股票池）。只返回股票代码，不返回完整信息，性能更优。",
    tags=["股票管理"],
    responses={
        200: {
            "description": "成功获取股票代码列表",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "获取股票代码列表成功",
                        "data": {
                            "codes": ["000001", "000002", "000004", "000005"],
                            "total": 4
                        }
                    }
                }
            }
        }
    }
)
async def get_stock_codes(
    market: Optional[str] = Query(None, description="市场类型筛选，如: 深圳主板、上海主板、创业板、科创板、北交所"),
    industry: Optional[str] = Query(None, description="行业筛选，如: 银行、医药、计算机"),
    status_filter: str = Query("正常", description="股票状态筛选，如: 正常、退市、暂停上市", alias="status"),
    search: Optional[str] = Query(None, description="搜索关键词，支持股票代码或名称的模糊匹配"),
    limit: int = Query(500, ge=1, le=1000, description="最大返回数量，范围: 1-1000，默认 500"),
):
    """
    获取符合筛选条件的股票代码列表

    ## 功能说明
    - 专门用于批量选择股票场景（如回测股票池配置）
    - 只返回股票代码，不返回完整股票信息，性能更优
    - 支持与 /list 接口相同的筛选条件
    - 最多支持一次性获取 1000 只股票代码

    ## 使用场景
    1. 回测页面"全选所有筛选结果"功能
    2. 批量导出股票代码
    3. 快速获取特定市场/行业的所有股票代码

    ## 返回格式
    - codes: 股票代码列表（不带后缀，如 "000001"）
    - total: 符合条件的股票总数

    ## 错误码说明
    - 200: 成功
    - 400: 参数错误
    - 500: 服务器内部错误
    """
    # 1. 调用 Core Adapter 获取股票列表
    stocks = await data_adapter.get_stock_list(market=market, status=status_filter)

    # 2. 行业过滤
    if industry:
        stocks = [
            stock
            for stock in stocks
            if stock.get("industry") == industry
        ]

    # 3. 搜索过滤
    if search:
        search_lower = search.lower()
        stocks = [
            stock
            for stock in stocks
            if search_lower in stock.get("code", "").lower() or search_lower in stock.get("name", "").lower()
        ]

    # 4. 提取股票代码（去除后缀）并限制数量
    codes = []
    for stock in stocks[:limit]:
        code = stock.get("code", "")
        # 去除 .SZ .SH 等后缀
        if "." in code:
            code = code.split(".")[0]
        codes.append(code)

    # 5. 返回结果
    return ApiResponse.success(
        data={
            "codes": codes,
            "total": len(codes)
        },
        message="获取股票代码列表成功"
    ).to_dict()


@router.get(
    "/{code}",
    summary="获取单只股票详情",
    description="根据股票代码获取该股票的详细信息，包括基本信息、行业分类、上市日期等",
    tags=["股票管理"],
    responses={
        200: {
            "description": "成功获取股票信息",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "获取股票信息成功",
                        "data": {
                            "code": "000001.SZ",
                            "name": "平安银行",
                            "market": "深圳主板",
                            "industry": "银行",
                            "list_date": "1991-04-03",
                            "status": "正常",
                            "region": "深圳",
                            "exchange": "SZSE"
                        }
                    }
                }
            }
        },
        404: {
            "description": "股票不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 404,
                        "message": "股票 999999.SZ 不存在",
                        "error": "STOCK_NOT_FOUND"
                    }
                }
            }
        },
        400: {
            "description": "股票代码格式错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "股票代码格式错误",
                        "error": "代码格式应为: 6位数字.市场代码 (如 000001.SZ 或 600000.SH)"
                    }
                }
            }
        }
    }
)
async def get_stock_info(code: str):
    """
    获取单只股票详细信息

    ✅ 架构修正版：调用 Core Adapter 的 get_stock_info 方法

    ## 功能说明
    根据股票代码查询该股票的完整信息，包括：
    - 基本信息：代码、名称、交易所
    - 分类信息：行业、板块、地区
    - 上市信息：上市日期、当前状态

    ## 股票代码格式
    - 上交所: 6位数字.SH (如 600000.SH)
    - 深交所: 6位数字.SZ (如 000001.SZ)
    - 北交所: 6位数字.BJ (如 430047.BJ)

    ## 错误码说明
    - 200: 成功
    - 400: 股票代码格式错误
    - 404: 股票不存在
    - 500: 服务器内部错误
    """
    # 调用 Core Adapter
    stock_info = await data_adapter.get_stock_info(code)

    if stock_info is None:
        return ApiResponse.not_found(message=f"股票 {code} 不存在").to_dict()

    return ApiResponse.success(data=stock_info, message="获取股票信息成功").to_dict()


@router.get(
    "/{code}/daily",
    summary="获取股票日线数据",
    description="获取指定股票的日线历史数据，包括开高低收、成交量、成交额等",
    tags=["股票管理"],
    responses={
        200: {
            "description": "成功获取日线数据",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "获取日线数据成功",
                        "data": {
                            "code": "000001.SZ",
                            "records": [
                                {
                                    "trade_date": "2024-01-02",
                                    "open": 12.50,
                                    "high": 12.80,
                                    "low": 12.45,
                                    "close": 12.75,
                                    "volume": 1500000,
                                    "amount": 19000000.0,
                                    "change": 0.05,
                                    "pct_change": 0.0039
                                }
                            ],
                            "record_count": 100
                        }
                    }
                }
            }
        },
        404: {
            "description": "无日线数据",
            "content": {
                "application/json": {
                    "example": {
                        "code": 404,
                        "message": "股票 000001.SZ 无日线数据",
                        "error": "DATA_NOT_AVAILABLE"
                    }
                }
            }
        },
        400: {
            "description": "日期格式错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "日期格式错误",
                        "error": "日期格式应为 YYYY-MM-DD"
                    }
                }
            }
        }
    }
)
async def get_stock_daily_data(
    code: str,
    start_date: Optional[str] = Query(None, description="开始日期，格式: YYYY-MM-DD，默认为最近100个交易日"),
    end_date: Optional[str] = Query(None, description="结束日期，格式: YYYY-MM-DD，默认为今天"),
    limit: int = Query(100, ge=1, le=1000, description="最大记录数，范围: 1-1000，默认100"),
):
    """
    获取股票日线数据

    ✅ 架构修正版：调用 Core Adapter 的 get_daily_data 方法

    ## 功能说明
    获取指定股票在指定时间范围内的日线数据，包括：
    - OHLC: 开盘价、最高价、最低价、收盘价
    - 成交量和成交额
    - 涨跌幅和涨跌额

    ## 使用场景
    1. 查询某只股票的历史走势
    2. 为技术分析提供数据支持
    3. 绘制K线图
    4. 计算技术指标

    ## 参数说明
    - 如果不指定日期范围，默认返回最近100个交易日的数据
    - limit 参数限制返回的最大记录数，避免一次返回过多数据
    - 日期必须为有效的交易日，非交易日会自动跳过

    ## 错误码说明
    - 200: 成功
    - 400: 日期格式错误
    - 404: 股票不存在或无数据
    - 500: 服务器内部错误
    """
    try:
        # 1. 参数转换
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    except ValueError as e:
        return ApiResponse.bad_request(message=f"日期格式错误: {str(e)}").to_dict()

    # 2. 调用 Core Adapter
    df = await data_adapter.get_daily_data(code=code, start_date=start_dt, end_date=end_dt)

    if df.empty:
        return ApiResponse.not_found(message=f"股票 {code} 无日线数据").to_dict()

    # 3. 限制返回记录数
    if len(df) > limit:
        df = df.tail(limit)

    # 4. 转换为响应格式
    records = df.to_dict("records")

    return ApiResponse.success(
        data={"code": code, "records": records, "record_count": len(records)},
        message="获取日线数据成功",
    ).to_dict()


@router.post("/update")
async def update_stock_list(
    current_user: User = Depends(require_admin)
):
    """
    更新股票列表（从数据源获取最新列表）

    ⚠️ 注意：此功能暂不支持，需要配合 Core 的数据下载功能
    未来版本将集成 Core 的 DataDownloadManager

    返回:
    {
        "code": 501,
        "message": "此功能暂未实现，请使用 Core 的数据下载功能"
    }
    """
    return ApiResponse.error(
        message="此功能暂未实现，请使用 Core 的数据下载功能", code=501
    ).to_dict()


@router.get(
    "/{code}/minute",
    summary="获取股票分时数据",
    description="获取指定股票在某个交易日的分钟级数据，支持多种时间周期",
    tags=["股票管理"],
    responses={
        200: {
            "description": "成功获取分时数据",
            "content": {
                "application/json": {
                    "examples": {
                        "有数据": {
                            "value": {
                                "code": 200,
                                "message": "获取分时数据成功",
                                "data": {
                                    "code": "000001.SZ",
                                    "date": "2024-01-02",
                                    "period": "1min",
                                    "records": [
                                        {
                                            "datetime": "2024-01-02 09:31:00",
                                            "open": 12.50,
                                            "high": 12.55,
                                            "low": 12.48,
                                            "close": 12.52,
                                            "volume": 50000,
                                            "amount": 625000.0
                                        }
                                    ],
                                    "record_count": 240
                                }
                            }
                        },
                        "非交易日": {
                            "value": {
                                "code": 200,
                                "message": "非交易日",
                                "data": {
                                    "code": "000001.SZ",
                                    "date": "2024-01-01",
                                    "records": [],
                                    "is_trading_day": False
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "日期格式错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "日期格式错误",
                        "error": "日期格式应为 YYYY-MM-DD"
                    }
                }
            }
        }
    }
)
async def get_minute_data(
    code: str,
    trade_date: Optional[str] = Query(None, description="交易日期，格式: YYYY-MM-DD，默认为今天"),
    period: str = Query("1min", description="分钟周期，可选值: 1min, 5min, 15min, 30min, 60min"),
):
    """
    获取股票分时数据

    ✅ 架构修正版：调用 Core Adapter 的 get_minute_data 方法

    ## 功能说明
    获取指定股票在某个交易日的分钟级行情数据，支持多种时间周期：
    - 1min: 1分钟K线（240条记录/天）
    - 5min: 5分钟K线（48条记录/天）
    - 15min: 15分钟K线（16条记录/天）
    - 30min: 30分钟K线（8条记录/天）
    - 60min: 60分钟K线（4条记录/天）

    ## 使用场景
    1. 盘中实时监控
    2. 短线交易分析
    3. 高频交易策略回测
    4. 绘制分时图

    ## 注意事项
    - 只返回指定交易日的数据
    - 非交易日返回空数组且 is_trading_day = false
    - 分时数据可能延迟15分钟（取决于数据源）

    ## 错误码说明
    - 200: 成功（包括非交易日也返回200）
    - 400: 日期格式错误
    - 500: 服务器内部错误
    """
    try:
        # 1. 默认日期为今天
        if not trade_date:
            trade_date_dt = datetime.now().date()
        else:
            trade_date_dt = datetime.strptime(trade_date, "%Y-%m-%d").date()
    except ValueError as e:
        return ApiResponse.bad_request(message=f"日期格式错误: {str(e)}").to_dict()

    # 2. 检查是否为交易日
    is_trading = await data_adapter.is_trading_day(trade_date_dt)
    if not is_trading:
        return ApiResponse.success(
            data={
                "code": code,
                "date": trade_date_dt.strftime("%Y-%m-%d"),
                "records": [],
                "is_trading_day": False,
            },
            message="非交易日",
        ).to_dict()

    # 3. 调用 Core Adapter 获取分时数据（先查数据库）
    # period 端点格式为 "1min"/"5min"，provider 格式为 "1"/"5"，转换一下
    period_num = period.replace("min", "")  # "1min" -> "1", "5min" -> "5"
    df = await data_adapter.get_minute_data(code=code, period=period_num, trade_date=trade_date_dt)

    # 4. 数据库为空时，从数据源实时拉取（不持久化，直接返回给前端）
    if df.empty:
        try:
            sync_service = RealtimeSyncService()
            sync_result = await sync_service.sync_minute_data(code=code, period=period_num, days=1)
            raw_records = sync_result.get("data", [])
            # 过滤只保留请求日期的数据
            date_str = trade_date_dt.strftime("%Y-%m-%d")
            records = [
                r for r in raw_records
                if str(r.get("trade_time", "")).startswith(date_str)
            ]
        except Exception as e:
            logger.warning(f"从数据源拉取分时数据失败: {e}")
            records = []
    else:
        records = df.to_dict("records")

    return ApiResponse.success(
        data={
            "code": code,
            "date": trade_date_dt.strftime("%Y-%m-%d"),
            "period": period,
            "records": records,
            "record_count": len(records),
        },
        message="获取分时数据成功" if records else "暂无分时数据",
    ).to_dict()
