"""盘前碰撞分析服务（编排者）

基于昨晚战术 + 今晨外盘 + 核心快讯，调用 LLM 生成盘前四维分析报告并输出极简行动指令。

职责边界：
- 数据聚合 → `premarket_data_collector.PremarketDataCollector`
- Prompt 构建 / 行动指令格式化 → `premarket_prompt_builder.PremarketPromptBuilder`
- 响应解析 → `app.services.ai_output_parser.parse_ai_json`
- 本文件只负责：流程编排、LLM 调用、结果持久化、查询

作者: AI Strategy Team
"""

import json
import time
from typing import Dict, Any, Optional
from loguru import logger

from src.database.connection_pool_manager import ConnectionPoolManager
from app.core.config import settings
from app.services.ai_service import AIStrategyService
from app.services.premarket_data_collector import PremarketDataCollector
from app.services.premarket_prompt_builder import PremarketPromptBuilder


class PremarketAnalysisService:
    """盘前碰撞分析服务（编排者）"""

    def __init__(self):
        self.ai_strategy_service = AIStrategyService()
        self.collector = PremarketDataCollector()
        self.prompt_builder = PremarketPromptBuilder()
        self._pool_manager: Optional[ConnectionPoolManager] = None

    def _get_pool_manager(self) -> ConnectionPoolManager:
        if self._pool_manager is None:
            self._pool_manager = ConnectionPoolManager(settings.db_config_dict())
        return self._pool_manager

    async def generate_collision_analysis(
        self,
        trade_date: str,
        provider: str = "deepseek",
        model: str = None,
    ) -> Dict[str, Any]:
        """生成盘前碰撞分析"""
        try:
            logger.info(f"开始生成 {trade_date} 的盘前碰撞分析...")

            # 1. 战术数据（优先当日，缺失则生成上一交易日）
            yesterday_tactics = await self.collector.get_or_generate_tactics(trade_date)
            if not yesterday_tactics:
                logger.warning(f"{trade_date} 无法获取或生成战术数据，使用默认空值")
                yesterday_tactics = {
                    "call_auction_tactics": {"participate_conditions": "无昨日计划", "avoid_conditions": "无昨日计划"},
                    "buy_conditions": ["无昨日计划"],
                    "stop_loss_conditions": ["无昨日计划"],
                }

            # 2. 今晨外盘
            overnight_data = self.collector.fetch_overnight_data(trade_date)
            if not overnight_data:
                return {
                    "success": False,
                    "trade_date": trade_date,
                    "error": f"{trade_date} 无隔夜外盘数据,请先执行盘前数据同步",
                }

            # 3. 今晨核心新闻
            critical_news = self.collector.fetch_critical_news(trade_date)

            # 4. 构建 Prompt
            prompt = self.prompt_builder.build_collision_prompt(
                yesterday_tactics, overnight_data, critical_news
            )

            # 5. 调用 LLM
            provider_config = self._get_provider_config(provider, model)
            client = self.ai_strategy_service.create_client(provider, provider_config)

            start_time = time.time()
            ai_response_text, tokens_used = await client.generate_strategy(prompt)
            generation_time = time.time() - start_time

            logger.info(
                f"AI碰撞分析完成: {len(ai_response_text)} 字符, 耗时: {generation_time:.2f}s, tokens: {tokens_used}"
            )

            # 6. 解析响应
            analysis_result = self._parse_response(ai_response_text)

            # 7. 生成极简行动指令
            action_command = self.prompt_builder.format_action_command(analysis_result)

            # 8. 持久化
            self._save_collision_analysis(
                trade_date=trade_date,
                yesterday_tactics=yesterday_tactics,
                overnight_data=overnight_data,
                critical_news=critical_news,
                analysis_result=analysis_result,
                action_command=action_command,
                ai_provider=provider,
                ai_model=provider_config.get('model_name', 'unknown'),
                tokens_used=tokens_used,
                generation_time=round(generation_time, 2),
            )

            logger.success(f"{trade_date} 盘前碰撞分析生成成功")

            return {
                "success": True,
                "trade_date": trade_date,
                "analysis_result": analysis_result,
                "action_command": action_command,
                "ai_provider": provider,
                "ai_model": provider_config.get('model_name', 'unknown'),
                "tokens_used": tokens_used,
                "generation_time": round(generation_time, 2),
            }

        except Exception as e:
            logger.error(f"生成盘前碰撞分析失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "trade_date": trade_date,
                "error": str(e),
            }

    @staticmethod
    def _parse_response(ai_response: str) -> Dict[str, Any]:
        """经 ai_output_parser 解析 AI 响应（Pydantic → 原始 dict → 失败标记）"""
        from app.schemas.ai_analysis_result import CollisionAnalysisResult
        from app.services.ai_output_parser import parse_ai_json, parse_ai_json_or_dict

        parsed = parse_ai_json(ai_response, CollisionAnalysisResult)
        if parsed is not None:
            logger.info("通过 Pydantic 模型成功解析碰撞分析 JSON")
            return parsed.model_dump()

        raw_dict = parse_ai_json_or_dict(ai_response)
        if raw_dict is not None:
            logger.info("降级为原始 JSON dict 解析成功")
            return raw_dict

        logger.warning("所有 JSON 解析策略均失败")
        return {
            "parse_failed": True,
            "raw_response": ai_response,
            "error": "无法从 AI 响应中提取有效 JSON",
        }

    def _get_provider_config(self, provider: str = None, model: str = None) -> Dict[str, Any]:
        """从数据库获取 AI 提供商配置"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            if provider:
                cursor.execute("""
                    SELECT provider, api_key, api_base_url, model_name,
                           max_tokens, temperature, timeout
                    FROM ai_provider_configs
                    WHERE provider = %s AND is_active = true
                    LIMIT 1
                """, (provider,))
            else:
                cursor.execute("""
                    SELECT provider, api_key, api_base_url, model_name,
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
                return self._default_provider_config(model)

            config = {
                "provider": row[0],
                "api_key": row[1],
                "api_base_url": row[2],
                "model_name": model or row[3],
                "max_tokens": row[4],
                "temperature": float(row[5]),
                "timeout": row[6],
            }
            logger.info(f"已加载AI配置: {config['provider']} / {config['model_name']}")
            return config

        except Exception as e:
            logger.error(f"获取AI配置失败: {e}")
            return self._default_provider_config(model)

    @staticmethod
    def _default_provider_config(model: Optional[str]) -> Dict[str, Any]:
        return {
            "provider": "deepseek",
            "api_key": settings.DEEPSEEK_API_KEY,
            "api_base_url": "https://api.deepseek.com/v1",
            "model_name": model or "deepseek-chat",
            "max_tokens": 4000,
            "temperature": 0.7,
            "timeout": 60,
        }

    def _save_collision_analysis(
        self,
        trade_date: str,
        yesterday_tactics: Dict,
        overnight_data: Dict,
        critical_news: str,
        analysis_result: Dict,
        action_command: str,
        ai_provider: str,
        ai_model: str,
        tokens_used: int,
        generation_time: float,
    ):
        """保存碰撞分析结果到数据库"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            yesterday_summary = {
                "call_auction_tactics": yesterday_tactics.get("call_auction_tactics"),
                "buy_conditions": yesterday_tactics.get("buy_conditions"),
                "stop_loss_conditions": yesterday_tactics.get("stop_loss_conditions"),
            }
            news_summary = {"raw_news": critical_news}
            status = "failed" if analysis_result.get("parse_failed") else "success"

            cursor.execute("""
                INSERT INTO premarket_collision_analysis (
                    trade_date, yesterday_tactics_summary, overnight_summary,
                    critical_news_summary, macro_tone, holdings_alert,
                    plan_adjustment, auction_focus, action_command,
                    ai_provider, ai_model, tokens_used, generation_time, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (trade_date) DO UPDATE SET
                    yesterday_tactics_summary = EXCLUDED.yesterday_tactics_summary,
                    overnight_summary = EXCLUDED.overnight_summary,
                    critical_news_summary = EXCLUDED.critical_news_summary,
                    macro_tone = EXCLUDED.macro_tone,
                    holdings_alert = EXCLUDED.holdings_alert,
                    plan_adjustment = EXCLUDED.plan_adjustment,
                    auction_focus = EXCLUDED.auction_focus,
                    action_command = EXCLUDED.action_command,
                    ai_provider = EXCLUDED.ai_provider,
                    ai_model = EXCLUDED.ai_model,
                    tokens_used = EXCLUDED.tokens_used,
                    generation_time = EXCLUDED.generation_time,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                trade_date,
                json.dumps(yesterday_summary, ensure_ascii=False),
                json.dumps(overnight_data, ensure_ascii=False),
                json.dumps(news_summary, ensure_ascii=False),
                json.dumps(analysis_result.get('macro_tone'), ensure_ascii=False) if analysis_result.get('macro_tone') else None,
                json.dumps(analysis_result.get('holdings_alert'), ensure_ascii=False) if analysis_result.get('holdings_alert') else None,
                json.dumps(analysis_result.get('plan_adjustment'), ensure_ascii=False) if analysis_result.get('plan_adjustment') else None,
                json.dumps(analysis_result.get('auction_focus'), ensure_ascii=False) if analysis_result.get('auction_focus') else None,
                action_command,
                ai_provider,
                ai_model,
                tokens_used,
                generation_time,
                status,
            ))

            conn.commit()
            cursor.close()
            pool_manager.release_connection(conn)

            logger.success(f"{trade_date} 碰撞分析已保存到数据库")

            try:
                from app.tasks.notification_tasks import schedule_report_notification_task

                schedule_report_notification_task.delay(
                    report_type='premarket_report',
                    trade_date=trade_date,
                    report_data={
                        'trade_date': trade_date,
                        'action_command': action_command,
                        'macro_tone': analysis_result.get('macro_tone', {}),
                        'holdings_alert': analysis_result.get('holdings_alert', {}),
                        'plan_adjustment': analysis_result.get('plan_adjustment', {}),
                        'auction_focus': analysis_result.get('auction_focus', {}),
                    },
                )
                logger.info(f"已触发 {trade_date} 盘前报告通知调度")
            except Exception as notify_error:
                logger.warning(f"触发通知调度失败（不影响主流程）: {notify_error}")

        except Exception as e:
            logger.error(f"保存碰撞分析失败: {e}")
            raise

    def get_collision_analysis(self, trade_date: str) -> Optional[Dict[str, Any]]:
        """获取指定日期的碰撞分析结果"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT trade_date, macro_tone, holdings_alert,
                       plan_adjustment, auction_focus, action_command,
                       ai_provider, ai_model, tokens_used, generation_time,
                       status, created_at
                FROM premarket_collision_analysis
                WHERE trade_date = %s
            """, (trade_date,))

            row = cursor.fetchone()
            cursor.close()
            pool_manager.release_connection(conn)

            if not row:
                return None

            return {
                "trade_date": str(row[0]),
                "macro_tone": row[1],
                "holdings_alert": row[2],
                "plan_adjustment": row[3],
                "auction_focus": row[4],
                "action_command": row[5],
                "ai_provider": row[6],
                "ai_model": row[7],
                "tokens_used": row[8],
                "generation_time": float(row[9]) if row[9] else 0,
                "status": row[10],
                "created_at": str(row[11]) if row[11] else None,
            }

        except Exception as e:
            logger.error(f"获取碰撞分析结果失败: {e}")
            return None


premarket_analysis_service = PremarketAnalysisService()
