-- =====================================================
-- 数据一致性保障 - 数据库迁移脚本
-- 版本: 003
-- 日期: 2026-01-30
-- 说明: 创建数据版本管理、校验和、修复和增量更新相关表
-- =====================================================

-- =====================================================
-- 1. 数据版本表 (data_versions)
-- =====================================================
CREATE TABLE IF NOT EXISTS data_versions (
    version_id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    version_number VARCHAR(50) NOT NULL,      -- 格式: v20260130_001
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_source VARCHAR(50),                  -- akshare/tushare
    record_count INTEGER,
    checksum VARCHAR(64),                     -- SHA256校验和
    checksum_method VARCHAR(20) DEFAULT 'sha256',
    is_active BOOLEAN DEFAULT TRUE,           -- 是否为当前活跃版本
    parent_version_id BIGINT,                 -- 父版本ID(用于增量更新)
    metadata JSONB,                           -- 其他元数据
    UNIQUE(symbol, version_number),
    FOREIGN KEY (parent_version_id) REFERENCES data_versions(version_id) ON DELETE SET NULL
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_data_versions_symbol ON data_versions(symbol);
CREATE INDEX IF NOT EXISTS idx_data_versions_active ON data_versions(is_active);
CREATE INDEX IF NOT EXISTS idx_data_versions_created ON data_versions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_data_versions_symbol_active ON data_versions(symbol, is_active);

-- 添加注释
COMMENT ON TABLE data_versions IS '数据版本管理表,记录每次数据更新的版本信息';
COMMENT ON COLUMN data_versions.version_number IS '版本号,格式: v20260130_001';
COMMENT ON COLUMN data_versions.checksum IS 'SHA256校验和,用于验证数据完整性';
COMMENT ON COLUMN data_versions.is_active IS '是否为当前活跃版本,每个股票只有一个活跃版本';
COMMENT ON COLUMN data_versions.parent_version_id IS '父版本ID,用于追踪增量更新链';

-- =====================================================
-- 2. 分块校验和表 (data_checksums)
-- =====================================================
CREATE TABLE IF NOT EXISTS data_checksums (
    id BIGSERIAL PRIMARY KEY,
    version_id BIGINT NOT NULL,
    chunk_type VARCHAR(20) NOT NULL,          -- 'daily' / 'weekly' / 'monthly'
    chunk_key VARCHAR(50) NOT NULL,           -- 日期或日期范围 (如: '2026-01-30' 或 '2026-01-W04')
    checksum VARCHAR(64) NOT NULL,
    record_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (version_id) REFERENCES data_versions(version_id) ON DELETE CASCADE,
    UNIQUE(version_id, chunk_type, chunk_key)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_data_checksums_version ON data_checksums(version_id);
CREATE INDEX IF NOT EXISTS idx_data_checksums_chunk ON data_checksums(chunk_type, chunk_key);

-- 添加注释
COMMENT ON TABLE data_checksums IS '分块校验和表,用于大数据集的增量校验';
COMMENT ON COLUMN data_checksums.chunk_type IS '分块类型: daily(按天), weekly(按周), monthly(按月)';
COMMENT ON COLUMN data_checksums.chunk_key IS '分块键,如日期或日期范围';

-- =====================================================
-- 3. 数据修复日志表 (data_repair_logs)
-- =====================================================
CREATE TABLE IF NOT EXISTS data_repair_logs (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    repair_date DATE NOT NULL,
    issue_type VARCHAR(50) NOT NULL,         -- missing_value/outlier/logic_error/duplicate/checksum_mismatch
    issue_count INTEGER,
    issue_details JSONB,                     -- 详细的问题描述
    repair_method VARCHAR(50),               -- fill_forward/interpolation/winsorize/redownload
    repair_status VARCHAR(20) NOT NULL,      -- success/failed/partial
    before_checksum VARCHAR(64),
    after_checksum VARCHAR(64),
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_repair_logs_symbol ON data_repair_logs(symbol);
CREATE INDEX IF NOT EXISTS idx_repair_logs_status ON data_repair_logs(repair_status);
CREATE INDEX IF NOT EXISTS idx_repair_logs_created ON data_repair_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_repair_logs_issue_type ON data_repair_logs(issue_type);

-- 添加注释
COMMENT ON TABLE data_repair_logs IS '数据修复日志表,记录所有数据修复操作';
COMMENT ON COLUMN data_repair_logs.issue_type IS '问题类型: missing_value(缺失值), outlier(异常值), logic_error(逻辑错误), duplicate(重复记录), checksum_mismatch(校验和不匹配)';
COMMENT ON COLUMN data_repair_logs.repair_method IS '修复方法: fill_forward(前向填充), interpolation(插值), winsorize(缩尾), redownload(重新下载)';
COMMENT ON COLUMN data_repair_logs.repair_status IS '修复状态: success(成功), failed(失败), partial(部分成功)';

-- =====================================================
-- 4. 增量更新日志表 (incremental_update_logs)
-- =====================================================
CREATE TABLE IF NOT EXISTS incremental_update_logs (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    update_type VARCHAR(20) NOT NULL,        -- daily/weekly/backfill/manual
    start_date DATE,
    end_date DATE,
    new_records INTEGER DEFAULT 0,
    updated_records INTEGER DEFAULT 0,
    unchanged_records INTEGER DEFAULT 0,
    deleted_records INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL,             -- success/failed/partial/running
    duration_seconds FLOAT,
    data_source VARCHAR(50),
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_inc_update_symbol ON incremental_update_logs(symbol);
CREATE INDEX IF NOT EXISTS idx_inc_update_status ON incremental_update_logs(status);
CREATE INDEX IF NOT EXISTS idx_inc_update_created ON incremental_update_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inc_update_type ON incremental_update_logs(update_type);

-- 添加注释
COMMENT ON TABLE incremental_update_logs IS '增量更新日志表,记录每次增量更新的详细信息';
COMMENT ON COLUMN incremental_update_logs.update_type IS '更新类型: daily(日常), weekly(周度), backfill(回填), manual(手动)';
COMMENT ON COLUMN incremental_update_logs.status IS '状态: success(成功), failed(失败), partial(部分成功), running(运行中)';
COMMENT ON COLUMN incremental_update_logs.duration_seconds IS '更新耗时(秒)';

-- =====================================================
-- 5. 创建触发器: 确保每个股票只有一个活跃版本
-- =====================================================
CREATE OR REPLACE FUNCTION ensure_single_active_version()
RETURNS TRIGGER AS $$
BEGIN
    -- 如果新插入/更新的版本标记为活跃
    IF NEW.is_active = TRUE THEN
        -- 将同一股票的其他版本标记为非活跃
        UPDATE data_versions
        SET is_active = FALSE
        WHERE symbol = NEW.symbol
          AND version_id != NEW.version_id
          AND is_active = TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器
DROP TRIGGER IF EXISTS trg_ensure_single_active_version ON data_versions;
CREATE TRIGGER trg_ensure_single_active_version
    AFTER INSERT OR UPDATE ON data_versions
    FOR EACH ROW
    EXECUTE FUNCTION ensure_single_active_version();

-- =====================================================
-- 6. 创建视图: 最新活跃版本
-- =====================================================
CREATE OR REPLACE VIEW v_active_versions AS
SELECT
    version_id,
    symbol,
    start_date,
    end_date,
    version_number,
    created_at,
    data_source,
    record_count,
    checksum,
    metadata
FROM data_versions
WHERE is_active = TRUE
ORDER BY symbol;

COMMENT ON VIEW v_active_versions IS '活跃版本视图,显示每个股票的当前版本';

-- =====================================================
-- 7. 创建视图: 修复统计
-- =====================================================
CREATE OR REPLACE VIEW v_repair_statistics AS
SELECT
    symbol,
    DATE(repair_date) as repair_date,
    issue_type,
    COUNT(*) as issue_count,
    SUM(CASE WHEN repair_status = 'success' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN repair_status = 'failed' THEN 1 ELSE 0 END) as failed_count,
    SUM(CASE WHEN repair_status = 'partial' THEN 1 ELSE 0 END) as partial_count
FROM data_repair_logs
GROUP BY symbol, DATE(repair_date), issue_type
ORDER BY repair_date DESC, symbol;

COMMENT ON VIEW v_repair_statistics IS '修复统计视图,按股票和日期统计修复情况';

-- =====================================================
-- 8. 创建视图: 增量更新统计
-- =====================================================
CREATE OR REPLACE VIEW v_incremental_update_statistics AS
SELECT
    symbol,
    update_type,
    COUNT(*) as total_updates,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
    SUM(new_records) as total_new_records,
    SUM(updated_records) as total_updated_records,
    AVG(duration_seconds) as avg_duration_seconds,
    MAX(created_at) as last_update_time
FROM incremental_update_logs
GROUP BY symbol, update_type
ORDER BY last_update_time DESC;

COMMENT ON VIEW v_incremental_update_statistics IS '增量更新统计视图,按股票和更新类型统计';

-- =====================================================
-- 9. 插入初始数据/示例数据 (可选)
-- =====================================================
-- 这部分在实际使用时由应用程序自动填充

-- =====================================================
-- 10. 数据库权限设置 (根据实际需要调整)
-- =====================================================
-- GRANT SELECT, INSERT, UPDATE, DELETE ON data_versions TO stock_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON data_checksums TO stock_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON data_repair_logs TO stock_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON incremental_update_logs TO stock_user;
-- GRANT SELECT ON v_active_versions TO stock_user;
-- GRANT SELECT ON v_repair_statistics TO stock_user;
-- GRANT SELECT ON v_incremental_update_statistics TO stock_user;

-- =====================================================
-- 迁移完成
-- =====================================================
