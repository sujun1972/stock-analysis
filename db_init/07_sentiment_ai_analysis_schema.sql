-- =====================================================
-- 市场情绪AI分析表
-- =====================================================
-- 功能：存储每日基于LLM的市场情绪深度分析结果
-- 包含四个维度：看空间、看情绪、看暗流、明日战术
-- 作者：AI Strategy Team
-- 创建时间：2026-03-10
-- =====================================================

-- 删除已存在的表（如果需要重建）
DROP TABLE IF EXISTS market_sentiment_ai_analysis CASCADE;

-- 创建AI分析结果表
CREATE TABLE market_sentiment_ai_analysis (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,

    -- AI分析结果（四个灵魂拷问）
    space_analysis JSONB,           -- 【看空间】分析结果
    sentiment_analysis JSONB,       -- 【看情绪】分析结果
    capital_flow_analysis JSONB,    -- 【看暗流】分析结果
    tomorrow_tactics JSONB,         -- 【明日战术】

    -- 完整文本
    full_report TEXT,               -- AI返回的完整报告（原始文本）

    -- 元信息
    ai_provider VARCHAR(50),        -- 使用的AI提供商（deepseek/gemini/openai/claude）
    ai_model VARCHAR(100),          -- 模型名称（如deepseek-chat, gpt-4o等）
    tokens_used INTEGER,            -- Token消耗
    generation_time NUMERIC(10,2),  -- 生成耗时(秒)

    -- 分析状态
    status VARCHAR(20) DEFAULT 'success',  -- success/failed/partial
    error_message TEXT,             -- 错误信息（如果失败）

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_sentiment_ai_analysis_date ON market_sentiment_ai_analysis(trade_date DESC);
CREATE INDEX idx_sentiment_ai_analysis_status ON market_sentiment_ai_analysis(status);
CREATE INDEX idx_sentiment_ai_analysis_provider ON market_sentiment_ai_analysis(ai_provider);

-- 添加表注释
COMMENT ON TABLE market_sentiment_ai_analysis IS '市场情绪AI深度分析表，存储每日基于LLM的四维度分析结果';

-- 添加列注释
COMMENT ON COLUMN market_sentiment_ai_analysis.trade_date IS '交易日期';
COMMENT ON COLUMN market_sentiment_ai_analysis.space_analysis IS '【看空间】分析结果：最高连板、题材、空间判断';
COMMENT ON COLUMN market_sentiment_ai_analysis.sentiment_analysis IS '【看情绪】分析结果：赚钱效应、操作策略';
COMMENT ON COLUMN market_sentiment_ai_analysis.capital_flow_analysis IS '【看暗流】分析结果：游资方向、机构动向、资金共识';
COMMENT ON COLUMN market_sentiment_ai_analysis.tomorrow_tactics IS '【明日战术】：集合竞价策略、开盘半小时策略、买入条件、止损条件';
COMMENT ON COLUMN market_sentiment_ai_analysis.full_report IS 'AI返回的完整原始报告文本';
COMMENT ON COLUMN market_sentiment_ai_analysis.ai_provider IS '使用的AI提供商（deepseek/gemini/openai/claude）';
COMMENT ON COLUMN market_sentiment_ai_analysis.ai_model IS '使用的AI模型名称';
COMMENT ON COLUMN market_sentiment_ai_analysis.tokens_used IS 'Token消耗数量';
COMMENT ON COLUMN market_sentiment_ai_analysis.generation_time IS '生成耗时（秒）';
COMMENT ON COLUMN market_sentiment_ai_analysis.status IS '分析状态：success（成功）/failed（失败）/partial（部分成功）';

-- 添加触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_sentiment_ai_analysis_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_sentiment_ai_analysis_updated_at
    BEFORE UPDATE ON market_sentiment_ai_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_sentiment_ai_analysis_updated_at();

-- =====================================================
-- 示例数据结构（用于参考）
-- =====================================================

-- space_analysis 结构示例:
-- {
--   "max_continuous_stock": {
--     "code": "000001",
--     "name": "平安银行",
--     "days": 7
--   },
--   "theme": "AI芯片+算力",
--   "space_level": "超高空间",
--   "analysis": "今日市场情绪极度亢奋，最高连板达到7天..."
-- }

-- sentiment_analysis 结构示例:
-- {
--   "money_making_effect": "超强",
--   "strategy": "激进进攻",
--   "reasoning": "炸板率仅25%，涨停50只，跌停仅10只..."
-- }

-- capital_flow_analysis 结构示例:
-- {
--   "hot_money_direction": {
--     "themes": ["AI芯片", "算力"],
--     "stocks": ["000001", "000002"],
--     "concentration": "高度集中"
--   },
--   "institution_direction": {
--     "sectors": ["科技", "半导体"],
--     "style": "进攻性"
--   },
--   "capital_consensus": "游资机构共振",
--   "analysis": "溧阳路、顺德大良等一线游资今日集中打板AI芯片..."
-- }

-- tomorrow_tactics 结构示例:
-- {
--   "call_auction_tactics": {
--     "participate_conditions": "AI芯片题材，2%以内高开...",
--     "avoid_conditions": "一字板、高开>5%..."
--   },
--   "opening_half_hour_tactics": {
--     "low_buy_opportunities": "主流题材昨日强势股，开盘-2%以内回踩...",
--     "chase_opportunities": "首板秒板，放量突破...",
--     "wait_signals": "大盘跳水、炸板频繁..."
--   },
--   "buy_conditions": [
--     "符合主流题材（AI芯片、算力）",
--     "技术上处于上升趋势，不破5日线",
--     "资金关注度高，龙虎榜有游资席位"
--   ],
--   "stop_loss_conditions": [
--     "跌破买入价-3%立即止损",
--     "持股超2天不涨，时间止损",
--     "龙头股闷杀，题材退潮，全仓止损"
--   ]
-- }

-- =====================================================
-- 查询示例
-- =====================================================

-- 查询最新的AI分析
-- SELECT * FROM market_sentiment_ai_analysis
-- ORDER BY trade_date DESC
-- LIMIT 1;

-- 查询指定日期的AI分析
-- SELECT * FROM market_sentiment_ai_analysis
-- WHERE trade_date = '2026-03-10';

-- 查询最近7天的分析趋势
-- SELECT
--     trade_date,
--     sentiment_analysis->>'strategy' as strategy,
--     capital_flow_analysis->>'capital_consensus' as capital_consensus,
--     ai_provider,
--     tokens_used
-- FROM market_sentiment_ai_analysis
-- WHERE trade_date >= CURRENT_DATE - INTERVAL '7 days'
-- ORDER BY trade_date DESC;

-- 统计AI提供商使用情况
-- SELECT
--     ai_provider,
--     COUNT(*) as usage_count,
--     AVG(tokens_used) as avg_tokens,
--     AVG(generation_time) as avg_time
-- FROM market_sentiment_ai_analysis
-- WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
-- GROUP BY ai_provider;
