-- 108_add_max_rpm_to_sync_configs.sql
-- sync_configs 新增每任务限速字段（NULL 表示继承全局配置）

ALTER TABLE sync_configs
    ADD COLUMN IF NOT EXISTS max_requests_per_minute INT NULL;

COMMENT ON COLUMN sync_configs.max_requests_per_minute IS '每分钟最大请求数（NULL 继承全局设置，0 不限速，正整数覆盖全局）';
