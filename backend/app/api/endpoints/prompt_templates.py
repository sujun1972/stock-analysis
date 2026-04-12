"""
提示词模板管理API接口

作者: Backend Team
创建时间: 2026-03-11
"""

import asyncio
import re
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.llm_prompt_template import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptTemplateListResponse,
    PromptTemplateVersionCreate,
    PromptTemplatePreviewRequest,
    PromptTemplatePreviewResponse,
    PromptTemplateStatistics,
    PromptTemplateHistoryResponse,
    BusinessTypeEnum
)
from app.services.prompt_template_service import get_prompt_template_service
from app.core.exceptions import DataNotFoundError, ValidationError
from app.core.dependencies import require_admin, get_current_active_user
from app.models.user import User
from app.models.api_response import ApiResponse

router = APIRouter()
service = get_prompt_template_service()


@router.get("/")
def list_templates(
    business_type: Optional[str] = Query(None, description="业务类型"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """获取提示词模板列表"""
    try:
        templates, total = service.list_templates(
            db,
            business_type=business_type,
            is_active=is_active,
            skip=skip,
            limit=limit
        )
        return ApiResponse.success(
            data={
                "total": total,
                "items": [PromptTemplateResponse.from_orm(t).model_dump() for t in templates]
            },
            message="获取提示词模板列表成功"
        ).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.get("/{template_id}")
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """获取模板详情"""
    try:
        template = service.get_template_by_id(db, template_id)
        return ApiResponse.success(
            data=PromptTemplateResponse.from_orm(template).model_dump(),
            message="获取模板详情成功"
        ).to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.post("/", status_code=201)
def create_template(
    template_data: PromptTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """创建新模板"""
    try:
        template = service.create_template(db, template_data)
        return ApiResponse.created(
            data=PromptTemplateResponse.from_orm(template).model_dump(),
            message="创建模板成功"
        ).to_dict()
    except ValidationError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.put("/{template_id}")
def update_template(
    template_id: int,
    updates: PromptTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """更新模板"""
    try:
        template = service.update_template(db, template_id, updates)
        return ApiResponse.success(
            data=PromptTemplateResponse.from_orm(template).model_dump(),
            message="更新模板成功"
        ).to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except ValidationError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.post("/{template_id}/versions", status_code=201)
def create_version(
    template_id: int,
    version_data: PromptTemplateVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """基于现有模板创建新版本"""
    try:
        template = service.create_version(db, template_id, version_data)
        return ApiResponse.created(
            data=PromptTemplateResponse.from_orm(template).model_dump(),
            message="创建新版本成功"
        ).to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except ValidationError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.post("/{template_id}/activate")
def activate_template(
    template_id: int,
    set_as_default: bool = Query(False, description="是否设为默认模板"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """激活模板"""
    try:
        template = service.activate_template(db, template_id, set_as_default)
        message = "已激活并设为默认模板" if set_as_default else "激活模板成功"
        return ApiResponse.success(
            data=PromptTemplateResponse.from_orm(template).model_dump(),
            message=message
        ).to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except ValidationError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.post("/{template_id}/deactivate")
def deactivate_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """停用模板"""
    try:
        template = service.deactivate_template(db, template_id)
        return ApiResponse.success(
            data=PromptTemplateResponse.from_orm(template).model_dump(),
            message="停用模板成功"
        ).to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except ValidationError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """删除模板"""
    try:
        service.delete_template(db, template_id)
        return ApiResponse.success(message="删除模板成功").to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except ValidationError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.post("/{template_id}/preview")
def preview_template(
    template_id: int,
    preview_request: PromptTemplatePreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """预览渲染后的提示词"""
    try:
        result = service.preview_render(
            db,
            template_id,
            preview_request.variables
        )
        return ApiResponse.success(
            data=result,
            message="预览渲染成功"
        ).to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.get("/{template_id}/statistics")
def get_template_statistics(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """获取模板的性能统计"""
    try:
        stats = service.get_template_statistics(db, template_id)
        return ApiResponse.success(
            data=stats,
            message="获取统计信息成功"
        ).to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.get("/{template_id}/history")
def get_template_history(
    template_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """获取模板的修改历史"""
    try:
        history = service.get_template_history(db, template_id, limit)
        return ApiResponse.success(
            data=[PromptTemplateHistoryResponse.from_orm(h).model_dump() for h in history],
            message="获取修改历史成功"
        ).to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.get("/business-types/all")
def get_business_types(
    current_user: User = Depends(require_admin)
):
    """获取所有业务类型"""
    return ApiResponse.success(
        data=BusinessTypeEnum.all(),
        message="获取业务类型列表成功"
    ).to_dict()


# ── by-key 路由（通过 template_key 操作，供前端稳定引用）──────────────────


def _render_template(text: str, variables: dict) -> str:
    """将 {{ var }} 占位符替换为 variables 中对应的值，未匹配的占位符保留原样。"""
    def replacer(m: re.Match) -> str:
        key = m.group(1).strip()
        return variables.get(key, m.group(0))
    return re.sub(r'\{\{\s*(\w+)\s*\}\}', replacer, text)


@router.get("/by-key/{template_key}")
async def get_template_by_key(
    template_key: str,
    stock_name: Optional[str] = Query(None, description="股票名称，用于替换模板中的占位符"),
    stock_code: Optional[str] = Query(None, description="股票代码，用于替换模板中的占位符"),
    ts_code: Optional[str] = Query(None, description="ts_code（如 000703.SZ），游资观点模板自动填充数据时使用"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """通过 template_key 获取模板详情。

    可选传入 stock_name / stock_code，后端会自动替换模板中的变量占位符，
    包括当前日期、最近交易日、以及股票名称/代码。

    对于 top_speculative_investor_v1 模板，还会自动填充 {{ stock_data_collection }}：
    检查当天是否已有该股的数据收集分析，若无则自动生成并保存，再填入模板。
    """
    try:
        template = service.get_template_by_key(db, template_key)
        if not template:
            return ApiResponse.not_found(message=f"模板不存在 (key={template_key})").to_dict()

        data = PromptTemplateResponse.from_orm(template).model_dump()

        if stock_name or stock_code:
            prompt_data = await build_stock_prompt(
                template_key=template_key,
                stock_name=stock_name,
                stock_code=stock_code,
                ts_code=ts_code,
                created_by=current_user.id,
                db=db,
            )
            data["system_prompt"] = prompt_data["system_prompt"]
            data["user_prompt_template"] = prompt_data["user_prompt"]

        return ApiResponse.success(data=data, message="获取模板详情成功").to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


async def build_stock_prompt(
    template_key: str,
    stock_name: Optional[str],
    stock_code: Optional[str],
    ts_code: Optional[str],
    created_by: Optional[int],
    db,
) -> dict:
    """
    构建股票分析完整提示词（供 get_template_by_key 端点和 generate 端点共用）。

    返回：
    {
      "system_prompt": str,
      "user_prompt": str,
      "recommended_provider": str,
      "recommended_model": str,
      "recommended_temperature": float,
      "recommended_max_tokens": int,
    }
    """
    template = service.get_template_by_key(db, template_key)
    if not template:
        raise ValueError(f"模板不存在 (key={template_key})")

    data = PromptTemplateResponse.from_orm(template).model_dump()

    variables: dict = {}

    if stock_name or stock_code:
        from app.repositories.trading_calendar_repository import TradingCalendarRepository
        calendar_repo = TradingCalendarRepository()
        latest_trade_day_raw = await asyncio.to_thread(calendar_repo.get_latest_trading_day)
        if latest_trade_day_raw:
            dt = datetime.strptime(latest_trade_day_raw, "%Y%m%d")
            latest_trade_day = f"{dt.year}年{dt.month}月{dt.day}日"
        else:
            latest_trade_day = "未知"

        today = datetime.now()
        today_str = f"{today.year}年{today.month}月{today.day}日"
        stock_name_and_code = f"{stock_name or ''} {stock_code or ''}".strip()

        variables = {
            "current_date": today_str,
            "latest_trade_date": latest_trade_day,
            "stock_name_and_code": stock_name_and_code,
        }

        if (
            template_key == "top_speculative_investor_v1"
            and ts_code
            and "{{ stock_data_collection }}" in (data.get("user_prompt_template") or "")
        ):
            stock_data_text = await _get_or_generate_stock_data_collection(
                ts_code=ts_code,
                stock_name=stock_name or stock_code or "",
                created_by=created_by,
            )
            variables["stock_data_collection"] = stock_data_text

    system_prompt = data.get("system_prompt") or ""
    user_prompt = data.get("user_prompt_template") or ""

    if variables:
        system_prompt = _render_template(system_prompt, variables)
        user_prompt = _render_template(user_prompt, variables)

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "recommended_provider": data.get("recommended_provider") or "deepseek",
        "recommended_model": data.get("recommended_model") or "deepseek-chat",
        "recommended_temperature": data.get("recommended_temperature") or 0.4,
        "recommended_max_tokens": data.get("recommended_max_tokens") or 3000,
    }


async def _get_or_generate_stock_data_collection(
    ts_code: str,
    stock_name: str,
    created_by: Optional[int],
) -> str:
    """
    查询今天是否已有该股的 stock_data_collection 分析记录：
    - 有 → 直接返回 analysis_text
    - 无 → 调用 StockDataCollectionService 生成并保存，再返回
    """
    from app.repositories.stock_ai_analysis_repository import StockAiAnalysisRepository
    from app.services.stock_data_collection_service import StockDataCollectionService
    from app.services.stock_ai_analysis_service import StockAiAnalysisService

    repo = StockAiAnalysisRepository()
    existing = await asyncio.to_thread(repo.get_today, ts_code, "stock_data_collection")
    if existing:
        logger.info(f"[游资模板] 使用今日已有数据收集记录: {ts_code} (id={existing['id']})")
        return existing["analysis_text"]

    logger.info(f"[游资模板] 今日无数据收集记录，自动生成: {ts_code}")
    try:
        collection_service = StockDataCollectionService()
        text = await collection_service.collect_and_format(ts_code, stock_name)

        ai_analysis_service = StockAiAnalysisService()
        await ai_analysis_service.save_analysis(
            ts_code=ts_code,
            analysis_type="stock_data_collection",
            analysis_text=text,
            score=None,
            prompt_text=None,
            ai_provider=None,
            ai_model=None,
            created_by=created_by,
        )
        logger.info(f"[游资模板] 数据收集已自动保存: {ts_code}")
        return text
    except Exception as e:
        logger.error(f"[游资模板] 自动生成数据收集失败: {ts_code}, 错误: {e}")
        return f"（数据自动收集失败，请手动点击生成分析按钮获取：{e}）"


@router.put("/by-key/{template_key}")
def update_template_by_key(
    template_key: str,
    updates: PromptTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """通过 template_key 更新模板"""
    try:
        template = service.get_template_by_key(db, template_key)
        if not template:
            return ApiResponse.not_found(message=f"模板不存在 (key={template_key})").to_dict()
        template = service.update_template(db, template.id, updates)
        return ApiResponse.success(
            data=PromptTemplateResponse.from_orm(template).model_dump(),
            message="更新模板成功"
        ).to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except ValidationError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.delete("/by-key/{template_key}")
def delete_template_by_key(
    template_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """通过 template_key 删除模板"""
    try:
        template = service.get_template_by_key(db, template_key)
        if not template:
            return ApiResponse.not_found(message=f"模板不存在 (key={template_key})").to_dict()
        service.delete_template(db, template.id)
        return ApiResponse.success(message="删除模板成功").to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except ValidationError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.post("/by-key/{template_key}/activate")
def activate_template_by_key(
    template_key: str,
    set_as_default: bool = Query(False, description="是否设为默认模板"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """通过 template_key 激活模板"""
    try:
        template = service.get_template_by_key(db, template_key)
        if not template:
            return ApiResponse.not_found(message=f"模板不存在 (key={template_key})").to_dict()
        template = service.activate_template(db, template.id, set_as_default)
        message = "已激活并设为默认模板" if set_as_default else "激活模板成功"
        return ApiResponse.success(
            data=PromptTemplateResponse.from_orm(template).model_dump(),
            message=message
        ).to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except ValidationError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.post("/by-key/{template_key}/deactivate")
def deactivate_template_by_key(
    template_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """通过 template_key 停用模板"""
    try:
        template = service.get_template_by_key(db, template_key)
        if not template:
            return ApiResponse.not_found(message=f"模板不存在 (key={template_key})").to_dict()
        template = service.deactivate_template(db, template.id)
        return ApiResponse.success(
            data=PromptTemplateResponse.from_orm(template).model_dump(),
            message="停用模板成功"
        ).to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except ValidationError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.post("/by-key/{template_key}/versions", status_code=201)
def create_version_by_key(
    template_key: str,
    version_data: PromptTemplateVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """通过 template_key 创建新版本"""
    try:
        template = service.get_template_by_key(db, template_key)
        if not template:
            return ApiResponse.not_found(message=f"模板不存在 (key={template_key})").to_dict()
        new_template = service.create_version(db, template.id, version_data)
        return ApiResponse.created(
            data=PromptTemplateResponse.from_orm(new_template).model_dump(),
            message="创建新版本成功"
        ).to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except ValidationError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.post("/by-key/{template_key}/preview")
def preview_template_by_key(
    template_key: str,
    preview_request: PromptTemplatePreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """通过 template_key 预览渲染后的提示词"""
    try:
        template = service.get_template_by_key(db, template_key)
        if not template:
            return ApiResponse.not_found(message=f"模板不存在 (key={template_key})").to_dict()
        result = service.preview_render(db, template.id, preview_request.variables)
        return ApiResponse.success(data=result, message="预览渲染成功").to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.get("/by-key/{template_key}/statistics")
def get_template_statistics_by_key(
    template_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """通过 template_key 获取模板的性能统计"""
    try:
        template = service.get_template_by_key(db, template_key)
        if not template:
            return ApiResponse.not_found(message=f"模板不存在 (key={template_key})").to_dict()
        stats = service.get_template_statistics(db, template.id)
        return ApiResponse.success(data=stats, message="获取统计信息成功").to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


@router.get("/by-key/{template_key}/history")
def get_template_history_by_key(
    template_key: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """通过 template_key 获取模板的修改历史"""
    try:
        template = service.get_template_by_key(db, template_key)
        if not template:
            return ApiResponse.not_found(message=f"模板不存在 (key={template_key})").to_dict()
        history = service.get_template_history(db, template.id, limit)
        return ApiResponse.success(
            data=[PromptTemplateHistoryResponse.from_orm(h).model_dump() for h in history],
            message="获取修改历史成功"
        ).to_dict()
    except DataNotFoundError as e:
        return ApiResponse.not_found(message=str(e)).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()
