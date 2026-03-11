"""
盘前碰撞分析服务

核心功能：
1. 获取或生成最新的明日战术（优先读取当日，缺失则生成上一交易日）
2. 读取今晨的隔夜外盘数据（A50、中概股、大宗商品、汇率、美股）
3. 读取今晨的核心新闻（22:00-8:00财联社/金十快讯）
4. 调用LLM进行碰撞测试（战术vs现实）
5. 生成四维分析报告（宏观定调、持仓排雷、计划修正、竞价盯盘）
6. 输出极简行动指令（200字精华）

作者: AI Strategy Team
创建日期: 2026-03-11
最后更新: 2026-03-11（优化战术获取逻辑）
"""

import json
import os
import re
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from src.database.connection_pool_manager import ConnectionPoolManager
from app.services.ai_service import AIStrategyService
from app.core.exceptions import AIServiceError


class PremarketAnalysisService:
    """盘前碰撞分析服务"""

    def __init__(self):
        self.ai_strategy_service = AIStrategyService()
        self._pool_manager = None

    def _get_pool_manager(self) -> ConnectionPoolManager:
        """获取数据库连接池"""
        if self._pool_manager is None:
            db_config = {
                'host': os.getenv('DATABASE_HOST', 'timescaledb'),
                'port': int(os.getenv('DATABASE_PORT', '5432')),
                'database': os.getenv('DATABASE_NAME', 'stock_analysis'),
                'user': os.getenv('DATABASE_USER', 'stock_user'),
                'password': os.getenv('DATABASE_PASSWORD', 'stock_password_123')
            }
            self._pool_manager = ConnectionPoolManager(db_config)
        return self._pool_manager

    # LLM碰撞测试Prompt模板
    COLLISION_PROMPT = """# A股盘前计划碰撞测试任务

你是一位拥有20年实战经验的A股短线大师,现在需要在开盘前(8:00-8:30)进行"计划碰撞测试"。

## 输入A：昨晚的计划(来自明日战术日报)

{yesterday_tactics}

## 输入B：今晨的环境(隔夜外盘数据)

### 外盘核心指标
- **富时A50期指**: {a50_change}%  ← 直接影响A股大盘开盘
- **中概股指数**: {china_concept_change}%  ← 外资对中国资产的态度
- **WTI原油**: {oil_change}%  | **COMEX黄金**: {gold_change}%  | **伦敦铜**: {copper_change}%
- **美元兑人民币**: {usdcnh_change}%  ← 外资流向指标
- **美股三大指数**: 标普{sp500_change}% | 纳指{nasdaq_change}% | 道指{dow_change}%

## 输入C：突发新闻(22:00-8:00核心快讯)

{critical_news}

---

## 请执行以下分析,并以JSON格式输出

**非常重要**: 请将整个分析结果放在一个JSON代码块中，格式如下：

```json
{{
  "macro_tone": {{
    "direction": "高开/低开/平开",
    "confidence": "置信度(%)",
    "a50_impact": "A50对开盘的具体影响分析",
    "reasoning": "综合外盘判断(100字)"
  }},
  "holdings_alert": {{
    "has_risk": true,
    "affected_sectors": ["板块1", "板块2"],
    "affected_stocks": [
      {{"code": "000001", "name": "某股票", "reason": "利空原因"}}
    ],
    "actions": "针对持仓的具体操作建议"
  }},
  "plan_adjustment": {{
    "cancel_buy": [
      {{"stock": "000001", "reason": "昨晚计划买入,但今晨外盘XX,取消"}}
    ],
    "early_stop_loss": [
      {{"stock": "600000", "reason": "昨晚计划止损XX价,但今晨新闻YY,提前到竞价止损"}}
    ],
    "keep_plan": "哪些计划依然有效,可以继续执行",
    "reasoning": "调整理由(150字)"
  }},
  "auction_focus": {{
    "stocks": [
      {{"code": "000001", "name": "某股票", "reason": "竞价必盯原因"}}
    ],
    "conditions": {{
      "participate_conditions": "如果XXX,则参与竞价买入",
      "avoid_conditions": "如果YYY,则竞价止损"
    }},
    "actions": "9:15-9:25具体操作步骤"
  }}
}}
```

## 核心要求

1. **宏观定调**: 根据A50和外盘,预测今日A股开盘是高开情绪好,还是低开有压力?
2. **持仓排雷**: 今晨的新闻中,是否有针对我计划中关注板块/个股的重大利空或利好?
3. **计划修正(最关键)**: 基于今晨环境,昨晚的买入计划是否需要取消?昨晚的止损动作是否需要提前到竞价阶段直接核按钮?
4. **竞价盯盘目标**: 给出今早9:15-9:25必须死盯的1-2个核心标的及应对条件

**输出格式**: 必须输出完整的JSON代码块,避免编造不存在的股票代码。如果昨晚的战术日报中没有具体股票,则根据市场情绪和外盘环境给出通用建议。

现在请开始碰撞测试!
"""

    async def generate_collision_analysis(
        self,
        trade_date: str,
        provider: str = "deepseek",
        model: str = None
    ) -> Dict[str, Any]:
        """
        生成盘前碰撞分析

        Args:
            trade_date: 交易日期 (YYYY-MM-DD)
            provider: AI提供商
            model: 模型名称

        Returns:
            分析结果
        """
        try:
            logger.info(f"开始生成 {trade_date} 的盘前碰撞分析...")

            # 1. 获取或生成战术数据
            # 策略：
            # - 优先读取当日的战术（如果已生成）
            # - 如果未生成，尝试生成上一个交易日的战术
            # - 如果生成失败，使用默认空值
            yesterday_tactics = await self._get_or_generate_tactics(trade_date)

            if not yesterday_tactics:
                logger.warning(f"{trade_date} 无法获取或生成战术数据，使用默认空值")
                yesterday_tactics = {
                    "call_auction_tactics": {"participate_conditions": "无昨日计划", "avoid_conditions": "无昨日计划"},
                    "buy_conditions": ["无昨日计划"],
                    "stop_loss_conditions": ["无昨日计划"]
                }

            # 2. 读取今晨外盘数据
            overnight_data = self._fetch_overnight_data(trade_date)
            if not overnight_data:
                return {
                    "success": False,
                    "trade_date": trade_date,
                    "error": f"{trade_date} 无隔夜外盘数据,请先执行盘前数据同步"
                }

            # 3. 读取今晨核心新闻
            critical_news = self._fetch_critical_news(trade_date)

            # 4. 构建Prompt
            prompt = self._build_collision_prompt(
                yesterday_tactics, overnight_data, critical_news
            )

            # 5. 调用AI生成
            provider_config = self._get_provider_config(provider, model)
            client = self.ai_strategy_service.create_client(provider, provider_config)

            start_time = time.time()
            ai_response_text, tokens_used = await client.generate_strategy(prompt)
            generation_time = time.time() - start_time

            logger.info(f"AI碰撞分析完成: {len(ai_response_text)} 字符, 耗时: {generation_time:.2f}s, tokens: {tokens_used}")

            # 6. 解析JSON结果
            analysis_result = self._parse_collision_response(ai_response_text)

            # 7. 生成极简行动指令
            action_command = self._generate_action_command(analysis_result)

            # 8. 保存到数据库
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
                generation_time=round(generation_time, 2)
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
                "generation_time": round(generation_time, 2)
            }

        except Exception as e:
            logger.error(f"生成盘前碰撞分析失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "trade_date": trade_date,
                "error": str(e)
            }

    async def _get_or_generate_tactics(self, trade_date: str) -> Optional[Dict]:
        """
        获取或生成战术数据

        逻辑：
        1. 优先读取当日的战术（如果已生成）
        2. 如果当日战术未生成，尝试生成上一个交易日的战术
        3. 如果生成失败或无法生成，返回None

        示例：
        - 11日晚22:00：读取11日的战术（已生成） ✓
        - 11日早08:00：读取11日的战术（如果昨晚已生成） ✓
        - 11日早08:00：如果11日战术未生成，生成10日战术 ✓
        """
        try:
            # 步骤1: 尝试读取当日战术
            tactics = self._fetch_tactics_by_date(trade_date)
            if tactics:
                logger.info(f"读取到 {trade_date} 的明日战术")
                return tactics

            # 步骤2: 当日战术不存在，获取上一个交易日
            logger.warning(f"{trade_date} 的战术未生成，尝试生成上一个交易日的战术")
            prev_trade_date = self._get_previous_trade_date(trade_date)

            if not prev_trade_date:
                logger.error(f"无法获取 {trade_date} 的上一个交易日")
                return None

            # 步骤3: 检查上一个交易日是否已有战术
            prev_tactics = self._fetch_tactics_by_date(prev_trade_date)
            if prev_tactics:
                logger.info(f"读取到上一交易日 {prev_trade_date} 的明日战术")
                return prev_tactics

            # 步骤4: 尝试生成上一个交易日的战术
            logger.info(f"开始生成 {prev_trade_date} 的明日战术...")
            generation_result = await self._trigger_tactics_generation(prev_trade_date)

            if generation_result:
                logger.success(f"成功生成 {prev_trade_date} 的明日战术")
                # 重新读取生成的战术
                tactics = self._fetch_tactics_by_date(prev_trade_date)
                return tactics
            else:
                logger.error(f"生成 {prev_trade_date} 的战术失败")
                return None

        except Exception as e:
            logger.error(f"获取或生成战术数据失败: {e}", exc_info=True)
            return None

    def _fetch_tactics_by_date(self, trade_date: str) -> Optional[Dict]:
        """读取指定日期的战术"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT tomorrow_tactics
                FROM market_sentiment_ai_analysis
                WHERE trade_date = %s
                  AND status = 'success'
                  AND tomorrow_tactics IS NOT NULL
            """, (trade_date,))

            row = cursor.fetchone()
            cursor.close()
            pool_manager.release_connection(conn)

            if row and row[0]:
                return row[0]  # JSONB字段直接返回dict
            return None

        except Exception as e:
            logger.error(f"读取 {trade_date} 的战术失败: {e}")
            return None

    def _get_previous_trade_date(self, trade_date: str) -> Optional[str]:
        """获取上一个交易日"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            # 查询小于当前日期的最新一个有情绪数据的交易日
            cursor.execute("""
                SELECT trade_date
                FROM market_sentiment_daily
                WHERE trade_date < %s
                ORDER BY trade_date DESC
                LIMIT 1
            """, (trade_date,))

            row = cursor.fetchone()
            cursor.close()
            pool_manager.release_connection(conn)

            if row:
                return str(row[0])
            return None

        except Exception as e:
            logger.error(f"获取上一交易日失败: {e}")
            return None

    async def _trigger_tactics_generation(self, trade_date: str) -> bool:
        """触发生成指定日期的战术"""
        try:
            # 导入情绪AI分析服务
            from app.services.sentiment_ai_analysis_service import SentimentAIAnalysisService

            sentiment_service = SentimentAIAnalysisService()

            # 调用AI分析服务生成战术
            result = await sentiment_service.generate_ai_analysis(
                trade_date=trade_date,
                provider="deepseek"  # 使用默认的deepseek
            )

            return result.get("success", False)

        except Exception as e:
            logger.error(f"触发生成 {trade_date} 战术失败: {e}", exc_info=True)
            return False

    def _fetch_overnight_data(self, trade_date: str) -> Optional[Dict]:
        """读取今晨外盘数据"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    a50_change, china_concept_change,
                    wti_crude_change, comex_gold_change, lme_copper_change,
                    usdcnh_change, sp500_change, nasdaq_change, dow_change
                FROM overnight_market_data
                WHERE trade_date = %s
            """, (trade_date,))

            row = cursor.fetchone()
            cursor.close()
            pool_manager.release_connection(conn)

            if row:
                return {
                    'a50_change': float(row[0]) if row[0] else 0,
                    'china_concept_change': float(row[1]) if row[1] else 0,
                    'wti_crude_change': float(row[2]) if row[2] else 0,
                    'comex_gold_change': float(row[3]) if row[3] else 0,
                    'lme_copper_change': float(row[4]) if row[4] else 0,
                    'usdcnh_change': float(row[5]) if row[5] else 0,
                    'sp500_change': float(row[6]) if row[6] else 0,
                    'nasdaq_change': float(row[7]) if row[7] else 0,
                    'dow_change': float(row[8]) if row[8] else 0,
                }
            return None

        except Exception as e:
            logger.error(f"读取隔夜数据失败: {e}")
            return None

    def _fetch_critical_news(self, trade_date: str) -> str:
        """读取今晨核心新闻"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT news_time, title, content, keywords
                FROM premarket_news_flash
                WHERE trade_date = %s
                  AND importance_level IN ('critical', 'high')
                ORDER BY news_time DESC
                LIMIT 10
            """, (trade_date,))

            rows = cursor.fetchall()
            cursor.close()
            pool_manager.release_connection(conn)

            if not rows:
                return "今晨无重大突发新闻"

            news_lines = []
            for idx, row in enumerate(rows, 1):
                news_time = row[0].strftime('%H:%M') if row[0] else ''
                title = row[1]
                keywords = ', '.join(row[3]) if row[3] else ''
                news_lines.append(f"{idx}. [{news_time}] {title} (关键词: {keywords})")

            return "\n".join(news_lines)

        except Exception as e:
            logger.error(f"读取核心新闻失败: {e}")
            return "今晨无重大突发新闻"

    def _build_collision_prompt(
        self,
        yesterday_tactics: Dict,
        overnight_data: Dict,
        critical_news: str
    ) -> str:
        """构建碰撞测试Prompt"""
        # 格式化昨晚战术
        tactics_text = json.dumps(yesterday_tactics, ensure_ascii=False, indent=2)

        prompt = self.COLLISION_PROMPT.format(
            yesterday_tactics=tactics_text,
            a50_change=overnight_data.get('a50_change', 0),
            china_concept_change=overnight_data.get('china_concept_change', 0),
            oil_change=overnight_data.get('wti_crude_change', 0),
            gold_change=overnight_data.get('comex_gold_change', 0),
            copper_change=overnight_data.get('lme_copper_change', 0),
            usdcnh_change=overnight_data.get('usdcnh_change', 0),
            sp500_change=overnight_data.get('sp500_change', 0),
            nasdaq_change=overnight_data.get('nasdaq_change', 0),
            dow_change=overnight_data.get('dow_change', 0),
            critical_news=critical_news
        )

        return prompt

    def _parse_collision_response(self, ai_response: str) -> Dict:
        """解析AI返回的碰撞分析JSON"""
        try:
            # 提取JSON代码块
            json_pattern = r'```json\s*(\{[\s\S]*?\})\s*```'
            matches = re.findall(json_pattern, ai_response)

            if matches:
                result = json.loads(matches[0])
                logger.info("成功解析AI返回的JSON代码块")
                return result

            # 尝试直接解析
            result = json.loads(ai_response)
            logger.info("成功直接解析AI返回的JSON")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return {
                "parse_failed": True,
                "raw_response": ai_response,
                "error": str(e)
            }

    def _generate_action_command(self, analysis: Dict) -> str:
        """生成极简的行动指令(200字以内)"""
        if analysis.get("parse_failed"):
            return "AI分析解析失败,请手动查看完整报告"

        try:
            macro = analysis.get('macro_tone', {})
            holdings = analysis.get('holdings_alert', {})
            adjustment = analysis.get('plan_adjustment', {})
            auction = analysis.get('auction_focus', {})

            command_lines = []

            # 开盘预期
            direction = macro.get('direction', '未知')
            confidence = macro.get('confidence', '?')
            command_lines.append(f"【开盘预期】{direction}, 信心{confidence}")

            # 持仓风险
            if holdings.get('has_risk'):
                affected = holdings.get('affected_stocks', [])
                if affected and len(affected) > 0:
                    stock_names = ', '.join([s.get('name', s.get('code', '')) for s in affected[:2]])
                    command_lines.append(f"【风险提示】{stock_names}有利空, 关注")

            # 计划调整
            cancel_count = len(adjustment.get('cancel_buy', []))
            stop_count = len(adjustment.get('early_stop_loss', []))
            if cancel_count > 0 or stop_count > 0:
                command_lines.append(f"【计划修正】取消买入{cancel_count}只, 提前止损{stop_count}只")
            else:
                keep_plan = adjustment.get('keep_plan', '')
                if keep_plan:
                    command_lines.append(f"【计划修正】{keep_plan[:30]}")

            # 竞价目标
            focus_stocks = auction.get('stocks', [])
            if focus_stocks and len(focus_stocks) > 0:
                stock_names = ', '.join([s.get('name', s.get('code', '')) for s in focus_stocks[:2]])
                command_lines.append(f"【竞价盯盘】死盯: {stock_names}")

            return "\n".join(command_lines) if command_lines else "今日保持观望，谨慎参与"

        except Exception as e:
            logger.error(f"生成行动指令失败: {e}")
            return "行动指令生成失败,请查看详细分析"

    def _get_provider_config(self, provider: str = None, model: str = None) -> Dict:
        """获取AI提供商配置"""
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
                # 如果没有配置，返回默认的DeepSeek配置
                logger.warning(f"未找到AI提供商配置: {provider}，使用默认配置")
                return {
                    "provider": "deepseek",
                    "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
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
                "model_name": model or row[3],
                "max_tokens": row[4],
                "temperature": float(row[5]),
                "timeout": row[6]
            }

            logger.info(f"已加载AI配置: {config['provider']} / {config['model_name']}")
            return config

        except Exception as e:
            logger.error(f"获取AI配置失败: {e}")
            # 失败时返回默认配置
            return {
                "provider": "deepseek",
                "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
                "api_base_url": "https://api.deepseek.com/v1",
                "model_name": model or "deepseek-chat",
                "max_tokens": 4000,
                "temperature": 0.7,
                "timeout": 60
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
        generation_time: float
    ):
        """保存碰撞分析结果到数据库"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            # 构建汇总数据
            yesterday_summary = {
                "call_auction_tactics": yesterday_tactics.get("call_auction_tactics"),
                "buy_conditions": yesterday_tactics.get("buy_conditions"),
                "stop_loss_conditions": yesterday_tactics.get("stop_loss_conditions")
            }

            overnight_summary = overnight_data

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
                json.dumps(overnight_summary, ensure_ascii=False),
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
                status
            ))

            conn.commit()
            cursor.close()
            pool_manager.release_connection(conn)

            logger.success(f"{trade_date} 碰撞分析已保存到数据库")

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
                SELECT
                    trade_date, macro_tone, holdings_alert,
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
                "created_at": str(row[11]) if row[11] else None
            }

        except Exception as e:
            logger.error(f"获取碰撞分析结果失败: {e}")
            return None


# 全局实例
premarket_analysis_service = PremarketAnalysisService()
