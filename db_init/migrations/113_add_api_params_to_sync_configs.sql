-- 为 sync_configs 添加 api_params 字段
-- 记录 Tushare/AkShare 接口的参数约束（通过实际调用 Tushare 接口验证）
-- 测试时间：2026-04-14，测试方法：scripts/test_api_params.py

ALTER TABLE sync_configs
    ADD COLUMN IF NOT EXISTS api_params JSONB DEFAULT NULL;

COMMENT ON COLUMN sync_configs.api_params IS '接口参数约束（JSON），通过实际调用验证';

-- api_params 结构：
-- {
--   "ts_code":    "optional" | "required" | "none",  -- 股票代码支持
--   "trade_date": "optional" | "required" | "none",  -- 单日交易日期支持
--   "start_date": true | false,                      -- 是否支持日期范围查询
--   "end_date":   true | false,                      -- 同上
--   "special_params": { ... }                        -- 特殊必填参数说明
-- }
--
-- ts_code 值说明：
--   "optional"  — 可传可不传，不传返回全市场数据
--   "required"  — 必填，或与 trade_date 至少传一个
--   "none"      — 接口不接受此参数
--
-- 特殊情况用 special_params 补充说明（如 month 必填、至少传一个参数等）

-- =============================================
-- 以下数据全部基于实际 API 调用结果
-- =============================================

-- ============ 基础数据 ============
-- stock_basic: 快照接口，无日期参数
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"说明": "快照接口，不传日期返回全量"}}'::jsonb
WHERE table_key = 'stock_basic';

-- trade_cal: 支持日期范围
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "none", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'trade_cal';

-- stock_st: 全参数可选
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'stock_st';

-- ============ 行情数据 ============
-- daily: 全参数可选，支持日期范围
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'stock_daily';

-- adj_factor: 同 daily
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'adj_factor';

-- daily_basic: 同 daily
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'daily_basic';

-- stk_limit: 同 daily
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'stk_limit_d';

-- suspend: ts_code 必填（无参数报错），不支持 trade_date/日期范围
UPDATE sync_configs SET api_params = '{"ts_code": "required", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"suspend_date": "停牌日期", "resume_date": "复牌日期"}}'::jsonb
WHERE table_key = 'suspend';

-- hsgt_top10: ts_code 可选，trade_date 传入返回 0 行（实际不生效），日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": true, "end_date": true, "special_params": {"market_type": "市场类型"}}'::jsonb
WHERE table_key = 'hsgt_top10';

-- ggt_top10: 无参数报错，trade_date 返回 0 行，日期范围报错 → 需要特殊参数
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"说明": "无参数和日期范围均报错，需按trade_date逐日请求", "market_type": "市场类型"}}'::jsonb
WHERE table_key = 'ggt_top10';

-- ggt_daily: 无 ts_code，trade_date 返回 0 行，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "none", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'ggt_daily';

-- ggt_monthly: 快照接口（无参数返回全量 74 行），month 参数返回 0 行
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"说明": "快照接口，无参数返回全量；month/start_month/end_month 参数实测返回0行"}}'::jsonb
WHERE table_key = 'ggt_monthly';

-- ============ 资金流向 ============
-- moneyflow: ts_code 和 trade_date 至少传一个
UPDATE sync_configs SET api_params = '{"ts_code": "required", "trade_date": "optional", "start_date": true, "end_date": true, "special_params": {"说明": "ts_code和trade_date至少输入一个"}}'::jsonb
WHERE table_key = 'moneyflow';

-- moneyflow_dc (moneyflow_stock_dc): 全参数可选
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'moneyflow_stock_dc';

-- moneyflow_ind_dc: 无 ts_code，trade_date 可选，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "optional", "start_date": true, "end_date": true, "special_params": {"content_type": "板块类型（行业/概念/地域）"}}'::jsonb
WHERE table_key = 'moneyflow_ind_dc';

-- moneyflow_mkt_dc: 无 ts_code，trade_date 可选，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'moneyflow_mkt_dc';

-- moneyflow_hsgt: 无参数报错，trade_date 返回 0 行，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "none", "start_date": true, "end_date": true, "special_params": {"说明": "无参数报错，必须传日期参数"}}'::jsonb
WHERE table_key = 'moneyflow_hsgt';

-- ============ 两融及转融通 ============
-- margin: 无 ts_code，trade_date 可选，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "optional", "start_date": true, "end_date": true, "special_params": {"exchange_id": "交易所代码"}}'::jsonb
WHERE table_key = 'margin';

-- margin_detail: 全参数可选
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'margin_detail';

-- margin_secs: 全参数可选（Provider 方法缺失，直接调 pro.margin_secs）
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'margin_secs';

-- slb_len: 无 ts_code，trade_date 可选，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'slb_len';

-- ============ 打板专题 ============
-- top_list: trade_date 必填
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "required", "start_date": false, "end_date": false}'::jsonb
WHERE table_key = 'top_list';

-- top_inst: trade_date 必填
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "required", "start_date": false, "end_date": false}'::jsonb
WHERE table_key = 'top_inst';

-- limit_list_d: 全参数可选
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true, "special_params": {"limit_type": "涨跌停类型"}}'::jsonb
WHERE table_key = 'limit_list';

-- limit_step: 无 ts_code，trade_date 可选，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'limit_step';

-- limit_cpt_list: 无 ts_code，trade_date 可选，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'limit_cpt';

-- dc_index: 快照型接口，trade_date/日期范围返回 0 行
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"idx_type": "板块类型（概念/行业/地域）", "说明": "快照接口，无参数返回全量；trade_date/日期范围实测返回0行"}}'::jsonb
WHERE table_key = 'dc_index';

-- dc_member: 快照型接口，trade_date/日期范围返回 0 行
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"说明": "快照接口，无参数返回全量；trade_date/日期范围实测返回0行", "con_code": "成分股代码"}}'::jsonb
WHERE table_key = 'dc_member';

-- dc_daily: ts_code 可选，trade_date 可选，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true, "special_params": {"idx_type": "板块类型"}}'::jsonb
WHERE table_key = 'dc_daily';

-- ============ 特色数据 ============
-- report_rc: ts_code 可选，无 trade_date，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'report_rc';

-- cyq_perf: ts_code 和 trade_date 至少传一个，日期范围不支持
UPDATE sync_configs SET api_params = '{"ts_code": "required", "trade_date": "optional", "start_date": false, "end_date": false, "special_params": {"说明": "ts_code和trade_date至少输入一个"}}'::jsonb
WHERE table_key = 'cyq_perf';

-- cyq_chips: ts_code 必填
UPDATE sync_configs SET api_params = '{"ts_code": "required", "trade_date": "none", "start_date": false, "end_date": false}'::jsonb
WHERE table_key = 'cyq_chips';

-- ccass_hold: ts_code 可选，trade_date 返回 0 行，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": true, "end_date": true, "special_params": {"hk_code": "港交所代码"}}'::jsonb
WHERE table_key = 'ccass_hold';

-- ccass_hold_detail: ts_code 和 trade_date 至少传一个，日期范围不支持
UPDATE sync_configs SET api_params = '{"ts_code": "required", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"hk_code": "港交所代码", "说明": "ts_code和trade_date至少输入一个"}}'::jsonb
WHERE table_key = 'ccass_hold_detail';

-- hk_hold: ts_code 可选，trade_date 返回 0 行，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": true, "end_date": true, "special_params": {"code": "原始代码", "exchange": "交易所"}}'::jsonb
WHERE table_key = 'hk_hold';

-- stk_auction_o: 全参数可选
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'stk_auction_o';

-- stk_auction_c: 全参数可选
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'stk_auction_c';

-- stk_nineturn: ts_code 和 trade_date 至少传一个，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "required", "trade_date": "optional", "start_date": true, "end_date": true, "special_params": {"说明": "ts_code和trade_date至少输入一个"}}'::jsonb
WHERE table_key = 'stk_nineturn';

-- stk_ah_comparison: ts_code 可选，trade_date/日期范围返回 0 行
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"说明": "无参数返回全量；trade_date/日期范围实测返回0行"}}'::jsonb
WHERE table_key = 'stk_ah_comparison';

-- stk_surv: 全参数可选
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'stk_surv';

-- broker_recommend: month 必填
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"month": "YYYYMM格式，必填"}}'::jsonb
WHERE table_key = 'broker_recommend';

-- ============ 参考数据 ============
-- stk_shock: 快照型（无参数返回数据，传参都返回 0 行）
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"说明": "快照接口，无参数返回最近数据；ts_code/trade_date/日期范围实测均返回0行"}}'::jsonb
WHERE table_key = 'stk_shock';

-- stk_high_shock: 同 stk_shock
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"说明": "快照接口，无参数返回最近数据；ts_code/trade_date/日期范围实测均返回0行"}}'::jsonb
WHERE table_key = 'stk_high_shock';

-- stk_alert: 同 stk_shock
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"说明": "快照接口，无参数返回最近数据；ts_code/trade_date/日期范围实测均返回0行"}}'::jsonb
WHERE table_key = 'stk_alert';

-- pledge_stat: ts_code 可选，end_date 返回 0 行，日期范围返回 0 行
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"说明": "无参数返回全量；end_date/日期范围实测返回0行"}}'::jsonb
WHERE table_key = 'pledge_stat';

-- repurchase: 无参数返回全量，ts_code 返回 0 行，日期范围有效（ann_date 语义）
UPDATE sync_configs SET api_params = '{"ts_code": "none", "trade_date": "none", "start_date": true, "end_date": true, "special_params": {"说明": "start_date/end_date 对应 ann_date 公告日期范围"}}'::jsonb
WHERE table_key = 'repurchase';

-- share_float: ts_code 可选，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'share_float';

-- block_trade: 全参数可选
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "optional", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'block_trade';

-- stk_holdernumber: ts_code 可选，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'stk_holdernumber';

-- stk_holdertrade: ts_code 可选，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": true, "end_date": true}'::jsonb
WHERE table_key = 'stk_holdertrade';

-- ============ 财务数据 ============
-- income_vip: ts_code 可选，日期范围有效
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": true, "end_date": true, "special_params": {"period": "报告期YYYYMMDD", "report_type": "报告类型", "comp_type": "公司类型"}}'::jsonb
WHERE table_key = 'income';

-- balancesheet_vip: 同 income
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": true, "end_date": true, "special_params": {"period": "报告期YYYYMMDD", "report_type": "报告类型", "comp_type": "公司类型"}}'::jsonb
WHERE table_key = 'balancesheet';

-- cashflow_vip: 同 income
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": true, "end_date": true, "special_params": {"period": "报告期YYYYMMDD", "report_type": "报告类型", "comp_type": "公司类型"}}'::jsonb
WHERE table_key = 'cashflow';

-- forecast_vip: 同 income
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": true, "end_date": true, "special_params": {"period": "报告期YYYYMMDD", "type": "预告类型"}}'::jsonb
WHERE table_key = 'forecast';

-- express_vip: 同 income
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": true, "end_date": true, "special_params": {"period": "报告期YYYYMMDD"}}'::jsonb
WHERE table_key = 'express';

-- dividend: ts_code/ann_date/record_date/ex_date/imp_ann_date 至少传一个
UPDATE sync_configs SET api_params = '{"ts_code": "required", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"说明": "ts_code/ann_date/record_date/ex_date/imp_ann_date至少传一个"}}'::jsonb
WHERE table_key = 'dividend';

-- fina_indicator_vip: ts_code 可选，日期范围返回 0 行
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"period": "报告期YYYYMMDD", "说明": "start_date/end_date实测返回0行"}}'::jsonb
WHERE table_key = 'fina_indicator';

-- fina_audit: ts_code 必填
UPDATE sync_configs SET api_params = '{"ts_code": "required", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"period": "报告期YYYYMMDD"}}'::jsonb
WHERE table_key = 'fina_audit';

-- fina_mainbz_vip: ts_code 可选，日期范围返回 0 行
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"period": "报告期YYYYMMDD", "type": "P-产品/D-地区/I-行业", "说明": "start_date/end_date实测返回0行"}}'::jsonb
WHERE table_key = 'fina_mainbz';

-- disclosure_date: ts_code 可选，无日期范围参数
UPDATE sync_configs SET api_params = '{"ts_code": "optional", "trade_date": "none", "start_date": false, "end_date": false, "special_params": {"end_date": "报告期", "pre_date": "预计披露日", "actual_date": "实际披露日"}}'::jsonb
WHERE table_key = 'disclosure_date';
