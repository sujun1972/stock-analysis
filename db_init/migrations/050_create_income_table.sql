-- 创建利润表数据表
CREATE TABLE IF NOT EXISTS income (
    ts_code VARCHAR(20) NOT NULL,
    ann_date VARCHAR(8),
    f_ann_date VARCHAR(8),
    end_date VARCHAR(8) NOT NULL,
    report_type VARCHAR(20) NOT NULL,
    comp_type VARCHAR(10),
    end_type VARCHAR(10),

    -- 每股收益
    basic_eps DECIMAL(20, 4),
    diluted_eps DECIMAL(20, 4),

    -- 收入类
    total_revenue DECIMAL(20, 2),
    revenue DECIMAL(20, 2),
    int_income DECIMAL(20, 2),
    prem_earned DECIMAL(20, 2),
    comm_income DECIMAL(20, 2),
    n_commis_income DECIMAL(20, 2),
    n_oth_income DECIMAL(20, 2),
    n_oth_b_income DECIMAL(20, 2),
    prem_income DECIMAL(20, 2),
    out_prem DECIMAL(20, 2),
    une_prem_reser DECIMAL(20, 2),
    reins_income DECIMAL(20, 2),
    n_sec_tb_income DECIMAL(20, 2),
    n_sec_uw_income DECIMAL(20, 2),
    n_asset_mg_income DECIMAL(20, 2),
    oth_b_income DECIMAL(20, 2),
    fv_value_chg_gain DECIMAL(20, 2),
    invest_income DECIMAL(20, 2),
    ass_invest_income DECIMAL(20, 2),
    forex_gain DECIMAL(20, 2),

    -- 成本类
    total_cogs DECIMAL(20, 2),
    oper_cost DECIMAL(20, 2),
    int_exp DECIMAL(20, 2),
    comm_exp DECIMAL(20, 2),
    biz_tax_surchg DECIMAL(20, 2),
    sell_exp DECIMAL(20, 2),
    admin_exp DECIMAL(20, 2),
    fin_exp DECIMAL(20, 2),
    assets_impair_loss DECIMAL(20, 2),
    prem_refund DECIMAL(20, 2),
    compens_payout DECIMAL(20, 2),
    reser_insur_liab DECIMAL(20, 2),
    div_payt DECIMAL(20, 2),
    reins_exp DECIMAL(20, 2),
    oper_exp DECIMAL(20, 2),
    compens_payout_refu DECIMAL(20, 2),
    insur_reser_refu DECIMAL(20, 2),
    reins_cost_refund DECIMAL(20, 2),
    other_bus_cost DECIMAL(20, 2),

    -- 利润类
    operate_profit DECIMAL(20, 2),
    non_oper_income DECIMAL(20, 2),
    non_oper_exp DECIMAL(20, 2),
    nca_disploss DECIMAL(20, 2),
    total_profit DECIMAL(20, 2),
    income_tax DECIMAL(20, 2),
    n_income DECIMAL(20, 2),
    n_income_attr_p DECIMAL(20, 2),
    minority_gain DECIMAL(20, 2),
    oth_compr_income DECIMAL(20, 2),
    t_compr_income DECIMAL(20, 2),
    compr_inc_attr_p DECIMAL(20, 2),
    compr_inc_attr_m_s DECIMAL(20, 2),

    -- 息税前利润
    ebit DECIMAL(20, 2),
    ebitda DECIMAL(20, 2),

    -- 保险业务
    insurance_exp DECIMAL(20, 2),
    undist_profit DECIMAL(20, 2),
    distable_profit DECIMAL(20, 2),

    -- 研发费用
    rd_exp DECIMAL(20, 2),
    fin_exp_int_exp DECIMAL(20, 2),
    fin_exp_int_inc DECIMAL(20, 2),

    -- 转让
    transfer_surplus_rese DECIMAL(20, 2),
    transfer_housing_imprest DECIMAL(20, 2),
    transfer_oth DECIMAL(20, 2),
    adj_lossgain DECIMAL(20, 2),
    withdra_legal_surplus DECIMAL(20, 2),
    withdra_legal_pubfund DECIMAL(20, 2),
    withdra_biz_devfund DECIMAL(20, 2),
    withdra_rese_fund DECIMAL(20, 2),
    withdra_oth_ersu DECIMAL(20, 2),
    workers_welfare DECIMAL(20, 2),
    distr_profit_shrhder DECIMAL(20, 2),
    prfshare_payable_dvd DECIMAL(20, 2),
    comshare_payable_dvd DECIMAL(20, 2),
    capit_comstock_div DECIMAL(20, 2),

    -- 更新时间
    update_flag VARCHAR(10),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (ts_code, end_date, report_type)
);

-- 创建索引
CREATE INDEX idx_income_ts_code ON income(ts_code);
CREATE INDEX idx_income_end_date ON income(end_date);
CREATE INDEX idx_income_ann_date ON income(ann_date);
CREATE INDEX idx_income_report_type ON income(report_type);

-- 添加表注释
COMMENT ON TABLE income IS 'Tushare利润表数据（income_vip接口）';
COMMENT ON COLUMN income.ts_code IS '股票代码';
COMMENT ON COLUMN income.ann_date IS '公告日期';
COMMENT ON COLUMN income.f_ann_date IS '实际公告日期';
COMMENT ON COLUMN income.end_date IS '报告期';
COMMENT ON COLUMN income.report_type IS '报告类型（1合并报表/2单季合并/3调整单季合并表/4调整合并报表/5调整前合并报表/6母公司报表/7母公司单季表/8母公司调整单季表/9母公司调整表/10母公司调整前报表/11调整前合并报表/12母公司调整前报表）';
COMMENT ON COLUMN income.comp_type IS '公司类型（1一般工商业/2银行/3保险/4证券）';
COMMENT ON COLUMN income.end_type IS '报告期类型';
COMMENT ON COLUMN income.basic_eps IS '基本每股收益';
COMMENT ON COLUMN income.diluted_eps IS '稀释每股收益';
COMMENT ON COLUMN income.total_revenue IS '营业总收入（元）';
COMMENT ON COLUMN income.revenue IS '营业收入（元）';
COMMENT ON COLUMN income.oper_cost IS '营业成本（元）';
COMMENT ON COLUMN income.sell_exp IS '销售费用（元）';
COMMENT ON COLUMN income.admin_exp IS '管理费用（元）';
COMMENT ON COLUMN income.fin_exp IS '财务费用（元）';
COMMENT ON COLUMN income.rd_exp IS '研发费用（元）';
COMMENT ON COLUMN income.operate_profit IS '营业利润（元）';
COMMENT ON COLUMN income.total_profit IS '利润总额（元）';
COMMENT ON COLUMN income.n_income IS '净利润（元）';
COMMENT ON COLUMN income.n_income_attr_p IS '归属于母公司所有者的净利润（元）';
COMMENT ON COLUMN income.ebit IS '息税前利润（元）';
COMMENT ON COLUMN income.ebitda IS '息税折旧摊销前利润（元）';
