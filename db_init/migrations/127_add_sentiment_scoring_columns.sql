-- 舆情情绪打分：在 stock_anns / news_flash 上扩展评分字段 + 事件/主题标签。
-- hypertable 的 ALTER TABLE ADD COLUMN 原地生效，无需 VACUUM/REINDEX。

BEGIN;

-- ===== stock_anns：事件标签 + 影响方向 + 情绪分 =====
ALTER TABLE stock_anns
    ADD COLUMN IF NOT EXISTS event_tags TEXT[],
    ADD COLUMN IF NOT EXISTS sentiment_score NUMERIC(4,2),       -- [-1.00, 1.00]
    ADD COLUMN IF NOT EXISTS sentiment_impact VARCHAR(20),        -- bullish/bearish/neutral
    ADD COLUMN IF NOT EXISTS scoring_reason TEXT,                 -- LLM 给出的一句话理由
    ADD COLUMN IF NOT EXISTS scored_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS score_model VARCHAR(80);

-- 按影响方向 + 时间倒序检索个股公告（AI 专家快速筛选利好/利空事件）
CREATE INDEX IF NOT EXISTS idx_stock_anns_sentiment
    ON stock_anns(ts_code, sentiment_impact, ann_date DESC)
    WHERE sentiment_impact IS NOT NULL;

-- 扫描"待打分"队列：近 N 天未打分且有 ts_code 的公告
CREATE INDEX IF NOT EXISTS idx_stock_anns_unscored
    ON stock_anns(ann_date DESC)
    WHERE scored_at IS NULL;

-- 事件标签 GIN 索引（按标签筛选，如 retrieve all 减持公告）
CREATE INDEX IF NOT EXISTS idx_stock_anns_event_tags
    ON stock_anns USING GIN (event_tags);


-- ===== news_flash：情绪分 + 影响方向 + 主题标签（不分类细粒度事件） =====
ALTER TABLE news_flash
    ADD COLUMN IF NOT EXISTS sentiment_score NUMERIC(4,2),
    ADD COLUMN IF NOT EXISTS sentiment_impact VARCHAR(20),
    ADD COLUMN IF NOT EXISTS sentiment_tags TEXT[],
    ADD COLUMN IF NOT EXISTS scoring_reason TEXT,
    ADD COLUMN IF NOT EXISTS scored_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS score_model VARCHAR(80);

-- 扫描"待打分"队列：近 N 天未打分且 related_ts_codes 非空的快讯
CREATE INDEX IF NOT EXISTS idx_news_flash_unscored
    ON news_flash(publish_time DESC)
    WHERE scored_at IS NULL
      AND related_ts_codes IS NOT NULL
      AND array_length(related_ts_codes, 1) > 0;

-- 情绪主题标签 GIN 索引
CREATE INDEX IF NOT EXISTS idx_news_flash_sentiment_tags
    ON news_flash USING GIN (sentiment_tags);


-- ===== llm_call_logs：扩展 business_type 允许 sentiment_scoring =====
-- business_type 字段是 VARCHAR，无 CHECK 约束，无需额外 ALTER；
-- admin 和后端代码处理新枚举值即可。

COMMIT;
