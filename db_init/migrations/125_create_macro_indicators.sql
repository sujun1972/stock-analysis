-- 宏观经济指标表（Phase 3 of news_anns roadmap）
-- 数据源：AkShare 免费接口（替代 Tushare 付费的 eco_cal 宏观日历）
--
-- 覆盖指标（indicator_code 取值）：
--   cpi_yoy            CPI 月度同比（ak.macro_china_cpi_monthly）
--   ppi_yoy            PPI 月度同比（ak.macro_china_ppi）
--   pmi_manu           制造业 PMI（ak.macro_china_pmi）
--   pmi_nonmanu        非制造业 PMI（ak.macro_china_pmi）
--   m2_yoy             M2 货币供应同比（ak.macro_china_m2_yearly）
--   new_credit_month   新增社融当月值（ak.macro_china_new_financial_credit，单位亿元）
--   gdp_yoy            GDP 季度同比（ak.macro_china_gdp_yearly）
--   shibor_on          Shibor 隔夜（ak.macro_china_shibor_all）
--   shibor_1w          Shibor 1 周
--   shibor_1m          Shibor 1 月
--
-- 存储规模：月度 × 7 个 + 日度 Shibor × 3 个（2015+ 约 2500 日 × 3 ≈ 7500 行）
-- 合计 ~1 万行级别，不用 hypertable。

CREATE TABLE IF NOT EXISTS macro_indicators (
    indicator_code      VARCHAR(50) NOT NULL,
    period_date         DATE        NOT NULL,

    value               NUMERIC(20, 6),
    yoy                 NUMERIC(10, 4),   -- 同比（%）
    mom                 NUMERIC(10, 4),   -- 环比（%）

    publish_date        DATE,             -- 发布日（可选；月度指标通常滞后约 1 个月）
    source              VARCHAR(30) NOT NULL DEFAULT 'akshare',
    raw                 JSONB,            -- 原始字段兜底

    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (indicator_code, period_date)
);

CREATE INDEX IF NOT EXISTS idx_macro_indicators_code_date
    ON macro_indicators (indicator_code, period_date DESC);

CREATE INDEX IF NOT EXISTS idx_macro_indicators_publish
    ON macro_indicators (publish_date DESC NULLS LAST);

COMMENT ON TABLE  macro_indicators                   IS '宏观经济指标（AkShare 免费数据源，替代 Tushare eco_cal）';
COMMENT ON COLUMN macro_indicators.indicator_code    IS '指标代码：cpi_yoy / ppi_yoy / pmi_manu / pmi_nonmanu / m2_yoy / new_credit_month / gdp_yoy / shibor_on / shibor_1w / shibor_1m';
COMMENT ON COLUMN macro_indicators.period_date       IS '报告期（月度=月初，季度=季度末，日度=当日）';
COMMENT ON COLUMN macro_indicators.value             IS '主值（CPI/PPI/PMI/GDP/M2=同比%；新增社融=亿元；Shibor=报价%）';
COMMENT ON COLUMN macro_indicators.yoy               IS '同比（%），若 value 已是同比则与 value 相同';
COMMENT ON COLUMN macro_indicators.mom               IS '环比（%），仅新增社融等少数指标提供';
COMMENT ON COLUMN macro_indicators.publish_date      IS '数据发布日（与 period_date 差代表滞后天数；LLM 用于时效标注）';
COMMENT ON COLUMN macro_indicators.source            IS '数据源标识：默认 akshare';
COMMENT ON COLUMN macro_indicators.raw               IS 'AkShare 原始字段兜底（中文列名）';
