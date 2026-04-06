-- 107_create_sync_history.sql
-- 新增同步历史记录表，记录每次增量/全量同步的执行情况

-- 1. 新建 sync_history 表
CREATE TABLE IF NOT EXISTS sync_history (
    id              SERIAL PRIMARY KEY,
    table_key       VARCHAR(100)  NOT NULL,                  -- 对应 sync_configs.table_key
    sync_type       VARCHAR(20)   NOT NULL,                  -- 'incremental' | 'full'
    sync_strategy   VARCHAR(30),                             -- 'by_date'|'by_month'|'by_ts_code'|'snapshot' 等，无时间段策略时为 NULL
    started_at      TIMESTAMP     NOT NULL DEFAULT NOW(),    -- 同步动作开始时间
    completed_at    TIMESTAMP,                               -- 同步动作结束时间（失败时也写）
    data_start_date VARCHAR(8),                              -- 请求的数据时间范围起始 YYYYMMDD，无时间段时为 NULL
    data_end_date   VARCHAR(8),                              -- 实际数据中最大日期 YYYYMMDD，无时间段时为 NULL
    records         INT           DEFAULT 0,                 -- 入库条数
    status          VARCHAR(20)   NOT NULL DEFAULT 'running',-- 'running' | 'success' | 'failure'
    error           TEXT                                     -- 失败时的错误信息
);

CREATE INDEX IF NOT EXISTS idx_sync_history_table_key     ON sync_history(table_key);
CREATE INDEX IF NOT EXISTS idx_sync_history_started_at    ON sync_history(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_history_table_type    ON sync_history(table_key, sync_type, started_at DESC);

COMMENT ON TABLE  sync_history                    IS '数据同步历史记录，每次增量/全量同步写一行';
COMMENT ON COLUMN sync_history.table_key          IS '对应 sync_configs.table_key';
COMMENT ON COLUMN sync_history.sync_type          IS 'incremental | full';
COMMENT ON COLUMN sync_history.sync_strategy      IS '同步策略，无时间段策略时为 NULL';
COMMENT ON COLUMN sync_history.data_start_date    IS '请求的时间范围起始 YYYYMMDD';
COMMENT ON COLUMN sync_history.data_end_date      IS '实际入库数据中最大日期 YYYYMMDD';

-- 2. sync_configs 新增 incremental_sync_strategy 字段
ALTER TABLE sync_configs
    ADD COLUMN IF NOT EXISTS incremental_sync_strategy VARCHAR(30);

COMMENT ON COLUMN sync_configs.incremental_sync_strategy IS '增量同步策略：by_date_range|by_date|by_week|by_month|by_ts_code|snapshot|none，NULL 表示使用默认逻辑';

-- 为 share_float 初始化增量同步策略
UPDATE sync_configs
SET incremental_sync_strategy = 'by_date_range'
WHERE table_key = 'share_float'
  AND (incremental_sync_strategy IS NULL OR incremental_sync_strategy = 'by_month');
