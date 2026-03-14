-- =========================================================
-- 扩展数据源配置
-- =========================================================
-- 功能：新增6种数据源配置，支持在Admin界面独立配置
--      1. 分时数据源（minute_data_source）
--      2. 实时数据源（realtime_data_source）
--      3. 涨停板池数据源（limit_up_data_source）
--      4. 龙虎榜数据源（top_list_data_source）
--      5. 盘前数据源（premarket_data_source）
--      6. 概念数据源（concept_data_source）
--
-- 作用：配合Tushare 5000积分，允许用户灵活选择数据源
-- 作者：Claude Code
-- 日期：2026-03-14
-- =========================================================

-- 1. 添加分时数据源配置（如果不存在）
INSERT INTO system_config (config_key, config_value, description, created_at, updated_at)
VALUES (
    'minute_data_source',
    'akshare',
    '分时数据源（tushare需要2000积分，更快更稳定）',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (config_key) DO NOTHING;

-- 2. 添加实时数据源配置（如果不存在）
INSERT INTO system_config (config_key, config_value, description, created_at, updated_at)
VALUES (
    'realtime_data_source',
    'akshare',
    '实时数据源（tushare需要5000积分，更快更稳定）',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (config_key) DO NOTHING;

-- 3. 添加涨停板池数据源配置（默认tushare，如果用户有5000积分）
INSERT INTO system_config (config_key, config_value, description, created_at, updated_at)
VALUES (
    'limit_up_data_source',
    'tushare',
    '涨停板池数据源（tushare需要2000积分，akshare免费但功能更丰富）',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (config_key) DO NOTHING;

-- 4. 添加龙虎榜数据源配置（默认tushare，如果用户有5000积分）
INSERT INTO system_config (config_key, config_value, description, created_at, updated_at)
VALUES (
    'top_list_data_source',
    'tushare',
    '龙虎榜数据源（tushare需要2000积分，akshare免费）',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (config_key) DO NOTHING;

-- 5. 添加盘前数据源配置（外盘数据只有akshare支持，盘前股本数据tushare支持）
INSERT INTO system_config (config_key, config_value, description, created_at, updated_at)
VALUES (
    'premarket_data_source',
    'akshare',
    '盘前数据源（外盘数据仅akshare支持，A股盘前数据tushare也支持）',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (config_key) DO NOTHING;

-- 6. 添加概念数据源配置（默认akshare，免费且数据完整）
INSERT INTO system_config (config_key, config_value, description, created_at, updated_at)
VALUES (
    'concept_data_source',
    'akshare',
    '概念数据源（tushare需要5000积分，数据更稳定；akshare免费，466个概念数据更丰富）',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (config_key) DO NOTHING;
