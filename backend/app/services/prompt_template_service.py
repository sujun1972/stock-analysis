"""
提示词模板管理服务

提供提示词模板的CRUD操作、渲染、统计等功能

作者: Backend Team
创建时间: 2026-03-11
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from loguru import logger

from app.models.llm_prompt_template import LLMPromptTemplate, LLMPromptTemplateHistory
from app.models.llm_call_log import LLMCallLog
from app.schemas.llm_prompt_template import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateVersionCreate,
    PromptTemplateResponse,
    PromptTemplateStatistics,
    PromptRenderError
)
from app.services.prompt_renderer import get_prompt_renderer
from app.core.exceptions import DataNotFoundError, ValidationError


class PromptTemplateService:
    """提示词模板服务"""

    def __init__(self):
        self.renderer = get_prompt_renderer()

    def get_template_by_id(self, db: Session, template_id: int) -> Optional[LLMPromptTemplate]:
        """根据ID获取模板"""
        template = db.query(LLMPromptTemplate).filter(
            LLMPromptTemplate.id == template_id
        ).first()

        if not template:
            raise DataNotFoundError(f"模板不存在 (ID: {template_id})")

        return template

    def get_template_by_key(
        self,
        db: Session,
        template_key: str,
        business_type: str = None
    ) -> Optional[LLMPromptTemplate]:
        """根据template_key获取模板"""
        query = db.query(LLMPromptTemplate).filter(
            LLMPromptTemplate.template_key == template_key
        )

        if business_type:
            query = query.filter(LLMPromptTemplate.business_type == business_type)

        return query.first()

    def get_active_template(
        self,
        db: Session,
        business_type: str,
        template_key: str = None
    ) -> Optional[LLMPromptTemplate]:
        """
        获取启用的模板（默认或指定）

        Args:
            db: 数据库会话
            business_type: 业务类型
            template_key: 模板key（可选，不指定则返回默认模板）

        Returns:
            模板对象，如果不存在则返回None
        """
        query = db.query(LLMPromptTemplate).filter(
            LLMPromptTemplate.business_type == business_type,
            LLMPromptTemplate.is_active == True
        )

        if template_key:
            query = query.filter(LLMPromptTemplate.template_key == template_key)
        else:
            # 获取默认模板
            query = query.filter(LLMPromptTemplate.is_default == True)

        template = query.first()

        if not template:
            if template_key:
                raise DataNotFoundError(
                    f"未找到启用的模板 (business_type={business_type}, key={template_key})"
                )
            else:
                raise DataNotFoundError(
                    f"未找到默认模板 (business_type={business_type})"
                )

        return template

    def list_templates(
        self,
        db: Session,
        business_type: str = None,
        is_active: bool = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[LLMPromptTemplate], int]:
        """
        获取模板列表

        Returns:
            (模板列表, 总数)
        """
        query = db.query(LLMPromptTemplate)

        if business_type:
            query = query.filter(LLMPromptTemplate.business_type == business_type)

        if is_active is not None:
            query = query.filter(LLMPromptTemplate.is_active == is_active)

        total = query.count()

        templates = query.order_by(
            desc(LLMPromptTemplate.is_default),
            desc(LLMPromptTemplate.created_at)
        ).offset(skip).limit(limit).all()

        return templates, total

    def create_template(
        self,
        db: Session,
        template_data: PromptTemplateCreate
    ) -> LLMPromptTemplate:
        """
        创建新模板

        Args:
            db: 数据库会话
            template_data: 模板数据

        Returns:
            创建的模板对象
        """
        # 1. 检查template_key是否已存在
        existing = self.get_template_by_key(db, template_data.template_key)
        if existing:
            raise ValidationError(f"模板key已存在: {template_data.template_key}")

        # 2. 验证模板语法
        is_valid, error_msg = self.renderer.validate_template(template_data.user_prompt_template)
        if not is_valid:
            raise ValidationError(f"模板语法错误: {error_msg}")

        if template_data.system_prompt:
            is_valid, error_msg = self.renderer.validate_template(template_data.system_prompt)
            if not is_valid:
                raise ValidationError(f"系统提示词语法错误: {error_msg}")

        # 3. 创建模板
        template = LLMPromptTemplate(
            **template_data.model_dump(exclude={'created_by'})
        )
        template.created_by = template_data.created_by
        template.updated_by = template_data.created_by

        # 4. 如果设置为默认，将同业务类型的其他模板设为非默认（触发器会自动处理）
        db.add(template)
        db.commit()
        db.refresh(template)

        logger.info(
            f"创建提示词模板成功: {template.template_name} "
            f"(key={template.template_key}, version={template.version})"
        )

        return template

    def update_template(
        self,
        db: Session,
        template_id: int,
        updates: PromptTemplateUpdate
    ) -> LLMPromptTemplate:
        """
        更新模板

        Args:
            db: 数据库会话
            template_id: 模板ID
            updates: 更新数据

        Returns:
            更新后的模板对象
        """
        template = self.get_template_by_id(db, template_id)

        # 验证新的模板内容
        if updates.user_prompt_template:
            is_valid, error_msg = self.renderer.validate_template(updates.user_prompt_template)
            if not is_valid:
                raise ValidationError(f"模板语法错误: {error_msg}")

        if updates.system_prompt:
            is_valid, error_msg = self.renderer.validate_template(updates.system_prompt)
            if not is_valid:
                raise ValidationError(f"系统提示词语法错误: {error_msg}")

        # 更新字段
        update_data = updates.model_dump(exclude_unset=True, exclude={'updated_by'})
        for field, value in update_data.items():
            setattr(template, field, value)

        template.updated_by = updates.updated_by

        db.commit()
        db.refresh(template)

        logger.info(f"更新提示词模板成功: {template.template_name} (ID={template_id})")

        return template

    def create_version(
        self,
        db: Session,
        parent_id: int,
        version_data: PromptTemplateVersionCreate
    ) -> LLMPromptTemplate:
        """
        基于现有模板创建新版本

        Args:
            db: 数据库会话
            parent_id: 父模板ID
            version_data: 版本数据

        Returns:
            新版本模板对象
        """
        parent_template = self.get_template_by_id(db, parent_id)

        # 创建新模板（复制父模板）
        new_template_data = {
            'business_type': parent_template.business_type,
            'template_name': version_data.template_name or parent_template.template_name,
            'template_key': parent_template.template_key,  # 使用相同的key
            'system_prompt': version_data.system_prompt or parent_template.system_prompt,
            'user_prompt_template': version_data.user_prompt_template or parent_template.user_prompt_template,
            'output_format': version_data.output_format or parent_template.output_format,
            'required_variables': version_data.required_variables or parent_template.required_variables,
            'optional_variables': version_data.optional_variables or parent_template.optional_variables,
            'version': version_data.version,
            'parent_template_id': parent_id,
            'is_active': False,  # 新版本默认不启用
            'is_default': False,
            'recommended_provider': version_data.recommended_provider or parent_template.recommended_provider,
            'recommended_model': version_data.recommended_model or parent_template.recommended_model,
            'recommended_temperature': version_data.recommended_temperature or parent_template.recommended_temperature,
            'recommended_max_tokens': version_data.recommended_max_tokens or parent_template.recommended_max_tokens,
            'description': version_data.description or parent_template.description,
            'changelog': version_data.changelog,
            'tags': version_data.tags or parent_template.tags,
            'created_by': version_data.created_by
        }

        # 注意：不能使用create_template，因为template_key已存在
        # 验证模板语法
        is_valid, error_msg = self.renderer.validate_template(new_template_data['user_prompt_template'])
        if not is_valid:
            raise ValidationError(f"模板语法错误: {error_msg}")

        new_template = LLMPromptTemplate(**new_template_data)
        new_template.updated_by = version_data.created_by

        db.add(new_template)
        db.commit()
        db.refresh(new_template)

        logger.info(
            f"创建模板新版本成功: {new_template.template_name} "
            f"(version={new_template.version}, parent_id={parent_id})"
        )

        return new_template

    def activate_template(
        self,
        db: Session,
        template_id: int,
        set_as_default: bool = False
    ) -> LLMPromptTemplate:
        """
        激活模板

        Args:
            db: 数据库会话
            template_id: 模板ID
            set_as_default: 是否设为默认模板

        Returns:
            激活的模板对象
        """
        template = self.get_template_by_id(db, template_id)

        template.is_active = True
        if set_as_default:
            template.is_default = True

        db.commit()
        db.refresh(template)

        logger.info(f"激活提示词模板: {template.template_name} (ID={template_id})")

        return template

    def deactivate_template(self, db: Session, template_id: int) -> LLMPromptTemplate:
        """停用模板"""
        template = self.get_template_by_id(db, template_id)

        if template.is_default:
            raise ValidationError("无法停用默认模板，请先设置其他模板为默认")

        template.is_active = False

        db.commit()
        db.refresh(template)

        logger.info(f"停用提示词模板: {template.template_name} (ID={template_id})")

        return template

    def delete_template(self, db: Session, template_id: int) -> None:
        """删除模板"""
        template = self.get_template_by_id(db, template_id)

        if template.is_default:
            raise ValidationError("无法删除默认模板")

        # 检查是否有调用日志使用此模板
        usage_count = db.query(LLMCallLog).filter(
            LLMCallLog.prompt_template_id == template_id
        ).count()

        if usage_count > 0:
            raise ValidationError(
                f"无法删除模板，已有{usage_count}条调用日志使用此模板。建议停用而非删除。"
            )

        db.delete(template)
        db.commit()

        logger.info(f"删除提示词模板: {template.template_name} (ID={template_id})")

    def render_template(
        self,
        db: Session,
        template_id: int,
        variables: Dict[str, Any]
    ) -> Tuple[Optional[str], str]:
        """
        渲染模板

        Args:
            db: 数据库会话
            template_id: 模板ID
            variables: 变量字典

        Returns:
            (system_prompt, user_prompt)

        Raises:
            PromptRenderError: 渲染失败
        """
        template = self.get_template_by_id(db, template_id)

        # 提取必填变量列表
        required_vars = list(template.required_variables.keys()) if template.required_variables else []

        # 渲染系统提示词
        system_prompt = None
        if template.system_prompt:
            system_prompt = self.renderer.render(
                template.system_prompt,
                variables,
                required_vars=[]  # 系统提示词通常不需要变量
            )

        # 渲染用户提示词
        user_prompt = self.renderer.render(
            template.user_prompt_template,
            variables,
            required_vars=required_vars
        )

        return system_prompt, user_prompt

    def preview_render(
        self,
        db: Session,
        template_id: int,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        预览渲染结果（包含诊断信息）

        Returns:
            包含渲染结果和诊断信息的字典
        """
        template = self.get_template_by_id(db, template_id)

        required_vars = list(template.required_variables.keys()) if template.required_variables else []

        # 预览用户提示词
        user_result = self.renderer.preview_render(
            template.user_prompt_template,
            variables,
            required_vars=required_vars
        )

        # 预览系统提示词
        system_result = None
        if template.system_prompt:
            system_result = self.renderer.preview_render(
                template.system_prompt,
                variables,
                required_vars=[]
            )

        return {
            "system_prompt": system_result.get("rendered") if system_result and system_result.get("success") else template.system_prompt,
            "user_prompt": user_result.get("rendered") if user_result.get("success") else "",
            "full_prompt": (
                f"{system_result.get('rendered', '')}\n\n{user_result.get('rendered', '')}"
                if system_result and system_result.get("success") and user_result.get("success")
                else user_result.get("rendered", "")
            ),
            "missing_variables": user_result.get("missing_variables", []),
            "extra_variables": user_result.get("extra_variables", []),
            "success": user_result.get("success", False),
            "error": user_result.get("error", "")
        }

    def get_template_statistics(
        self,
        db: Session,
        template_id: int
    ) -> PromptTemplateStatistics:
        """
        获取模板的性能统计（从llm_call_logs聚合）

        Returns:
            统计信息对象
        """
        template = self.get_template_by_id(db, template_id)

        # 从llm_call_logs聚合统计数据
        stats = db.query(
            func.count(LLMCallLog.id).label('total_calls'),
            func.count(func.nullif(LLMCallLog.status == 'success', False)).label('successful_calls'),
            func.count(func.nullif(LLMCallLog.status == 'failed', False)).label('failed_calls'),
            func.avg(LLMCallLog.tokens_total).label('avg_tokens'),
            func.avg(LLMCallLog.duration_ms).label('avg_duration_ms'),
            func.sum(LLMCallLog.cost_estimate).label('total_cost'),
            func.max(LLMCallLog.created_at).label('last_used_at')
        ).filter(
            LLMCallLog.prompt_template_id == template_id
        ).first()

        total_calls = stats.total_calls or 0
        successful_calls = stats.successful_calls or 0

        success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0.0

        return PromptTemplateStatistics(
            template_id=template.id,
            template_name=template.template_name,
            template_key=template.template_key,
            version=template.version,
            total_calls=total_calls,
            successful_calls=successful_calls,
            failed_calls=stats.failed_calls or 0,
            success_rate=round(success_rate, 2),
            avg_tokens_used=round(stats.avg_tokens) if stats.avg_tokens else None,
            avg_duration_sec=round(stats.avg_duration_ms / 1000, 2) if stats.avg_duration_ms else None,
            total_cost=float(stats.total_cost) if stats.total_cost else None,
            last_used_at=stats.last_used_at,
            created_at=template.created_at
        )

    def get_template_history(
        self,
        db: Session,
        template_id: int,
        limit: int = 50
    ) -> List[LLMPromptTemplateHistory]:
        """获取模板的修改历史"""
        return db.query(LLMPromptTemplateHistory).filter(
            LLMPromptTemplateHistory.template_id == template_id
        ).order_by(
            desc(LLMPromptTemplateHistory.changed_at)
        ).limit(limit).all()

    def update_template_statistics(self, db: Session) -> None:
        """
        定时任务：更新所有模板的统计字段

        从llm_call_logs聚合最新的统计数据并更新到模板表
        """
        templates = db.query(LLMPromptTemplate).all()

        for template in templates:
            try:
                stats = db.query(
                    func.avg(LLMCallLog.tokens_total).label('avg_tokens'),
                    func.avg(LLMCallLog.duration_ms).label('avg_duration_ms'),
                    func.count(LLMCallLog.id).label('total_calls'),
                    func.count(func.nullif(LLMCallLog.status == 'success', False)).label('successful_calls')
                ).filter(
                    LLMCallLog.prompt_template_id == template.id
                ).first()

                if stats and stats.total_calls and stats.total_calls > 0:
                    template.avg_tokens_used = round(stats.avg_tokens) if stats.avg_tokens else None
                    template.avg_generation_time = round(stats.avg_duration_ms / 1000, 2) if stats.avg_duration_ms else None
                    template.usage_count = stats.total_calls
                    template.success_rate = round(
                        (stats.successful_calls / stats.total_calls * 100), 2
                    ) if stats.total_calls > 0 else 0.0

            except Exception as e:
                logger.error(f"更新模板统计失败 (ID={template.id}): {e}")
                continue

        db.commit()
        logger.info(f"更新了 {len(templates)} 个模板的统计信息")


# 全局服务实例
_prompt_template_service = None


def get_prompt_template_service() -> PromptTemplateService:
    """获取提示词模板服务单例"""
    global _prompt_template_service
    if _prompt_template_service is None:
        _prompt_template_service = PromptTemplateService()
    return _prompt_template_service
