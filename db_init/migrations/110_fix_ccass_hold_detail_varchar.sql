-- 修复 ccass_hold_detail 表中 col_participant_id 字段长度不足问题
-- 错误：value too long for type character varying(20)
-- 实际数据中参与者编号可能超过 20 个字符

-- col_participant_id 是主键的一部分，需先删除主键约束再修改类型，最后重建
ALTER TABLE ccass_hold_detail DROP CONSTRAINT ccass_hold_detail_pkey;

ALTER TABLE ccass_hold_detail
    ALTER COLUMN col_participant_id TYPE VARCHAR(100);

ALTER TABLE ccass_hold_detail
    ADD PRIMARY KEY (trade_date, ts_code, col_participant_id);
