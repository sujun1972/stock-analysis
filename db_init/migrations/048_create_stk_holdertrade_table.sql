-- 创建股东增减持表
CREATE TABLE IF NOT EXISTS stk_holdertrade (
    ts_code VARCHAR(10) NOT NULL,
    ann_date VARCHAR(8) NOT NULL,
    holder_name VARCHAR(200),
    holder_type VARCHAR(10),
    in_de VARCHAR(10),
    change_vol FLOAT,
    change_ratio FLOAT,
    after_share FLOAT,
    after_ratio FLOAT,
    avg_price FLOAT,
    total_share FLOAT,
    begin_date VARCHAR(8),
    close_date VARCHAR(8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, ann_date, holder_name, in_de)
);

CREATE INDEX idx_stk_holdertrade_ann_date ON stk_holdertrade(ann_date DESC);
CREATE INDEX idx_stk_holdertrade_ts_code ON stk_holdertrade(ts_code);
CREATE INDEX idx_stk_holdertrade_holder_type ON stk_holdertrade(holder_type);
CREATE INDEX idx_stk_holdertrade_in_de ON stk_holdertrade(in_de);

COMMENT ON TABLE stk_holdertrade IS 'Tushare - 股东增减持数据（stk_holdertrade，2000积分）';
COMMENT ON COLUMN stk_holdertrade.ts_code IS 'TS股票代码';
COMMENT ON COLUMN stk_holdertrade.ann_date IS '公告日期 YYYYMMDD';
COMMENT ON COLUMN stk_holdertrade.holder_name IS '股东名称';
COMMENT ON COLUMN stk_holdertrade.holder_type IS '股东类型 G=高管 P=个人 C=公司';
COMMENT ON COLUMN stk_holdertrade.in_de IS '类型 IN=增持 DE=减持';
COMMENT ON COLUMN stk_holdertrade.change_vol IS '变动数量';
COMMENT ON COLUMN stk_holdertrade.change_ratio IS '占流通比例(%)';
COMMENT ON COLUMN stk_holdertrade.after_share IS '变动后持股';
COMMENT ON COLUMN stk_holdertrade.after_ratio IS '变动后占流通比例(%)';
COMMENT ON COLUMN stk_holdertrade.avg_price IS '平均价格';
COMMENT ON COLUMN stk_holdertrade.total_share IS '持股总数';
COMMENT ON COLUMN stk_holdertrade.begin_date IS '增减持开始日期 YYYYMMDD';
COMMENT ON COLUMN stk_holdertrade.close_date IS '增减持结束日期 YYYYMMDD';
