"""
股票AI分析结果 API 端点
支持保存分析结果（游资观点等多种类型）、查询最新版本、浏览历史版本
"""

import json
import re
import time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from loguru import logger
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.api_response import ApiResponse
from app.models.user import User
from app.services.stock_ai_analysis_service import StockAiAnalysisService
from sqlalchemy.orm import Session


def _extract_json_and_score(ai_text: str) -> tuple[str, Optional[float]]:
    """
    从 AI 返回文本中：
    1. 去掉 ```json ... ``` 代码块标识，只保留纯 JSON 内容
    2. 尝试从多个候选路径提取评分（按优先级依次尝试）

    候选评分路径（.分隔的 key 路径）：
      - final_score.score        游资观点
      - comprehensive_score      中线专家、价值守望者、CIO 顶级 key
      - score                    CIO 简单结构

    返回 (cleaned_text, score_or_None)
    """
    # 去掉 markdown 代码块标识
    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', ai_text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned.strip(), flags=re.MULTILINE)
    cleaned = cleaned.strip()

    _SCORE_PATHS = [
        ["final_score", "score"],   # 游资观点
        ["comprehensive_score"],    # 中线专家 / 价值守望者 / CIO
        ["score"],                  # CIO 简单结构兜底
    ]

    score: Optional[float] = None
    try:
        data = json.loads(cleaned)
        for path in _SCORE_PATHS:
            node = data
            for key in path:
                if not isinstance(node, dict):
                    node = None
                    break
                node = node.get(key)
            if node is not None:
                try:
                    candidate = float(node)
                    if 0 <= candidate <= 10:
                        score = candidate
                        break
                except (TypeError, ValueError):
                    pass
    except Exception:
        pass

    return cleaned, score


# 需要走 JSON 清洗 + 评分提取的分析类型集合
_JSON_ANALYSIS_TYPES = {
    "hot_money_view",
    "midline_industry_expert",
    "longterm_value_watcher",
    "cio_directive",
}

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
    trade_date: Optional[str] = Field(None, description="交易日，YYYYMMDD 格式")


class UpdateAnalysisRequest(BaseModel):
    analysis_text: str = Field(..., min_length=1, description="修改后的AI分析结果文本")
    score: Optional[float] = Field(None, ge=0, le=10, description="评分 0-10，支持一位小数（可选）")


class GenerateAnalysisRequest(BaseModel):
    ts_code: str = Field(..., description="股票代码，如 000001.SZ")
    stock_name: str = Field(..., description="股票名称")
    stock_code: str = Field(..., description="股票纯代码，如 000001")
    analysis_type: str = Field(..., description="分析类型，hot_money_view 或 stock_data_collection")
    template_key: str = Field(..., description="提示词模板 key，如 top_speculative_investor_v1")


# ------------------------------------------------------------------
# 端点
# ------------------------------------------------------------------

@router.get("/list")
async def list_analyses(
    ts_code: Optional[str] = Query(None, description="股票代码过滤"),
    analysis_type: Optional[str] = Query(None, description="分析类型过滤"),
    ai_provider: Optional[str] = Query(None, description="AI提供商过滤"),
    trade_date: Optional[str] = Query(None, description="交易日过滤，YYYYMMDD"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向: asc/desc"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    _: User = Depends(get_current_active_user),
):
    """查询所有股票AI分析记录（支持过滤、排序、分页）"""
    service = StockAiAnalysisService()
    result = await service.list_all(
        ts_code=ts_code,
        analysis_type=analysis_type,
        ai_provider=ai_provider,
        trade_date=trade_date,
        sort_by=sort_by or "created_at",
        sort_order=sort_order or "desc",
        limit=limit,
        offset=offset,
    )
    return ApiResponse.success(data=result).to_dict()


@router.post("/generate")
async def generate_analysis(
    body: GenerateAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """调用后端 AI 服务生成个股分析并自动保存，返回生成的记录。

    提示词通过 build_stock_prompt() 构建，与前端展示的提示词完全一致。
    """
    from app.api.endpoints.prompt_templates import build_stock_prompt
    from app.services.ai_service import AIStrategyService

    # 1. 构建提示词（生成分析时允许自动触发数据收集）
    try:
        prompt_data = await build_stock_prompt(
            template_key=body.template_key,
            stock_name=body.stock_name,
            stock_code=body.stock_code,
            ts_code=body.ts_code,
            created_by=current_user.id,
            db=db,
            allow_generate_data_collection=True,
        )
    except ValueError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        logger.error(f"[generate_analysis] 构建提示词失败: {e}", exc_info=True)
        return ApiResponse.error(message=f"构建提示词失败: {e}", code=500).to_dict()

    # system_prompt + user_prompt 合并为单条 user 消息（与其他 AI 调用路径一致）
    system_prompt = prompt_data["system_prompt"]
    user_prompt = prompt_data["user_prompt"]
    full_prompt = f"{system_prompt}\n\n{user_prompt}".strip() if system_prompt else user_prompt

    # 2. 获取 AI 提供商配置，用模板推荐参数覆盖 temperature / max_tokens
    ai_service = AIStrategyService()
    provider_name = prompt_data["recommended_provider"]
    provider_config = ai_service.get_provider_config(provider_name)
    provider_config["temperature"] = prompt_data["recommended_temperature"]
    provider_config["max_tokens"] = prompt_data["recommended_max_tokens"]

    # 3. 调用 AI 生成
    try:
        client = ai_service.create_client(provider_name, provider_config)
        start_time = time.time()
        ai_text, tokens_used = await client.generate_strategy(full_prompt)
        generation_time = time.time() - start_time
        logger.info(
            f"[generate_analysis] {body.ts_code} {body.analysis_type} "
            f"生成完成: {len(ai_text)}字 / {tokens_used} tokens / {generation_time:.2f}s"
        )
    except Exception as e:
        logger.error(f"[generate_analysis] AI 调用失败: {e}", exc_info=True)
        return ApiResponse.error(message=f"AI 调用失败: {e}", code=500).to_dict()

    # 4. 清理 JSON 代码块标识并提取评分（对所有 JSON 格式分析类型）
    if body.analysis_type in _JSON_ANALYSIS_TYPES:
        ai_text, extracted_score = _extract_json_and_score(ai_text)
    else:
        extracted_score = None

    # 5. 保存分析结果（版本自动递增）
    #    trade_date 来自数据采集记录，确保分析结果与采集数据对应同一交易日
    trade_date = prompt_data.get("trade_date")
    try:
        result = await StockAiAnalysisService().save_analysis(
            ts_code=body.ts_code,
            analysis_type=body.analysis_type,
            analysis_text=ai_text,
            score=extracted_score,
            prompt_text=full_prompt,
            ai_provider=provider_name,
            ai_model=provider_config.get("model_name"),
            created_by=current_user.id,
            trade_date=trade_date,
        )
    except ValueError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()

    return ApiResponse.success(
        data={
            **result,
            "analysis_text": ai_text,
            "score": extracted_score,
            "tokens_used": tokens_used,
            "generation_time": round(generation_time, 2),
        },
        message="AI 分析生成并保存成功",
    ).to_dict()


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
            trade_date=body.trade_date,
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
