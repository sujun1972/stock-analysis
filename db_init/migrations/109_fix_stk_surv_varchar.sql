-- 修复 stk_surv 表中 rece_mode/org_type 字段长度不足问题
-- 错误：value too long for type character varying(50)
-- 实际数据中这两个字段值可能超过 50 个字符

ALTER TABLE stk_surv
    ALTER COLUMN rece_mode TYPE VARCHAR(200),
    ALTER COLUMN org_type  TYPE VARCHAR(200);
