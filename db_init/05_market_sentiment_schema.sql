-- =====================================================
-- 市场情绪数据表结构
-- 创建时间: 2026-03-10
-- 用途: 存储每日17:30采集的市场情绪指标数据
-- =====================================================

-- 1. 交易日历表
CREATE TABLE IF NOT EXISTS trading_calendar (
    trade_date DATE PRIMARY KEY,
    is_trading_day BOOLEAN NOT NULL DEFAULT true,
    exchange VARCHAR(10) NOT NULL DEFAULT 'SSE',
    day_type VARCHAR(20),  -- '工作日', '周末', '节假日'
    holiday_name VARCHAR(100),  -- 节日名称（如非交易日）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trading_calendar_date ON trading_calendar(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_trading_calendar_trading ON trading_calendar(is_trading_day, trade_date);

COMMENT ON TABLE trading_calendar IS 'A股交易日历（精确到节假日）';
COMMENT ON COLUMN trading_calendar.trade_date IS '交易日期';
COMMENT ON COLUMN trading_calendar.is_trading_day IS '是否交易日';
COMMENT ON COLUMN trading_calendar.exchange IS '交易所代码 (SSE/SZSE)';
COMMENT ON COLUMN trading_calendar.day_type IS '日期类型';
COMMENT ON COLUMN trading_calendar.holiday_name IS '节假日名称';

-- 2. 大盘基础数据表
CREATE TABLE IF NOT EXISTS market_sentiment_daily (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,

    -- 上证指数
    sh_index_code VARCHAR(20) DEFAULT '000001',
    sh_index_close NUMERIC(10, 2),
    sh_index_change NUMERIC(10, 4),  -- 涨跌幅(%)
    sh_index_amplitude NUMERIC(10, 4),  -- 振幅(%)
    sh_index_volume BIGINT,  -- 成交量
    sh_index_amount NUMERIC(20, 2),  -- 成交额

    -- 深成指数
    sz_index_code VARCHAR(20) DEFAULT '399001',
    sz_index_close NUMERIC(10, 2),
    sz_index_change NUMERIC(10, 4),
    sz_index_amplitude NUMERIC(10, 4),
    sz_index_volume BIGINT,
    sz_index_amount NUMERIC(20, 2),

    -- 创业板指数
    cyb_index_code VARCHAR(20) DEFAULT '399006',
    cyb_index_close NUMERIC(10, 2),
    cyb_index_change NUMERIC(10, 4),
    cyb_index_amplitude NUMERIC(10, 4),
    cyb_index_volume BIGINT,
    cyb_index_amount NUMERIC(20, 2),

    -- 市场成交汇总
    total_volume BIGINT,  -- 两市总成交量（手）
    total_amount NUMERIC(20, 2),  -- 两市总成交额（元）

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_market_sentiment_date ON market_sentiment_daily(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_market_sentiment_created ON market_sentiment_daily(created_at DESC);

COMMENT ON TABLE market_sentiment_daily IS '每日大盘基础数据';
COMMENT ON COLUMN market_sentiment_daily.trade_date IS '交易日期';
COMMENT ON COLUMN market_sentiment_daily.sh_index_close IS '上证指数收盘价';
COMMENT ON COLUMN market_sentiment_daily.sh_index_change IS '上证指数涨跌幅(%)';
COMMENT ON COLUMN market_sentiment_daily.total_amount IS '两市总成交额（元）';

-- 3. 涨停板情绪池表
CREATE TABLE IF NOT EXISTS limit_up_pool (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,

    -- 涨停数据（剔除ST）
    limit_up_count INTEGER DEFAULT 0,  -- 涨停家数
    limit_down_count INTEGER DEFAULT 0,  -- 跌停家数

    -- 炸板数据
    blast_count INTEGER DEFAULT 0,  -- 炸板数量
    blast_rate NUMERIC(10, 4),  -- 炸板率 = 炸板/(炸板+涨停)

    -- 连板天梯
    max_continuous_days INTEGER DEFAULT 0,  -- 最高连板天数
    max_continuous_count INTEGER DEFAULT 0,  -- 最高连板股票数量
    continuous_ladder JSONB,  -- 连板天梯树 {"2连板": 15, "3连板": 8, ...}

    -- 涨停板详细列表（股票代码）
    limit_up_stocks JSONB,  -- [{"code": "000001", "name": "平安银行", "days": 1, "reason": "xx"}, ...]

    -- 炸板详细列表
    blast_stocks JSONB,  -- [{"code": "000002", "name": "万科A", "blast_times": 2, "final_change": 5.5}, ...]

    -- 统计数据
    total_stocks INTEGER DEFAULT 0,  -- 总股票数
    rise_count INTEGER DEFAULT 0,  -- 上涨家数
    fall_count INTEGER DEFAULT 0,  -- 下跌家数
    rise_fall_ratio NUMERIC(10, 4),  -- 涨跌比

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_limit_up_pool_date ON limit_up_pool(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_limit_up_pool_blast_rate ON limit_up_pool(blast_rate);
CREATE INDEX IF NOT EXISTS idx_limit_up_pool_max_days ON limit_up_pool(max_continuous_days DESC);

COMMENT ON TABLE limit_up_pool IS '涨停板情绪池（核心情绪指标）';
COMMENT ON COLUMN limit_up_pool.trade_date IS '交易日期';
COMMENT ON COLUMN limit_up_pool.limit_up_count IS '涨停家数（剔除ST）';
COMMENT ON COLUMN limit_up_pool.blast_rate IS '炸板率';
COMMENT ON COLUMN limit_up_pool.continuous_ladder IS '连板天梯树（JSONB）';

-- 4. 龙虎榜数据表
CREATE TABLE IF NOT EXISTS dragon_tiger_list (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),

    -- 上榜原因
    reason VARCHAR(200),  -- '日涨幅偏离值达7%', '日换手率达20%'
    reason_type VARCHAR(50),  -- '涨幅偏离', '换手异常', '振幅异常'

    -- 股票行情
    close_price NUMERIC(10, 2),  -- 收盘价
    price_change NUMERIC(10, 4),  -- 涨跌幅(%)
    turnover_rate NUMERIC(10, 4),  -- 换手率(%)

    -- 买卖数据
    buy_amount NUMERIC(20, 2),  -- 买入总额
    sell_amount NUMERIC(20, 2),  -- 卖出总额
    net_amount NUMERIC(20, 2),  -- 净额 = 买入 - 卖出

    -- 前五买卖席位（JSONB存储）
    top_buyers JSONB,  -- [{"rank": 1, "name": "机构专用", "amount": 5000000}, ...]
    top_sellers JSONB,  -- [{"rank": 1, "name": "XX营业部", "amount": 3000000}, ...]

    -- 是否有机构参与
    has_institution BOOLEAN DEFAULT false,
    institution_count INTEGER DEFAULT 0,

    -- 营业部数据
    dept_buy_count INTEGER DEFAULT 0,  -- 买入营业部数量
    dept_sell_count INTEGER DEFAULT 0,  -- 卖出营业部数量

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(trade_date, stock_code)
);

CREATE INDEX IF NOT EXISTS idx_dragon_tiger_date ON dragon_tiger_list(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_dragon_tiger_stock ON dragon_tiger_list(stock_code);
CREATE INDEX IF NOT EXISTS idx_dragon_tiger_net_amount ON dragon_tiger_list(net_amount DESC);
CREATE INDEX IF NOT EXISTS idx_dragon_tiger_institution ON dragon_tiger_list(has_institution, trade_date);
CREATE INDEX IF NOT EXISTS idx_dragon_tiger_reason ON dragon_tiger_list(reason_type);

COMMENT ON TABLE dragon_tiger_list IS '龙虎榜数据';
COMMENT ON COLUMN dragon_tiger_list.trade_date IS '交易日期';
COMMENT ON COLUMN dragon_tiger_list.stock_code IS '股票代码';
COMMENT ON COLUMN dragon_tiger_list.reason IS '上榜原因';
COMMENT ON COLUMN dragon_tiger_list.net_amount IS '净买入额（正数表示净买入）';
COMMENT ON COLUMN dragon_tiger_list.top_buyers IS '买入前五席位（JSONB）';
COMMENT ON COLUMN dragon_tiger_list.has_institution IS '是否有机构参与';

-- 5. 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要的表添加触发器
DROP TRIGGER IF EXISTS update_market_sentiment_daily_updated_at ON market_sentiment_daily;
CREATE TRIGGER update_market_sentiment_daily_updated_at
    BEFORE UPDATE ON market_sentiment_daily
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_limit_up_pool_updated_at ON limit_up_pool;
CREATE TRIGGER update_limit_up_pool_updated_at
    BEFORE UPDATE ON limit_up_pool
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_dragon_tiger_list_updated_at ON dragon_tiger_list;
CREATE TRIGGER update_dragon_tiger_list_updated_at
    BEFORE UPDATE ON dragon_tiger_list
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 6. 插入初始交易日历数据（2024-2025年部分节假日）
-- 注意：完整数据需要通过API同步
INSERT INTO trading_calendar (trade_date, is_trading_day, exchange, day_type, holiday_name) VALUES
    -- 2024年节假日示例
    ('2024-01-01', false, 'SSE', '节假日', '元旦'),
    ('2024-02-10', false, 'SSE', '节假日', '春节'),
    ('2024-02-11', false, 'SSE', '节假日', '春节'),
    ('2024-02-12', false, 'SSE', '节假日', '春节'),
    ('2024-02-13', false, 'SSE', '节假日', '春节'),
    ('2024-02-14', false, 'SSE', '节假日', '春节'),
    ('2024-02-15', false, 'SSE', '节假日', '春节'),
    ('2024-02-16', false, 'SSE', '节假日', '春节'),
    ('2024-02-17', false, 'SSE', '节假日', '春节'),
    ('2024-04-04', false, 'SSE', '节假日', '清明节'),
    ('2024-04-05', false, 'SSE', '节假日', '清明节'),
    ('2024-04-06', false, 'SSE', '节假日', '清明节'),
    ('2024-05-01', false, 'SSE', '节假日', '劳动节'),
    ('2024-05-02', false, 'SSE', '节假日', '劳动节'),
    ('2024-05-03', false, 'SSE', '节假日', '劳动节'),
    ('2024-05-04', false, 'SSE', '节假日', '劳动节'),
    ('2024-05-05', false, 'SSE', '节假日', '劳动节'),
    ('2024-06-10', false, 'SSE', '节假日', '端午节'),
    ('2024-09-15', false, 'SSE', '节假日', '中秋节'),
    ('2024-09-16', false, 'SSE', '节假日', '中秋节'),
    ('2024-09-17', false, 'SSE', '节假日', '中秋节'),
    ('2024-10-01', false, 'SSE', '节假日', '国庆节'),
    ('2024-10-02', false, 'SSE', '节假日', '国庆节'),
    ('2024-10-03', false, 'SSE', '节假日', '国庆节'),
    ('2024-10-04', false, 'SSE', '节假日', '国庆节'),
    ('2024-10-05', false, 'SSE', '节假日', '国庆节'),
    ('2024-10-06', false, 'SSE', '节假日', '国庆节'),
    ('2024-10-07', false, 'SSE', '节假日', '国庆节'),
    -- 2025年节假日示例
    ('2025-01-01', false, 'SSE', '节假日', '元旦'),
    ('2025-01-28', false, 'SSE', '节假日', '春节'),
    ('2025-01-29', false, 'SSE', '节假日', '春节'),
    ('2025-01-30', false, 'SSE', '节假日', '春节'),
    ('2025-01-31', false, 'SSE', '节假日', '春节'),
    ('2025-02-01', false, 'SSE', '节假日', '春节'),
    ('2025-02-02', false, 'SSE', '节假日', '春节'),
    ('2025-02-03', false, 'SSE', '节假日', '春节'),
    ('2025-02-04', false, 'SSE', '节假日', '春节')
ON CONFLICT (trade_date) DO NOTHING;

-- 7. 初始化scheduled_tasks表记录
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    created_at,
    updated_at
) VALUES (
    'daily_sentiment_sync',
    'sentiment',
    '市场情绪数据抓取（17:30北京时间）- 包含交易日历、大盘数据、涨停板池、龙虎榜',
    '30 9 * * 1-5',  -- UTC 9:30 = 北京时间 17:30
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO NOTHING;

-- 8. 创建视图：每日情绪汇总（方便查询）
CREATE OR REPLACE VIEW daily_sentiment_summary AS
SELECT
    m.trade_date,
    m.sh_index_close,
    m.sh_index_change,
    m.total_amount,
    l.limit_up_count,
    l.limit_down_count,
    l.blast_rate,
    l.max_continuous_days,
    l.rise_fall_ratio,
    COUNT(DISTINCT d.id) as dragon_tiger_count,
    COUNT(DISTINCT CASE WHEN d.has_institution THEN d.id END) as institution_count
FROM
    market_sentiment_daily m
    LEFT JOIN limit_up_pool l ON m.trade_date = l.trade_date
    LEFT JOIN dragon_tiger_list d ON m.trade_date = d.trade_date
GROUP BY
    m.trade_date, m.sh_index_close, m.sh_index_change, m.total_amount,
    l.limit_up_count, l.limit_down_count, l.blast_rate,
    l.max_continuous_days, l.rise_fall_ratio;

COMMENT ON VIEW daily_sentiment_summary IS '每日情绪数据汇总视图';

-- 完成提示
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE '市场情绪数据表结构创建完成！';
    RAISE NOTICE '创建的表:';
    RAISE NOTICE '  1. trading_calendar - 交易日历';
    RAISE NOTICE '  2. market_sentiment_daily - 大盘基础数据';
    RAISE NOTICE '  3. limit_up_pool - 涨停板情绪池';
    RAISE NOTICE '  4. dragon_tiger_list - 龙虎榜数据';
    RAISE NOTICE '';
    RAISE NOTICE '创建的视图:';
    RAISE NOTICE '  - daily_sentiment_summary - 每日情绪汇总';
    RAISE NOTICE '';
    RAISE NOTICE '下一步: 同步完整交易日历数据';
    RAISE NOTICE '  API: POST /api/sentiment/calendar/sync';
    RAISE NOTICE '============================================';
END$$;
