"""
AI策略生成异步任务

功能：
- 在Celery worker中异步调用AI服务生成策略
- 支持状态更新（不使用具体进度百分比）
- 完整的错误处理和失败回调
- 支持多种AI提供商（DeepSeek、Gemini、OpenAI）

设计说明：
- 参考回测系统的异步架构
- 使用 run_async_in_celery 运行异步AI服务
- 避免阻塞前端，提升用户体验
"""
from typing import Dict, Any
from celery import Task
from loguru import logger

from app.celery_app import celery_app
from app.services.ai_service import ai_strategy_service
from app.core.exceptions import AIServiceError
from app.tasks.extended_sync_tasks import run_async_in_celery


class AIStrategyCallbackTask(Task):
    """
    AI策略生成任务基类

    功能：
    - 自动处理任务失败时的日志记录
    - 继承自Celery Task，提供失败回调机制
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        任务失败时的回调函数

        Args:
            exc: 异常对象
            task_id: Celery任务ID
            args: 任务参数
            kwargs: 任务关键字参数
            einfo: 异常信息对象
        """
        logger.error(f"AI策略生成任务失败 [task_id={task_id}]: {str(exc)}")
        logger.error(f"Traceback: {einfo}")


@celery_app.task(
    base=AIStrategyCallbackTask,
    bind=True,
    name='app.tasks.ai_strategy_tasks.generate_strategy_async'
)
def generate_strategy_async(
    self,
    strategy_requirement: str,
    provider_config: Dict[str, Any],
    strategy_type: str = "entry",
    custom_prompt_template: str = None
) -> Dict[str, Any]:
    """
    异步生成策略代码

    Args:
        self: Celery任务实例
        strategy_requirement: 策略需求描述
        provider_config: AI提供商配置字典
            - provider: 提供商名称（deepseek, gemini, openai）
            - api_key: API密钥
            - api_base_url: API基础URL
            - model_name: 模型名称
            - max_tokens: 最大token数
            - temperature: 温度参数
            - timeout: 超时时间
        strategy_type: 策略类型（entry / exit / stock_selection）
        custom_prompt_template: 自定义提示词模板（可选）

    Returns:
        包含strategy_code, strategy_metadata, tokens_used, generation_time的字典

    Raises:
        AIServiceError: AI服务调用失败
        Exception: 其他异常
    """
    try:
        # 更新任务状态为进行中（不显示具体进度，只显示状态）
        self.update_state(
            state='PROGRESS',
            meta={
                'status': f"正在使用 {provider_config.get('provider')} 生成策略..."
            }
        )

        logger.info(
            f"开始AI策略生成任务 [task_id={self.request.id}], "
            f"provider={provider_config.get('provider')}"
        )

        # 调用AI服务生成策略（这是耗时的操作，通常10-60秒）
        result = run_async_in_celery(
            ai_strategy_service.generate_strategy,
            strategy_requirement=strategy_requirement,
            provider_config=provider_config,
            strategy_type=strategy_type,
            custom_prompt_template=custom_prompt_template
        )

        logger.info(
            f"AI策略生成完成 [task_id={self.request.id}], "
            f"耗时={result['generation_time']}s, "
            f"tokens={result['tokens_used']}"
        )

        # 返回成功结果
        return {
            'status': 'SUCCESS',
            'strategy_code': result['strategy_code'],
            'strategy_metadata': result['strategy_metadata'],
            'tokens_used': result['tokens_used'],
            'generation_time': result['generation_time'],
            'provider_used': provider_config['provider']
        }

    except AIServiceError as e:
        error_msg = f"AI服务错误: {str(e)}"
        logger.error(f"{error_msg} [task_id={self.request.id}]")
        raise  # Celery会将任务标记为FAILURE

    except Exception as e:
        error_msg = f"策略生成异常: {str(e)}"
        logger.error(f"{error_msg} [task_id={self.request.id}]", exc_info=True)
        raise
