"""
个股数据收集 API 端点

从本地数据库收集多维度数据，供 AI 提示词填充后调用大模型生成分析报告。
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_active_user
from app.models.api_response import ApiResponse
from app.models.user import User
from app.services.stock_data_collection_service import StockDataCollectionService

router = APIRouter(prefix="/stock-data-collection", tags=["个股数据收集"])


class CollectRequest(BaseModel):
    ts_code: str = Field(..., description="股票代码，如 000001.SZ")
    stock_name: str = Field(..., description="股票名称，如 平安银行")
    format: Optional[str] = Field("text", description="返回格式：text（结构化文本）或 json（原始字典）")


@router.post("/collect")
async def collect_stock_data(
    body: CollectRequest,
    _: User = Depends(get_current_active_user),
):
    """
    收集指定股票的多维度本地数据，格式化为结构化文本供 AI 提示词使用。

    - format=text：返回 Markdown 格式的结构化数据文本（推荐，直接填入提示词）
    - format=json：返回原始数据字典（供前端自行渲染）
    """
    service = StockDataCollectionService()

    if body.format == "json":
        result = await service.collect(body.ts_code, body.stock_name)
        return ApiResponse.success(data=result).to_dict()
    else:
        text = await service.collect_and_format(body.ts_code, body.stock_name)
        return ApiResponse.success(data={"text": text, "ts_code": body.ts_code, "stock_name": body.stock_name}).to_dict()
