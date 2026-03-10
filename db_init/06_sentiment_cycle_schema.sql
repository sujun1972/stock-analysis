-- =====================================================
-- 情绪周期量化计算模块 - 数据表结构
-- 创建时间: 2026-03-10
-- 用途: 赚钱效应模型 + 游资席位打标系统
-- =====================================================

-- 1. 市场情绪周期记录表
CREATE TABLE IF NOT EXISTS market_sentiment_cycle (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,

    -- ========== 情绪周期阶段 ==========
    cycle_stage VARCHAR(20) NOT NULL,  -- 'freezing', 'starting', 'fermenting', 'retreating'
    cycle_stage_cn VARCHAR(20) NOT NULL,  -- '冰点', '启动', '发酵', '退潮'
    confidence_score NUMERIC(5, 2),  -- 置信度 0-100

    -- ========== 计算指标 ==========
    -- 涨跌停数据
    limit_up_count INTEGER DEFAULT 0,
    limit_down_count INTEGER DEFAULT 0,
    limit_ratio NUMERIC(10, 4),  -- 涨停/跌停比值

    -- 炸板数据
    blast_count INTEGER DEFAULT 0,
    blast_rate NUMERIC(10, 4),  -- 炸板率

    -- 连板数据
    max_continuous_days INTEGER DEFAULT 0,  -- 最高连板天数
    max_continuous_count INTEGER DEFAULT 0,  -- 最高连板股票数
    continuous_growth_rate NUMERIC(10, 4),  -- 连板高度增长率 (相比前一日)

    -- ========== 核心指数 ==========
    money_making_index NUMERIC(5, 2),  -- 赚钱效应指数 (0-100)
    sentiment_score NUMERIC(5, 2),  -- 综合情绪得分 (0-100)

    -- ========== 阶段统计 ==========
    stage_duration_days INTEGER DEFAULT 1,  -- 当前阶段持续天数
    previous_stage VARCHAR(20),  -- 前一个阶段
    stage_change_date DATE,  -- 阶段切换日期

    -- ========== 市场统计 ==========
    total_stocks INTEGER DEFAULT 0,  -- 总股票数
    rise_count INTEGER DEFAULT 0,  -- 上涨家数
    fall_count INTEGER DEFAULT 0,  -- 下跌家数
    rise_fall_ratio NUMERIC(10, 4),  -- 涨跌比

    -- 市场成交
    total_amount NUMERIC(20, 2),  -- 两市总成交额
    amount_change_rate NUMERIC(10, 4),  -- 成交额变化率

    -- ========== 详细分析 ==========
    analysis_result JSONB,  -- 详细分析结果 (JSON格式)
    /*
    {
        "stage_reason": "涨停家数超过50家，连板高度达到7天",
        "key_indicators": {
            "limit_up_strength": "强",
            "continuous_height": "高",
            "blast_pressure": "低"
        },
        "market_hotspots": ["AI", "新能源", "半导体"],
        "risk_warning": "情绪过热，注意回调风险"
    }
    */

    -- ========== 时间戳 ==========
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_sentiment_cycle_date ON market_sentiment_cycle(trade_date DESC);
CREATE INDEX idx_sentiment_cycle_stage ON market_sentiment_cycle(cycle_stage, trade_date);
CREATE INDEX idx_sentiment_cycle_money_index ON market_sentiment_cycle(money_making_index DESC);

-- 注释
COMMENT ON TABLE market_sentiment_cycle IS '市场情绪周期记录表 - 赚钱效应模型';
COMMENT ON COLUMN market_sentiment_cycle.cycle_stage IS '情绪周期阶段 (freezing/starting/fermenting/retreating)';
COMMENT ON COLUMN market_sentiment_cycle.money_making_index IS '赚钱效应指数 (0-100分)';
COMMENT ON COLUMN market_sentiment_cycle.sentiment_score IS '综合情绪得分 (0-100分)';
COMMENT ON COLUMN market_sentiment_cycle.limit_ratio IS '涨停/跌停比值 (>1表示涨停多)';
COMMENT ON COLUMN market_sentiment_cycle.continuous_growth_rate IS '连板高度增长率 (正数增长，负数下降)';


-- 2. 游资席位字典表
CREATE TABLE IF NOT EXISTS hot_money_seats (
    id SERIAL PRIMARY KEY,
    seat_name VARCHAR(200) NOT NULL UNIQUE,  -- 完整席位名称

    -- ========== 席位分类 ==========
    seat_type VARCHAR(50) NOT NULL,  -- 'top_tier', 'famous', 'retail_base', 'institution', 'unknown'
    seat_label VARCHAR(50) NOT NULL,  -- '[一线顶级游资]', '[知名游资]', '[散户大本营]', '[机构]'

    -- ========== 匹配规则 ==========
    match_keywords TEXT[],  -- 匹配关键词数组
    match_type VARCHAR(20) DEFAULT 'exact',  -- 'exact', 'fuzzy', 'keyword'
    priority INTEGER DEFAULT 0,  -- 优先级 (数字越大优先级越高)

    -- ========== 席位信息 ==========
    city VARCHAR(50),  -- 城市
    broker VARCHAR(100),  -- 券商名称
    branch_office VARCHAR(200),  -- 营业部全称
    region VARCHAR(50),  -- 地区 (华东/华南/西南等)

    -- ========== 统计信息 ==========
    appearance_count INTEGER DEFAULT 0,  -- 上榜次数
    total_buy_amount NUMERIC(20, 2) DEFAULT 0,  -- 累计买入金额
    total_sell_amount NUMERIC(20, 2) DEFAULT 0,  -- 累计卖出金额
    net_amount NUMERIC(20, 2) DEFAULT 0,  -- 累计净买入
    win_rate NUMERIC(5, 2),  -- 胜率 (%)
    avg_hold_days NUMERIC(5, 2),  -- 平均持仓天数

    -- ========== 席位特征 ==========
    trade_style VARCHAR(50),  -- '激进', '稳健', '短线', '波段', '中长线'
    specialty_sectors TEXT[],  -- 擅长板块 ['AI', '新能源', '半导体']
    is_active BOOLEAN DEFAULT true,  -- 是否活跃
    activity_level VARCHAR(20),  -- 活跃度 'high', 'medium', 'low'

    -- ========== 标签 ==========
    tags TEXT[],  -- 自定义标签 ['打板高手', '龙头战法', '低吸']

    -- ========== 备注 ==========
    description TEXT,  -- 席位描述

    -- ========== 数据更新 ==========
    last_appearance_date DATE,  -- 最后一次上榜日期
    data_source VARCHAR(50) DEFAULT 'manual',  -- 'manual', 'auto', 'import'

    -- ========== 时间戳 ==========
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_hot_money_type ON hot_money_seats(seat_type);
CREATE INDEX idx_hot_money_label ON hot_money_seats(seat_label);
CREATE INDEX idx_hot_money_active ON hot_money_seats(is_active, appearance_count DESC);
CREATE INDEX idx_hot_money_broker ON hot_money_seats(broker);
CREATE INDEX idx_hot_money_city ON hot_money_seats(city);
CREATE INDEX idx_hot_money_priority ON hot_money_seats(priority DESC);

-- 注释
COMMENT ON TABLE hot_money_seats IS '游资席位字典表 - 标签化处理系统';
COMMENT ON COLUMN hot_money_seats.seat_type IS '席位类型 (top_tier/famous/retail_base/institution/unknown)';
COMMENT ON COLUMN hot_money_seats.seat_label IS '席位标签 (显示用)';
COMMENT ON COLUMN hot_money_seats.match_keywords IS '匹配关键词数组';
COMMENT ON COLUMN hot_money_seats.priority IS '优先级 (用于冲突时的匹配选择)';
COMMENT ON COLUMN hot_money_seats.win_rate IS '胜率 (基于历史数据计算)';
COMMENT ON COLUMN hot_money_seats.trade_style IS '交易风格';


-- 3. 游资操作记录表 (用于统计分析)
CREATE TABLE IF NOT EXISTS hot_money_operations (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,

    -- ========== 席位信息 ==========
    seat_id INTEGER REFERENCES hot_money_seats(id),
    seat_name VARCHAR(200) NOT NULL,
    seat_type VARCHAR(50) NOT NULL,
    seat_label VARCHAR(50) NOT NULL,

    -- ========== 股票信息 ==========
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),

    -- ========== 交易数据 ==========
    operation_type VARCHAR(20) NOT NULL,  -- 'buy', 'sell', 'both'
    buy_amount NUMERIC(20, 2) DEFAULT 0,
    sell_amount NUMERIC(20, 2) DEFAULT 0,
    net_amount NUMERIC(20, 2),  -- 净买入额

    buy_rank INTEGER,  -- 买入榜排名
    sell_rank INTEGER,  -- 卖出榜排名

    -- ========== 股票行情 ==========
    close_price NUMERIC(10, 2),
    price_change NUMERIC(10, 4),
    is_limit_up BOOLEAN DEFAULT false,  -- 是否涨停
    continuous_days INTEGER DEFAULT 0,  -- 连板天数

    -- ========== 统计分析 ==========
    is_leading_stock BOOLEAN DEFAULT false,  -- 是否龙头股
    sector VARCHAR(100),  -- 所属板块

    -- ========== 时间戳 ==========
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(trade_date, seat_name, stock_code)
);

-- 索引
CREATE INDEX idx_hot_money_ops_date ON hot_money_operations(trade_date DESC);
CREATE INDEX idx_hot_money_ops_seat ON hot_money_operations(seat_id, trade_date DESC);
CREATE INDEX idx_hot_money_ops_stock ON hot_money_operations(stock_code, trade_date DESC);
CREATE INDEX idx_hot_money_ops_type ON hot_money_operations(seat_type, operation_type, trade_date DESC);
CREATE INDEX idx_hot_money_ops_limit_up ON hot_money_operations(is_limit_up, trade_date DESC);

COMMENT ON TABLE hot_money_operations IS '游资操作记录表 - 用于统计和分析';
COMMENT ON COLUMN hot_money_operations.operation_type IS '操作类型 (buy/sell/both)';
COMMENT ON COLUMN hot_money_operations.net_amount IS '净买入额 (正数买入，负数卖出)';


-- 4. 插入默认游资席位数据
INSERT INTO hot_money_seats (seat_name, seat_type, seat_label, match_keywords, city, broker, trade_style, priority, description) VALUES

-- ========== [一线顶级游资] - 市场风向标 ==========
('中信证券股份有限公司上海溧阳路证券营业部', 'top_tier', '[一线顶级游资]', ARRAY['溧阳路', '中信上海溧阳'], '上海', '中信证券', '激进', 100, 'A股最知名游资席位，有"中国第一游资"之称'),
('中信证券股份有限公司上海东方路证券营业部', 'top_tier', '[一线顶级游资]', ARRAY['东方路', '中信东方'], '上海', '中信证券', '激进', 95, '顶级游资，擅长龙头战法'),
('国泰君安证券股份有限公司顺德大良营业部', 'top_tier', '[一线顶级游资]', ARRAY['顺德大良', '国泰顺德'], '佛山', '国泰君安', '稳健', 95, '老牌顶级游资，操作稳健'),
('国泰君安证券股份有限公司成都北一环路证券营业部', 'top_tier', '[一线顶级游资]', ARRAY['成都北一环', '国泰成都'], '成都', '国泰君安', '波段', 90, '西南地区顶级游资'),
('华泰证券股份有限公司深圳益田路荣超商务中心证券营业部', 'top_tier', '[一线顶级游资]', ARRAY['荣超商务', '益田路荣超'], '深圳', '华泰证券', '激进', 95, '深圳顶级游资，擅长题材炒作'),
('华泰证券股份有限公司深圳益田路江苏大厦证券营业部', 'top_tier', '[一线顶级游资]', ARRAY['江苏大厦', '益田路江苏'], '深圳', '华泰证券', '激进', 95, '深圳顶级游资'),
('银河证券绍兴证券营业部', 'top_tier', '[一线顶级游资]', ARRAY['银河绍兴', '绍兴'], '绍兴', '银河证券', '短线', 90, '著名短线游资'),
('招商证券股份有限公司深圳蛇口工业七路证券营业部', 'top_tier', '[一线顶级游资]', ARRAY['蛇口工业', '招商蛇口'], '深圳', '招商证券', '波段', 85, '招商系顶级游资'),
('申万宏源西部证券有限公司成都天府二街证券营业部', 'top_tier', '[一线顶级游资]', ARRAY['天府二街', '申万成都'], '成都', '申万宏源', '激进', 85, '成都知名游资'),
('申万宏源西部证券有限公司重庆民权路证券营业部', 'top_tier', '[一线顶级游资]', ARRAY['重庆民权', '申万重庆'], '重庆', '申万宏源', '激进', 85, '重庆知名游资'),
('财通证券股份有限公司杭州上塘路证券营业部', 'top_tier', '[一线顶级游资]', ARRAY['上塘路', '财通上塘'], '杭州', '财通证券', '稳健', 85, '浙江系顶级游资'),
('财通证券股份有限公司台州解放南路证券营业部', 'top_tier', '[一线顶级游资]', ARRAY['台州解放', '财通台州'], '台州', '财通证券', '波段', 80, '浙江系游资'),
('中信建投证券股份有限公司杭州庆春路证券营业部', 'top_tier', '[一线顶级游资]', ARRAY['庆春路', '中信建投杭州'], '杭州', '中信建投', '波段', 80, '杭州知名游资'),

-- ========== [散户大本营] - 散户集中地 ==========
('东方财富证券股份有限公司拉萨团结路第二证券营业部', 'retail_base', '[散户大本营]', ARRAY['拉萨团结路', '东财拉萨'], '拉萨', '东方财富', '激进', 60, '著名散户集中营'),
('东方财富证券股份有限公司拉萨东环路第二证券营业部', 'retail_base', '[散户大本营]', ARRAY['拉萨东环路', '东财拉萨'], '拉萨', '东方财富', '激进', 60, '散户大本营'),
('东方财富证券股份有限公司拉萨金珠西路第二证券营业部', 'retail_base', '[散户大本营]', ARRAY['拉萨金珠', '东财拉萨'], '拉萨', '东方财富', '激进', 60, '散户集中地'),
('华泰证券股份有限公司深圳福田区深南大道证券营业部', 'retail_base', '[散户大本营]', ARRAY['深圳福田', '华泰福田'], '深圳', '华泰证券', '激进', 50, '深圳散户聚集地'),

-- ========== [知名游资] - 二线游资 ==========
('中信证券股份有限公司杭州延安路证券营业部', 'famous', '[知名游资]', ARRAY['杭州延安', '中信杭州'], '杭州', '中信证券', '波段', 70, '杭州知名游资'),
('中信证券股份有限公司北京总部证券营业部', 'famous', '[知名游资]', ARRAY['中信北京', '北京总部'], '北京', '中信证券', '稳健', 70, '北京知名席位'),
('国泰君安证券股份有限公司深圳益田路证券营业部', 'famous', '[知名游资]', ARRAY['国泰益田', '国泰深圳'], '深圳', '国泰君安', '波段', 70, '深圳知名游资'),
('海通证券股份有限公司上海建国西路证券营业部', 'famous', '[知名游资]', ARRAY['建国西路', '海通上海'], '上海', '海通证券', '稳健', 65, '上海知名席位'),
('光大证券股份有限公司宁波解放南路证券营业部', 'famous', '[知名游资]', ARRAY['宁波解放', '光大宁波'], '宁波', '光大证券', '波段', 65, '宁波知名游资')

ON CONFLICT (seat_name) DO NOTHING;


-- 5. 创建更新时间触发器
DROP TRIGGER IF EXISTS update_sentiment_cycle_updated_at ON market_sentiment_cycle;
CREATE TRIGGER update_sentiment_cycle_updated_at
    BEFORE UPDATE ON market_sentiment_cycle
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_hot_money_seats_updated_at ON hot_money_seats;
CREATE TRIGGER update_hot_money_seats_updated_at
    BEFORE UPDATE ON hot_money_seats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- 6. 创建实用视图

-- 6.1 每日情绪周期摘要视图
CREATE OR REPLACE VIEW daily_sentiment_cycle_summary AS
SELECT
    sc.trade_date,
    sc.cycle_stage,
    sc.cycle_stage_cn,
    sc.money_making_index,
    sc.sentiment_score,
    sc.limit_up_count,
    sc.limit_down_count,
    sc.limit_ratio,
    sc.blast_rate,
    sc.max_continuous_days,
    sc.stage_duration_days,
    sc.total_amount,
    -- 涨跌家数
    sc.rise_count,
    sc.fall_count,
    sc.rise_fall_ratio,
    -- 龙虎榜统计
    COUNT(DISTINCT dt.id) as dragon_tiger_count,
    COUNT(DISTINCT CASE WHEN dt.has_institution THEN dt.id END) as institution_count
FROM
    market_sentiment_cycle sc
    LEFT JOIN dragon_tiger_list dt ON sc.trade_date = dt.trade_date
GROUP BY
    sc.trade_date, sc.cycle_stage, sc.cycle_stage_cn, sc.money_making_index,
    sc.sentiment_score, sc.limit_up_count, sc.limit_down_count, sc.limit_ratio,
    sc.blast_rate, sc.max_continuous_days, sc.stage_duration_days,
    sc.total_amount, sc.rise_count, sc.fall_count, sc.rise_fall_ratio
ORDER BY sc.trade_date DESC;

COMMENT ON VIEW daily_sentiment_cycle_summary IS '每日情绪周期摘要视图 (便于前端展示)';


-- 6.2 游资活跃度排行视图
CREATE OR REPLACE VIEW hot_money_activity_ranking AS
SELECT
    hm.id,
    hm.seat_name,
    hm.seat_type,
    hm.seat_label,
    hm.city,
    hm.broker,
    hm.trade_style,
    hm.appearance_count,
    hm.total_buy_amount,
    hm.total_sell_amount,
    hm.net_amount,
    hm.win_rate,
    hm.last_appearance_date,
    hm.is_active,
    -- 计算活跃度得分
    (
        hm.appearance_count * 0.4 +
        COALESCE(hm.win_rate, 0) * 0.3 +
        (CASE
            WHEN hm.last_appearance_date >= CURRENT_DATE - INTERVAL '30 days' THEN 30
            WHEN hm.last_appearance_date >= CURRENT_DATE - INTERVAL '90 days' THEN 15
            ELSE 0
        END)
    ) as activity_score
FROM
    hot_money_seats hm
WHERE
    hm.is_active = true
ORDER BY activity_score DESC, appearance_count DESC;

COMMENT ON VIEW hot_money_activity_ranking IS '游资活跃度排行榜';


-- 7. 创建辅助函数

-- 7.1 获取情绪周期阶段中文名
CREATE OR REPLACE FUNCTION get_cycle_stage_cn(stage VARCHAR)
RETURNS VARCHAR AS $$
BEGIN
    RETURN CASE stage
        WHEN 'freezing' THEN '冰点'
        WHEN 'starting' THEN '启动'
        WHEN 'fermenting' THEN '发酵'
        WHEN 'retreating' THEN '退潮'
        ELSE '未知'
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION get_cycle_stage_cn IS '将英文阶段名转换为中文';


-- 8. 完成提示
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE '情绪周期量化计算模块 - 数据表创建完成！';
    RAISE NOTICE '';
    RAISE NOTICE '创建的表:';
    RAISE NOTICE '  1. market_sentiment_cycle      情绪周期记录表';
    RAISE NOTICE '  2. hot_money_seats              游资席位字典表';
    RAISE NOTICE '  3. hot_money_operations         游资操作记录表';
    RAISE NOTICE '';
    RAISE NOTICE '创建的视图:';
    RAISE NOTICE '  1. daily_sentiment_cycle_summary     每日情绪周期摘要';
    RAISE NOTICE '  2. hot_money_activity_ranking        游资活跃度排行';
    RAISE NOTICE '';
    RAISE NOTICE '创建的函数:';
    RAISE NOTICE '  1. get_cycle_stage_cn()              阶段名中文转换';
    RAISE NOTICE '';
    RAISE NOTICE '初始化游资席位: 已插入 20+ 知名游资席位';
    RAISE NOTICE '';
    RAISE NOTICE '下一步: 运行核心计算引擎';
    RAISE NOTICE '============================================';
END$$;
