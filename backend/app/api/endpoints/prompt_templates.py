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


@router.get("/by-key/{template_key}")
def get_template_by_key(
    template_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """通过 template_key 获取模板详情"""
    try:
        template = service.get_template_by_key(db, template_key)
        if not template:
            return ApiResponse.not_found(message=f"模板不存在 (key={template_key})").to_dict()
        return ApiResponse.success(
            data=PromptTemplateResponse.from_orm(template).model_dump(),
            message="获取模板详情成功"
        ).to_dict()
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500).to_dict()


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
