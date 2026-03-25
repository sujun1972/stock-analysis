-- ========================================
-- 迁移脚本: 089_alter_stock_basic_add_tushare_fields.sql
-- 描述: 扩展 stock_basic 表以支持 Tushare stock_basic 接口的完整字段
-- 作者: Claude Code
-- 日期: 2026-03-25
-- ========================================

-- 说明：
-- 根据 Tushare stock_basic 接口规范，添加缺失字段
-- 接口文档：https://tushare.pro/document/2?doc_id=25
-- 积分要求：2000积分起，每分钟请求50次

BEGIN;

-- 1. 添加 ts_code 字段（Tushare 标准代码，如 000001.SZ）
ALTER TABLE stock_basic
ADD COLUMN IF NOT EXISTS ts_code VARCHAR(20);

-- 2. 添加 symbol 字段（原始股票代码，与 code 相同，保留用于兼容）
ALTER TABLE stock_basic
ADD COLUMN IF NOT EXISTS symbol VARCHAR(10);

-- 3. 添加 fullname 字段（股票全称）
ALTER TABLE stock_basic
ADD COLUMN IF NOT EXISTS fullname VARCHAR(100);

-- 4. 添加 enname 字段（英文全称）
ALTER TABLE stock_basic
ADD COLUMN IF NOT EXISTS enname VARCHAR(200);

-- 5. 添加 cnspell 字段（拼音缩写）
ALTER TABLE stock_basic
ADD COLUMN IF NOT EXISTS cnspell VARCHAR(20);

-- 6. 添加 exchange 字段（交易所代码：SSE上交所/SZSE深交所/BSE北交所）
ALTER TABLE stock_basic
ADD COLUMN IF NOT EXISTS exchange VARCHAR(10);

-- 7. 添加 curr_type 字段（交易货币）
ALTER TABLE stock_basic
ADD COLUMN IF NOT EXISTS curr_type VARCHAR(10);

-- 8. 添加 list_status 字段（上市状态：L上市/D退市/P暂停上市/G过会未交易）
ALTER TABLE stock_basic
ADD COLUMN IF NOT EXISTS list_status VARCHAR(2);

-- 9. 添加 is_hs 字段（是否沪深港通标的：N否/H沪股通/S深股通）
ALTER TABLE stock_basic
ADD COLUMN IF NOT EXISTS is_hs VARCHAR(2);

-- 10. 添加 act_name 字段（实控人名称）
ALTER TABLE stock_basic
ADD COLUMN IF NOT EXISTS act_name VARCHAR(100);

-- 11. 添加 act_ent_type 字段（实控人企业性质）
ALTER TABLE stock_basic
ADD COLUMN IF NOT EXISTS act_ent_type VARCHAR(50);

-- ========================================
-- 创建索引
-- ========================================

-- ts_code 唯一索引（用于 Tushare 数据同步）
CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_basic_ts_code ON stock_basic(ts_code);

-- exchange 索引（用于按交易所筛选）
CREATE INDEX IF NOT EXISTS idx_stock_basic_exchange ON stock_basic(exchange);

-- list_status 索引（用于按上市状态筛选）
CREATE INDEX IF NOT EXISTS idx_stock_basic_list_status ON stock_basic(list_status);

-- is_hs 索引（用于筛选沪深港通标的）
CREATE INDEX IF NOT EXISTS idx_stock_basic_is_hs ON stock_basic(is_hs);

-- cnspell 索引（用于拼音搜索）
CREATE INDEX IF NOT EXISTS idx_stock_basic_cnspell ON stock_basic(cnspell);

-- ========================================
-- 添加注释
-- ========================================

COMMENT ON COLUMN stock_basic.ts_code IS 'Tushare 标准代码（如 000001.SZ）';
COMMENT ON COLUMN stock_basic.symbol IS '原始股票代码（与 code 相同，兼容字段）';
COMMENT ON COLUMN stock_basic.fullname IS '股票全称';
COMMENT ON COLUMN stock_basic.enname IS '英文全称';
COMMENT ON COLUMN stock_basic.cnspell IS '拼音缩写';
COMMENT ON COLUMN stock_basic.exchange IS '交易所代码（SSE上交所/SZSE深交所/BSE北交所）';
COMMENT ON COLUMN stock_basic.curr_type IS '交易货币';
COMMENT ON COLUMN stock_basic.list_status IS '上市状态（L上市/D退市/P暂停上市/G过会未交易）';
COMMENT ON COLUMN stock_basic.is_hs IS '是否沪深港通标的（N否/H沪股通/S深股通）';
COMMENT ON COLUMN stock_basic.act_name IS '实控人名称';
COMMENT ON COLUMN stock_basic.act_ent_type IS '实控人企业性质';

-- ========================================
-- 更新现有数据（初始化新字段）
-- ========================================

-- 根据 code 生成 ts_code（假设 code 已经是正确格式）
UPDATE stock_basic
SET ts_code = CASE
    WHEN code ~ '^(6|68|688)' THEN code || '.SH'  -- 上海
    WHEN code ~ '^(0|2|3|8|4)' THEN code || '.SZ'  -- 深圳
    ELSE code || '.SH'  -- 默认上海
END
WHERE ts_code IS NULL;

-- 复制 code 到 symbol（兼容字段）
UPDATE stock_basic
SET symbol = code
WHERE symbol IS NULL;

-- 根据 code 推断 exchange
UPDATE stock_basic
SET exchange = CASE
    WHEN code ~ '^(6|68|688)' THEN 'SSE'  -- 上交所
    WHEN code ~ '^(0|2|3)' THEN 'SZSE'    -- 深交所
    WHEN code ~ '^(8|4)' THEN 'BSE'       -- 北交所
    ELSE 'SSE'  -- 默认上交所
END
WHERE exchange IS NULL;

-- 根据 status 推断 list_status
UPDATE stock_basic
SET list_status = CASE
    WHEN status = '正常' THEN 'L'
    WHEN status = '退市' THEN 'D'
    WHEN status = '停牌' THEN 'P'
    ELSE 'L'  -- 默认上市
END
WHERE list_status IS NULL;

-- 设置默认货币为 CNY
UPDATE stock_basic
SET curr_type = 'CNY'
WHERE curr_type IS NULL;

-- 设置默认 is_hs 为 N（后续可通过 Tushare 数据更新）
UPDATE stock_basic
SET is_hs = 'N'
WHERE is_hs IS NULL;

-- ========================================
-- 更新表注释
-- ========================================

COMMENT ON TABLE stock_basic IS '股票基础信息表（已扩展支持 Tushare stock_basic 接口完整字段）';

COMMIT;

-- ========================================
-- 验证迁移
-- ========================================

-- 查看表结构
\d stock_basic

-- 统计记录数
SELECT
    COUNT(*) as total_stocks,
    COUNT(DISTINCT exchange) as exchanges,
    COUNT(DISTINCT list_status) as statuses,
    COUNT(DISTINCT is_hs) as hs_types
FROM stock_basic;

-- 显示示例数据
SELECT
    code, name, ts_code, exchange, market,
    list_status, is_hs, cnspell, list_date
FROM stock_basic
LIMIT 10;
