# 同步服务统一架构重构计划

## 背景

同步配置页面（`/settings/sync-config`）管理 57 个数据同步任务。其中只有 5 个完全遵循参考实现（`stock_daily_service.py`）的标准架构，其余 52 个存在不同程度的偏差。

偏差导致的问题：
- 从同步配置页面无参数触发增量同步时，部分任务不读 `sync_configs` 的 `incremental_default_days`，使用硬编码回看天数
- 不调用 `get_suggested_start_date()`，不查 `sync_history.data_end_date`，无法保证数据连续性
- 不使用 `run_incremental_sync()`，增量同步不记录 `sync_history`，导致同步配置页新增的「数据至 YYYY-MM-DD」显示为空
- `incremental_sync_strategy` 配置字段形同虚设，修改配置不影响实际同步行为

## 接口参数约束

`sync_configs.api_params`（JSONB 字段，migration 113）记录了每个 Tushare 接口的实际参数支持情况，通过 `scripts/test_api_params.py` 实际调用 API 验证。重构时根据此字段选择同步策略：

| api_params 模式 | 推荐增量策略 | 示例 |
|----------------|-------------|------|
| `start_date=true` | `by_date_range` | daily, adj_factor |
| `trade_date=required` | `by_date`（逐交易日） | top_list, top_inst |
| `ts_code=required, start_date=false` | `by_ts_code` | cyq_chips, fina_audit |
| `ts_code=required, trade_date=optional` | `by_ts_code` 或 `by_date` | cyq_perf, moneyflow |
| 快照接口（全 none/false） | `snapshot` | stk_shock, dc_index, ggt_monthly |
| `month` 必填 | 自定义逐月 | broker_recommend |

## 参考实现标准

以 `stock_daily_service.py` 为标准，一个合规的同步服务需要：

```
Service (extends TushareSyncBase)
├── sync_incremental(start_date=None, end_date=None, sync_strategy=None, ...)
│   ├── 从 sync_configs 读取 api_limit
│   ├── 从 sync_configs 读取 incremental_sync_strategy（sync_strategy=None 时）
│   ├── 调用 get_suggested_start_date()（start_date=None 时）
│   └── 调用 self.run_incremental_sync()（基类方法，自动记录 sync_history）
├── sync_full_history(redis_client, start_date=None, concurrency=5, ...)
│   ├── 从 sync_configs 读取 api_limit
│   └── 调用 self.run_full_sync()（基类方法）
└── get_suggested_start_date()
    ├── 从 sync_configs 读取 incremental_default_days
    └── 从 sync_history 读取上次同步 data_end_date，取更早者
```

Celery 增量任务无参数调用时必须走 `service.sync_incremental()`，不直接调原始方法。

## 现状分类

### A 类：完全合规（5 个）— 无需修改

| Service | table_key |
|---------|-----------|
| stock_daily_service.py | stock_daily |
| adj_factor_service.py | adj_factor |
| daily_basic_service.py | daily_basic |
| stk_limit_d_service.py | stk_limit_d |
| stock_st_service.py | stock_st |

### B 类：半合规（19 个）— 需加 sync_incremental 包装

继承 TushareSyncBase，原始 sync 方法已使用 `run_incremental_sync()` + 读取 `api_limit`，但缺少 `sync_incremental()` 包装层。Celery 任务直接调原始方法，无参数时不走 `get_suggested_start_date()`。

| Service | 原始方法 | table_key |
|---------|---------|-----------|
| block_trade_service.py | sync_block_trade | block_trade |
| ccass_hold_service.py | sync_ccass_hold | ccass_hold |
| cyq_perf_service.py | sync_cyq_perf | cyq_perf |
| cyq_chips_service.py | sync_cyq_chips | cyq_chips |
| hk_hold_service.py | sync_hk_hold | hk_hold |
| stk_auction_o_service.py | sync_stk_auction_o | stk_auction_o |
| stk_auction_c_service.py | sync_stk_auction_c | stk_auction_c |
| stk_ah_comparison_service.py | sync_stk_ah_comparison | stk_ah_comparison |
| stk_surv_service.py | sync_stk_surv | stk_surv |
| stk_nineturn_service.py | sync_stk_nineturn | stk_nineturn |
| stk_shock_service.py | sync_stk_shock | stk_shock |
| stk_high_shock_service.py | sync_stk_high_shock | stk_high_shock |
| stk_alert_service.py | sync_stk_alert | stk_alert |
| report_rc_service.py | sync_report_rc | report_rc |
| pledge_stat_service.py | sync_pledge_stat | pledge_stat |
| repurchase_service.py | sync_repurchase | repurchase |
| share_float_service.py | sync_share_float | share_float |
| stk_holdernumber_service.py | sync_stk_holdernumber | stk_holdernumber |
| stk_holdertrade_service.py | sync_stk_holdertrade | stk_holdertrade |

### B2 类：接口特殊（2 个）— 需定制 sync_incremental

继承 TushareSyncBase，但 Tushare 接口约束导致无法使用 `run_incremental_sync()`。

| Service | 原因 | table_key |
|---------|------|-----------|
| broker_recommend_service.py | 接口只接受 month=YYYYMM | broker_recommend |
| ccass_hold_detail_service.py | 接口要求 ts_code 或 trade_date 必传 | ccass_hold_detail |

### C 类：部分配置（13 个）— 需迁移到 TushareSyncBase

不继承 TushareSyncBase。有 `sync_incremental()` 读取 `incremental_default_days`，但不使用 `run_incremental_sync()`（无 sync_history 记录），不调用 `get_suggested_start_date()`。

| Service | table_key | 接口特点 |
|---------|-----------|---------|
| income_service.py | income | ts_code 必填，by_ts_code |
| balancesheet_service.py | balancesheet | ts_code 必填，by_ts_code |
| cashflow_service.py | cashflow | ts_code 必填，by_ts_code |
| forecast_service.py | forecast | ts_code 必填，by_ts_code |
| express_service.py | express | ts_code 必填，by_ts_code |
| dividend_service.py | dividend | ts_code 必填，by_ts_code |
| disclosure_date_service.py | disclosure_date | 支持日期范围 |
| fina_indicator_service.py | fina_indicator | ts_code 必填，by_ts_code |
| fina_mainbz_service.py | fina_mainbz | ts_code 必填，by_ts_code |
| fina_audit_service.py | fina_audit | ts_code 必填，by_ts_code |
| ggt_top10_service.py | ggt_top10 | 仅支持 trade_date |
| ggt_daily_service.py | ggt_daily | 支持日期范围 |
| margin_secs_service.py | margin_secs | 支持日期范围 |

### D 类：完全自定义（18 个）— 需从零迁移

不继承 TushareSyncBase，无 `sync_incremental()`，不读 `sync_configs`，日期参数硬编码。

| Service | table_key | 接口特点 |
|---------|-----------|---------|
| suspend_service.py | suspend | 支持日期范围 |
| hsgt_top10_service.py | hsgt_top10 | 仅支持 trade_date |
| ggt_monthly_service.py | ggt_monthly | 快照接口 |
| margin_service.py | margin | 支持日期范围 |
| margin_detail_service.py | margin_detail | 支持日期范围 |
| slb_len_service.py | slb_len | 支持日期范围 |
| moneyflow_hsgt_service.py | moneyflow_hsgt | 支持日期范围 |
| moneyflow_mkt_dc_service.py | moneyflow_mkt_dc | 支持日期范围 |
| moneyflow_ind_dc_service.py | moneyflow_ind_dc | 支持日期范围 |
| moneyflow_stock_dc_service.py | moneyflow_stock_dc | akshare，按 ts_code |
| top_list_service.py | top_list | 仅支持 trade_date |
| top_inst_service.py | top_inst | 仅支持 trade_date |
| limit_list_service.py | limit_list | 仅支持 trade_date |
| limit_step_service.py | limit_step | 仅支持 trade_date |
| limit_cpt_service.py | limit_cpt | 仅支持 trade_date |
| dc_index_service.py | dc_index | akshare 快照 |
| dc_member_service.py | dc_member | akshare 快照 |
| dc_daily_service.py | dc_daily | akshare，按板块代码 |

---

## 实施计划

### 第一阶段：B 类批量修复（19 个，低风险，高收益）

这些服务已经继承 TushareSyncBase、已有 `get_suggested_start_date()`、已用 `run_incremental_sync()`，只需加一层薄包装。

**每个服务的改动模板（以 ccass_hold_service.py 为例）**：

**Service 改动** — 新增 `sync_incremental()` 方法：
```python
async def sync_incremental(
    self,
    start_date=None, end_date=None,
    sync_strategy=None, max_requests_per_minute=None,
) -> Dict:
    cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
    if sync_strategy is None:
        sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range'
    if start_date is None:
        start_date = await self.get_suggested_start_date()
    # 委托给已有的原始方法
    return await self.sync_ccass_hold(
        start_date=start_date, end_date=end_date,
        sync_strategy=sync_strategy, max_requests_per_minute=max_requests_per_minute,
    )
```

**Celery 任务改动** — 无参数时调用 `sync_incremental()`：
```python
if not any([ts_code, hk_code, trade_date, start_date, end_date]):
    result = run_async_in_celery(service.sync_incremental)
else:
    result = run_async_in_celery(service.sync_ccass_hold, ...)
```

**执行顺序**：按同步配置页面的分类顺序批量处理。

预计每个服务改动量：Service +15 行，Task +5 行。总计 ~380 行。

### 第二阶段：B2 类定制修复（2 个，中等风险）

**broker_recommend_service.py**：
- 新增 `sync_incremental()` 从 `sync_configs` 读 `incremental_default_days`，计算月份列表
- 手动记录 `sync_history`（调用 `sync_history_repo.create()` / `complete()`）

**ccass_hold_detail_service.py**：
- 已有逐交易日遍历逻辑，改造 `sync_ccass_hold_detail` 无参数分支为 `sync_incremental()`
- 手动记录 `sync_history`

预计每个服务改动量：~30 行。

### 第三阶段：C 类迁移到 TushareSyncBase（13 个，中等风险）

这些服务的特殊性：大部分是财务报表类，Tushare 接口 `ts_code` 必填，增量同步本质是遍历全部股票（`by_ts_code` 策略），这与 `run_incremental_sync` 的 `by_ts_code` 模式完全匹配。

**每个服务的改动**：
1. 改继承 `TushareSyncBase`
2. 添加类常量 `TABLE_KEY`, `FULL_HISTORY_PROGRESS_KEY`, `FULL_HISTORY_LOCK_KEY`
3. 改造 `sync_incremental()` 调用 `run_incremental_sync(sync_strategy='by_ts_code')`
4. 添加 `get_suggested_start_date()`
5. 改造 `sync_full_history()` 调用 `run_full_sync()`

**特殊处理**：
- `ggt_top10_service.py`：接口仅支持 `trade_date`，增量策略用 `by_date`
- `ggt_daily_service.py`：支持日期范围，增量策略用 `by_date_range`
- `margin_secs_service.py`：支持日期范围，增量策略用 `by_date_range`

**执行顺序**：先做 `disclosure_date`、`ggt_daily`、`margin_secs`（支持日期范围，最简单）→ 再做 10 个财务类（统一 by_ts_code 模式）→ 最后做 `ggt_top10`（by_date 特殊模式）。

预计每个服务改动量：~50 行重构。

### 第四阶段：D 类从零迁移（18 个，较高风险）

需要较大重构，但模式统一。按子分类分批实施：

**批次 1：支持日期范围的接口（7 个，最直接）**
- suspend, margin, margin_detail, slb_len
- moneyflow_hsgt, moneyflow_mkt_dc, moneyflow_ind_dc

改动：继承 TushareSyncBase → 添加三个标准方法 → 改造原始 sync 方法调用 `run_incremental_sync`。

**批次 2：仅支持 trade_date 的接口（7 个）**
- hsgt_top10, top_list, top_inst
- limit_list, limit_step, limit_cpt

改动同上，`sync_strategy` 默认 `by_date`，`run_incremental_sync` 的 `by_date` 模式从交易日历获取日期列表逐日请求。

**批次 3：akshare / 快照接口（4 个，需特殊处理）**
- ggt_monthly（快照）
- dc_index, dc_member（akshare 快照）
- dc_daily（akshare，按板块代码遍历）
- moneyflow_stock_dc（akshare，按 ts_code 遍历）

akshare 接口与 Tushare 的 Provider 模式不同，需评估是否适合继承 TushareSyncBase。如果不适合，至少要求：
1. 有 `sync_incremental()` 从 `sync_configs` 读配置
2. 手动记录 `sync_history`

预计每个服务改动量：D 批次 1/2 约 60 行，D 批次 3 约 40 行。

---

## 验证清单

每个服务修改完成后检查：

- [ ] `sync_incremental()` 存在且从 `sync_configs` 读取 `api_limit`
- [ ] `sync_incremental()` 从 `sync_configs` 读取 `incremental_sync_strategy`（或有合理默认值）
- [ ] `sync_incremental()` 在 `start_date=None` 时调用 `get_suggested_start_date()`
- [ ] `get_suggested_start_date()` 从 `sync_configs` 读取 `incremental_default_days`
- [ ] `get_suggested_start_date()` 查询 `sync_history.data_end_date`
- [ ] 增量同步通过 `run_incremental_sync()` 执行（自动记录 sync_history）或手动记录
- [ ] Celery 增量任务无参数调用时走 `service.sync_incremental()`
- [ ] 同步配置页面「数据至」日期正常显示
- [ ] `docker-compose restart celery_worker` 后任务正常注册

## 风险控制

- **不改变原始同步方法的签名和行为**：`sync_incremental()` 是新增的包装层，原始 `sync_xxx()` 方法保持不变，有参数调用时仍走原始路径
- **逐分类提交**：每完成一个分类（如「特色数据」的 B 类服务）提交一次，便于回滚
- **优先 B 类**：改动最小、风险最低、覆盖面最广（19 个），立即可见收益（sync_history 记录 → 「数据至」日期显示）
