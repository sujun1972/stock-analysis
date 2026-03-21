-- 创建股权质押统计数据表
CREATE TABLE IF NOT EXISTS pledge_stat (
    ts_code VARCHAR(10) NOT NULL,           -- 股票代码
    end_date VARCHAR(8) NOT NULL,           -- 截止日期 (YYYYMMDD)
    pledge_count INT,                       -- 质押次数
    unrest_pledge FLOAT,                    -- 无限售股质押数量(万股)
    rest_pledge FLOAT,                      -- 限售股份质押数量(万股)
    total_share FLOAT,                      -- 总股本(万股)
    pledge_ratio FLOAT,                     -- 质押比例(%)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, end_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_pledge_stat_end_date ON pledge_stat(end_date DESC);
CREATE INDEX IF NOT EXISTS idx_pledge_stat_ts_code ON pledge_stat(ts_code);
CREATE INDEX IF NOT EXISTS idx_pledge_stat_pledge_ratio ON pledge_stat(pledge_ratio DESC);

-- 添加表注释
COMMENT ON TABLE pledge_stat IS 'Tushare接口pledge_stat: 获取股票质押统计数据,包括质押次数、质押数量、质押比例等';
COMMENT ON COLUMN pledge_stat.ts_code IS 'TS股票代码';
COMMENT ON COLUMN pledge_stat.end_date IS '截止日期 (YYYYMMDD格式)';
COMMENT ON COLUMN pledge_stat.pledge_count IS '质押次数';
COMMENT ON COLUMN pledge_stat.unrest_pledge IS '无限售股质押数量(万股)';
COMMENT ON COLUMN pledge_stat.rest_pledge IS '限售股份质押数量(万股)';
COMMENT ON COLUMN pledge_stat.total_share IS '总股本(万股)';
COMMENT ON COLUMN pledge_stat.pledge_ratio IS '质押比例(%)';
