-- 创建停复牌信息表（suspend_d）
-- Tushare接口：suspend_d
-- 描述：股票每日停复牌信息
-- 数据起始：根据实际停复牌情况
-- 更新频率：不定期

CREATE TABLE IF NOT EXISTS suspend_d (
    ts_code VARCHAR(10) NOT NULL,           -- 股票代码
    trade_date VARCHAR(8) NOT NULL,         -- 停复牌日期 YYYYMMDD
    suspend_timing VARCHAR(50),             -- 日内停牌时间段（如 09:30-10:00）
    suspend_type VARCHAR(1) NOT NULL,       -- 停复牌类型：S-停牌，R-复牌
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_suspend_d_trade_date ON suspend_d(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_suspend_d_ts_code ON suspend_d(ts_code);
CREATE INDEX IF NOT EXISTS idx_suspend_d_type ON suspend_d(suspend_type);

-- 添加表注释
COMMENT ON TABLE suspend_d IS 'Tushare-每日停复牌信息';
COMMENT ON COLUMN suspend_d.ts_code IS '股票代码';
COMMENT ON COLUMN suspend_d.trade_date IS '停复牌日期 YYYYMMDD';
COMMENT ON COLUMN suspend_d.suspend_timing IS '日内停牌时间段';
COMMENT ON COLUMN suspend_d.suspend_type IS '停复牌类型：S-停牌，R-复牌';
