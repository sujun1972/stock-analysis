-- 创建现金流量表表
CREATE TABLE IF NOT EXISTS cashflow (
    ts_code VARCHAR(20) NOT NULL,
    ann_date VARCHAR(8),
    f_ann_date VARCHAR(8),
    end_date VARCHAR(8) NOT NULL,
    comp_type VARCHAR(1),
    report_type VARCHAR(1) NOT NULL,
    end_type VARCHAR(1),

    -- 净利润和费用
    net_profit DOUBLE PRECISION,
    finan_exp DOUBLE PRECISION,

    -- 经营活动现金流入
    c_fr_sale_sg DOUBLE PRECISION,
    recp_tax_rends DOUBLE PRECISION,
    n_depos_incr_fi DOUBLE PRECISION,
    n_incr_loans_cb DOUBLE PRECISION,
    n_inc_borr_oth_fi DOUBLE PRECISION,
    prem_fr_orig_contr DOUBLE PRECISION,
    n_incr_insured_dep DOUBLE PRECISION,
    n_reinsur_prem DOUBLE PRECISION,
    n_incr_disp_tfa DOUBLE PRECISION,
    ifc_cash_incr DOUBLE PRECISION,
    n_incr_disp_faas DOUBLE PRECISION,
    n_incr_loans_oth_bank DOUBLE PRECISION,
    n_cap_incr_repur DOUBLE PRECISION,
    c_fr_oth_operate_a DOUBLE PRECISION,
    c_inf_fr_operate_a DOUBLE PRECISION,

    -- 经营活动现金流出
    c_paid_goods_s DOUBLE PRECISION,
    c_paid_to_for_empl DOUBLE PRECISION,
    c_paid_for_taxes DOUBLE PRECISION,
    n_incr_clt_loan_adv DOUBLE PRECISION,
    n_incr_dep_cbob DOUBLE PRECISION,
    c_pay_claims_orig_inco DOUBLE PRECISION,
    pay_handling_chrg DOUBLE PRECISION,
    pay_comm_insur_plcy DOUBLE PRECISION,
    oth_cash_pay_oper_act DOUBLE PRECISION,
    st_cash_out_act DOUBLE PRECISION,
    n_cashflow_act DOUBLE PRECISION,

    -- 投资活动现金流
    oth_recp_ral_inv_act DOUBLE PRECISION,
    c_disp_withdrwl_invest DOUBLE PRECISION,
    c_recp_return_invest DOUBLE PRECISION,
    n_recp_disp_fiolta DOUBLE PRECISION,
    n_recp_disp_sobu DOUBLE PRECISION,
    stot_inflows_inv_act DOUBLE PRECISION,
    c_pay_acq_const_fiolta DOUBLE PRECISION,
    c_paid_invest DOUBLE PRECISION,
    n_disp_subs_oth_biz DOUBLE PRECISION,
    oth_pay_ral_inv_act DOUBLE PRECISION,
    n_incr_pledge_loan DOUBLE PRECISION,
    stot_out_inv_act DOUBLE PRECISION,
    n_cashflow_inv_act DOUBLE PRECISION,

    -- 筹资活动现金流
    c_recp_borrow DOUBLE PRECISION,
    proc_issue_bonds DOUBLE PRECISION,
    oth_cash_recp_ral_fnc_act DOUBLE PRECISION,
    stot_cash_in_fnc_act DOUBLE PRECISION,
    free_cashflow DOUBLE PRECISION,
    c_prepay_amt_borr DOUBLE PRECISION,
    c_pay_dist_dpcp_int_exp DOUBLE PRECISION,
    incl_dvd_profit_paid_sc_ms DOUBLE PRECISION,
    oth_cashpay_ral_fnc_act DOUBLE PRECISION,
    stot_cashout_fnc_act DOUBLE PRECISION,
    n_cash_flows_fnc_act DOUBLE PRECISION,
    eff_fx_flu_cash DOUBLE PRECISION,

    -- 现金及现金等价物
    n_incr_cash_cash_equ DOUBLE PRECISION,
    c_cash_equ_beg_period DOUBLE PRECISION,
    c_cash_equ_end_period DOUBLE PRECISION,

    -- 其他项目
    c_recp_cap_contrib DOUBLE PRECISION,
    incl_cash_rec_saims DOUBLE PRECISION,
    uncon_invest_loss DOUBLE PRECISION,
    prov_depr_assets DOUBLE PRECISION,
    depr_fa_coga_dpba DOUBLE PRECISION,
    amort_intang_assets DOUBLE PRECISION,
    lt_amort_deferred_exp DOUBLE PRECISION,
    decr_deferred_exp DOUBLE PRECISION,
    incr_acc_exp DOUBLE PRECISION,
    loss_disp_fiolta DOUBLE PRECISION,
    loss_scr_fa DOUBLE PRECISION,
    loss_fv_chg DOUBLE PRECISION,
    invest_loss DOUBLE PRECISION,
    decr_def_inc_tax_assets DOUBLE PRECISION,
    incr_def_inc_tax_liab DOUBLE PRECISION,
    decr_inventories DOUBLE PRECISION,
    decr_oper_payable DOUBLE PRECISION,
    incr_oper_payable DOUBLE PRECISION,
    others DOUBLE PRECISION,
    im_net_cashflow_oper_act DOUBLE PRECISION,
    conv_debt_into_cap DOUBLE PRECISION,
    conv_copbonds_due_within_1y DOUBLE PRECISION,
    fa_fnc_leases DOUBLE PRECISION,
    im_n_incr_cash_equ DOUBLE PRECISION,
    net_dism_capital_add DOUBLE PRECISION,
    net_cash_rece_sec DOUBLE PRECISION,
    credit_impa_loss DOUBLE PRECISION,
    use_right_asset_dep DOUBLE PRECISION,
    oth_loss_asset DOUBLE PRECISION,
    end_bal_cash DOUBLE PRECISION,
    beg_bal_cash DOUBLE PRECISION,
    end_bal_cash_equ DOUBLE PRECISION,
    beg_bal_cash_equ DOUBLE PRECISION,

    -- 更新标志
    update_flag VARCHAR(1),

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (ts_code, end_date, report_type)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_cashflow_ts_code ON cashflow(ts_code);
CREATE INDEX IF NOT EXISTS idx_cashflow_end_date ON cashflow(end_date DESC);
CREATE INDEX IF NOT EXISTS idx_cashflow_ann_date ON cashflow(ann_date DESC);
CREATE INDEX IF NOT EXISTS idx_cashflow_report_type ON cashflow(report_type);

-- 表注释
COMMENT ON TABLE cashflow IS '上市公司现金流量表（Tushare cashflow_vip接口，2000积分/次）';

-- 字段注释
COMMENT ON COLUMN cashflow.ts_code IS 'TS股票代码';
COMMENT ON COLUMN cashflow.ann_date IS '公告日期';
COMMENT ON COLUMN cashflow.f_ann_date IS '实际公告日期';
COMMENT ON COLUMN cashflow.end_date IS '报告期';
COMMENT ON COLUMN cashflow.comp_type IS '公司类型(1一般工商业2银行3保险4证券)';
COMMENT ON COLUMN cashflow.report_type IS '报表类型';
COMMENT ON COLUMN cashflow.n_cashflow_act IS '经营活动产生的现金流量净额';
COMMENT ON COLUMN cashflow.n_cashflow_inv_act IS '投资活动产生的现金流量净额';
COMMENT ON COLUMN cashflow.n_cash_flows_fnc_act IS '筹资活动产生的现金流量净额';
COMMENT ON COLUMN cashflow.free_cashflow IS '企业自由现金流量';
COMMENT ON COLUMN cashflow.update_flag IS '更新标志(1最新）';
