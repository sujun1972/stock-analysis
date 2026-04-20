-- 财经快讯表（Phase 2 of news_anns roadmap）
-- 数据源：
--   - caixin  : 财新要闻精选（ak.stock_news_main_cx）— 宏观/产业快讯，最近 ~100 条
--   - eastmoney : 东方财富个股新闻（ak.stock_news_em）— 按 ts_code 拉，最近 ~10 条/股
-- 替代 Tushare 付费的 news / major_news 接口。
--
-- 设计要点：
--   - title + source + publish_time 唯一（财新快讯无独立 publish_time，用抓取时刻兜底；
--     GIN 索引放在 related_ts_codes 上，供个股反查）
--   - related_ts_codes 由 Service 层用"正则 + stock_basic 白名单"双重过滤后写入；
--     eastmoney 来源天然带 [ts_code]；caixin 来源从 summary 中抽取

CREATE TABLE IF NOT EXISTS news_flash (
    id                  BIGSERIAL,
    publish_time        TIMESTAMP   NOT NULL,
    source              VARCHAR(20) NOT NULL,   -- caixin / eastmoney / cls / sina（cls/sina 预留）

    title               TEXT        NOT NULL,
    summary             TEXT,                    -- 摘要或正文（eastmoney 的新闻内容）
    url                 VARCHAR(500),

    tags                TEXT[],                  -- AkShare 原始 tag 或文章来源
    related_ts_codes    TEXT[],                  -- 关联股票代码（Service 层过滤后的合法 ts_code）

    created_at          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id, publish_time)
);

-- TimescaleDB hypertable（按 publish_time 分区，7 天一个 chunk；快讯密集）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'news_flash'
    ) THEN
        PERFORM create_hypertable(
            'news_flash',
            'publish_time',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        );
    END IF;
END $$;

-- 个股反查（GIN 数组索引）
CREATE INDEX IF NOT EXISTS idx_news_flash_related_codes
    ON news_flash USING GIN (related_ts_codes);

-- 按来源 + 时间筛选
CREATE INDEX IF NOT EXISTS idx_news_flash_source_time
    ON news_flash (source, publish_time DESC);

-- 去重辅助索引（注意 hypertable 不能加 UNIQUE 跨分区约束，在 Service 层通过 ON CONFLICT 处理）
CREATE INDEX IF NOT EXISTS idx_news_flash_dedup
    ON news_flash (source, title, publish_time DESC);

COMMENT ON TABLE  news_flash                   IS '财经快讯（AkShare 免费数据源，替代 Tushare news/major_news）';
COMMENT ON COLUMN news_flash.publish_time      IS '发布时间；caixin 接口无此字段时用抓取时刻兜底';
COMMENT ON COLUMN news_flash.source            IS '数据源：caixin / eastmoney / cls / sina';
COMMENT ON COLUMN news_flash.title             IS '快讯标题（caixin 由 summary 首 60 字截取）';
COMMENT ON COLUMN news_flash.summary           IS '摘要或正文';
COMMENT ON COLUMN news_flash.tags              IS 'AkShare 原始 tag（caixin）或 文章来源（eastmoney）';
COMMENT ON COLUMN news_flash.related_ts_codes  IS '关联的 ts_code 列表（经 stock_basic 白名单过滤）';
