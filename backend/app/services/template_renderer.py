"""
通知模板渲染服务 - Jinja2 模板引擎

功能:
- 从数据库加载模板
- Jinja2 动态渲染
- 模板缓存机制
- 错误处理和降级
- 模板预览
"""
from typing import Dict, Any, Optional, List
from jinja2 import Environment, BaseLoader, TemplateNotFound, TemplateSyntaxError
from sqlalchemy.orm import Session
from loguru import logger
from functools import lru_cache
import re

from app.models.notification_template import NotificationTemplate


class DatabaseTemplateLoader(BaseLoader):
    """从数据库加载模板的 Jinja2 Loader"""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_source(self, environment, template_name):
        """
        加载模板源码

        Args:
            environment: Jinja2 Environment
            template_name: 模板名称

        Returns:
            (source, filename, uptodate_func)
        """
        template = self.db_session.query(NotificationTemplate).filter(
            NotificationTemplate.template_name == template_name,
            NotificationTemplate.is_active == True
        ).first()

        if not template:
            raise TemplateNotFound(template_name)

        # 返回模板源码
        source = template.content_template

        # 定义更新检查函数（始终重新加载）
        def uptodate():
            return False

        return source, None, uptodate


class TemplateRenderer:
    """模板渲染服务"""

    def __init__(self, db: Session):
        self.db = db
        self._env = None

    @property
    def env(self) -> Environment:
        """获取 Jinja2 Environment（懒加载）"""
        if self._env is None:
            loader = DatabaseTemplateLoader(self.db)
            self._env = Environment(
                loader=loader,
                autoescape=True,  # 自动转义（防止 XSS）
                trim_blocks=True,
                lstrip_blocks=True
            )

            # 注册自定义过滤器
            self._env.filters['nl2br'] = self._nl2br_filter
            self._env.filters['truncate_words'] = self._truncate_words_filter

        return self._env

    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any],
        fallback_content: Optional[str] = None
    ) -> str:
        """
        渲染模板

        Args:
            template_name: 模板名称
            context: 模板变量上下文
            fallback_content: 降级内容（模板不存在或渲染失败时使用）

        Returns:
            渲染后的内容
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)

        except TemplateNotFound:
            logger.error(f"模板不存在: {template_name}")
            if fallback_content:
                logger.info(f"使用降级内容")
                return fallback_content
            return self._generate_fallback_content(template_name, context)

        except TemplateSyntaxError as e:
            logger.error(f"模板语法错误: {template_name}, {e}")
            if fallback_content:
                return fallback_content
            return self._generate_fallback_content(template_name, context)

        except Exception as e:
            logger.error(f"模板渲染失败: {template_name}, {e}", exc_info=True)
            if fallback_content:
                return fallback_content
            return self._generate_fallback_content(template_name, context)

    def render_subject(
        self,
        template_name: str,
        context: Dict[str, Any],
        fallback_subject: Optional[str] = None
    ) -> str:
        """
        渲染主题/标题

        Args:
            template_name: 模板名称
            context: 模板变量上下文
            fallback_subject: 降级主题

        Returns:
            渲染后的主题
        """
        try:
            template_obj = self.db.query(NotificationTemplate).filter(
                NotificationTemplate.template_name == template_name,
                NotificationTemplate.is_active == True
            ).first()

            if not template_obj or not template_obj.subject_template:
                return fallback_subject or f"通知 - {context.get('trade_date', '')}"

            # 渲染主题模板
            subject_env = Environment(autoescape=False)
            subject_template = subject_env.from_string(template_obj.subject_template)
            return subject_template.render(**context)

        except Exception as e:
            logger.error(f"主题渲染失败: {template_name}, {e}")
            return fallback_subject or "通知"

    def get_template_by_criteria(
        self,
        notification_type: str,
        channel: str,
        content_format: str = 'full'
    ) -> Optional[NotificationTemplate]:
        """
        根据条件查找最佳模板

        Args:
            notification_type: 通知类型
            channel: 渠道
            content_format: 内容格式（full, summary, action_only）

        Returns:
            模板对象，不存在返回 None
        """
        # 构建模板名称（优先级顺序）
        template_name_candidates = [
            f"{notification_type}_{channel}_{content_format}",  # 精确匹配
            f"{notification_type}_{channel}_full",              # 降级为完整版
            f"{notification_type}_{channel}",                   # 默认模板
        ]

        for template_name in template_name_candidates:
            template = self.db.query(NotificationTemplate).filter(
                NotificationTemplate.template_name == template_name,
                NotificationTemplate.is_active == True
            ).first()

            if template:
                logger.info(f"找到模板: {template_name}")
                return template

        # 未找到，返回 None
        logger.warning(
            f"未找到合适的模板: type={notification_type}, "
            f"channel={channel}, format={content_format}"
        )
        return None

    def render_notification(
        self,
        notification_type: str,
        channel: str,
        context: Dict[str, Any],
        content_format: str = 'full'
    ) -> Dict[str, str]:
        """
        渲染完整通知（主题 + 内容）

        Args:
            notification_type: 通知类型
            channel: 渠道
            context: 变量上下文
            content_format: 内容格式

        Returns:
            {
                "subject": "主题",
                "content": "内容",
                "template_name": "使用的模板名称"
            }
        """
        template = self.get_template_by_criteria(notification_type, channel, content_format)

        if not template:
            # 生成默认内容
            return {
                "subject": f"{notification_type} 通知",
                "content": self._generate_fallback_content(notification_type, context),
                "template_name": None
            }

        # 渲染主题
        subject = self.render_subject(
            template.template_name,
            context,
            fallback_subject=f"{notification_type} 通知"
        )

        # 渲染内容
        content = self.render_template(
            template.template_name,
            context,
            fallback_content=None
        )

        return {
            "subject": subject,
            "content": content,
            "template_name": template.template_name
        }

    def preview_template(
        self,
        template_id: int
    ) -> Dict[str, Any]:
        """
        预览模板（使用示例数据）

        Args:
            template_id: 模板 ID

        Returns:
            {
                "subject": "渲染后的主题",
                "content": "渲染后的内容",
                "example_data": {},
                "success": bool,
                "error": str
            }
        """
        try:
            template = self.db.query(NotificationTemplate).filter(
                NotificationTemplate.id == template_id
            ).first()

            if not template:
                return {
                    "success": False,
                    "error": "模板不存在"
                }

            # 使用示例数据
            example_data = template.example_data or {}

            # 渲染主题
            subject = self.render_subject(
                template.template_name,
                example_data,
                fallback_subject=""
            )

            # 渲染内容
            content = self.render_template(
                template.template_name,
                example_data,
                fallback_content=""
            )

            return {
                "subject": subject,
                "content": content,
                "example_data": example_data,
                "success": True,
                "error": None
            }

        except Exception as e:
            logger.error(f"模板预览失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def validate_template(
        self,
        subject_template: Optional[str],
        content_template: str,
        example_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证模板语法（用于保存前检查）

        Args:
            subject_template: 主题模板
            content_template: 内容模板
            example_data: 示例数据

        Returns:
            {
                "valid": bool,
                "subject_preview": str,
                "content_preview": str,
                "errors": []
            }
        """
        errors = []
        subject_preview = ""
        content_preview = ""

        # 验证主题模板
        if subject_template:
            try:
                env = Environment(autoescape=False)
                subject_tpl = env.from_string(subject_template)
                subject_preview = subject_tpl.render(**example_data)
            except Exception as e:
                errors.append(f"主题模板错误: {str(e)}")

        # 验证内容模板
        try:
            env = Environment(autoescape=True)
            content_tpl = env.from_string(content_template)
            content_preview = content_tpl.render(**example_data)
        except Exception as e:
            errors.append(f"内容模板错误: {str(e)}")

        return {
            "valid": len(errors) == 0,
            "subject_preview": subject_preview,
            "content_preview": content_preview,
            "errors": errors
        }

    @staticmethod
    def _nl2br_filter(text: str) -> str:
        """换行符转 <br> 标签（用于 HTML 邮件）"""
        if not text:
            return ""
        return text.replace('\n', '<br>\n')

    @staticmethod
    def _truncate_words_filter(text: str, length: int = 50) -> str:
        """截断文本（按字数）"""
        if not text:
            return ""
        words = text.split()
        if len(words) <= length:
            return text
        return ' '.join(words[:length]) + '...'

    @staticmethod
    def _generate_fallback_content(
        notification_type: str,
        context: Dict[str, Any]
    ) -> str:
        """
        生成降级内容（模板不存在时）

        Args:
            notification_type: 通知类型
            context: 变量上下文

        Returns:
            简单的纯文本内容
        """
        trade_date = context.get('trade_date', '')

        if notification_type == 'sentiment_report':
            return f"""
{trade_date} 盘后情绪分析报告

{context.get('full_report', '报告内容生成中...')}

---
本报告由 AI 智能分析生成
"""

        elif notification_type == 'premarket_report':
            return f"""
{trade_date} 盘前碰撞分析

{context.get('full_report', '报告内容生成中...')}

---
本报告由 AI 智能分析生成
"""

        elif notification_type == 'backtest_result':
            return f"""
回测任务完成通知

策略名称: {context.get('strategy_name', 'N/A')}
回测周期: {context.get('start_date', '')} ~ {context.get('end_date', '')}
总收益: {context.get('total_return', 'N/A')}%

---
详情请登录系统查看
"""

        else:
            return f"{notification_type} 通知\n\n内容: {str(context)}"


class TemplateCache:
    """模板缓存（可选，用于高频场景）"""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache: Dict[str, str] = {}

    @lru_cache(maxsize=100)
    def get_cached_template(
        self,
        db: Session,
        template_name: str
    ) -> Optional[str]:
        """获取缓存的模板内容"""
        template = db.query(NotificationTemplate).filter(
            NotificationTemplate.template_name == template_name,
            NotificationTemplate.is_active == True
        ).first()

        return template.content_template if template else None

    def clear_cache(self):
        """清空缓存"""
        self.get_cached_template.cache_clear()
