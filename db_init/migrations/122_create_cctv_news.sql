-- 新闻联播表（Phase 2 of news_anns roadmap）
-- 数据源：AkShare `ak.news_cctv`（覆盖 2016-02 起）
-- 替代 Tushare 付费的 cctv_news 接口。
--
-- 每条新闻由 (news_date, seq_no) 唯一确定；seq_no 按当日行序递增。
-- 全量覆盖时每日单次调用约 3-8s，1500 个日历日约 1-2 小时。

CREATE TABLE IF NOT EXISTS cctv_news (
    news_date       DATE        NOT NULL,
    seq_no          INT         NOT NULL,
    title           TEXT        NOT NULL,
    content         TEXT,

    created_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (news_date, seq_no)
);

-- TimescaleDB hypertable（按 news_date 分区，1 个月一个 chunk）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'cctv_news'
    ) THEN
        PERFORM create_hypertable(
            'cctv_news',
            'news_date',
            chunk_time_interval => INTERVAL '1 month',
            if_not_exists => TRUE
        );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_cctv_news_date
    ON cctv_news (news_date DESC);

COMMENT ON TABLE  cctv_news             IS '新闻联播文字稿（AkShare 免费数据源，替代 Tushare cctv_news）';
COMMENT ON COLUMN cctv_news.news_date   IS '联播日期';
COMMENT ON COLUMN cctv_news.seq_no      IS '当日第 N 条（按行序递增，1 起）';
COMMENT ON COLUMN cctv_news.title       IS '新闻标题';
COMMENT ON COLUMN cctv_news.content     IS '新闻全文';
