-- 为所有 sync_configs 条目填充 api_name（Tushare 接口名称）
-- 仅更新 api_name 为 NULL 的记录，避免覆盖已手动维护的值

-- 基础数据
UPDATE sync_configs SET api_name = 'stock_basic' WHERE table_key = 'stock_basic' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'new_share' WHERE table_key = 'new_stocks' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'trade_cal' WHERE table_key = 'trade_cal' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'stock_st' WHERE table_key = 'stock_st' AND api_name IS NULL;

-- 行情数据
UPDATE sync_configs SET api_name = 'daily' WHERE table_key = 'stock_daily' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'adj_factor' WHERE table_key = 'adj_factor' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'daily_basic' WHERE table_key = 'daily_basic' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'stk_limit' WHERE table_key = 'stk_limit_d' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'suspend_d' WHERE table_key = 'suspend' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'hsgt_top10' WHERE table_key = 'hsgt_top10' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'ggt_top10' WHERE table_key = 'ggt_top10' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'ggt_daily' WHERE table_key = 'ggt_daily' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'ggt_monthly' WHERE table_key = 'ggt_monthly' AND api_name IS NULL;

-- 资金流向
UPDATE sync_configs SET api_name = 'moneyflow' WHERE table_key = 'moneyflow' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'moneyflow_dc' WHERE table_key = 'moneyflow_stock_dc' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'moneyflow_ind_dc' WHERE table_key = 'moneyflow_ind_dc' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'moneyflow_mkt_dc' WHERE table_key = 'moneyflow_mkt_dc' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'moneyflow_hsgt' WHERE table_key = 'moneyflow_hsgt' AND api_name IS NULL;

-- 两融及转融通
UPDATE sync_configs SET api_name = 'margin' WHERE table_key = 'margin' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'margin_detail' WHERE table_key = 'margin_detail' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'margin_secs' WHERE table_key = 'margin_secs' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'slb_len' WHERE table_key = 'slb_len' AND api_name IS NULL;

-- 打板专题
UPDATE sync_configs SET api_name = 'top_list' WHERE table_key = 'top_list' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'top_inst' WHERE table_key = 'top_inst' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'limit_list_d' WHERE table_key = 'limit_list' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'limit_step' WHERE table_key = 'limit_step' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'limit_cpt_list' WHERE table_key = 'limit_cpt' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'dc_index' WHERE table_key = 'dc_index' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'dc_member' WHERE table_key = 'dc_member' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'dc_daily' WHERE table_key = 'dc_daily' AND api_name IS NULL;

-- 特色数据
UPDATE sync_configs SET api_name = 'report_rc' WHERE table_key = 'report_rc' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'cyq_perf' WHERE table_key = 'cyq_perf' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'cyq_chips' WHERE table_key = 'cyq_chips' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'ccass_hold' WHERE table_key = 'ccass_hold' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'ccass_hold_detail' WHERE table_key = 'ccass_hold_detail' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'hk_hold' WHERE table_key = 'hk_hold' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'stk_auction_o' WHERE table_key = 'stk_auction_o' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'stk_auction_c' WHERE table_key = 'stk_auction_c' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'stk_nineturn' WHERE table_key = 'stk_nineturn' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'stk_ah_comparison' WHERE table_key = 'stk_ah_comparison' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'stk_surv' WHERE table_key = 'stk_surv' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'broker_recommend' WHERE table_key = 'broker_recommend' AND api_name IS NULL;

-- 参考数据
UPDATE sync_configs SET api_name = 'stk_shock' WHERE table_key = 'stk_shock' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'stk_high_shock' WHERE table_key = 'stk_high_shock' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'stk_alert' WHERE table_key = 'stk_alert' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'pledge_stat' WHERE table_key = 'pledge_stat' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'repurchase' WHERE table_key = 'repurchase' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'share_float' WHERE table_key = 'share_float' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'block_trade' WHERE table_key = 'block_trade' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'stk_holdernumber' WHERE table_key = 'stk_holdernumber' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'stk_holdertrade' WHERE table_key = 'stk_holdertrade' AND api_name IS NULL;

-- 财务数据
UPDATE sync_configs SET api_name = 'income_vip' WHERE table_key = 'income' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'balancesheet_vip' WHERE table_key = 'balancesheet' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'cashflow_vip' WHERE table_key = 'cashflow' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'forecast_vip' WHERE table_key = 'forecast' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'express_vip' WHERE table_key = 'express' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'dividend' WHERE table_key = 'dividend' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'fina_indicator_vip' WHERE table_key = 'fina_indicator' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'fina_audit' WHERE table_key = 'fina_audit' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'fina_mainbz_vip' WHERE table_key = 'fina_mainbz' AND api_name IS NULL;
UPDATE sync_configs SET api_name = 'disclosure_date' WHERE table_key = 'disclosure_date' AND api_name IS NULL;
