# Claude Development Guide

## 开发环境启动

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## 项目结构

| 子项目 | 技术栈 | 说明 | 详细指南 |
|--------|--------|------|---------|
| `/admin` | Next.js, Zustand, shadcn/ui | 管理后台 | [admin/CLAUDE.md](admin/CLAUDE.md) |
| `/backend` | FastAPI, Celery, PostgreSQL | 后端 API 服务 | [backend/CLAUDE.md](backend/CLAUDE.md) |
| `/core` | Python, Tushare, LightGBM | 核心业务逻辑 | [core/CLAUDE.md](core/CLAUDE.md) |
| `/frontend` | Next.js | 用户前端 | [frontend/CLAUDE.md](frontend/CLAUDE.md) |
| `/db_init` | SQL | 数据库迁移脚本 | — |

## 常用命令

```bash
docker-compose ps                          # 查看容器状态
docker-compose logs -f [service_name]      # 查看日志
docker-compose restart [service_name]      # 重启服务
docker-compose down                        # 停止所有服务
docker-compose restart celery_worker       # 新增 Celery 任务后必须重启
```

## 文档写入规范

- **不要**在项目目录中创建任务过程说明文档（如 `docs/xxx_summary.md`）
- 临时记录使用系统临时目录：`/tmp/claude_notes_<timestamp>.md`
- 项目正式文档仅包括：架构设计、API 文档、用户手册、长期维护的开发指南

## Git Commit 规范

```bash
git commit -m "type(scope): 简短描述

详细说明:
- 问题1: 描述 + 修复
- 问题2: 描述 + 修复

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## 跨项目架构

### 数据流

```
Tushare / AkShare
    ↓
core/src/providers/    ← Provider 封装（统一接口）
    ↓
backend/app/services/  ← Service 层（业务逻辑、Celery 任务）
    ↓
backend/app/repositories/ ← Repository 层（数据库访问）
    ↓
TimescaleDB / Redis
    ↓
backend/app/api/       ← FastAPI 端点
    ↓
admin/ 或 frontend/    ← 前端页面
```

### LLM 调用架构

所有 AI 分析（个股专家、市场情绪、盘前碰撞、策略生成）统一通过 LangChain 调用 LLM：

```
ai_provider_configs 表          ← 数据库驱动的 Provider 配置（api_key、model、temperature 等）
    ↓
AIStrategyService.create_client(provider, config)
    ↓
LangChainClient                 ← backend/app/services/langchain_client.py
    ↓
ChatOpenAI (deepseek/openai)    或  ChatGoogleGenerativeAI (gemini)
```

- **新增 Provider**：在 `langchain_client.py` 的 `_MODEL_FACTORIES` 注册工厂函数，数据库 `ai_provider_configs` 添加配置行
- **Prompt 模板**：数据库驱动（`llm_prompt_template` 表），通过 `PromptTemplateService` 管理
- **调用日志**：`llm_call_logs` 表 + `LLMCallLogger` 单例，手动 `create_log_entry` / `update_log_success`
- **依赖包**：`langchain`、`langchain-core`、`langchain-openai`、`langchain-google-genai`

### CIO Agent 架构（Phase 3）

CIO（首席投资官）专家使用 LangChain Agent 模式，可自主决定查询哪些数据维度：

```
CIOAgentService                      ← backend/app/services/cio_agent_service.py
    ↓
create_agent(model, tools, system_prompt)   ← langchain.agents.create_agent（LangGraph）
    ↓
11 个 LangChain Tool                 ← backend/app/services/langchain_tools.py
    ├── get_basic_market             基础盘面（价格/PE-PB 双窗口分位+估值通道/大盘相对强度/财务+滞后天数/行业/筹码/回购）
    ├── get_capital_flow             资金流向（主力分档：超大单/大单/中单/小单；近5/10日资金vs价格；北向滞后标注）
    ├── get_shareholder_info         股东信息（人数变化+滞后天数、减持、解禁）
    ├── get_technical_indicators     技术指标（MA/RSI/MACD/布林/K线/量价；含涨停日专属语义、明日布林上轨推演）
    ├── get_financial_reports        财报披露日期 + 业绩预告(24个月) + Forward PE 推演
    ├── get_risk_alerts              风险警示（ST、质押）
    ├── get_nine_turn                TD 序列（即神奇九转，第9根为变盘窗口）
    ├── get_recent_anns              近 N 天公司公告（标题/类型/日期/URL，来自 AkShare 东方财富聚合）
    ├── get_recent_news              近 N 天关联财经快讯（财新要闻 + 东财个股新闻，news_flash 表 GIN 数组反查）
    ├── get_today_cctv_news          新闻联播文字稿（指定日或最近 N 天；宏观/政策信号背景）
    └── get_macro_snapshot           宏观经济指标快照（CPI/PPI/PMI/M2/新增社融/GDP/Shibor，带滞后天数；`macro_indicators` 表）

`StockDataCollectionService.collect_and_format()` 主链路另含六个维度尚未挂为 LangChain Tool；如需 CIO Agent 主动查询可在 `langchain_tools.py` 追加对应工具（`get_recent_anns` / `get_recent_news` / `get_today_cctv_news` 已按该模式挂载）：
- **smart_money**：融资融券明细 + 龙虎榜事件（含席位性质标记 `_SEAT_TAGS` / `_SEAT_SUBSTRING_TAGS`；无上榜时 `on_billboard_60d=False` 显式标记，避免 LLM 误判为数据缺失）
- **limit_ecology**：涨停生态（最近交易日全市场涨停/跌停/炸板 + 连板天梯 Top5 + 最强板块 Top5 + 本股当日涨停身位）
- **limit_history**：个股近 60 日涨停基因（涨停次数 / T+1 胜率 + 平均溢价 / 最近涨停距今交易日数）
- **auction_baseline**：竞价基准对比（当日开盘/收盘竞价成交额 vs 近 20 日均值倍数，识别盘前抢筹/冷场）
- **dividend**：股息率 TTM + 最近实施年度（含税派息 + 分红率）+ 最新预案 + 连续分红年数 + 近 6 年派息历史（长线价值的"债性回报锚"）
- **analyst_consensus**：近 60 日券商一致预期（基于 `report_rc` 表）— 机构覆盖数 + 评级分布 + EPS 共识（按年度聚合）+ 目标价中位数/空间（`min_price` 取值，`tp` 字段单位异常已过滤，目标价 > 当前价×4 视为污染剔除）
- **recent_announcements**：近 30 天公司公告（标题/类型/日期/URL，元数据，来自 `stock_anns` 表 / AkShare 东方财富聚合）；text_formatter 渲染到"三B、近期公司公告"段，CIO Agent 通过 `get_recent_anns` 工具按需查询
- **recent_news**：近 7 天关联财经快讯（`news_flash` 表 / AkShare 财新要闻 + 东财个股新闻），GIN 数组索引按 `related_ts_codes` 反查；text_formatter 渲染到"三C、近期关联快讯"段，CIO Agent 通过 `get_recent_news` 工具按需查询。caixin 来源无关联股，由 `StockCodeExtractor`（正则 + `stock_basic` 白名单双校验）从 title/summary 抽取后写入

**PE / PB 估值分位双窗口（v2 起）**：`get_basic_market` 输出 `pe_valuation` / `pb_valuation`，各含 `window_3y` + `window_10y`（近周期 vs 全周期）。当两窗口分位差 ≥ 30pct 时附加 `divergence.note` 中性事实（由 LLM 判断是"估值泡沫"还是"盈利塌陷导致分母效应"）。长线专家 prompt v3 强制消费这两对分位 + 股息 + 卖方共识，避免单一 PE 分位对周期股的系统性误判。
```

`get_technical_indicators` 内部委托三个独立分析服务（纯计算，无 IO）：

| 服务 | 文件 | 职责 |
|------|------|------|
| `MaAnalysisService` | `ma_analysis_service.py` | 均线多周期结构（排列形态、支撑阻力、核心博弈点、收敛度、乖离率） |
| `MacdAnalysisService` | `macd_analysis_service.py` | MACD 多级别分析（零轴、交叉、动能、背离、跨级别共振） |
| `RsiAnalysisService` | `rsi_analysis_service.py` | RSI 多周期分析（超买超卖、趋势方向、背离、跨周期共振） |
| `BollAnalysisService` | `boll_analysis_service.py` | 布林线多级别分析（通道宽度、价格位置/%B、中轨方向、突破信号、跨级别共振） |
| `CandlestickAnalysisService` | `candlestick_analysis_service.py` | K 线形态识别（单根形态基于真实涨跌幅分档、组合形态含高低位语境、重心趋势） |
| `VolumePriceAnalysisService` | `volume_price_analysis_service.py` | 量价动能（逐日推演、中线结构、天量压力、异动检测、近5日量能结构=上涨日总量/下跌日总量） |

**数据层输出原则（适用于所有写给 LLM 的数据收集模块，不仅是技术指标服务）**：

1. **只给中性事实，不下定论**。禁止使用"诱多失败/恐慌出货/边际利好钝化/反转预期被打脸/极端高估区/势均力敌/趋势惯性仍强"等带情感或判断的措辞。把"显著放量"换成"量比 1.5~2.0x"，把"⚠ 估值透支告警"换成"PE 与 P90 偏离度 +22.0%"。判断由 LLM 完成。
2. **季度/季报快照必须告知滞后天数**（`days_lag` / `days_since_end`）。北向持股（季报频次）、股东人数、财报 ROE 等都是快照，不带滞后提示会被 AI 误用为即时数据。统一用 `formatters.days_since(date_raw, today)`。
3. **环比/同比对比必须明示基准期**。"较历史变动 +184%" 是黑话；"较上期(2025-12-31)持股变动 -58.79%" 才是事实。
4. **暴露口径与单位**。"主力净流入"在 LLM 语境是黑盒，必须在表头或 caliber 字段说清"主力 = 超大单(≥100万) + 大单(20~100万)，单位：万元"。同理 PE Band 应给出 P10/P50/P90/P99 的具体数值，让 AI 直接对比。
5. **缺失维度也是事实**。如果某项数据库无（如盘口挂单），就不渲染该字段；不要伪造。
6. **共用工具集中在 `formatters.py`**：日期解析（`parse_date_loose` / `days_since` / `format_date_dashed`）、分位数（`quantile`）、各类格式化（`fmt_amount` / `fmt_wan` / `fmt_flow` / `fmt_vol`）。新加 collector 时不要重复造轮子。
7. **金额/股数渲染必须走 `fmt_amount`（原始单位：元）/ `fmt_vol`（原始单位：股）**，禁止手写 `{fmt(v)} 万元` —— 除非底层字段确实是万元单位。Tushare 的 `repurchase.amount`、`margin_detail.rzye`、`moneyflow.*` 等原始单位是元，直接贴"万元"会放大 1 万倍（见历史 bug：回购金额 6182 万被误显示为 6182 亿）。
8. **时效性文案用"距披露日 / 距报告期末 N 个自然日"**，禁止模糊"距今 N 天"——周末/节假日会让 LLM 按自然日误判数据陈旧度。跨度用交易日时明说"距今 N 交易日"。

**两套输出格式**：
- **LangChain Tool 输出**（CIO Agent 调用）：Markdown 表格格式
- **`collect_and_format()` 输出**（个股专家分析）：技术指标部分使用 YAML 代码块（```` ```yaml ````），其余章节保持 Markdown；综合推理任务在 YAML 外作为自然语言指令

**`_build_cross_verification`（信号汇总）**为动态生成：根据实际检测到的信号（矛盾点、背离、K线危险形态、乖离率盈亏比）自动组装编号任务列表，无背离时不生成背离评估指令，避免 AI 幻觉。输出包含支撑/阻力位阶梯（从 MA、布林带、20日极值自动聚合）。

**`ai_output_parser.extract_json_text` 含 JSON 自动修复**：两级修复策略——① 中间修复（`_repair_misplaced_keys`）：通过深度追踪检测应在顶层的 key 被嵌入子对象时，在其前方插入缺失的 `}`；② 末尾补全（`_repair_trailing`）：AI 截断导致缺少 1-3 个闭合 `}` / `]` 时自动补全。`_EXPECTED_TOP_KEYS` 集合定义了专家分析 JSON 的顶层字段名。

- **触发方式**：`analysis_type == "cio_directive"` 时自动走 Agent 路径（`/generate` 和 `/generate-multi` 端点）
- **非 CIO 类型**不走 Agent，保持现有直接调用方式
- **max_iterations**：5 轮（通过 LangGraph `recursion_limit` 控制）
- **超时**：120 秒
- **Expert Summaries**：`/generate-multi` 的 `include_cio=true` 时，前面专家的输出摘要会注入 Agent 的用户消息

### 个股专家 Prompt 模板规范

所有个股 JSON 分析类型（`hot_money_view` / `midline_industry_expert` / `longterm_value_watcher` / `macro_risk_expert`）的 prompt 模板（`llm_prompt_templates` 表）共享以下约定：

**模板变量**（由 `build_stock_prompt()` 在 `backend/app/api/endpoints/prompt_templates.py` 注入）：
- `{{ stock_name_and_code }}`：目标股票名称+代码
- `{{ current_date_with_context }}`：带交易日语义的参考日期——今日是交易日则注明"今日为交易日"，否则注明"系统分析日，非交易日 + 上一交易日 + 下一交易日"；所有"次日"预测统一指向**下一交易日**，避免 LLM 在周末/节假日做时间错位预测
- `{{ next_trade_date }}`：独立的下一交易日字段（经 `TradingCalendarRepository.get_next_trading_day` 查询真实日历）
- `{{ stock_data_collection }}`：完整数据收集报告（由 `StockDataCollectionService.collect_and_format()` 填充）

**硬约束块**（推荐放在 `system_prompt` 或 user prompt 开头）：
1. 不得脑补（缺失字段据实填 `数据不足 / 未上榜 / 无披露`）
2. 不得换算（所有数值直接引用原始数据）
3. 滞后数据必须标注报告期 + 滞后天数
4. 异常值过滤（单位错误/逻辑矛盾时写"数据异常/不可用"）

**JSON schema 统一 `final_score` 结构**：
```
"final_score": {
  "score": 0.0,
  "rating": "专家自定义分档",
  "bull_factors": ["正向因子 1（引用具体数据）", ...],
  "bear_factors": ["负向因子 1（引用具体数据）", ...],
  "key_quote": "一句话核心结论（≤50 字）"
}
```
`ai_output_parser.StockExpertAnalysisResult.extract_score()` 会按 `final_score.score` → `comprehensive_score` → `score` 顺序提取；旧模板的 `pros/cons` 字段前端仍兜底兼容但新模板一律用 `bull_factors/bear_factors`。

**新增专家类型 checklist**：
1. Prompt 迁移脚本在 `backend/scripts/migrate_*_template.py`（重新执行会 UPSERT）
2. 后端 `app/api/endpoints/stock_ai_analysis.py` 的 `ALLOWED_ANALYSIS_TYPES` 和 `_JSON_ANALYSIS_TYPES` 更新
3. 前端 `HotMoneyViewDialog.tsx` 的 `SECTION_CONFIGS` 添加对应 `analysisType` 的 section 列表（title + labels 映射）
4. `admin/types/prompt-template.ts` 的 `BUSINESS_TYPES` 和 `BUSINESS_TYPE_LABELS` 添加

### 专家自评（事后复盘）架构

各专家可对自己此前发出的报告做事后复盘（`POST /api/stock-ai-analysis/generate-review`）。复盘结果作为独立 `analysis_type` 写入 `stock_ai_analysis` 表，并通过 `original_analysis_id` 列指向被复盘的原记录。

**REVIEW_CONFIGS**（在 `endpoints/stock_ai_analysis.py` 维护）：单一 endpoint 按 `review_type` 路由到不同 source/save 类型 + prompt 模板 + 时间窗约束。新增复盘类型在此追加一行即可。

| review_type | source_type | save_type | 模板 | min_days_lag |
|-------------|------------|-----------|------|--------------|
| `hot_money` | `hot_money_view` | `hot_money_review` | `hot_money_review_v1` | 0（T+1 即可复盘） |
| `midline` | `midline_industry_expert` | `midline_review` | `midline_review_v1` | 20（≥1 个月） |
| `longterm` | `longterm_value_watcher` | `longterm_review` | `longterm_review_v1` | 90（≥1 个季度） |

- **时间窗校验**：原报告距今 `< min_days_lag` 自然日时拒绝，错误消息含"建议..."关键词；前端 `handleReview` 检测到该关键词弹 `window.confirm` 询问是否 `force=true` 重试。
- **`build_stock_prompt` 的 `extra_variables` 参数**：复盘端点通过该参数把 `{{ original_analysis_date }}` / `{{ original_analysis_json }}` / `{{ days_since_original }}` 注入复盘模板，避免在通用 `build_stock_prompt` 内硬编码复盘字段。
- **复盘 prompt 评分语义**：`final_score.score` 评的是**原报告预测准确度**而非股票投资价值；中线/长线复盘模板含"时效降级规则"（时效不足时评分上限封顶）。
- **前端 Tab 布局**：`HotMoneyViewDialog` 的 `TabsList` 用 `grid-cols-8` 排：游资 / 游资复盘 / 中线 / 中线复盘 / 价值 / 价值复盘 / CIO / 数据；游资/中线/价值三个原始 Tab 通过 `enableReview + reviewType` 在每条历史记录旁渲染橙色 `RotateCcw` 按钮触发复盘，成功后 `onReviewCreated(reviewType)` 让父组件切到对应复盘 Tab。

### Celery 任务架构

- Worker：`celery_worker` 容器
- Beat 调度器：`celery_beat` 容器（数据库驱动，30秒同步配置）
- 任务状态持久化：`celery_task_history` 表（通过 `celery_signals.py` 信号自动更新）
- 前端轮询：Header 组件每 5 秒轮询活动任务，每 30 秒同步历史

**fork pool worker 注意**：Celery worker 通过 fork 继承父进程连接池。`celery_signals.py` 中的 `worker_process_init` 信号在每个 fork worker 启动时重置 `DatabaseManager` 单例，避免连接池损坏。

### 数据库连接池总览

| 连接池 | 上限 |
|--------|------|
| SQLAlchemy 同步引擎（backend） | 15 |
| SQLAlchemy 异步引擎（backend） | 15 |
| psycopg2（core） | 20 |
| **合计** | **≈50** |
| PostgreSQL max_connections | **200** |

`max_connections=200` 已通过 `ALTER SYSTEM` 持久化。

### 数据同步架构（异步任务模式）

所有数据同步操作通过 Celery 异步任务执行：

1. 前端点击同步按钮 → `POST /api/{table}/sync-async`
2. 后端提交 Celery task + 记录 `celery_task_history`
3. 前端 `addTask()` + `triggerPoll()` 立即更新 Header 图标
4. Celery worker 执行同步，信号自动更新任务状态
5. 前端完成回调 `registerCompletionCallback` 触发数据刷新

**sync_configs 表**（`db_init/migrations/105_create_sync_configs.sql`）是所有数据表同步配置的单一数据源，驱动同步配置页面（`/settings/sync-config`）的展示和操作。

**AkShare 数据源独立同步路径**（现已覆盖公司公告 / 财经快讯 / 新闻联播 / 宏观经济指标）：

| 表 | 数据来源（AkShare 接口） | 增量语义 | 全量能力 |
|----|---------------------|---------|---------|
| `stock_anns` | `stock_notice_report` + `stock_individual_notice_report` | 逐交易日拉全市场公告 | 按交易日并发 + Redis Set 续继 |
| `news_flash` | `stock_news_main_cx`（caixin）+ `stock_news_em`（eastmoney 个股） | 高频增量（无日期参数） | 退化为单次增量（无历史能力） |
| `cctv_news` | `news_cctv` | 按自然日逐日回看 N 天 | 按日并发 + Redis Set 续继 |
| `macro_indicators` | `macro_china_cpi_monthly` / `macro_china_ppi` / `macro_china_pmi` / `macro_china_m2_yearly` / `macro_china_new_financial_credit` / `macro_china_gdp_yearly` / `macro_china_shibor_all` | 单次遍历 7 个接口各拉完整历史并 UPSERT（无日期参数） | 同增量（无历史参数） |

**宏观指标派生 code**：`pmi` 接口同时产出 `pmi_manu` / `pmi_nonmanu`；`shibor` 接口产出 `shibor_on` / `shibor_1w` / `shibor_1m`。Provider 层注册表 `MACRO_INDICATOR_FETCHERS` 是 7 条（fetcher 维度），落地表是 10 条 `indicator_code`（物理维度）。Service `get_macro_snapshot(lookback_months=0)` 跳过序列拉取供 CIO Tool 用，`=12` 供前端画图用。

AkShare 接口签名（无 `limit/offset`，无统一 `start_date/end_date`，部分接口按自然日而非交易日）与 `TushareSyncBase.run_incremental_sync` 不兼容，需手写 Service 流程：

- **Provider**：在 `core/src/providers/akshare/_mixins/` 下新建功能域 mixin（如 `news_and_anns.py`），挂到 `AkShareProvider` 的多重继承链上。多 schema 共存时用 `_call_and_wrap(normalizer=..., empty_factory=..., call_context=...)` 复用错误处理样板，不为每个数据域复制一份
- **Service**：放在 `backend/app/services/news_anns/`（或新子包），**不继承** `TushareSyncBase`；手写 `sync_incremental` / `sync_by_stock` / `sync_full_history` 三个入口，并手动调用 `sync_history_repo.create` / `.complete`。接口无历史能力时 `sync_full_history` 退化为单次增量（参考 `news_flash_sync_service`），按钮仅兼容同步配置页
- **Celery 任务**：仍可用 `_task_factory.make_incremental_task` / `make_full_history_task`，把 `raw_sync_method` 指回 `sync_incremental`，参考 `backend/app/tasks/news_anns_tasks.py`
- **sync_configs**：分类 `新闻公告`（与 Tushare 数据源并列），`passive_sync_enabled=true` 支持单只被动同步（如 `tasks.sync_stock_anns_single` / `tasks.sync_news_flash_single`）
- **Service 层重试**：Service 自己做的非 Provider 爬虫（如 `anns_content_fetcher` 抓 PDF/HTML 正文）用 `app.services.news_anns.AkShareRetryDecorator` —— 指数退避 + 限流识别 + 失败告警，支持同步/异步函数
- **文本 → ts_code 抽取**：`StockCodeExtractor`（`app.services.news_anns.stock_code_extractor`）提供"正则 + `stock_basic` 白名单"双校验，覆盖上市/退市/暂停三种状态。`.extract_from_items(items)` 就地为 dict 列表填充 `related_ts_codes`，合并已有与正则抽取结果。caixin 快讯因原始接口无关联股，必须经此抽取才能 GIN 反查

## 已移除功能（2026-03-25）

以下功能已从系统中移除，勿再添加：

- **概念标签管理**：`/concepts` 页面、`ConceptRepository`、`ConceptSyncService`、相关表（`concept`、`stock_concept`）
- **Frontend 股票/数据中心页面**：`/stocks`、`/stocks/[code]`、`/sync/initialize`、`/sync/extended`（API 和数据保留）
- **市场情绪功能**：大盘情绪指标、涨停板池、龙虎榜数据查询、情绪周期分析（AI 情绪分析和盘前预期保留）
