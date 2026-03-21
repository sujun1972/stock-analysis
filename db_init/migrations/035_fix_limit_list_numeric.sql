-- 修复涨跌停列表表的数值字段精度
-- 问题：金额字段可能超出 DECIMAL(20,2) 的范围

ALTER TABLE limit_list_d
    ALTER COLUMN amount TYPE NUMERIC(30,2),
    ALTER COLUMN limit_amount TYPE NUMERIC(30,2),
    ALTER COLUMN float_mv TYPE NUMERIC(30,2),
    ALTER COLUMN total_mv TYPE NUMERIC(30,2),
    ALTER COLUMN fd_amount TYPE NUMERIC(30,2);
