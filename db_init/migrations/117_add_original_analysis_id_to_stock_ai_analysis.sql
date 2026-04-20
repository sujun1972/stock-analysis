-- 短线专家自评功能：为 stock_ai_analysis 增加 original_analysis_id 列
-- 当 analysis_type = 'hot_money_review' 时，指向被复盘的原游资观点记录 ID

ALTER TABLE stock_ai_analysis
    ADD COLUMN IF NOT EXISTS original_analysis_id INTEGER
        REFERENCES stock_ai_analysis(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_stock_ai_analysis_original_id
    ON stock_ai_analysis(original_analysis_id)
    WHERE original_analysis_id IS NOT NULL;

COMMENT ON COLUMN stock_ai_analysis.original_analysis_id
    IS '复盘类记录（如 hot_money_review）指向的原分析记录 ID';
