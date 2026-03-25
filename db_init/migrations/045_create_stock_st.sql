-- ST股票列表表
-- Tushare stock_st 接口数据
-- 获取ST股票列表，可根据交易日期获取历史上每天的ST列表
-- 权限：3000积分起
-- 数据从20160101开始

CREATE TABLE IF NOT EXISTS stock_st (
    -- 主键字段
    ts_code VARCHAR(10) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,

    -- 基本信息
    name VARCHAR(50),
    type VARCHAR(10),
    type_name VARCHAR(50),

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (ts_code, trade_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_stock_st_trade_date ON stock_st(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_stock_st_ts_code ON stock_st(ts_code);
CREATE INDEX IF NOT EXISTS idx_stock_st_type ON stock_st(type);

-- 添加表注释
COMMENT ON TABLE stock_st IS 'ST股票列表 - Tushare stock_st接口，数据从20160101开始，每天上午9:20更新';
COMMENT ON COLUMN stock_st.ts_code IS '股票代码';
COMMENT ON COLUMN stock_st.trade_date IS '交易日期 YYYYMMDD';
COMMENT ON COLUMN stock_st.name IS '股票名称';
COMMENT ON COLUMN stock_st.type IS 'ST类型';
COMMENT ON COLUMN stock_st.type_name IS 'ST类型名称';
