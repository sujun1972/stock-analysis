-- stock_ai_analysis 新增 followup_triggers 字段
-- 用于 CIO 综合决策的"复查触发器"：时间触发（指定事件/日期）+ 价格触发（上下方阈值）
-- 结构示例见 backend/app/schemas/ai_analysis_result.py 的 FollowupTriggers 模型
-- 仅 analysis_type='cio_directive' 类型会写入该列，其他类型保持 NULL

ALTER TABLE stock_ai_analysis
    ADD COLUMN IF NOT EXISTS followup_triggers JSONB;

COMMENT ON COLUMN stock_ai_analysis.followup_triggers
    IS 'CIO 复查触发器（JSONB）：time_triggers[]（事件/日期驱动） + price_triggers[]（上下方价位驱动） + review_horizon_days';

-- 股票列表页"关注价位/日期"按最近一条 CIO 记录查询：
--   SELECT DISTINCT ON (ts_code) ts_code, followup_triggers, created_at
--   FROM stock_ai_analysis
--   WHERE analysis_type = 'cio_directive'
--   ORDER BY ts_code, created_at DESC
-- 现有索引 idx_stock_ai_analysis_ts_code_type_created 已覆盖，无需新增
