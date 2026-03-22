-- 业绩快报表（Tushare express_vip 接口）
-- 2000积分/次
-- 说明：获取上市公司业绩快报

CREATE TABLE IF NOT EXISTS express (
    ts_code VARCHAR(10) NOT NULL,              -- TS股票代码
    ann_date VARCHAR(8) NOT NULL,              -- 公告日期 YYYYMMDD
    end_date VARCHAR(8) NOT NULL,              -- 报告期 YYYYMMDD
    revenue DOUBLE PRECISION,                  -- 营业收入(元)
    operate_profit DOUBLE PRECISION,           -- 营业利润(元)
    total_profit DOUBLE PRECISION,             -- 利润总额(元)
    n_income DOUBLE PRECISION,                 -- 净利润(元)
    total_assets DOUBLE PRECISION,             -- 总资产(元)
    total_hldr_eqy_exc_min_int DOUBLE PRECISION, -- 股东权益合计(不含少数股东权益)(元)
    diluted_eps DOUBLE PRECISION,              -- 每股收益(摊薄)(元)
    diluted_roe DOUBLE PRECISION,              -- 净资产收益率(摊薄)(%)
    yoy_net_profit DOUBLE PRECISION,           -- 去年同期修正后净利润
    bps DOUBLE PRECISION,                      -- 每股净资产
    yoy_sales DOUBLE PRECISION,                -- 同比增长率:营业收入
    yoy_op DOUBLE PRECISION,                   -- 同比增长率:营业利润
    yoy_tp DOUBLE PRECISION,                   -- 同比增长率:利润总额
    yoy_dedu_np DOUBLE PRECISION,              -- 同比增长率:归属母公司股东的净利润
    yoy_eps DOUBLE PRECISION,                  -- 同比增长率:基本每股收益
    yoy_roe DOUBLE PRECISION,                  -- 同比增减:加权平均净资产收益率
    growth_assets DOUBLE PRECISION,            -- 比年初增长率:总资产
    yoy_equity DOUBLE PRECISION,               -- 比年初增长率:归属母公司的股东权益
    growth_bps DOUBLE PRECISION,               -- 比年初增长率:归属于母公司股东的每股净资产
    or_last_year DOUBLE PRECISION,             -- 去年同期营业收入
    op_last_year DOUBLE PRECISION,             -- 去年同期营业利润
    tp_last_year DOUBLE PRECISION,             -- 去年同期利润总额
    np_last_year DOUBLE PRECISION,             -- 去年同期净利润
    eps_last_year DOUBLE PRECISION,            -- 去年同期每股收益
    open_net_assets DOUBLE PRECISION,          -- 期初净资产
    open_bps DOUBLE PRECISION,                 -- 期初每股净资产
    perf_summary TEXT,                         -- 业绩简要说明
    is_audit INTEGER,                          -- 是否审计：1是 0否
    remark TEXT,                               -- 备注
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, ann_date, end_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_express_ann_date ON express(ann_date DESC);
CREATE INDEX IF NOT EXISTS idx_express_end_date ON express(end_date DESC);
CREATE INDEX IF NOT EXISTS idx_express_ts_code ON express(ts_code);

-- 添加表注释
COMMENT ON TABLE express IS 'Tushare业绩快报数据 (express_vip接口, 2000积分/次)';
COMMENT ON COLUMN express.ts_code IS 'TS股票代码';
COMMENT ON COLUMN express.ann_date IS '公告日期 YYYYMMDD';
COMMENT ON COLUMN express.end_date IS '报告期 YYYYMMDD (每个季度最后一天)';
COMMENT ON COLUMN express.revenue IS '营业收入(元)';
COMMENT ON COLUMN express.operate_profit IS '营业利润(元)';
COMMENT ON COLUMN express.total_profit IS '利润总额(元)';
COMMENT ON COLUMN express.n_income IS '净利润(元)';
COMMENT ON COLUMN express.total_assets IS '总资产(元)';
COMMENT ON COLUMN express.total_hldr_eqy_exc_min_int IS '股东权益合计(不含少数股东权益)(元)';
COMMENT ON COLUMN express.diluted_eps IS '每股收益(摊薄)(元)';
COMMENT ON COLUMN express.diluted_roe IS '净资产收益率(摊薄)(%)';
COMMENT ON COLUMN express.yoy_net_profit IS '去年同期修正后净利润';
COMMENT ON COLUMN express.bps IS '每股净资产';
COMMENT ON COLUMN express.yoy_sales IS '同比增长率:营业收入';
COMMENT ON COLUMN express.yoy_op IS '同比增长率:营业利润';
COMMENT ON COLUMN express.yoy_tp IS '同比增长率:利润总额';
COMMENT ON COLUMN express.yoy_dedu_np IS '同比增长率:归属母公司股东的净利润';
COMMENT ON COLUMN express.yoy_eps IS '同比增长率:基本每股收益';
COMMENT ON COLUMN express.yoy_roe IS '同比增减:加权平均净资产收益率';
COMMENT ON COLUMN express.growth_assets IS '比年初增长率:总资产';
COMMENT ON COLUMN express.yoy_equity IS '比年初增长率:归属母公司的股东权益';
COMMENT ON COLUMN express.growth_bps IS '比年初增长率:归属于母公司股东的每股净资产';
COMMENT ON COLUMN express.or_last_year IS '去年同期营业收入';
COMMENT ON COLUMN express.op_last_year IS '去年同期营业利润';
COMMENT ON COLUMN express.tp_last_year IS '去年同期利润总额';
COMMENT ON COLUMN express.np_last_year IS '去年同期净利润';
COMMENT ON COLUMN express.eps_last_year IS '去年同期每股收益';
COMMENT ON COLUMN express.open_net_assets IS '期初净资产';
COMMENT ON COLUMN express.open_bps IS '期初每股净资产';
COMMENT ON COLUMN express.perf_summary IS '业绩简要说明';
COMMENT ON COLUMN express.is_audit IS '是否审计：1是 0否';
COMMENT ON COLUMN express.remark IS '备注';
