"""
LLM调用日志记录服务
单例模式，负责记录所有LLM调用的详细信息
"""

import uuid
import hashlib
import time
from datetime import datetime, date
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, text
from decimal import Decimal

from app.models.llm_call_log import LLMCallLog, LLMPricingConfig
from app.schemas.llm_call_log import (
    BusinessType, CallStatus, LLMCallLogCreate,
    LLMCallLogResponse, LLMCallLogQuery, LLMCallStatistics
)
from app.core.logging_config import get_logger

logger = get_logger()


class LLMCallLogger:
    """LLM调用日志记录器（单例模式）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def generate_call_id() -> str:
        """生成唯一的调用ID"""
        return str(uuid.uuid4())

    @staticmethod
    def hash_prompt(prompt: str) -> str:
        """生成prompt的SHA256哈希"""
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()

    def calculate_cost(
        self,
        db: Session,
        provider: str,
        model_name: str,
        tokens_input: Optional[int],
        tokens_output: Optional[int],
        call_date: Optional[date] = None
    ) -> Optional[Decimal]:
        """
        计算调用成本

        Args:
            db: 数据库会话
            provider: AI提供商
            model_name: 模型名称
            tokens_input: 输入token数
            tokens_output: 输出token数
            call_date: 调用日期（用于查找有效价格）

        Returns:
            成本（美元），如果无法计算则返回None
        """
        try:
            if tokens_input is None or tokens_output is None:
                return None

            if call_date is None:
                call_date = date.today()

            # 查询价格配置
            pricing = db.query(LLMPricingConfig).filter(
                and_(
                    LLMPricingConfig.provider == provider,
                    LLMPricingConfig.model_name == model_name,
                    LLMPricingConfig.effective_from <= call_date,
                    (LLMPricingConfig.effective_to.is_(None) |
                     (LLMPricingConfig.effective_to >= call_date))
                )
            ).order_by(LLMPricingConfig.effective_from.desc()).first()

            if not pricing:
                logger.warning(f"No pricing found for {provider}/{model_name}")
                return None

            # 计算成本（价格单位是每百万token）
            input_cost = (tokens_input / 1_000_000) * float(pricing.input_price_per_million or 0)
            output_cost = (tokens_output / 1_000_000) * float(pricing.output_price_per_million or 0)
            total_cost = input_cost + output_cost

            return Decimal(str(round(total_cost, 4)))

        except Exception as e:
            logger.error(f"Error calculating cost: {e}")
            return None

    def create_log_entry(
        self,
        db: Session,
        business_type: BusinessType,
        provider: str,
        model_name: str,
        call_parameters: Dict[str, Any],
        prompt_text: str,
        caller_service: str,
        caller_function: str,
        business_date: Optional[date] = None,
        business_id: Optional[str] = None,
        user_id: Optional[str] = None,
        is_scheduled: bool = False,
        parent_call_id: Optional[str] = None
    ) -> Tuple[str, datetime]:
        """
        创建日志条目（调用前）

        Returns:
            (call_id, start_time)
        """
        call_id = self.generate_call_id()
        start_time = datetime.now()
        prompt_hash = self.hash_prompt(prompt_text)

        log_entry = LLMCallLog(
            call_id=call_id,
            business_type=business_type.value,
            business_date=business_date,
            business_id=business_id,

            provider=provider,
            model_name=model_name,
            call_parameters=call_parameters,

            prompt_text=prompt_text,
            prompt_length=len(prompt_text),
            prompt_hash=prompt_hash,

            start_time=start_time,
            status=CallStatus.FAILED.value,  # 默认失败，成功后更新

            caller_service=caller_service,
            caller_function=caller_function,
            user_id=user_id,
            is_scheduled=is_scheduled,
            retry_count=0 if parent_call_id is None else 1,
            parent_call_id=parent_call_id
        )

        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        logger.info(f"Created LLM call log: {call_id} for {business_type.value}")
        return call_id, start_time

    def update_log_success(
        self,
        db: Session,
        call_id: str,
        start_time: datetime,
        response_text: str,
        parsed_result: Optional[Dict[str, Any]] = None,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        tokens_total: Optional[int] = None,
        http_status_code: Optional[int] = None,
        response_headers: Optional[Dict[str, Any]] = None
    ):
        """更新日志为成功状态"""
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        log_entry = db.query(LLMCallLog).filter(LLMCallLog.call_id == call_id).first()
        if not log_entry:
            logger.error(f"Log entry not found: {call_id}")
            return

        # 计算总tokens（优先使用传入的tokens_total）
        final_tokens_total = tokens_total
        if final_tokens_total is None and tokens_input is not None and tokens_output is not None:
            final_tokens_total = tokens_input + tokens_output

        # 计算成本
        cost_estimate = None
        if tokens_input is not None and tokens_output is not None:
            cost_estimate = self.calculate_cost(
                db=db,
                provider=log_entry.provider,
                model_name=log_entry.model_name,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                call_date=log_entry.business_date or date.today()
            )

        # 更新字段
        log_entry.response_text = response_text
        log_entry.response_length = len(response_text) if response_text else 0
        log_entry.parsed_result = parsed_result

        log_entry.tokens_input = tokens_input
        log_entry.tokens_output = tokens_output
        log_entry.tokens_total = final_tokens_total
        log_entry.cost_estimate = cost_estimate

        log_entry.duration_ms = duration_ms
        log_entry.end_time = end_time

        log_entry.status = CallStatus.SUCCESS.value
        log_entry.http_status_code = http_status_code
        log_entry.response_headers = response_headers

        db.commit()
        db.refresh(log_entry)

        logger.info(f"Updated LLM call log to success: {call_id} (duration={duration_ms}ms, tokens={final_tokens_total}, cost=${cost_estimate})")

    def update_log_failure(
        self,
        db: Session,
        call_id: str,
        start_time: datetime,
        status: CallStatus,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        http_status_code: Optional[int] = None
    ):
        """更新日志为失败状态"""
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        log_entry = db.query(LLMCallLog).filter(LLMCallLog.call_id == call_id).first()
        if not log_entry:
            logger.error(f"Log entry not found: {call_id}")
            return

        log_entry.status = status.value
        log_entry.error_code = error_code
        log_entry.error_message = error_message
        log_entry.http_status_code = http_status_code
        log_entry.duration_ms = duration_ms
        log_entry.end_time = end_time

        db.commit()
        db.refresh(log_entry)

        logger.warning(f"Updated LLM call log to {status.value}: {call_id} - {error_message}")

    def query_logs(
        self,
        db: Session,
        query_params: LLMCallLogQuery
    ) -> Tuple[list[LLMCallLogResponse], int]:
        """查询日志列表"""
        query = db.query(LLMCallLog)

        # 过滤条件
        if query_params.business_type:
            query = query.filter(LLMCallLog.business_type == query_params.business_type.value)

        if query_params.provider:
            query = query.filter(LLMCallLog.provider == query_params.provider)

        if query_params.status:
            query = query.filter(LLMCallLog.status == query_params.status.value)

        if query_params.start_date:
            query = query.filter(LLMCallLog.business_date >= query_params.start_date)

        if query_params.end_date:
            query = query.filter(LLMCallLog.business_date <= query_params.end_date)

        # 总数
        total = query.count()

        # 分页
        offset = (query_params.page - 1) * query_params.page_size
        logs = query.order_by(LLMCallLog.created_at.desc()).offset(offset).limit(query_params.page_size).all()

        return [LLMCallLogResponse.model_validate(log) for log in logs], total

    def get_statistics(
        self,
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> list[LLMCallStatistics]:
        """获取统计数据"""
        query = text("""
            SELECT * FROM llm_call_statistics_daily
            WHERE 1=1
            AND (:start_date IS NULL OR stat_date >= :start_date)
            AND (:end_date IS NULL OR stat_date <= :end_date)
            ORDER BY stat_date DESC, total_calls DESC
        """)

        result = db.execute(query, {"start_date": start_date, "end_date": end_date})
        rows = result.fetchall()

        stats = []
        for row in rows:
            stats.append(LLMCallStatistics(
                stat_date=row.stat_date,
                business_type=row.business_type,
                provider=row.provider,
                model_name=row.model_name,
                total_calls=row.total_calls,
                success_calls=row.success_calls,
                failed_calls=row.failed_calls,
                success_rate=float(row.success_rate or 0),
                total_tokens=row.total_tokens,
                avg_tokens_per_call=float(row.avg_tokens_per_call) if row.avg_tokens_per_call else None,
                max_tokens=row.max_tokens,
                total_cost=float(row.total_cost) if row.total_cost else None,
                avg_cost_per_call=float(row.avg_cost_per_call) if row.avg_cost_per_call else None,
                avg_duration_ms=float(row.avg_duration_ms) if row.avg_duration_ms else None,
                min_duration_ms=row.min_duration_ms,
                max_duration_ms=row.max_duration_ms,
                p95_duration_ms=float(row.p95_duration_ms) if row.p95_duration_ms else None,
                total_retries=row.total_retries,
                avg_retry_per_call=float(row.avg_retry_per_call) if row.avg_retry_per_call else None
            ))

        return stats


# 全局单例实例
llm_call_logger = LLMCallLogger()
