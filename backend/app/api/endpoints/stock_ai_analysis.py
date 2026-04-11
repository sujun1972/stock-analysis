"""
股票AI分析结果 API 端点
支持保存分析结果（游资观点等多种类型）、查询最新版本、浏览历史版本
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_active_user
from app.models.api_response import ApiResponse
from app.models.user import User
from app.services.stock_ai_analysis_service import StockAiAnalysisService

router = APIRouter(prefix="/stock-ai-analysis", tags=["股票AI分析"])


# ------------------------------------------------------------------
# Request 模型
# ------------------------------------------------------------------

class SaveAnalysisRequest(BaseModel):
    ts_code: str = Field(..., description="股票代码，如 000001.SZ")
    analysis_type: str = Field(..., description="分析类型，如 hot_money_view")
    analysis_text: str = Field(..., min_length=1, description="AI分析结果文本")
    score: Optional[float] = Field(None, ge=0, le=10, description="评分 0-10，支持一位小数（可选）")
    prompt_text: Optional[str] = Field(None, description="生成本次分析所用的完整提示词快照")
    ai_provider: Optional[str] = Field(None, description="AI提供商，如 deepseek")
    ai_model: Optional[str] = Field(None, description="AI模型名称，如 deepseek-chat")


class UpdateAnalysisRequest(BaseModel):
    analysis_text: str = Field(..., min_length=1, description="修改后的AI分析结果文本")
    score: Optional[float] = Field(None, ge=0, le=10, description="评分 0-10，支持一位小数（可选）")


# ------------------------------------------------------------------
# 端点
# ------------------------------------------------------------------

@router.post("/")
async def save_analysis(
    body: SaveAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
):
    """保存一条新的AI分析结果（每次保存为新版本）"""
    service = StockAiAnalysisService()
    try:
        result = await service.save_analysis(
            ts_code=body.ts_code,
            analysis_type=body.analysis_type,
            analysis_text=body.analysis_text,
            score=body.score,
            prompt_text=body.prompt_text,
            ai_provider=body.ai_provider,
            ai_model=body.ai_model,
            created_by=current_user.id,
        )
    except ValueError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    return ApiResponse.success(data=result, message="分析结果已保存").to_dict()


@router.get("/latest")
async def get_latest(
    ts_code: str = Query(..., description="股票代码，如 000001.SZ"),
    analysis_type: str = Query(..., description="分析类型，如 hot_money_view"),
    _: User = Depends(get_current_active_user),
):
    """获取指定股票+类型的最新一条分析结果"""
    service = StockAiAnalysisService()
    result = await service.get_latest(ts_code, analysis_type)
    if result is None:
        return ApiResponse.not_found(message="暂无分析记录").to_dict()
    return ApiResponse.success(data=result).to_dict()


@router.get("/history")
async def get_history(
    ts_code: str = Query(..., description="股票代码，如 000001.SZ"),
    analysis_type: str = Query(..., description="分析类型，如 hot_money_view"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_active_user),
):
    """获取指定股票+类型的所有版本历史（分页，最新在前）"""
    service = StockAiAnalysisService()
    result = await service.get_history(ts_code, analysis_type, limit, offset)
    return ApiResponse.success(data=result).to_dict()


@router.put("/{record_id}")
async def update_analysis(
    record_id: int,
    body: UpdateAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
):
    """修改已保存的分析记录（仅限记录创建者）"""
    service = StockAiAnalysisService()
    try:
        result = await service.update_analysis(
            record_id=record_id,
            analysis_text=body.analysis_text,
            score=body.score,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except PermissionError as e:
        return ApiResponse.forbidden(message=str(e)).to_dict()
    if result is None:
        return ApiResponse.not_found(message="记录不存在").to_dict()
    return ApiResponse.success(data=result, message="修改成功").to_dict()


@router.delete("/{record_id}")
async def delete_analysis(
    record_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """删除已保存的分析记录（仅限记录创建者）"""
    service = StockAiAnalysisService()
    try:
        deleted = await service.delete_analysis(
            record_id=record_id,
            current_user_id=current_user.id,
        )
    except PermissionError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    if not deleted:
        return ApiResponse.not_found(message="记录不存在").to_dict()
    return ApiResponse.success(message="删除成功").to_dict()
