-- 删除旧 stk_limit 表（已被 stk_limit_d 取代）
-- stk_limit_d 是新版实现，字段相同但主键顺序为 (trade_date, ts_code)，trade_date 使用 VARCHAR(8)
-- 旧 stk_limit 表：主键为 (ts_code, trade_date)，trade_date 为 DATE 类型，已停止维护

DROP TABLE IF EXISTS stk_limit CASCADE;
