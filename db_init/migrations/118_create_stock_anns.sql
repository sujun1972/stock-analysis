-- 公司公告表（Phase 1 of news_anns roadmap）
-- 数据源：AkShare 东方财富聚合（ak.stock_notice_report / ak.stock_individual_notice_report）
-- 替代 Tushare 付费的 anns_d / anns_l 接口

CREATE TABLE IF NOT EXISTS stock_anns (
    ts_code             VARCHAR(20) NOT NULL,
    ann_date            DATE        NOT NULL,

    title               TEXT        NOT NULL,
    anno_type           VARCHAR(50),
    stock_name          VARCHAR(50),
    url                 VARCHAR(500),

    -- 数据源：东方财富（eastmoney）为主；Phase 1.5 按需从 cninfo/交易所抓全文后可扩展
    source              VARCHAR(20) NOT NULL DEFAULT 'eastmoney',

    -- 全文（Phase 1.5 按需填充，默认 NULL）
    content             TEXT,
    content_fetched_at  TIMESTAMP,

    created_at          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (ts_code, ann_date, title)
);

-- TimescaleDB hypertable（按 ann_date 分区，1 个月一个 chunk）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'stock_anns'
    ) THEN
        PERFORM create_hypertable(
            'stock_anns',
            'ann_date',
            chunk_time_interval => INTERVAL '1 month',
            if_not_exists => TRUE
        );
    END IF;
END $$;

-- 查询索引
CREATE INDEX IF NOT EXISTS idx_stock_anns_ts_code
    ON stock_anns (ts_code, ann_date DESC);

CREATE INDEX IF NOT EXISTS idx_stock_anns_anno_type
    ON stock_anns (anno_type, ann_date DESC);

CREATE INDEX IF NOT EXISTS idx_stock_anns_ann_date
    ON stock_anns (ann_date DESC);

-- 全文 URL 按需补齐扫描辅助索引（content_fetched_at IS NULL 的部分索引）
CREATE INDEX IF NOT EXISTS idx_stock_anns_missing_content
    ON stock_anns (ann_date DESC)
    WHERE content_fetched_at IS NULL AND url IS NOT NULL;

COMMENT ON TABLE  stock_anns                    IS '公司公告（AkShare 东方财富聚合，替代 Tushare anns_d）';
COMMENT ON COLUMN stock_anns.ts_code            IS '股票代码（如 300746.SZ）';
COMMENT ON COLUMN stock_anns.ann_date           IS '公告日期';
COMMENT ON COLUMN stock_anns.title              IS '公告标题';
COMMENT ON COLUMN stock_anns.anno_type          IS '公告类型（东方财富口径：年度报告摘要 / 独立董事述职报告 / 减持 / 回购 等）';
COMMENT ON COLUMN stock_anns.stock_name         IS '股票简称（冗余，便于查询免 JOIN）';
COMMENT ON COLUMN stock_anns.url                IS '原始公告详情页 URL（data.eastmoney.com/notices/...）';
COMMENT ON COLUMN stock_anns.source             IS '数据源标识：eastmoney / cninfo / sse / szse';
COMMENT ON COLUMN stock_anns.content            IS '公告正文（按需从 url 抓取，默认 NULL）';
COMMENT ON COLUMN stock_anns.content_fetched_at IS '正文抓取成功时间；NULL 表示未抓取';
