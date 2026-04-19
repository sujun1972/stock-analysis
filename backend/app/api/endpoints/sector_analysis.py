"""板块行情分析 API 端点"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.error_handler import handle_api_errors
from app.core.dependencies import require_admin
from app.models.api_response import ApiResponse
from app.models.user import User
from app.services.sector_analysis_service import SectorAnalysisService

router = APIRouter()


@router.get("/board")
@handle_api_errors
async def get_sector_board_view(
    trade_date: Optional[date] = Query(None, description="交易日期；不传取板块数据最新日期"),
    current_user: User = Depends(require_admin),
):
    """返回指定交易日的板块四视图聚合（涨幅榜 / 资金流入榜 / 涨停集中榜 / 量价背离）。"""
    trade_date_str = trade_date.strftime('%Y%m%d') if trade_date else None
    service = SectorAnalysisService()
    result = await service.analyze_board(trade_date_str)
    return ApiResponse.success(data=result)
