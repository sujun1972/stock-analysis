"""
市场情绪AI分析服务

基于打板专题数据（龙虎榜、涨跌停列表、连板天梯、最强板块）通过LLM生成盘后深度分析报告。

主要功能：
- 从打板专题表读取当日数据（top_list / limit_list_d / limit_step / limit_cpt_list）
- 构建结构化 Prompt（七节数据 + 四个灵魂拷问）
- 调用 AI 服务生成 JSON 格式的盘后报告
- 解析 JSON 结果并存储到 market_sentiment_ai_analysis 表

关键方法：
- _fetch_sentiment_data: 读取打板专题数据（供 Celery 任务和 preview-prompt 端点共用）
- _build_prompt: 构建分析 Prompt（供 Celery 任务和 preview-prompt 端点共用）

作者: AI Strategy Team
创建日期: 2026-03-10
"""

import json
import re
import time
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from src.database.connection_pool_manager import ConnectionPoolManager
from app.core.config import settings
from app.services.ai_service import AIStrategyService
from app.core.exceptions import AIServiceError
from app.services.llm_call_logger import llm_call_logger
from app.schemas.llm_call_log import BusinessType, CallStatus
from app.core.database import get_db


class SentimentAIAnalysisService:
    """市场情绪AI分析服务"""

    def __init__(self):
        """初始化服务"""
        self.ai_strategy_service = AIStrategyService()  # 用于创建AI客户端
        self._pool_manager = None

    def _get_pool_manager(self) -> ConnectionPoolManager:
        """获取数据库连接池管理器（懒加载）"""
        if self._pool_manager is None:
            self._pool_manager = ConnectionPoolManager(settings.db_config_dict())
        return self._pool_manager

    async def generate_ai_analysis(
        self,
        trade_date: str,
        provider: str = "deepseek",
        model: str = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        生成AI盘后分析（带LLM调用日志记录）

        Args:
            trade_date: 交易日期（YYYY-MM-DD）
            provider: AI提供商（deepseek/gemini/openai）
            model: 模型名称（可选，使用默认）
            user_id: 触发用户ID（可选，None表示定时任务触发）

        Returns:
            {
                "success": True/False,
                "trade_date": "2026-03-10",
                "analysis_result": {...},
                "ai_provider": "deepseek",
                "ai_model": "deepseek-chat",
                "tokens_used": 1500,
                "generation_time": 5.2,
                "call_id": "uuid",  # LLM调用日志ID
                "error": "错误信息（如果失败）"
            }
        """
        call_id = None
        start_time_log = None
        db = None

        try:
            logger.info(f"开始生成 {trade_date} 的AI情绪分析...")

            # 1. 从数据库获取完整情绪数据
            sentiment_data = self._fetch_sentiment_data(trade_date)
            if not sentiment_data:
                return {
                    "success": False,
                    "trade_date": trade_date,
                    "error": f"{trade_date} 无情绪数据，请先执行数据同步"
                }

            # 2. 构建Prompt
            prompt = self._build_prompt(sentiment_data)

            # 3. 获取AI提供商配置
            provider_config = self._get_provider_config(provider, model)

            # 4. 创建LLM调用日志（调用前）
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

            # 5. 调用AI生成情绪分析文本
            logger.info(f"调用 {provider} AI服务生成情绪分析...")

            client = self.ai_strategy_service.create_client(provider, provider_config)
            start_time = time.time()
            ai_response_text, tokens_used = await client.generate_strategy(prompt)
            generation_time = time.time() - start_time

            logger.info(f"AI分析完成: {len(ai_response_text)} 字符, 耗时: {generation_time:.2f}s, tokens: {tokens_used}")

            if not ai_response_text or not isinstance(ai_response_text, str):
                raise ValueError(f"AI返回内容无效: {type(ai_response_text)}")

            # 6. 解析JSON结果（从AI返回的文本中提取JSON）
            analysis_result = self._parse_ai_response(ai_response_text)

            # 7. 存储到数据库
            self._save_ai_analysis(
                trade_date=trade_date,
                analysis_result=analysis_result,
                full_report=ai_response_text,  # 保存完整的AI响应文本
                ai_provider=provider,
                ai_model=provider_config.get('model_name', 'unknown'),
                tokens_used=tokens_used,
                generation_time=round(generation_time, 2)
            )

            # 8. 更新LLM调用日志为成功状态
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

            # 更新LLM调用日志为失败状态
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

    def _fetch_sentiment_data(self, trade_date: str) -> Optional[Dict[str, Any]]:
        """从打板专题表读取数据（与 preview-prompt 端点逻辑保持一致）"""
        try:
            from app.repositories.top_list_repository import TopListRepository
            from app.repositories.limit_list_repository import LimitListRepository
            from app.repositories.limit_step_repository import LimitStepRepository
            from app.repositories.limit_cpt_repository import LimitCptRepository

            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            trade_date_fmt = trade_date.replace('-', '')

            top_list_repo = TopListRepository()
            limit_list_repo = LimitListRepository()
            limit_step_repo = LimitStepRepository()
            limit_cpt_repo = LimitCptRepository()

            top_list_data = top_list_repo.get_by_trade_date(trade_date_fmt)
            limit_list_data = limit_list_repo.get_by_date_range(
                start_date=trade_date_fmt, end_date=trade_date_fmt, limit=200
            )
            limit_step_data = limit_step_repo.get_by_trade_date(trade_date_fmt)
            limit_cpt_data = limit_cpt_repo.get_by_trade_date(trade_date_fmt, limit=20)

            # 如果核心数据（涨跌停）为空，视为无数据
            if not limit_list_data and not limit_step_data and not top_list_data:
                logger.warning(f"{trade_date} 打板专题数据为空，请先同步数据")
                return None

            return {
                "trade_date": trade_date,
                "trade_date_fmt": trade_date_fmt,
                "top_list_data": top_list_data,
                "limit_list_data": limit_list_data,
                "limit_step_data": limit_step_data,
                "limit_cpt_data": limit_cpt_data,
            }

        except Exception as e:
            logger.error(f"读取情绪数据失败: {str(e)}")
            return None

    def _build_prompt(self, data: Dict[str, Any]) -> str:
        """基于打板专题数据构建分析 Prompt（与 preview-prompt 端点逻辑保持一致）"""
        trade_date = data['trade_date']
        top_list_data = data['top_list_data']
        limit_list_data = data['limit_list_data']
        limit_step_data = data['limit_step_data']
        limit_cpt_data = data['limit_cpt_data']

        # 分类涨跌停数据
        limit_up_list = [s for s in limit_list_data if s.get('limit_type') == 'U']
        limit_down_list = [s for s in limit_list_data if s.get('limit_type') == 'D']
        blast_list = [s for s in limit_list_data if s.get('limit_type') == 'Z']

        # 按连板数降序排列
        limit_up_list_sorted = sorted(
            limit_up_list,
            key=lambda x: (x.get('limit_times') or 0),
            reverse=True
        )

        # 构建连板天梯文本
        step_by_nums: dict = {}
        for row in limit_step_data:
            n = str(row.get('nums', ''))
            if n not in step_by_nums:
                step_by_nums[n] = []
            step_by_nums[n].append(f"{row.get('name', '')}({row.get('ts_code', '')})")

        ladder_lines = []
        for nums_key in sorted(step_by_nums.keys(), key=lambda x: int(x) if x.isdigit() else 0, reverse=True):
            stocks_str = '、'.join(step_by_nums[nums_key][:5])
            if len(step_by_nums[nums_key]) > 5:
                stocks_str += f" 等{len(step_by_nums[nums_key])}只"
            ladder_lines.append(f"- {nums_key}连板({len(step_by_nums[nums_key])}只): {stocks_str}")
        continuous_ladder_text = '\n'.join(ladder_lines) if ladder_lines else '- 暂无连板数据'

        # 涨停股票列表（前15，按连板数排序）
        limit_up_lines = []
        for i, s in enumerate(limit_up_list_sorted[:15], 1):
            lt = s.get('limit_times') or 1
            ft = s.get('first_time') or '--'
            ot = s.get('open_times') or 0
            industry = s.get('industry') or ''
            limit_up_lines.append(
                f"{i}. {s.get('name', '')}({s.get('ts_code', '')}) "
                f"- {lt}连板 | 封板时间:{ft} | 炸板次数:{ot} | 所属行业:{industry}"
            )
        limit_up_stocks_text = '\n'.join(limit_up_lines) if limit_up_lines else '- 无涨停数据'

        # 跌停股票列表（前5）
        limit_down_lines = []
        for i, s in enumerate(limit_down_list[:5], 1):
            industry = s.get('industry') or ''
            limit_down_lines.append(
                f"{i}. {s.get('name', '')}({s.get('ts_code', '')}) - 所属行业:{industry}"
            )
        limit_down_stocks_text = '\n'.join(limit_down_lines) if limit_down_lines else '- 无跌停数据'

        # 炸板股票列表（前5）
        blast_lines = []
        for i, s in enumerate(blast_list[:5], 1):
            ft = s.get('first_time') or '--'
            industry = s.get('industry') or ''
            blast_lines.append(
                f"{i}. {s.get('name', '')}({s.get('ts_code', '')}) "
                f"- 首次封板:{ft} | 所属行业:{industry}"
            )
        blast_stocks_text = '\n'.join(blast_lines) if blast_lines else '- 无炸板数据'

        # 龙虎榜数据（净买入前5 / 净卖出前5）
        top_list_sorted = sorted(top_list_data, key=lambda x: x.get('net_amount') or 0, reverse=True)
        net_buy_top5 = top_list_sorted[:5]
        net_sell_top5 = sorted(top_list_data, key=lambda x: x.get('net_amount') or 0)[:5]

        net_buy_lines = []
        for i, s in enumerate(net_buy_top5, 1):
            amt = (s.get('net_amount') or 0) / 1e8
            reason = s.get('reason') or ''
            net_buy_lines.append(
                f"{i}. {s.get('name', '')}({s.get('ts_code', '')}) "
                f"- 净买入 {amt:.2f}亿 | 上榜原因:{reason}"
            )
        net_buy_text = '\n'.join(net_buy_lines) if net_buy_lines else '- 无龙虎榜净买入数据'

        net_sell_lines = []
        for i, s in enumerate(net_sell_top5, 1):
            amt = (s.get('net_amount') or 0) / 1e8
            reason = s.get('reason') or ''
            net_sell_lines.append(
                f"{i}. {s.get('name', '')}({s.get('ts_code', '')}) "
                f"- 净卖出 {abs(amt):.2f}亿 | 上榜原因:{reason}"
            )
        net_sell_text = '\n'.join(net_sell_lines) if net_sell_lines else '- 无龙虎榜净卖出数据'

        # 最强板块（前10）
        cpt_lines = []
        for i, c in enumerate(limit_cpt_data[:10], 1):
            cpt_lines.append(
                f"{i}. {c.get('name', '')}({c.get('ts_code', '')}) "
                f"- 涨停{c.get('up_nums', 0)}只 | 连板{c.get('cons_nums', 0)}只 "
                f"| 高度{c.get('up_stat', '')} | 涨幅{c.get('pct_chg', 0) or 0:.2f}%"
            )
        cpt_text = '\n'.join(cpt_lines) if cpt_lines else '- 无板块数据'

        # 计算最高连板
        max_continuous = max(
            [int(k) for k in step_by_nums.keys() if k.isdigit()],
            default=0
        )
        max_continuous_stock = ''
        if max_continuous > 0 and str(max_continuous) in step_by_nums:
            max_continuous_stock = step_by_nums[str(max_continuous)][0]

        # 统计数据
        limit_up_count = len(limit_up_list)
        limit_down_count = len(limit_down_list)
        blast_count = len(blast_list)
        blast_rate = blast_count / (limit_up_count + blast_count) if (limit_up_count + blast_count) > 0 else 0

        prompt = f"""# A股打板专题盘后深度分析（{trade_date}）

你是一位拥有20年实战经验的A股短线大师，擅长通过盘后数据精准解读市场情绪和资金动向。以下数据均来自当日A股真实市场数据。

## 一、情绪核心数据

- **涨停家数**: {limit_up_count} 只
- **跌停家数**: {limit_down_count} 只
- **炸板家数**: {blast_count} 只
- **炸板率**: {blast_rate:.1%}
- **最高连板**: {max_continuous} 天（{max_continuous_stock}）

## 二、连板天梯（晋级结构）

{continuous_ladder_text}

## 三、涨停股票列表（前15，按连板数排序）

{limit_up_stocks_text}

## 四、跌停股票列表（前5）

{limit_down_stocks_text}

## 五、炸板股票列表（前5）

{blast_stocks_text}

## 六、最强概念板块 TOP10

{cpt_text}

## 七、龙虎榜资金动向

### 净买入前5（主力资金流入）
{net_buy_text}

### 净卖出前5（主力资金流出）
{net_sell_text}

---

## 请以JSON格式回答以下四个灵魂拷问

**非常重要**: 请将整个分析结果放在一个JSON代码块中，格式如下：

```json
{{
  "space_analysis": {{ ... }},
  "sentiment_analysis": {{ ... }},
  "capital_flow_analysis": {{ ... }},
  "tomorrow_tactics": {{ ... }}
}}
```

### 1. 【看空间】：今日最高连板是谁？代表什么题材？空间是否被打开？

请在 `space_analysis` 字段中包含：
- `max_continuous_stock`: 对象，包含 `code`(代码), `name`(名称), `days`(连板天数)
- `theme`: 题材名称（字符串）
- `space_level`: "超高空间"/"高空间"/"中等空间"/"低空间"
- `analysis`: 详细分析文字（150-300字）

### 2. 【看情绪】：结合炸板率和跌停数，今日接力资金赚钱效应如何？是该进攻还是防守？

请在 `sentiment_analysis` 字段中包含：
- `money_making_effect`: "超强"/"中等"/"较差"/"极差"
- `strategy`: "激进进攻"/"稳健参与"/"防守为主"/"空仓观望"
- `reasoning`: 详细推理（150-300字）

### 3. 【看暗流】：分析龙虎榜数据，顶级游资今天主攻了哪个方向？机构在建仓什么？

请在 `capital_flow_analysis` 字段中包含：
- `hot_money_direction`: 对象，包含 `themes`(题材数组), `stocks`(股票代码数组), `concentration`("高度集中"/"分散"/"无明显方向")
- `institution_direction`: 对象，包含 `sectors`(行业数组), `style`("防御性"/"进攻性"/"均衡配置")
- `capital_consensus`: "游资机构共振"/"游资单边进攻"/"机构独立建仓"/"资金分歧"
- `analysis`: 详细分析（200-400字）

### 4. 【明日战术】：基于以上推演，制定明日集合竞价和开盘半小时的应对策略

请在 `tomorrow_tactics` 字段中包含：
- `call_auction_tactics`: 对象，包含 `participate_conditions`(参与条件), `avoid_conditions`(禁止条件)
- `opening_half_hour_tactics`: 对象，包含 `low_buy_opportunities`(低吸机会), `chase_opportunities`(追涨机会), `wait_signals`(观望信号)
- `buy_conditions`: 数组，包含3个买入条件
- `stop_loss_conditions`: 数组，包含3个止损条件

---

**输出要求**:
1. 必须输出完整的JSON格式，放在代码块中
2. 所有分析必须有理有据，引用具体数据
3. 避免模棱两可，给出明确的操作建议
4. 不要编造不存在的股票代码（可以用"主流题材龙头"等泛称）

**现在请开始分析！**"""

        return prompt

    def _get_provider_config(self, provider: str = None, model: str = None) -> Dict[str, Any]:
        """
        从数据库获取AI提供商配置

        Args:
            provider: AI提供商名称，如果为None则使用默认配置
            model: 模型名称，覆盖配置中的默认模型

        Returns:
            AI提供商配置字典
        """
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            # 如果指定了provider，查询该provider的配置
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
                # 否则获取默认的active配置
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
                # 如果没有配置，返回默认的DeepSeek配置（向后兼容）
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

            # 构建配置字典
            config = {
                "provider": row[0],
                "api_key": row[1],
                "api_base_url": row[2],
                "model_name": model or row[3],  # 如果指定了model则覆盖
                "max_tokens": row[4],
                "temperature": float(row[5]),
                "timeout": row[6]
            }

            logger.info(f"已加载AI配置: {config['provider']} / {config['model_name']}")
            return config

        except Exception as e:
            logger.error(f"获取AI配置失败: {str(e)}")
            # 失败时返回默认配置
            return {
                "provider": "deepseek",
                "api_key": settings.DEEPSEEK_API_KEY,
                "api_base_url": "https://api.deepseek.com/v1",
                "model_name": model or "deepseek-chat",
                "max_tokens": 4000,
                "temperature": 0.7,
                "timeout": 60
            }

    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """解析AI返回的JSON，优先使用 Pydantic 结构化解析，失败降级为原始 JSON"""
        try:
            if ai_response is None:
                raise ValueError("AI响应内容为None")

            if not isinstance(ai_response, str):
                raise ValueError(f"AI响应内容类型错误，期望str，实际{type(ai_response)}")

            # 优先：Pydantic 结构化解析
            from app.schemas.ai_analysis_result import SentimentAnalysisResult
            from app.services.ai_output_parser import parse_ai_json, parse_ai_json_or_dict

            parsed = parse_ai_json(ai_response, SentimentAnalysisResult)
            if parsed is not None:
                logger.info("通过 Pydantic 模型成功解析情绪分析 JSON")
                return parsed.model_dump()

            # 降级：提取 JSON dict（无 Pydantic 校验）
            raw_dict = parse_ai_json_or_dict(ai_response)
            if raw_dict is not None:
                logger.info("降级为原始 JSON dict 解析成功")
                return raw_dict

            # 最终降级：返回解析失败标记
            logger.warning("所有 JSON 解析策略均失败")
            return {
                "parse_failed": True,
                "raw_response": ai_response,
                "error": "无法从 AI 响应中提取有效 JSON"
            }

        except Exception as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return {
                "parse_failed": True,
                "raw_response": ai_response,
                "error": str(e)
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

            # 判断是否解析成功
            status = "failed" if analysis_result.get("parse_failed") else "success"

            # 提取四个分析字段
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

            # 触发通知调度（异步）
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
                # 通知失败不影响主流程
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


# 全局实例
sentiment_ai_analysis_service = SentimentAIAnalysisService()
