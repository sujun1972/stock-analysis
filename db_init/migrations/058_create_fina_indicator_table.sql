-- 创建财务指标数据表 (fina_indicator)
-- Tushare接口：fina_indicator_vip
-- 权限要求：2000积分

CREATE TABLE IF NOT EXISTS fina_indicator (
    -- 主键字段
    ts_code VARCHAR(10) NOT NULL,
    ann_date VARCHAR(8) NOT NULL,
    end_date VARCHAR(8) NOT NULL,

    -- 每股指标
    eps NUMERIC,                     -- 基本每股收益
    dt_eps NUMERIC,                  -- 稀释每股收益
    total_revenue_ps NUMERIC,        -- 每股营业总收入
    revenue_ps NUMERIC,              -- 每股营业收入
    capital_rese_ps NUMERIC,         -- 每股资本公积
    surplus_rese_ps NUMERIC,         -- 每股盈余公积
    undist_profit_ps NUMERIC,        -- 每股未分配利润
    extra_item NUMERIC,              -- 非经常性损益
    profit_dedt NUMERIC,             -- 扣非净利润

    -- 盈利能力指标
    gross_margin NUMERIC,            -- 毛利
    current_ratio NUMERIC,           -- 流动比率
    quick_ratio NUMERIC,             -- 速动比率
    cash_ratio NUMERIC,              -- 保守速动比率

    -- 营运能力指标
    invturn_days NUMERIC,            -- 存货周转天数
    arturn_days NUMERIC,             -- 应收账款周转天数
    inv_turn NUMERIC,                -- 存货周转率
    ar_turn NUMERIC,                 -- 应收账款周转率
    ca_turn NUMERIC,                 -- 流动资产周转率
    fa_turn NUMERIC,                 -- 固定资产周转率
    assets_turn NUMERIC,             -- 总资产周转率

    -- 现金流指标
    op_income NUMERIC,               -- 经营活动净收益
    valuechange_income NUMERIC,      -- 价值变动净收益
    interst_income NUMERIC,          -- 利息费用
    daa NUMERIC,                     -- 折旧与摊销

    -- 盈利指标
    ebit NUMERIC,                    -- 息税前利润
    ebitda NUMERIC,                  -- 息税折旧摊销前利润
    fcff NUMERIC,                    -- 企业自由现金流量
    fcfe NUMERIC,                    -- 股权自由现金流量

    -- 资本结构
    current_exint NUMERIC,           -- 无息流动负债
    noncurrent_exint NUMERIC,        -- 无息非流动负债
    interestdebt NUMERIC,            -- 带息债务
    netdebt NUMERIC,                 -- 净债务
    tangible_asset NUMERIC,          -- 有形资产
    working_capital NUMERIC,         -- 营运资金
    networking_capital NUMERIC,      -- 营运流动资本
    invest_capital NUMERIC,          -- 全部投入资本
    retained_earnings NUMERIC,       -- 留存收益

    -- 每股指标（续）
    diluted2_eps NUMERIC,            -- 期末摊薄每股收益
    bps NUMERIC,                     -- 每股净资产
    ocfps NUMERIC,                   -- 每股经营活动现金流净额
    retainedps NUMERIC,              -- 每股留存收益
    cfps NUMERIC,                    -- 每股现金流量净额
    ebit_ps NUMERIC,                 -- 每股息税前利润
    fcff_ps NUMERIC,                 -- 每股企业自由现金流量
    fcfe_ps NUMERIC,                 -- 每股股东自由现金流量

    -- 利润率指标
    netprofit_margin NUMERIC,        -- 销售净利率
    grossprofit_margin NUMERIC,      -- 销售毛利率
    cogs_of_sales NUMERIC,           -- 销售成本率
    expense_of_sales NUMERIC,        -- 销售期间费用率
    profit_to_gr NUMERIC,            -- 净利润/营业总收入
    saleexp_to_gr NUMERIC,           -- 销售费用/营业总收入
    adminexp_of_gr NUMERIC,          -- 管理费用/营业总收入
    finaexp_of_gr NUMERIC,           -- 财务费用/营业总收入
    impai_ttm NUMERIC,               -- 资产减值损失/营业总收入
    gc_of_gr NUMERIC,                -- 营业总成本/营业总收入
    op_of_gr NUMERIC,                -- 营业利润/营业总收入
    ebit_of_gr NUMERIC,              -- 息税前利润/营业总收入

    -- 收益率指标
    roe NUMERIC,                     -- 净资产收益率
    roe_waa NUMERIC,                 -- 加权平均净资产收益率
    roe_dt NUMERIC,                  -- 净资产收益率(扣非)
    roa NUMERIC,                     -- 总资产报酬率
    npta NUMERIC,                    -- 总资产净利润
    roic NUMERIC,                    -- 投入资本回报率
    roe_yearly NUMERIC,              -- 年化净资产收益率
    roa2_yearly NUMERIC,             -- 年化总资产报酬率
    roe_avg NUMERIC,                 -- 平均净资产收益率

    -- 利润结构
    opincome_of_ebt NUMERIC,         -- 经营活动净收益/利润总额
    investincome_of_ebt NUMERIC,     -- 价值变动净收益/利润总额
    n_op_profit_of_ebt NUMERIC,      -- 营业外收支净额/利润总额
    tax_to_ebt NUMERIC,              -- 所得税/利润总额
    dtprofit_to_profit NUMERIC,      -- 扣非净利润/净利润

    -- 现金流结构
    salescash_to_or NUMERIC,         -- 销售商品收到现金/营业收入
    ocf_to_or NUMERIC,               -- 经营现金流净额/营业收入
    ocf_to_opincome NUMERIC,         -- 经营现金流净额/经营活动净收益
    capitalized_to_da NUMERIC,       -- 资本支出/折旧摊销

    -- 资产负债结构
    debt_to_assets NUMERIC,          -- 资产负债率
    assets_to_eqt NUMERIC,           -- 权益乘数
    dp_assets_to_eqt NUMERIC,        -- 权益乘数(杜邦分析)
    ca_to_assets NUMERIC,            -- 流动资产/总资产
    nca_to_assets NUMERIC,           -- 非流动资产/总资产
    tbassets_to_totalassets NUMERIC, -- 有形资产/总资产
    int_to_talcap NUMERIC,           -- 带息债务/全部投入资本
    eqt_to_talcapital NUMERIC,       -- 股东权益/全部投入资本
    currentdebt_to_debt NUMERIC,     -- 流动负债/负债合计
    longdeb_to_debt NUMERIC,         -- 非流动负债/负债合计

    -- 偿债能力
    ocf_to_shortdebt NUMERIC,        -- 经营现金流/流动负债
    debt_to_eqt NUMERIC,             -- 产权比率
    eqt_to_debt NUMERIC,             -- 股东权益/负债合计
    eqt_to_interestdebt NUMERIC,     -- 股东权益/带息债务
    tangibleasset_to_debt NUMERIC,   -- 有形资产/负债合计
    tangasset_to_intdebt NUMERIC,    -- 有形资产/带息债务
    tangibleasset_to_netdebt NUMERIC,-- 有形资产/净债务
    ocf_to_debt NUMERIC,             -- 经营现金流/负债合计
    ocf_to_interestdebt NUMERIC,     -- 经营现金流/带息债务
    ocf_to_netdebt NUMERIC,          -- 经营现金流/净债务
    ebit_to_interest NUMERIC,        -- 已获利息倍数
    longdebt_to_workingcapital NUMERIC, -- 长期债务与营运资金比率
    ebitda_to_debt NUMERIC,          -- 息税折旧摊销前利润/负债合计

    -- 营运能力（续）
    turn_days NUMERIC,               -- 营业周期
    roa_yearly NUMERIC,              -- 年化总资产净利率
    roa_dp NUMERIC,                  -- 总资产净利率(杜邦)
    fixed_assets NUMERIC,            -- 固定资产合计

    -- 利润质量
    profit_prefin_exp NUMERIC,       -- 扣除财务费用前营业利润
    non_op_profit NUMERIC,           -- 非营业利润
    op_to_ebt NUMERIC,               -- 营业利润/利润总额
    nop_to_ebt NUMERIC,              -- 非营业利润/利润总额
    ocf_to_profit NUMERIC,           -- 经营现金流/营业利润
    cash_to_liqdebt NUMERIC,         -- 货币资金/流动负债
    cash_to_liqdebt_withinterest NUMERIC, -- 货币资金/带息流动负债
    op_to_liqdebt NUMERIC,           -- 营业利润/流动负债
    op_to_debt NUMERIC,              -- 营业利润/负债合计
    roic_yearly NUMERIC,             -- 年化投入���本回报率
    total_fa_trun NUMERIC,           -- 固定资产周转率
    profit_to_op NUMERIC,            -- 利润总额/营业收入

    -- 单季度财务指标
    q_opincome NUMERIC,              -- 经营活动单季度净收益
    q_investincome NUMERIC,          -- 价值变动单季度净收益
    q_dtprofit NUMERIC,              -- 扣非单季度净利润
    q_eps NUMERIC,                   -- 每股收益(单季度)
    q_netprofit_margin NUMERIC,      -- 销售净利率(单季度)
    q_gsprofit_margin NUMERIC,       -- 销售毛利率(单季度)
    q_exp_to_sales NUMERIC,          -- 销售期间费用率(单季度)
    q_profit_to_gr NUMERIC,          -- 净利润/营业总收入(单季度)
    q_saleexp_to_gr NUMERIC,         -- 销售费用/营业总收入(单季度)
    q_adminexp_to_gr NUMERIC,        -- 管理费用/营业总收入(单季度)
    q_finaexp_to_gr NUMERIC,         -- 财务费用/营业总收入(单季度)
    q_impair_to_gr_ttm NUMERIC,      -- 资产减值损失/营业总收入(单季度)
    q_gc_to_gr NUMERIC,              -- 营业总成本/营业总收入(单季度)
    q_op_to_gr NUMERIC,              -- 营业利润/营业总收入(单季度)
    q_roe NUMERIC,                   -- 净资产收益率(单季度)
    q_dt_roe NUMERIC,                -- 净资产收益率(扣非,单季度)
    q_npta NUMERIC,                  -- 总资产净利润(单季度)
    q_opincome_to_ebt NUMERIC,       -- 经营活动净收益/利润总额(单季度)
    q_investincome_to_ebt NUMERIC,   -- 价值变动净收益/利润总额(单季度)
    q_dtprofit_to_profit NUMERIC,    -- 扣非净利润/净利润(单季度)
    q_salescash_to_or NUMERIC,       -- 销售商品收到现金/营业收入(单季度)
    q_ocf_to_sales NUMERIC,          -- 经营现金流/营业收入(单季度)
    q_ocf_to_or NUMERIC,             -- 经营现金流/经营活动净收益(单季度)

    -- 成长能力指标
    basic_eps_yoy NUMERIC,           -- 基本每股收益同比增长率(%)
    dt_eps_yoy NUMERIC,              -- 稀释每股收益同比增长率(%)
    cfps_yoy NUMERIC,                -- 每股经营现金流同比增长率(%)
    op_yoy NUMERIC,                  -- 营业利润同比增长率(%)
    ebt_yoy NUMERIC,                 -- 利润总额同比增长率(%)
    netprofit_yoy NUMERIC,           -- 归母净利润同比增长率(%)
    dt_netprofit_yoy NUMERIC,        -- 归母净利润(扣非)同比增长率(%)
    ocf_yoy NUMERIC,                 -- 经营现金流同比增长率(%)
    roe_yoy NUMERIC,                 -- 净资产收益率同比增长率(%)
    bps_yoy NUMERIC,                 -- 每股净资产相对年初增长率(%)
    assets_yoy NUMERIC,              -- 资产总计相对年初增长率(%)
    eqt_yoy NUMERIC,                 -- 归母股东权益相对年初增长率(%)
    tr_yoy NUMERIC,                  -- 营业总收入同比增长率(%)
    or_yoy NUMERIC,                  -- 营业收入同比增长率(%)

    -- 单季度成长能力
    q_gr_yoy NUMERIC,                -- 营业总收入同比增长率(单季度)
    q_gr_qoq NUMERIC,                -- 营业总收入环比增长率(单季度)
    q_sales_yoy NUMERIC,             -- 营业收入同比增长率(单季度)
    q_sales_qoq NUMERIC,             -- 营业收入环比增长率(单季度)
    q_op_yoy NUMERIC,                -- 营业利润同比增长率(单季度)
    q_op_qoq NUMERIC,                -- 营业利润环比增长率(单季度)
    q_profit_yoy NUMERIC,            -- 净利润同比增长率(单季度)
    q_profit_qoq NUMERIC,            -- 净利润环比增长率(单季度)
    q_netprofit_yoy NUMERIC,         -- 归母净利润同比增长率(单季度)
    q_netprofit_qoq NUMERIC,         -- 归母净利润环比增长率(单季度)
    equity_yoy NUMERIC,              -- 净资产同比增长率

    -- 研发费用
    rd_exp NUMERIC,                  -- 研发费用

    -- 更新标识
    update_flag VARCHAR(1),          -- 更新标识

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (ts_code, ann_date, end_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_fina_indicator_ts_code ON fina_indicator(ts_code);
CREATE INDEX IF NOT EXISTS idx_fina_indicator_ann_date ON fina_indicator(ann_date DESC);
CREATE INDEX IF NOT EXISTS idx_fina_indicator_end_date ON fina_indicator(end_date DESC);

-- 表注释
COMMENT ON TABLE fina_indicator IS '财务指标数据（Tushare fina_indicator_vip接口，2000积分/次）';
COMMENT ON COLUMN fina_indicator.ts_code IS 'TS股票代码';
COMMENT ON COLUMN fina_indicator.ann_date IS '公告日期 YYYYMMDD';
COMMENT ON COLUMN fina_indicator.end_date IS '报告期 YYYYMMDD';
COMMENT ON COLUMN fina_indicator.eps IS '基本每股收益';
COMMENT ON COLUMN fina_indicator.dt_eps IS '稀释每股收益';
COMMENT ON COLUMN fina_indicator.roe IS '净资产收益率';
COMMENT ON COLUMN fina_indicator.roe_waa IS '加权平均净资产收益率';
COMMENT ON COLUMN fina_indicator.debt_to_assets IS '资产负债率';
COMMENT ON COLUMN fina_indicator.netprofit_margin IS '销售净利率';
COMMENT ON COLUMN fina_indicator.grossprofit_margin IS '销售毛利率';
