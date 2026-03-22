-- 修改 fina_indicator 表的 ts_code 字段长度从 VARCHAR(10) 改为 VARCHAR(20)
-- 原因：北交所股票代码（如 874510.BJ）和其他股票代码可能超过10个字符

ALTER TABLE fina_indicator
ALTER COLUMN ts_code TYPE VARCHAR(20);

COMMENT ON COLUMN fina_indicator.ts_code IS '股票代码（格式：TSXXXXXX.XX，最长20字符）';
