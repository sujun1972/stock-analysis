-- 股票AI分析结果表
-- 存储每只股票的AI分析结果，支持多种分析类型（如游资观点）和版本历史

CREATE TABLE IF NOT EXISTS stock_ai_analysis (
    id              SERIAL PRIMARY KEY,
    ts_code         VARCHAR(20)    NOT NULL,          -- 股票代码，如 000001.SZ
    analysis_type   VARCHAR(50)    NOT NULL,          -- 分析类型，如 'hot_money_view'
    analysis_text   TEXT           NOT NULL,          -- AI分析结果正文
    score           NUMERIC(5, 2),                    -- 评分（0-10，支持一位小数），可选
    prompt_text     TEXT,                             -- 生成本次分析所用的完整提示词快照
    ai_provider     VARCHAR(50),                      -- AI提供商，如 'deepseek'
    ai_model        VARCHAR(100),                     -- 模型名称，如 'deepseek-chat'
    version         INTEGER        NOT NULL DEFAULT 1,-- 同一股票+类型的版本号（从1递增）
    created_by      INTEGER        REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_ai_analysis_ts_code
    ON stock_ai_analysis(ts_code);
CREATE INDEX IF NOT EXISTS idx_stock_ai_analysis_type
    ON stock_ai_analysis(analysis_type);
CREATE INDEX IF NOT EXISTS idx_stock_ai_analysis_ts_code_type_created
    ON stock_ai_analysis(ts_code, analysis_type, created_at DESC);

COMMENT ON TABLE  stock_ai_analysis                     IS '股票AI分析结果，支持多类型、多版本';
COMMENT ON COLUMN stock_ai_analysis.ts_code             IS '股票代码（ts_code格式，如000001.SZ）';
COMMENT ON COLUMN stock_ai_analysis.analysis_type       IS '分析类型标识符，如hot_money_view';
COMMENT ON COLUMN stock_ai_analysis.analysis_text       IS 'AI返回的分析文本正文';
COMMENT ON COLUMN stock_ai_analysis.score               IS '综合评分，0-10（支持一位小数）';
COMMENT ON COLUMN stock_ai_analysis.prompt_text         IS '生成本次分析所用的完整提示词快照';
COMMENT ON COLUMN stock_ai_analysis.version             IS '同一ts_code+analysis_type下的版本号（自动递增）';
COMMENT ON COLUMN stock_ai_analysis.created_by          IS '保存操作者的用户ID';
