"""
市场情绪AI分析服务

将市场情绪数据（模块1+模块2）通过LLM进行深度分析，生成"四个灵魂拷问"式的盘后报告。

主要功能：
- 从数据库读取当日完整情绪数据
- 构建结构化Prompt（灵魂拷问模板）
- 调用AI服务生成分析报告
- 解析JSON结果并存储到数据库

作者: AI Strategy Team
创建日期: 2026-03-10
"""

import json
import os
import re
import time
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from src.database.connection_pool_manager import ConnectionPoolManager
from app.services.ai_service import AIStrategyService
from app.core.exceptions import AIServiceError


class SentimentAIAnalysisService:
    """市场情绪AI分析服务"""

    def __init__(self):
        """初始化服务"""
        self.ai_strategy_service = AIStrategyService()  # 用于创建AI客户端
        self._pool_manager = None

    def _get_pool_manager(self) -> ConnectionPoolManager:
        """获取数据库连接池管理器（懒加载）"""
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

    # 灵魂拷问Prompt模板
    SOUL_QUESTIONING_PROMPT = """# A股盘后情绪深度分析任务

你是一位拥有20年实战经验的A股短线大师，擅长通过盘后数据精准解读市场情绪和资金动向。

## 今日市场数据（{trade_date}）

### 一、大盘基础数据
- **上证指数**: 收盘 {sh_close} 点，涨跌幅 {sh_change}%
- **深证成指**: 收盘 {sz_close} 点，涨跌幅 {sz_change}%
- **创业板指**: 收盘 {cyb_close} 点，涨跌幅 {cyb_change}%
- **两市总成交额**: {total_amount} 亿元

### 二、情绪核心数据
- **涨停家数**: {limit_up_count} 只（剔除ST）
- **跌停家数**: {limit_down_count} 只
- **涨跌比**: {rise_fall_ratio:.2f}
- **炸板率**: {blast_rate:.1%}
- **最高连板**: {max_continuous_days} 天

#### 连板天梯树（高度分布）:
{continuous_ladder_text}

#### 涨停股票列表（前10）:
{limit_up_stocks_text}

#### 炸板股票列表（前5）:
{blast_stocks_text}

### 三、情绪周期量化结果
- **周期阶段**: {cycle_stage_cn}
- **赚钱效应指数**: {money_making_index:.1f}/100
- **情绪得分**: {sentiment_score:.1f}/100
- **置信度**: {confidence_score:.1f}%
- **阶段持续天数**: {stage_duration_days} 天

### 四、龙虎榜资金动向

#### 机构动向（净买入前3）:
{institution_top_stocks_text}

#### 顶级游资打板（一线游资主导）:
{hot_money_top_stocks_text}

#### 游资活跃度:
- 一线顶级游资出现: {top_tier_count} 次
- 机构出现: {institution_count} 次

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

**现在请开始分析！**
"""

    async def generate_ai_analysis(
        self,
        trade_date: str,
        provider: str = "deepseek",
        model: str = None
    ) -> Dict[str, Any]:
        """
        生成AI盘后分析

        Args:
            trade_date: 交易日期（YYYY-MM-DD）
            provider: AI提供商（deepseek/gemini/openai）
            model: 模型名称（可选，使用默认）

        Returns:
            {
                "success": True/False,
                "trade_date": "2026-03-10",
                "analysis_result": {...},
                "ai_provider": "deepseek",
                "ai_model": "deepseek-chat",
                "tokens_used": 1500,
                "generation_time": 5.2,
                "error": "错误信息（如果失败）"
            }
        """
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

            # 4. 调用AI生成情绪分析文本
            # 注意：直接调用AI客户端获取文本响应，不使用generate_strategy()
            # 因为generate_strategy()是用于生成策略代码的，会额外解析Python代码
            logger.info(f"调用 {provider} AI服务生成情绪分析...")

            client = self.ai_strategy_service.create_client(provider, provider_config)
            start_time = time.time()
            ai_response_text, tokens_used = await client.generate_strategy(prompt)
            generation_time = time.time() - start_time

            logger.info(f"AI分析完成: {len(ai_response_text)} 字符, 耗时: {generation_time:.2f}s, tokens: {tokens_used}")

            if not ai_response_text or not isinstance(ai_response_text, str):
                raise ValueError(f"AI返回内容无效: {type(ai_response_text)}")

            # 5. 解析JSON结果（从AI返回的文本中提取JSON）
            analysis_result = self._parse_ai_response(ai_response_text)

            # 6. 存储到数据库
            self._save_ai_analysis(
                trade_date=trade_date,
                analysis_result=analysis_result,
                full_report=ai_response_text,  # 保存完整的AI响应文本
                ai_provider=provider,
                ai_model=provider_config.get('model_name', 'unknown'),
                tokens_used=tokens_used,
                generation_time=round(generation_time, 2)
            )

            logger.success(f"{trade_date} AI情绪分析生成成功")

            return {
                "success": True,
                "trade_date": trade_date,
                "analysis_result": analysis_result,
                "ai_provider": provider,
                "ai_model": provider_config.get('model_name', 'unknown'),
                "tokens_used": tokens_used,
                "generation_time": round(generation_time, 2)
            }

        except Exception as e:
            logger.error(f"生成AI分析失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "trade_date": trade_date,
                "error": str(e)
            }

    def _fetch_sentiment_data(self, trade_date: str) -> Optional[Dict[str, Any]]:
        """从数据库读取完整情绪数据"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            # 查询大盘数据
            cursor.execute("""
                SELECT
                    sh_index_close, sh_index_change,
                    sz_index_close, sz_index_change,
                    cyb_index_close, cyb_index_change,
                    total_amount
                FROM market_sentiment_daily
                WHERE trade_date = %s
            """, (trade_date,))
            market_data = cursor.fetchone()

            if not market_data:
                logger.warning(f"{trade_date} 无大盘数据")
                cursor.close()
                conn.close()
                return None

            # 查询涨停板池数据
            cursor.execute("""
                SELECT
                    limit_up_count, limit_down_count, rise_fall_ratio,
                    blast_rate, max_continuous_days,
                    continuous_ladder, limit_up_stocks, blast_stocks
                FROM limit_up_pool
                WHERE trade_date = %s
            """, (trade_date,))
            limit_up_data = cursor.fetchone()

            # 查询情绪周期数据
            cursor.execute("""
                SELECT
                    cycle_stage_cn, money_making_index, sentiment_score,
                    confidence_score, stage_duration_days
                FROM market_sentiment_cycle
                WHERE trade_date = %s
            """, (trade_date,))
            cycle_data = cursor.fetchone()

            # 查询机构净买入TOP3
            cursor.execute("""
                SELECT
                    stock_code, stock_name,
                    net_amount, reason
                FROM dragon_tiger_list
                WHERE trade_date = %s
                  AND has_institution = true
                ORDER BY net_amount DESC
                LIMIT 3
            """, (trade_date,))
            institution_stocks = cursor.fetchall()

            # 查询一线游资打板数据（简化版，实际应调用hot_money_classifier）
            cursor.execute("""
                SELECT
                    stock_code, stock_name,
                    buy_amount, reason
                FROM dragon_tiger_list
                WHERE trade_date = %s
                  AND price_change >= 9.5  -- 涨停或接近涨停
                ORDER BY buy_amount DESC
                LIMIT 10
            """, (trade_date,))
            hot_money_stocks = cursor.fetchall()

            cursor.close()
            pool_manager.release_connection(conn)

            # 构建数据字典
            data = {
                "trade_date": trade_date,
                "sh_close": market_data[0] if market_data[0] else 0,
                "sh_change": market_data[1] if market_data[1] else 0,
                "sz_close": market_data[2] if market_data[2] else 0,
                "sz_change": market_data[3] if market_data[3] else 0,
                "cyb_close": market_data[4] if market_data[4] else 0,
                "cyb_change": market_data[5] if market_data[5] else 0,
                "total_amount": float(market_data[6]) if market_data[6] else 0,
                "limit_up_count": limit_up_data[0] if limit_up_data else 0,
                "limit_down_count": limit_up_data[1] if limit_up_data else 0,
                "rise_fall_ratio": float(limit_up_data[2]) if limit_up_data and limit_up_data[2] else 0,
                "blast_rate": float(limit_up_data[3]) if limit_up_data and limit_up_data[3] else 0,
                "max_continuous_days": limit_up_data[4] if limit_up_data else 0,
                "continuous_ladder": limit_up_data[5] if limit_up_data else {},
                "limit_up_stocks": limit_up_data[6] if limit_up_data else [],
                "blast_stocks": limit_up_data[7] if limit_up_data else [],
                "cycle_stage_cn": cycle_data[0] if cycle_data else "未知",
                "money_making_index": float(cycle_data[1]) if cycle_data and cycle_data[1] else 0,
                "sentiment_score": float(cycle_data[2]) if cycle_data and cycle_data[2] else 0,
                "confidence_score": float(cycle_data[3]) if cycle_data and cycle_data[3] else 0,
                "stage_duration_days": cycle_data[4] if cycle_data else 0,
                "institution_stocks": [
                    {"code": row[0], "name": row[1], "amount": float(row[2]), "reason": row[3]}
                    for row in institution_stocks
                ],
                "hot_money_stocks": [
                    {"code": row[0], "name": row[1], "amount": float(row[2]), "reason": row[3]}
                    for row in hot_money_stocks
                ],
                "top_tier_count": len(hot_money_stocks),
                "institution_count": len(institution_stocks)
            }

            return data

        except Exception as e:
            logger.error(f"读取情绪数据失败: {str(e)}")
            return None

    def _build_prompt(self, data: Dict[str, Any]) -> str:
        """构建灵魂拷问Prompt"""
        # 格式化连板天梯
        ladder = data.get('continuous_ladder', {})
        ladder_lines = []
        for days in sorted([int(k) for k in ladder.keys()], reverse=True):
            count = ladder.get(str(days), 0)
            if count > 0:
                ladder_lines.append(f"- {days}连板: {count}只")
        continuous_ladder_text = "\n".join(ladder_lines) if ladder_lines else "- 无连板数据"

        # 格式化涨停股票列表
        limit_up_stocks = data.get('limit_up_stocks', [])[:10]
        limit_up_lines = []
        for idx, stock in enumerate(limit_up_stocks, 1):
            name = stock.get('name', '未知')
            code = stock.get('code', '000000')
            reason = stock.get('reason', '')
            days = stock.get('days', 1)
            limit_up_lines.append(f"{idx}. {name}({code}) - {days}连板 - {reason}")
        limit_up_stocks_text = "\n".join(limit_up_lines) if limit_up_lines else "- 无涨停数据"

        # 格式化炸板股票列表
        blast_stocks = data.get('blast_stocks', [])[:5]
        blast_lines = []
        for idx, stock in enumerate(blast_stocks, 1):
            name = stock.get('name', '未知')
            code = stock.get('code', '000000')
            reason = stock.get('reason', '')
            blast_lines.append(f"{idx}. {name}({code}) - {reason}")
        blast_stocks_text = "\n".join(blast_lines) if blast_lines else "- 无炸板数据"

        # 格式化机构股票
        institution_stocks = data.get('institution_stocks', [])
        inst_lines = []
        for idx, stock in enumerate(institution_stocks, 1):
            name = stock.get('name', '未知')
            code = stock.get('code', '000000')
            amount = stock.get('amount', 0) / 100000000  # 转换为亿
            reason = stock.get('reason', '')
            inst_lines.append(f"{idx}. {name}({code}) - 净买入 {amount:.2f}亿 - {reason}")
        institution_top_stocks_text = "\n".join(inst_lines) if inst_lines else "- 无机构数据"

        # 格式化游资股票
        hot_money_stocks = data.get('hot_money_stocks', [])
        hm_lines = []
        for idx, stock in enumerate(hot_money_stocks, 1):
            name = stock.get('name', '未知')
            code = stock.get('code', '000000')
            amount = stock.get('amount', 0) / 100000000  # 转换为亿
            reason = stock.get('reason', '')
            hm_lines.append(f"{idx}. {name}({code}) - 买入 {amount:.2f}亿 - {reason}")
        hot_money_top_stocks_text = "\n".join(hm_lines) if hm_lines else "- 无游资数据"

        # 填充模板
        prompt = self.SOUL_QUESTIONING_PROMPT.format(
            trade_date=data['trade_date'],
            sh_close=data['sh_close'],
            sh_change=data['sh_change'],
            sz_close=data['sz_close'],
            sz_change=data['sz_change'],
            cyb_close=data['cyb_close'],
            cyb_change=data['cyb_change'],
            total_amount=data['total_amount'] / 100000000,  # 转换为亿
            limit_up_count=data['limit_up_count'],
            limit_down_count=data['limit_down_count'],
            rise_fall_ratio=data['rise_fall_ratio'],
            blast_rate=data['blast_rate'],
            max_continuous_days=data['max_continuous_days'],
            continuous_ladder_text=continuous_ladder_text,
            limit_up_stocks_text=limit_up_stocks_text,
            blast_stocks_text=blast_stocks_text,
            cycle_stage_cn=data['cycle_stage_cn'],
            money_making_index=data['money_making_index'],
            sentiment_score=data['sentiment_score'],
            confidence_score=data['confidence_score'],
            stage_duration_days=data['stage_duration_days'],
            institution_top_stocks_text=institution_top_stocks_text,
            hot_money_top_stocks_text=hot_money_top_stocks_text,
            top_tier_count=data['top_tier_count'],
            institution_count=data['institution_count']
        )

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
                "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
                "api_base_url": "https://api.deepseek.com/v1",
                "model_name": model or "deepseek-chat",
                "max_tokens": 4000,
                "temperature": 0.7,
                "timeout": 60
            }

    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """解析AI返回的JSON"""
        try:
            if ai_response is None:
                raise ValueError("AI响应内容为None")

            if not isinstance(ai_response, str):
                raise ValueError(f"AI响应内容类型错误，期望str，实际{type(ai_response)}")

            # 尝试提取JSON代码块
            json_pattern = r'```json\s*(\{[\s\S]*?\})\s*```'
            matches = re.findall(json_pattern, ai_response)

            if matches:
                analysis = json.loads(matches[0])
                logger.info("成功解析AI返回的JSON代码块")
                return analysis

            # 如果没有代码块，尝试直接解析
            analysis = json.loads(ai_response)
            logger.info("成功直接解析AI返回的JSON")
            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            # 返回原始文本作为降级方案
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
