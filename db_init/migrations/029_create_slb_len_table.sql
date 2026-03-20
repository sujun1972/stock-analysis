-- 029: 创建转融资交易汇总表 (slb_len)
-- 描述: 转融通融资汇总数据表
-- Tushare接口: slb_len
-- 积分消耗: 2000积分/分钟200次，5000积分500次
-- 单次限量: 最大5000行

-- 创建转融资交易汇总表
CREATE TABLE IF NOT EXISTS slb_len (
    trade_date VARCHAR(8) NOT NULL,           -- 交易日期（YYYYMMDD）
    ob DECIMAL(20, 2),                        -- 期初余额(亿元)
    auc_amount DECIMAL(20, 2),                -- 竞价成交金额(亿元)
    repo_amount DECIMAL(20, 2),               -- 再借成交金额(亿元)
    repay_amount DECIMAL(20, 2),              -- 偿还金额(亿元)
    cb DECIMAL(20, 2),                        -- 期末余额(亿元)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date)
);

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_slb_len_trade_date ON slb_len(trade_date DESC);

-- 添加表注释
COMMENT ON TABLE slb_len IS '转融资交易汇总表（转融通融资汇总）';
COMMENT ON COLUMN slb_len.trade_date IS '交易日期（YYYYMMDD）';
COMMENT ON COLUMN slb_len.ob IS '期初余额（亿元）';
COMMENT ON COLUMN slb_len.auc_amount IS '竞价成交金额（亿元）';
COMMENT ON COLUMN slb_len.repo_amount IS '再借成交金额（亿元）';
COMMENT ON COLUMN slb_len.repay_amount IS '偿还金额（亿元）';
COMMENT ON COLUMN slb_len.cb IS '期末余额（亿元）';
