-- 创建资产负债表数据表
-- 接口: balancesheet_vip
-- 描述: 获取上市公司资产负债表
-- 积分: 2000积分/次

CREATE TABLE IF NOT EXISTS balancesheet (
    -- 主键字段
    ts_code VARCHAR(20) NOT NULL,           -- TS股票代码
    ann_date VARCHAR(8) NOT NULL,           -- 公告日期
    end_date VARCHAR(8) NOT NULL,           -- 报告期
    report_type VARCHAR(20),                -- 报表类型(见下方详细说明)
    comp_type VARCHAR(20),                  -- 公司类型(1一般工商业2银行3保险4证券)

    -- 基础信息
    f_ann_date VARCHAR(8),                  -- 实际公告日期
    end_type VARCHAR(20),                   -- 报告期类型

    -- 股本信息
    total_share NUMERIC(20, 4),             -- 期末总股本
    cap_rese NUMERIC(20, 4),                -- 资本公积金
    undistr_porfit NUMERIC(20, 4),          -- 未分配利润
    surplus_rese NUMERIC(20, 4),            -- 盈余公积金
    special_rese NUMERIC(20, 4),            -- 专项储备

    -- 流动资产
    money_cap NUMERIC(20, 4),               -- 货币资金
    trad_asset NUMERIC(20, 4),              -- 交易性金融资产
    notes_receiv NUMERIC(20, 4),            -- 应收票据
    accounts_receiv NUMERIC(20, 4),         -- 应收账款
    oth_receiv NUMERIC(20, 4),              -- 其他应收款
    prepayment NUMERIC(20, 4),              -- 预付款项
    div_receiv NUMERIC(20, 4),              -- 应收股利
    int_receiv NUMERIC(20, 4),              -- 应收利息
    inventories NUMERIC(20, 4),             -- 存货
    amor_exp NUMERIC(20, 4),                -- 待摊费用
    nca_within_1y NUMERIC(20, 4),           -- 一年内到期的非流动资产
    sett_rsrv NUMERIC(20, 4),               -- 结算备付金
    loanto_oth_bank_fi NUMERIC(20, 4),      -- 拆出资金
    premium_receiv NUMERIC(20, 4),          -- 应收保费
    reinsur_receiv NUMERIC(20, 4),          -- 应收分保账款
    reinsur_res_receiv NUMERIC(20, 4),      -- 应收分保合同准备金
    pur_resale_fa NUMERIC(20, 4),           -- 买入返售金融资产
    oth_cur_assets NUMERIC(20, 4),          -- 其他流动资产
    total_cur_assets NUMERIC(20, 4),        -- 流动资产合计

    -- 非流动资产
    fa_avail_for_sale NUMERIC(20, 4),       -- 可供出售金融资产
    htm_invest NUMERIC(20, 4),              -- 持有至到期投资
    lt_eqt_invest NUMERIC(20, 4),           -- 长期股权投资
    invest_real_estate NUMERIC(20, 4),      -- 投资性房地产
    time_deposits NUMERIC(20, 4),           -- 定期存款
    oth_assets NUMERIC(20, 4),              -- 其他资产
    lt_rec NUMERIC(20, 4),                  -- 长期应收款
    fix_assets NUMERIC(20, 4),              -- 固定资产
    cip NUMERIC(20, 4),                     -- 在建工程
    const_materials NUMERIC(20, 4),         -- 工程物资
    fixed_assets_disp NUMERIC(20, 4),       -- 固定资产清理
    produc_bio_assets NUMERIC(20, 4),       -- 生产性生物资产
    oil_and_gas_assets NUMERIC(20, 4),      -- 油气资产
    intan_assets NUMERIC(20, 4),            -- 无形资产
    r_and_d NUMERIC(20, 4),                 -- 研发支出
    goodwill NUMERIC(20, 4),                -- 商誉
    lt_amor_exp NUMERIC(20, 4),             -- 长期待摊费用
    defer_tax_assets NUMERIC(20, 4),        -- 递延所得税资产
    decr_in_disbur NUMERIC(20, 4),          -- 发放贷款及垫款
    oth_nca NUMERIC(20, 4),                 -- 其他非流动资产
    total_nca NUMERIC(20, 4),               -- 非流动资产合计

    -- 特殊资产
    cash_reser_cb NUMERIC(20, 4),           -- 现金及存放中央银行款项
    depos_in_oth_bfi NUMERIC(20, 4),        -- 存放同业和其它金融机构款项
    prec_metals NUMERIC(20, 4),             -- 贵金属
    deriv_assets NUMERIC(20, 4),            -- 衍生金融资产
    rr_reins_une_prem NUMERIC(20, 4),       -- 应收分保未到期责任准备金
    rr_reins_outstd_cla NUMERIC(20, 4),     -- 应收分保未决赔款准备金
    rr_reins_lins_liab NUMERIC(20, 4),      -- 应收分保寿险责任准备金
    rr_reins_lthins_liab NUMERIC(20, 4),    -- 应收分保长期健康险责任准备金
    refund_depos NUMERIC(20, 4),            -- 存出保证金
    ph_pledge_loans NUMERIC(20, 4),         -- 保户质押贷款
    refund_cap_depos NUMERIC(20, 4),        -- 存出资本保证金
    indep_acct_assets NUMERIC(20, 4),       -- 独立账户资产
    client_depos NUMERIC(20, 4),            -- 其中：客户资金存款
    client_prov NUMERIC(20, 4),             -- 其中：客户备付金
    transac_seat_fee NUMERIC(20, 4),        -- 其中:交易席位费
    invest_as_receiv NUMERIC(20, 4),        -- 应收款项类投资
    total_assets NUMERIC(20, 4),            -- 资产总计

    -- 流动负债
    lt_borr NUMERIC(20, 4),                 -- 长期借款
    st_borr NUMERIC(20, 4),                 -- 短期借款
    cb_borr NUMERIC(20, 4),                 -- 向中央银行借款
    depos_ib_deposits NUMERIC(20, 4),       -- 吸收存款及同业存放
    loan_oth_bank NUMERIC(20, 4),           -- 拆入资金
    trading_fl NUMERIC(20, 4),              -- 交易性金融负债
    notes_payable NUMERIC(20, 4),           -- 应付票据
    acct_payable NUMERIC(20, 4),            -- 应付账款
    adv_receipts NUMERIC(20, 4),            -- 预收款项
    sold_for_repur_fa NUMERIC(20, 4),       -- 卖出回购金融资产款
    comm_payable NUMERIC(20, 4),            -- 应付手续费及佣金
    payroll_payable NUMERIC(20, 4),         -- 应付职工薪酬
    taxes_payable NUMERIC(20, 4),           -- 应交税费
    int_payable NUMERIC(20, 4),             -- 应付利息
    div_payable NUMERIC(20, 4),             -- 应付股利
    oth_payable NUMERIC(20, 4),             -- 其他应付款
    acc_exp NUMERIC(20, 4),                 -- 预提费用
    deferred_inc NUMERIC(20, 4),            -- 递延收益
    st_bonds_payable NUMERIC(20, 4),        -- 应付短期债券
    payable_to_reinsurer NUMERIC(20, 4),    -- 应付分保账款
    rsrv_insur_cont NUMERIC(20, 4),         -- 保险合同准备金
    acting_trading_sec NUMERIC(20, 4),      -- 代理买卖证券款
    acting_uw_sec NUMERIC(20, 4),           -- 代理承销证券款
    non_cur_liab_due_1y NUMERIC(20, 4),     -- 一年内到期的非流动负债
    oth_cur_liab NUMERIC(20, 4),            -- 其他流动负债
    total_cur_liab NUMERIC(20, 4),          -- 流动负债合计

    -- 非流动负债
    bond_payable NUMERIC(20, 4),            -- 应付债券
    lt_payable NUMERIC(20, 4),              -- 长期应付款
    specific_payables NUMERIC(20, 4),       -- 专项应付款
    estimated_liab NUMERIC(20, 4),          -- 预计负债
    defer_tax_liab NUMERIC(20, 4),          -- 递延所得税负债
    defer_inc_non_cur_liab NUMERIC(20, 4),  -- 递延收益-非流动负债
    oth_ncl NUMERIC(20, 4),                 -- 其他非流动负债
    total_ncl NUMERIC(20, 4),               -- 非流动负债合计

    -- 特殊负债
    depos_oth_bfi NUMERIC(20, 4),           -- 同业和其它金融机构存放款项
    deriv_liab NUMERIC(20, 4),              -- 衍生金融负债
    depos NUMERIC(20, 4),                   -- 吸收存款
    agency_bus_liab NUMERIC(20, 4),         -- 代理业务负债
    oth_liab NUMERIC(20, 4),                -- 其他负债
    prem_receiv_adva NUMERIC(20, 4),        -- 预收保费
    depos_received NUMERIC(20, 4),          -- 存入保证金
    ph_invest NUMERIC(20, 4),               -- 保户储金及投资款
    reser_une_prem NUMERIC(20, 4),          -- 未到期责任准备金
    reser_outstd_claims NUMERIC(20, 4),     -- 未决赔款准备金
    reser_lins_liab NUMERIC(20, 4),         -- 寿险责任准备金
    reser_lthins_liab NUMERIC(20, 4),       -- 长期健康险责任准备金
    indept_acc_liab NUMERIC(20, 4),         -- 独立账户负债
    pledge_borr NUMERIC(20, 4),             -- 其中:质押借款
    indem_payable NUMERIC(20, 4),           -- 应付赔付款
    policy_div_payable NUMERIC(20, 4),      -- 应付保单红利
    total_liab NUMERIC(20, 4),              -- 负债合计

    -- 所有者权益
    treasury_share NUMERIC(20, 4),          -- 减:库存股
    ordin_risk_reser NUMERIC(20, 4),        -- 一般风险准备
    forex_differ NUMERIC(20, 4),            -- 外币报表折算差额
    invest_loss_unconf NUMERIC(20, 4),      -- 未确认的投资损失
    minority_int NUMERIC(20, 4),            -- 少数股东权益
    total_hldr_eqy_exc_min_int NUMERIC(20, 4), -- 股东权益合计(不含少数股东权益)
    total_hldr_eqy_inc_min_int NUMERIC(20, 4), -- 股东权益合计(含少数股东权益)
    total_liab_hldr_eqy NUMERIC(20, 4),     -- 负债及股东权益总计

    -- 其他字段
    lt_payroll_payable NUMERIC(20, 4),      -- 长期应付职工薪酬
    oth_comp_income NUMERIC(20, 4),         -- 其他综合收益
    oth_eqt_tools NUMERIC(20, 4),           -- 其他权益工具
    oth_eqt_tools_p_shr NUMERIC(20, 4),     -- 其他权益工具(优先股)
    lending_funds NUMERIC(20, 4),           -- 融出资金
    acc_receivable NUMERIC(20, 4),          -- 应收款项
    st_fin_payable NUMERIC(20, 4),          -- 应付短期融资款
    payables NUMERIC(20, 4),                -- 应付款项
    hfs_assets NUMERIC(20, 4),              -- 持有待售的资产
    hfs_sales NUMERIC(20, 4),               -- 持有待售的负债
    cost_fin_assets NUMERIC(20, 4),         -- 以摊余成本计量的金融资产
    fair_value_fin_assets NUMERIC(20, 4),   -- 以公允价值计量且其变动计入其他综合收益的金融资产
    cip_total NUMERIC(20, 4),               -- 在建工程(合计)(元)
    oth_pay_total NUMERIC(20, 4),           -- 其他应付款(合计)(元)
    long_pay_total NUMERIC(20, 4),          -- 长期应付款(合计)(元)
    debt_invest NUMERIC(20, 4),             -- 债权投资(元)
    oth_debt_invest NUMERIC(20, 4),         -- 其他债权投资(元)
    oth_eq_invest NUMERIC(20, 4),           -- 其他权益工具投资(元)
    oth_illiq_fin_assets NUMERIC(20, 4),    -- 其他非流动金融资产(元)
    oth_eq_ppbond NUMERIC(20, 4),           -- 其他权益工具:永续债(元)
    receiv_financing NUMERIC(20, 4),        -- 应收款项融资
    use_right_assets NUMERIC(20, 4),        -- 使用权资产
    lease_liab NUMERIC(20, 4),              -- 租赁负债
    contract_assets NUMERIC(20, 4),         -- 合同资产
    contract_liab NUMERIC(20, 4),           -- 合同负债
    accounts_receiv_bill NUMERIC(20, 4),    -- 应收票据及应收账款
    accounts_pay NUMERIC(20, 4),            -- 应付票据及应付账款
    oth_rcv_total NUMERIC(20, 4),           -- 其他应收款(合计)（元）
    fix_assets_total NUMERIC(20, 4),        -- 固定资产(合计)(元)
    update_flag VARCHAR(1),                 -- 更新标识

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 主键
    PRIMARY KEY (ts_code, ann_date, end_date, report_type)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_balancesheet_ts_code ON balancesheet(ts_code);
CREATE INDEX IF NOT EXISTS idx_balancesheet_ann_date ON balancesheet(ann_date DESC);
CREATE INDEX IF NOT EXISTS idx_balancesheet_end_date ON balancesheet(end_date DESC);
CREATE INDEX IF NOT EXISTS idx_balancesheet_report_type ON balancesheet(report_type);

-- 添加表注释
COMMENT ON TABLE balancesheet IS '资产负债表数据 (Tushare balancesheet_vip接口, 2000积分/次)';
