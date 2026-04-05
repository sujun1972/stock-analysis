-- 为 sync_configs 表添加 data_source 字段
-- 每个同步任务独立配置数据源（tushare 或 akshare），默认 tushare
ALTER TABLE sync_configs ADD COLUMN IF NOT EXISTS data_source VARCHAR(20) DEFAULT 'tushare';
UPDATE sync_configs SET data_source = 'tushare' WHERE data_source IS NULL;
COMMENT ON COLUMN sync_configs.data_source IS '数据源：tushare（默认）或 akshare';
