"""
市场情绪AI分析服务（编排者）

基于打板专题数据（龙虎榜、涨跌停列表、连板天梯、最强板块）通过LLM生成盘后深度分析报告。

职责边界：
- 数据聚合 → `sentiment_data_collector.SentimentDataCollector`
- Prompt 构建 → `sentiment_prompt_builder.SentimentPromptBuilder`
- 响应解析 → `app.services.ai_output_parser.parse_ai_json`
- 本文件只负责：流程编排、LLM 调用、调用日志、结果持久化、查询

作者: AI Strategy Team
创建日期: 2026-03-10
"""

import json
import time
from typing import Dict, Any, Optional
from loguru import logger

from src.database.connection_pool_manager import ConnectionPoolManager
from app.core.config import settings
from app.services.ai_service import AIStrategyService
from app.services.sentiment_data_collector import SentimentDataCollector
from app.services.sentiment_prompt_builder import SentimentPromptBuilder
from app.services.llm_call_logger import llm_call_logger
from app.schemas.llm_call_log import BusinessType, CallStatus
from app.core.database import get_db


class SentimentAIAnalysisService:
    """市场情绪AI分析服务（编排者）"""

    def __init__(self):
        self.ai_strategy_service = AIStrategyService()
        self.collector = SentimentDataCollector()
        self.prompt_builder = SentimentPromptBuilder()
        self._pool_manager = None

    def _get_pool_manager(self) -> ConnectionPoolManager:
        if self._pool_manager is None:
            self._pool_manager = ConnectionPoolManager(settings.db_config_dict())
        return self._pool_manager

    # ---- 向后兼容的 shim（端点仍直接调用这两个方法） ----
    def _fetch_sentiment_data(self, trade_date: str) -> Optional[Dict[str, Any]]:
        return self.collector.fetch_data(trade_date)

    def _build_prompt(self, data: Dict[str, Any]) -> str:
        return self.prompt_builder.build(data)

    async def generate_ai_analysis(
        self,
        trade_date: str,
        provider: str = "deepseek",
        model: str = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """生成AI盘后分析（带LLM调用日志记录）"""
        call_id = None
        start_time_log = None
        db = None

        try:
            logger.info(f"开始生成 {trade_date} 的AI情绪分析...")

            # 1. 数据聚合
            sentiment_data = self.collector.fetch_data(trade_date)
            if not sentiment_data:
                return {
                    "success": False,
                    "trade_date": trade_date,
                    "error": f"{trade_date} 无情绪数据，请先执行数据同步"
                }

            # 2. Prompt 构建
            prompt = self.prompt_builder.build(sentiment_data)

            # 3. AI 提供商配置
            provider_config = self._get_provider_config(provider, model)

            # 4. 创建 LLM 调用日志
            try:
                from datetime import date as date_type
                db = next(get_db())

                call_parameters = {
                    "temperature": provider_config.get("temperature", 0.7),
                    "max_tokens": provider_config.get("max_tokens", 4000),
                    "timeout": provider_config.get("timeout", 60)
                }

                call_id, start_time_log = llm_call_logger.create_log_entry(
                    db=db,
                    business_type=BusinessType.SENTIMENT_ANALYSIS,
                    provider=provider,
                    model_name=provider_config.get("model_name", model or "deepseek-chat"),
                    call_parameters=call_parameters,
                    prompt_text=prompt,
                    caller_service="SentimentAIAnalysisService",
                    caller_function="generate_ai_analysis",
                    business_date=date_type.fromisoformat(trade_date),
                    user_id=user_id,
                    is_scheduled=(user_id is None)
                )
                logger.info(f"LLM调用日志已创建: {call_id}")
            except Exception as log_error:
                logger.warning(f"创建LLM调用日志失败（不影响主流程）: {log_error}")

            # 5. 调用 LLM
            logger.info(f"调用 {provider} AI服务生成情绪分析...")
            client = self.ai_strategy_service.create_client(provider, provider_config)
            start_time = time.time()
            ai_response_text, tokens_used = await client.generate_strategy(prompt)
            generation_time = time.time() - start_time

            logger.info(
                f"AI分析完成: {len(ai_response_text)} 字符, 耗时: {generation_time:.2f}s, tokens: {tokens_used}"
            )

            if not ai_response_text or not isinstance(ai_response_text, str):
                raise ValueError(f"AI返回内容无效: {type(ai_response_text)}")

            # 6. 响应解析（统一经 ai_output_parser）
            analysis_result = self._parse_response(ai_response_text)

            # 7. 数据库持久化
            self._save_ai_analysis(
                trade_date=trade_date,
                analysis_result=analysis_result,
                full_report=ai_response_text,
                ai_provider=provider,
                ai_model=provider_config.get('model_name', 'unknown'),
                tokens_used=tokens_used,
                generation_time=round(generation_time, 2)
            )

            # 8. 更新调用日志为成功
            if call_id and start_time_log and db:
                try:
                    llm_call_logger.update_log_success(
                        db=db,
                        call_id=call_id,
                        start_time=start_time_log,
                        response_text=ai_response_text,
                        parsed_result=analysis_result,
                        tokens_total=tokens_used
                    )
                    logger.info(f"LLM调用日志已更新为成功: {call_id}")
                except Exception as log_error:
                    logger.warning(f"更新LLM调用日志失败（不影响主流程）: {log_error}")

            logger.success(f"{trade_date} AI情绪分析生成成功")

            return {
                "success": True,
                "trade_date": trade_date,
                "analysis_result": analysis_result,
                "ai_provider": provider,
                "ai_model": provider_config.get('model_name', 'unknown'),
                "tokens_used": tokens_used,
                "generation_time": round(generation_time, 2),
                "call_id": call_id
            }

        except Exception as e:
            logger.error(f"生成AI分析失败: {str(e)}", exc_info=True)

            if call_id and start_time_log and db:
                try:
                    llm_call_logger.update_log_failure(
                        db=db,
                        call_id=call_id,
                        start_time=start_time_log,
                        status=CallStatus.FAILED,
                        error_code=type(e).__name__,
                        error_message=str(e)
                    )
                    logger.info(f"LLM调用日志已更新为失败: {call_id}")
                except Exception as log_error:
                    logger.warning(f"更新LLM调用日志失败: {log_error}")

            return {
                "success": False,
                "trade_date": trade_date,
                "error": str(e),
                "call_id": call_id
            }
        finally:
            if db:
                db.close()

    @staticmethod
    def _parse_response(ai_response: str) -> Dict[str, Any]:
        """经 ai_output_parser 解析 AI 响应（Pydantic → 原始 dict → 失败标记）"""
        from app.schemas.ai_analysis_result import SentimentAnalysisResult
        from app.services.ai_output_parser import parse_ai_json, parse_ai_json_or_dict

        parsed = parse_ai_json(ai_response, SentimentAnalysisResult)
        if parsed is not None:
            logger.info("通过 Pydantic 模型成功解析情绪分析 JSON")
            return parsed.model_dump()

        raw_dict = parse_ai_json_or_dict(ai_response)
        if raw_dict is not None:
            logger.info("降级为原始 JSON dict 解析成功")
            return raw_dict

        logger.warning("所有 JSON 解析策略均失败")
        return {
            "parse_failed": True,
            "raw_response": ai_response,
            "error": "无法从 AI 响应中提取有效 JSON"
        }

    def _get_provider_config(self, provider: str = None, model: str = None) -> Dict[str, Any]:
        """从数据库获取AI提供商配置"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            if provider:
                cursor.execute("""
                    SELECT
                        provider, api_key, api_base_url, model_name,
                        max_tokens, temperature, timeout
                    FROM ai_provider_configs
                    WHERE provider = %s AND is_active = true
                    LIMIT 1
                """, (provider,))
            else:
                cursor.execute("""
                    SELECT
                        provider, api_key, api_base_url, model_name,
                        max_tokens, temperature, timeout
                    FROM ai_provider_configs
                    WHERE is_active = true AND is_default = true
                    LIMIT 1
                """)

            row = cursor.fetchone()
            cursor.close()
            pool_manager.release_connection(conn)

            if not row:
                logger.warning(f"未找到AI提供商配置: {provider}，使用默认配置")
                return {
                    "provider": "deepseek",
                    "api_key": settings.DEEPSEEK_API_KEY,
                    "api_base_url": "https://api.deepseek.com/v1",
                    "model_name": model or "deepseek-chat",
                    "max_tokens": 4000,
                    "temperature": 0.7,
                    "timeout": 60
                }

            config = {
                "provider": row[0],
                "api_key": row[1],
                "api_base_url": row[2],
                "model_name": model or row[3],
                "max_tokens": row[4],
                "temperature": float(row[5]),
                "timeout": row[6]
            }

            logger.info(f"已加载AI配置: {config['provider']} / {config['model_name']}")
            return config

        except Exception as e:
            logger.error(f"获取AI配置失败: {str(e)}")
            return {
                "provider": "deepseek",
                "api_key": settings.DEEPSEEK_API_KEY,
                "api_base_url": "https://api.deepseek.com/v1",
                "model_name": model or "deepseek-chat",
                "max_tokens": 4000,
                "temperature": 0.7,
                "timeout": 60
            }

    def _save_ai_analysis(
        self,
        trade_date: str,
        analysis_result: Dict[str, Any],
        full_report: str,
        ai_provider: str,
        ai_model: str,
        tokens_used: int,
        generation_time: float
    ):
        """存储AI分析结果到数据库"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            status = "failed" if analysis_result.get("parse_failed") else "success"

            space_analysis = analysis_result.get("space_analysis")
            sentiment_analysis = analysis_result.get("sentiment_analysis")
            capital_flow_analysis = analysis_result.get("capital_flow_analysis")
            tomorrow_tactics = analysis_result.get("tomorrow_tactics")

            cursor.execute("""
                INSERT INTO market_sentiment_ai_analysis (
                    trade_date, space_analysis, sentiment_analysis,
                    capital_flow_analysis, tomorrow_tactics, full_report,
                    ai_provider, ai_model, tokens_used, generation_time, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (trade_date) DO UPDATE SET
                    space_analysis = EXCLUDED.space_analysis,
                    sentiment_analysis = EXCLUDED.sentiment_analysis,
                    capital_flow_analysis = EXCLUDED.capital_flow_analysis,
                    tomorrow_tactics = EXCLUDED.tomorrow_tactics,
                    full_report = EXCLUDED.full_report,
                    ai_provider = EXCLUDED.ai_provider,
                    ai_model = EXCLUDED.ai_model,
                    tokens_used = EXCLUDED.tokens_used,
                    generation_time = EXCLUDED.generation_time,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                trade_date,
                json.dumps(space_analysis) if space_analysis else None,
                json.dumps(sentiment_analysis) if sentiment_analysis else None,
                json.dumps(capital_flow_analysis) if capital_flow_analysis else None,
                json.dumps(tomorrow_tactics) if tomorrow_tactics else None,
                full_report,
                ai_provider,
                ai_model,
                tokens_used,
                generation_time,
                status
            ))

            conn.commit()
            cursor.close()
            pool_manager.release_connection(conn)

            logger.success(f"{trade_date} AI分析结果已保存到数据库")

            try:
                from app.tasks.notification_tasks import schedule_report_notification_task

                schedule_report_notification_task.delay(
                    report_type='sentiment_report',
                    trade_date=trade_date,
                    report_data={
                        'trade_date': trade_date,
                        'full_report': full_report,
                        'space_analysis': space_analysis,
                        'sentiment_analysis': sentiment_analysis,
                        'capital_flow_analysis': capital_flow_analysis,
                        'tomorrow_tactics': tomorrow_tactics
                    }
                )
                logger.info(f"已触发 {trade_date} 情绪报告通知调度")
            except Exception as notify_error:
                logger.warning(f"触发通知调度失败（不影响主流程）: {notify_error}")

        except Exception as e:
            logger.error(f"保存AI分析结果失败: {str(e)}")
            raise

    def get_ai_analysis(self, trade_date: str) -> Optional[Dict[str, Any]]:
        """获取指定日期的AI分析结果"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    trade_date, space_analysis, sentiment_analysis,
                    capital_flow_analysis, tomorrow_tactics, full_report,
                    ai_provider, ai_model, tokens_used, generation_time,
                    status, created_at
                FROM market_sentiment_ai_analysis
                WHERE trade_date = %s
            """, (trade_date,))

            row = cursor.fetchone()
            cursor.close()
            pool_manager.release_connection(conn)

            if not row:
                return None

            return {
                "trade_date": str(row[0]),
                "space_analysis": row[1],
                "sentiment_analysis": row[2],
                "capital_flow_analysis": row[3],
                "tomorrow_tactics": row[4],
                "full_report": row[5],
                "ai_provider": row[6],
                "ai_model": row[7],
                "tokens_used": row[8],
                "generation_time": float(row[9]) if row[9] else 0,
                "status": row[10],
                "created_at": str(row[11]) if row[11] else None
            }

        except Exception as e:
            logger.error(f"获取AI分析结果失败: {str(e)}")
            return None


sentiment_ai_analysis_service = SentimentAIAnalysisService()
