"""
用户股票列表 API 端点
允许已登录用户管理自选股列表（创建、重命名、删除、添加/移除股票）
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_active_user
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.models.user import User
from app.services.user_stock_list_service import UserStockListService

router = APIRouter(prefix="/user-stock-lists", tags=["用户股票列表"])


# ------------------------------------------------------------------
# Request / Response 模型
# ------------------------------------------------------------------

class CreateListRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="列表名称")
    description: Optional[str] = Field(None, max_length=200, description="列表描述")


class UpdateListRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="列表名称")
    description: Optional[str] = Field(None, max_length=200, description="列表描述")


class StockCodesRequest(BaseModel):
    ts_codes: List[str] = Field(..., min_length=1, description="股票代码列表（ts_code 格式，如 000001.SZ）")


# ------------------------------------------------------------------
# 列表 CRUD
# ------------------------------------------------------------------

@router.get("")
@handle_api_errors
async def get_my_lists(
    current_user: User = Depends(get_current_active_user),
):
    """获取当前用户的所有股票列表"""
    service = UserStockListService()
    lists = await service.get_lists(current_user.id)
    return ApiResponse.success(data={"items": lists, "total": len(lists)}).to_dict()


@router.post("")
@handle_api_errors
async def create_list(
    body: CreateListRequest,
    current_user: User = Depends(get_current_active_user),
):
    """创建新股票列表"""
    service = UserStockListService()
    result = await service.create_list(current_user.id, body.name, body.description)
    return ApiResponse.success(data=result, message="列表创建成功").to_dict()


@router.put("/{list_id}")
@handle_api_errors
async def update_list(
    list_id: int,
    body: UpdateListRequest,
    current_user: User = Depends(get_current_active_user),
):
    """重命名 / 修改列表描述"""
    service = UserStockListService()
    result = await service.update_list(list_id, current_user.id, body.name, body.description)
    return ApiResponse.success(data=result, message="列表更新成功").to_dict()


@router.delete("/{list_id}")
@handle_api_errors
async def delete_list(
    list_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """删除列表（同时删除列表中的所有股票）"""
    service = UserStockListService()
    await service.delete_list(list_id, current_user.id)
    return ApiResponse.success(message="列表删除成功").to_dict()


# ------------------------------------------------------------------
# 成分股操作
# ------------------------------------------------------------------

@router.get("/{list_id}/items")
@handle_api_errors
async def get_list_items(
    list_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """获取列表中的所有股票（含名称、最新价、涨跌幅）"""
    service = UserStockListService()
    items = await service.get_items(list_id, current_user.id)
    return ApiResponse.success(data={"items": items, "total": len(items)}).to_dict()


@router.get("/{list_id}/ts-codes")
@handle_api_errors
async def get_list_ts_codes(
    list_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """轻量接口：仅返回列表中所有股票的 ts_code 列表"""
    service = UserStockListService()
    codes = await service.get_ts_codes(list_id, current_user.id)
    return ApiResponse.success(data={"ts_codes": codes}).to_dict()


@router.post("/{list_id}/items")
@handle_api_errors
async def add_stocks_to_list(
    list_id: int,
    body: StockCodesRequest,
    current_user: User = Depends(get_current_active_user),
):
    """批量添加股票到列表"""
    service = UserStockListService()
    result = await service.add_stocks(list_id, current_user.id, body.ts_codes)
    return ApiResponse.success(
        data=result,
        message=f"已添加 {result['added']} 只股票"
    ).to_dict()


@router.delete("/{list_id}/items")
@handle_api_errors
async def remove_stocks_from_list(
    list_id: int,
    body: StockCodesRequest,
    current_user: User = Depends(get_current_active_user),
):
    """批量从列表移除股票"""
    service = UserStockListService()
    result = await service.remove_stocks(list_id, current_user.id, body.ts_codes)
    return ApiResponse.success(
        data=result,
        message=f"已移除 {result['removed']} 只股票"
    ).to_dict()
