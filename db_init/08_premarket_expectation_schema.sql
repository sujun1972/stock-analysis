-- =====================================================
-- 盘前预期管理系统数据表
-- 创建时间: 2026-03-11
-- 用途: 存储盘前计划、隔夜数据、AI碰撞分析结果
-- =====================================================

-- 1. 隔夜外盘数据表
CREATE TABLE IF NOT EXISTS overnight_market_data (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,  -- 对应A股交易日

    -- A50期指
    a50_close NUMERIC(10, 2),
    a50_change NUMERIC(10, 4),  -- 隔夜涨跌幅(%)
    a50_amplitude NUMERIC(10, 4),

    -- 中概股指数(纳斯达克金龙指数)
    china_concept_close NUMERIC(10, 2),
    china_concept_change NUMERIC(10, 4),

    -- 大宗商品
    wti_crude_close NUMERIC(10, 2),  -- WTI原油
    wti_crude_change NUMERIC(10, 4),
    comex_gold_close NUMERIC(10, 2),  -- COMEX黄金
    comex_gold_change NUMERIC(10, 4),
    lme_copper_close NUMERIC(10, 2),  -- 伦铜
    lme_copper_change NUMERIC(10, 4),

    -- 外汇
    usdcnh_close NUMERIC(10, 4),  -- 美元兑离岸人民币
    usdcnh_change NUMERIC(10, 4),

    -- 美股三大指数(参考)
    sp500_close NUMERIC(10, 2),
    sp500_change NUMERIC(10, 4),
    nasdaq_close NUMERIC(10, 2),
    nasdaq_change NUMERIC(10, 4),
    dow_close NUMERIC(10, 2),
    dow_change NUMERIC(10, 4),

    fetch_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_overnight_market_date ON overnight_market_data(trade_date DESC);
COMMENT ON TABLE overnight_market_data IS '隔夜外盘核心数据(每日8:00采集)';
COMMENT ON COLUMN overnight_market_data.a50_change IS '富时A50期指涨跌幅(直接影响A股开盘)';
COMMENT ON COLUMN overnight_market_data.china_concept_change IS '中概股指数涨跌幅(外资对中国资产态度)';

-- 2. 盘前核心新闻表
CREATE TABLE IF NOT EXISTS premarket_news_flash (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,  -- 对应A股交易日
    news_time TIMESTAMP NOT NULL,  -- 新闻发布时间

    source VARCHAR(50),  -- 'cailianshe', 'jin10'
    title VARCHAR(500),
    content TEXT,
    keywords JSONB,  -- ["超预期", "停牌", "战争"] 匹配的关键词
    importance_level VARCHAR(20),  -- 'critical', 'high', 'medium'

    -- 是否影响持仓
    affects_holdings BOOLEAN DEFAULT false,
    related_stocks JSONB,  -- [{"code": "000001", "reason": "涉及重组"}]

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_premarket_news_date ON premarket_news_flash(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_premarket_news_time ON premarket_news_flash(news_time DESC);
CREATE INDEX IF NOT EXISTS idx_premarket_news_importance ON premarket_news_flash(importance_level);

COMMENT ON TABLE premarket_news_flash IS '盘前核心新闻(22:00-8:00的重要快讯)';
COMMENT ON COLUMN premarket_news_flash.keywords IS '匹配的强情绪关键词(JSONB数组)';
COMMENT ON COLUMN premarket_news_flash.importance_level IS '重要性级别: critical=核弹级, high=高, medium=中';

-- 3. 盘前碰撞分析结果表
CREATE TABLE IF NOT EXISTS premarket_collision_analysis (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,

    -- 输入A: 昨晚战术日报摘要
    yesterday_tactics_summary JSONB,  -- 从market_sentiment_ai_analysis.tomorrow_tactics读取

    -- 输入B: 今晨外盘环境
    overnight_summary JSONB,  -- 从overnight_market_data汇总

    -- 输入C: 突发新闻摘要
    critical_news_summary JSONB,  -- 从premarket_news_flash过滤

    -- AI分析结果(LLM生成的四个维度)
    macro_tone JSONB,  -- 宏观定调: {direction: "高开/低开", confidence: "80%", reasoning: "..."}
    holdings_alert JSONB,  -- 持仓排雷: {has_risk: true, affected_stocks: [...], actions: "..."}
    plan_adjustment JSONB,  -- 计划修正: {cancel_buy: [...], early_stop_loss: [...], reasoning: "..."}
    auction_focus JSONB,  -- 竞价盯盘: {stocks: ["000001", "600000"], conditions: "...", actions: "..."}

    -- 生成的核心指令(简化版)
    action_command TEXT,  -- 极简的行动指令(200字以内)

    -- 元信息
    ai_provider VARCHAR(50),
    ai_model VARCHAR(100),
    tokens_used INTEGER,
    generation_time NUMERIC(10, 2),
    status VARCHAR(20) DEFAULT 'success',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_collision_analysis_date ON premarket_collision_analysis(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_collision_analysis_status ON premarket_collision_analysis(status);

COMMENT ON TABLE premarket_collision_analysis IS '盘前计划碰撞测试分析结果';
COMMENT ON COLUMN premarket_collision_analysis.macro_tone IS '宏观定调(AI判断今日开盘方向)';
COMMENT ON COLUMN premarket_collision_analysis.holdings_alert IS '持仓排雷(检测昨晚计划是否遇到利空)';
COMMENT ON COLUMN premarket_collision_analysis.plan_adjustment IS '计划修正(取消买入/提前止损)';
COMMENT ON COLUMN premarket_collision_analysis.auction_focus IS '竞价盯盘目标(9:15-9:25重点关注)';
COMMENT ON COLUMN premarket_collision_analysis.action_command IS '极简行动指令(200字精华)';

-- 4. 添加更新触发器
CREATE TRIGGER update_collision_analysis_updated_at
    BEFORE UPDATE ON premarket_collision_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 5. 初始化定时任务配置
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    created_at,
    updated_at
) VALUES (
    'premarket_expectation_8_00',
    'premarket',
    '盘前预期管理系统(8:00北京时间) - 抓取外盘数据+过滤新闻+AI碰撞分析',
    '0 0 * * 1-5',  -- UTC 0:00 = 北京时间 8:00
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO NOTHING;

-- 6. 创建视图：盘前数据汇总
CREATE OR REPLACE VIEW premarket_summary AS
SELECT
    c.trade_date,
    c.action_command,
    c.status,
    c.created_at,
    o.a50_change,
    o.china_concept_change,
    o.wti_crude_change,
    COUNT(DISTINCT n.id) as news_count,
    COUNT(DISTINCT CASE WHEN n.importance_level = 'critical' THEN n.id END) as critical_news_count
FROM
    premarket_collision_analysis c
    LEFT JOIN overnight_market_data o ON c.trade_date = o.trade_date
    LEFT JOIN premarket_news_flash n ON c.trade_date = n.trade_date
GROUP BY
    c.trade_date, c.action_command, c.status, c.created_at,
    o.a50_change, o.china_concept_change, o.wti_crude_change
ORDER BY c.trade_date DESC;

COMMENT ON VIEW premarket_summary IS '盘前数据汇总视图(用于快速查询)';

-- 完成提示
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE '盘前预期管理系统数据表创建完成！';
    RAISE NOTICE '创建的表:';
    RAISE NOTICE '  1. overnight_market_data - 隔夜外盘数据';
    RAISE NOTICE '  2. premarket_news_flash - 盘前核心新闻';
    RAISE NOTICE '  3. premarket_collision_analysis - AI碰撞分析结果';
    RAISE NOTICE '';
    RAISE NOTICE '创建的视图:';
    RAISE NOTICE '  - premarket_summary - 盘前数据汇总';
    RAISE NOTICE '';
    RAISE NOTICE '定时任务已配置:';
    RAISE NOTICE '  - premarket_expectation_8_00 (每日8:00)';
    RAISE NOTICE '';
    RAISE NOTICE '下一步: 执行 docker-compose exec timescaledb psql -U stock_user -d stock_analysis -f /docker-entrypoint-initdb.d/08_premarket_expectation_schema.sql';
    RAISE NOTICE '============================================';
END$$;
