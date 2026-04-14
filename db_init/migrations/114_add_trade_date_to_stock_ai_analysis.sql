-- stock_ai_analysis 新增 trade_date 字段
-- 记录分析数据所对应的交易日（YYYYMMDD 格式），与系统其他交易日期格式一致
-- 数据采集从实际行情数据确定交易日，其他分析类型继承数据采集的交易日

ALTER TABLE stock_ai_analysis
    ADD COLUMN IF NOT EXISTS trade_date VARCHAR(8);

-- 按交易日查询（替代原来的 created_at >= CURRENT_DATE 逻辑）
CREATE INDEX IF NOT EXISTS idx_stock_ai_analysis_trade_date
    ON stock_ai_analysis(trade_date);

-- 按 ts_code + analysis_type + trade_date 精确查询（去重判断用）
CREATE INDEX IF NOT EXISTS idx_stock_ai_analysis_ts_type_trade
    ON stock_ai_analysis(ts_code, analysis_type, trade_date);

COMMENT ON COLUMN stock_ai_analysis.trade_date
    IS '分析数据对应的交易日（YYYYMMDD），数据采集从行情确定，其他类型继承数据采集的交易日';
