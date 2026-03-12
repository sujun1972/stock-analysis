"""
提示词模板管理API接口

作者: Backend Team
创建时间: 2026-03-11
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
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

router = APIRouter()
service = get_prompt_template_service()


@router.get("/", response_model=PromptTemplateListResponse)
def list_templates(
    business_type: Optional[str] = Query(None, description="业务类型"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
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
        return PromptTemplateListResponse(
            total=total,
            items=[PromptTemplateResponse.from_orm(t) for t in templates]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}", response_model=PromptTemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """获取模板详情"""
    try:
        template = service.get_template_by_id(db, template_id)
        return PromptTemplateResponse.from_orm(template)
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=PromptTemplateResponse, status_code=201)
def create_template(
    template_data: PromptTemplateCreate,
    db: Session = Depends(get_db)
):
    """创建新模板"""
    try:
        template = service.create_template(db, template_data)
        return PromptTemplateResponse.from_orm(template)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{template_id}", response_model=PromptTemplateResponse)
def update_template(
    template_id: int,
    updates: PromptTemplateUpdate,
    db: Session = Depends(get_db)
):
    """更新模板"""
    try:
        template = service.update_template(db, template_id, updates)
        return PromptTemplateResponse.from_orm(template)
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/versions", response_model=PromptTemplateResponse, status_code=201)
def create_version(
    template_id: int,
    version_data: PromptTemplateVersionCreate,
    db: Session = Depends(get_db)
):
    """基于现有模板创建新版本"""
    try:
        template = service.create_version(db, template_id, version_data)
        return PromptTemplateResponse.from_orm(template)
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/activate", response_model=PromptTemplateResponse)
def activate_template(
    template_id: int,
    set_as_default: bool = Query(False, description="是否设为默认模板"),
    db: Session = Depends(get_db)
):
    """激活模板"""
    try:
        template = service.activate_template(db, template_id, set_as_default)
        return PromptTemplateResponse.from_orm(template)
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/deactivate", response_model=PromptTemplateResponse)
def deactivate_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """停用模板"""
    try:
        template = service.deactivate_template(db, template_id)
        return PromptTemplateResponse.from_orm(template)
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """删除模板"""
    try:
        service.delete_template(db, template_id)
        return None
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/preview", response_model=PromptTemplatePreviewResponse)
def preview_template(
    template_id: int,
    preview_request: PromptTemplatePreviewRequest,
    db: Session = Depends(get_db)
):
    """预览渲染后的提示词"""
    try:
        result = service.preview_render(
            db,
            template_id,
            preview_request.variables
        )
        return PromptTemplatePreviewResponse(**result)
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}/statistics", response_model=PromptTemplateStatistics)
def get_template_statistics(
    template_id: int,
    db: Session = Depends(get_db)
):
    """获取模板的性能统计"""
    try:
        stats = service.get_template_statistics(db, template_id)
        return stats
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}/history", response_model=list[PromptTemplateHistoryResponse])
def get_template_history(
    template_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """获取模板的修改历史"""
    try:
        history = service.get_template_history(db, template_id, limit)
        return [PromptTemplateHistoryResponse.from_orm(h) for h in history]
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/business-types/all", response_model=list[str])
def get_business_types():
    """获取所有业务类型"""
    return BusinessTypeEnum.all()
