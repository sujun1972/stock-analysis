# Tushare数据同步扩展实施方案

## 项目背景

本系统是一个A股量化交易分析平台，主要用于股票分析和AI生成交易提示词，重点服务于短线交易策略。当前系统已实现部分基础功能，需要扩展Tushare数据源的同步范围，以支持更全面的短线交易分析。

## 一、现状分析

### 1.1 已实现功能

#### 基础架构
- **数据提供者模式**：BaseDataProvider抽象类 + Tushare/AKShare具体实现
- **任务调度系统**：Celery + Redis + DatabaseScheduler动态任务管理
- **数据库架构**：PostgreSQL + TimescaleDB时序数据库
- **API服务**：FastAPI + 异步处理
- **数据处理管道**：验证、修复、增量更新机制

#### 已有数据表
| 数据类型 | 表名 | 说明 | 状态 |
|---------|------|------|------|
| 股票列表 | stock_basic | 全部A股基本信息 | ✅ 已实现 |
| 日线行情 | stock_daily | 历史日线数据(Hypertable) | ✅ 已实现 |
| 分钟行情 | stock_min | 1/5/15/30/60分钟数据 | ✅ 已实现 |
| 实时行情 | stock_realtime | 最新行情快照 | ✅ 已实现 |
| 交易日历 | trading_calendar | A股交易日历 | ✅ 已实现 |
| 涨停数据 | limit_up_pool | 涨停板情绪池 | ✅ 已实现 |
| 龙虎榜 | dragon_tiger_list | 龙虎榜详情 | ✅ 已实现 |
| 市场情绪 | market_sentiment_daily | 大盘指数数据 | ✅ 已实现 |

### 1.2 缺失的关键数据（短线交易必需）

| 优先级 | 数据类型 | Tushare接口 | 积分消耗 | 对短线交易价值 |
|-------|---------|------------|---------|--------------|
| P0 | 资金流向 | moneyflow | 2000 | 判断主力动向，极其重要 |
| P0 | 每日指标 | daily_basic | 120 | 换手率、PE等关键指标 |
| P1 | 北向资金 | hk_hold | 300 | 外资动向，重要参考 |
| P1 | 涨跌停价格 | stk_limit | 120 | 交易价格参考 |
| P2 | 融资融券 | margin_detail | 300 | 市场情绪指标 |
| P2 | 复权因子 | adj_factor | 120 | 价格准确性保证 |
| P3 | 大宗交易 | block_trade | 300 | 机构动向 |
| P3 | 停复牌信息 | suspend | 120 | 风险规避 |

## 二、详细实施计划

### 第一阶段：数据库设计与核心功能开发（第1-2周）

#### 2.1 数据库表结构设计

创建文件：`/db_init/tushare_extension_schema.sql`

```sql
-- =====================================================
-- Tushare扩展数据表
-- 创建时间：2024-03
-- 说明：补充短线交易所需的关键数据表
-- =====================================================

-- 1. 每日指标表（包含换手率、市盈率等关键指标）
CREATE TABLE IF NOT EXISTS daily_basic (
    ts_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    close DECIMAL(10,2),           -- 当日收盘价
    turnover_rate DECIMAL(10,4),   -- 换手率（%）
    turnover_rate_f DECIMAL(10,4), -- 换手率（自由流通股）
    volume_ratio DECIMAL(10,4),    -- 量比
    pe DECIMAL(10,4),              -- 市盈率（静态）
    pe_ttm DECIMAL(10,4),          -- 市盈率（TTM）
    pb DECIMAL(10,4),              -- 市净率
    ps DECIMAL(10,4),              -- 市销率（静态）
    ps_ttm DECIMAL(10,4),          -- 市销率（TTM）
    dv_ratio DECIMAL(10,4),        -- 股息率（%）
    dv_ttm DECIMAL(10,4),          -- 股息率（TTM）
    total_share DECIMAL(20,4),     -- 总股本（万股）
    float_share DECIMAL(20,4),     -- 流通股本（万股）
    free_share DECIMAL(20,4),      -- 自由流通股本（万股）
    total_mv DECIMAL(20,4),        -- 总市值（万元）
    circ_mv DECIMAL(20,4),         -- 流通市值（万元）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 2. 个股资金流向表（追踪主力资金动向）
CREATE TABLE IF NOT EXISTS moneyflow (
    ts_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    buy_sm_vol BIGINT,             -- 小单买入量（手）
    buy_sm_amount DECIMAL(20,4),   -- 小单买入金额（万元）
    sell_sm_vol BIGINT,            -- 小单卖出量
    sell_sm_amount DECIMAL(20,4),  -- 小单卖出金额
    buy_md_vol BIGINT,             -- 中单买入量
    buy_md_amount DECIMAL(20,4),   -- 中单买入金额
    sell_md_vol BIGINT,            -- 中单卖出量
    sell_md_amount DECIMAL(20,4),  -- 中单卖出金额
    buy_lg_vol BIGINT,             -- 大单买入量
    buy_lg_amount DECIMAL(20,4),   -- 大单买入金额
    sell_lg_vol BIGINT,            -- 大单卖出量
    sell_lg_amount DECIMAL(20,4),  -- 大单卖出金额
    buy_elg_vol BIGINT,            -- 特大单买入量
    buy_elg_amount DECIMAL(20,4),  -- 特大单买入金额
    sell_elg_vol BIGINT,           -- 特大单卖出量
    sell_elg_amount DECIMAL(20,4), -- 特大单卖出金额
    net_mf_vol BIGINT,             -- 净流入量（手）
    net_mf_amount DECIMAL(20,4),   -- 净流入额（万元）
    trade_count BIGINT,            -- 交易笔数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 3. 复权因子表（确保价格数据准确性）
CREATE TABLE IF NOT EXISTS adj_factor (
    ts_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    adj_factor DECIMAL(12,6),      -- 复权因子
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 4. 沪深港通持股表（北向资金）
CREATE TABLE IF NOT EXISTS hk_hold (
    code VARCHAR(10) NOT NULL,     -- 股票代码
    trade_date DATE NOT NULL,
    ts_code VARCHAR(10),           -- TS代码
    name VARCHAR(100),             -- 股票名称
    vol BIGINT,                    -- 持股数量（股）
    ratio DECIMAL(10,4),           -- 持股占比（%）
    exchange VARCHAR(10),          -- 交易所（SH/SZ）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (code, trade_date, exchange)
);

-- 5. 融资融券详细表
CREATE TABLE IF NOT EXISTS margin_detail (
    ts_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    rzye DECIMAL(20,4),            -- 融资余额（万元）
    rqye DECIMAL(20,4),            -- 融券余额（万元）
    rzmre DECIMAL(20,4),           -- 融资买入额（万元）
    rqyl BIGINT,                   -- 融券余量（股）
    rzche DECIMAL(20,4),           -- 融资偿还额（万元）
    rqchl BIGINT,                  -- 融券偿还量（股）
    rqmcl BIGINT,                  -- 融券卖出量（股）
    rzrqye DECIMAL(20,4),          -- 融资融券余额（万元）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 6. 大宗交易表
CREATE TABLE IF NOT EXISTS block_trade (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    price DECIMAL(10,2),           -- 成交价
    vol DECIMAL(20,4),             -- 成交量（万股）
    amount DECIMAL(20,4),          -- 成交额（万元）
    buyer VARCHAR(200),            -- 买方营业部
    seller VARCHAR(200),           -- 卖方营业部
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. 每日涨跌停价格表
CREATE TABLE IF NOT EXISTS stk_limit (
    ts_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    pre_close DECIMAL(10,2),       -- 昨收价
    up_limit DECIMAL(10,2),        -- 涨停价
    down_limit DECIMAL(10,2),      -- 跌停价
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 8. 停复牌信息表
CREATE TABLE IF NOT EXISTS suspend_info (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(10) NOT NULL,
    suspend_date DATE,             -- 停��日期
    resume_date DATE,              -- 复牌日期
    ann_date DATE,                 -- 公告日期
    suspend_reason VARCHAR(500),   -- 停牌原因
    reason_type VARCHAR(50),       -- 停牌原因类型
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. ST股票列表（风险控制）
CREATE TABLE IF NOT EXISTS st_stocks (
    ts_code VARCHAR(10) NOT NULL,
    name VARCHAR(100),
    st_date DATE,                  -- ST日期
    reason VARCHAR(500),           -- ST原因
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code)
);

-- 10. 股权质押表（风险监控）
CREATE TABLE IF NOT EXISTS share_pledge (
    ts_code VARCHAR(10) NOT NULL,
    ann_date DATE NOT NULL,        -- 公告日期
    pledge_ratio DECIMAL(10,4),    -- 质押比例（%）
    pledgor VARCHAR(200),          -- 质押方
    pledgee VARCHAR(200),          -- 质押权人
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建TimescaleDB hypertables以优化时序数据查询
SELECT create_hypertable('daily_basic', 'trade_date', if_not_exists => TRUE);
SELECT create_hypertable('moneyflow', 'trade_date', if_not_exists => TRUE);
SELECT create_hypertable('adj_factor', 'trade_date', if_not_exists => TRUE);
SELECT create_hypertable('hk_hold', 'trade_date', if_not_exists => TRUE);
SELECT create_hypertable('margin_detail', 'trade_date', if_not_exists => TRUE);
SELECT create_hypertable('block_trade', 'trade_date', if_not_exists => TRUE);
SELECT create_hypertable('stk_limit', 'trade_date', if_not_exists => TRUE);

-- 创建索引以提升查询性能
CREATE INDEX idx_daily_basic_ts_code ON daily_basic(ts_code);
CREATE INDEX idx_daily_basic_turnover ON daily_basic(turnover_rate DESC);
CREATE INDEX idx_moneyflow_ts_code ON moneyflow(ts_code);
CREATE INDEX idx_moneyflow_net_amount ON moneyflow(net_mf_amount DESC);
CREATE INDEX idx_margin_detail_ts_code ON margin_detail(ts_code);
CREATE INDEX idx_block_trade_ts_code ON block_trade(ts_code);
CREATE INDEX idx_block_trade_amount ON block_trade(amount DESC);
CREATE INDEX idx_suspend_info_ts_code ON suspend_info(ts_code);

-- 添加注释
COMMENT ON TABLE daily_basic IS '每日指标数据表，包含换手率、市盈率等关键指标';
COMMENT ON TABLE moneyflow IS '个股资金流向表，追踪不同级别资金的买卖情况';
COMMENT ON TABLE adj_factor IS '复权因子表，用于价格数据的复权处理';
COMMENT ON TABLE hk_hold IS '沪深港通持股表，追踪北向资金动向';
COMMENT ON TABLE margin_detail IS '融资融券详细数据表';
COMMENT ON TABLE block_trade IS '大宗交易表，追踪机构大额交易';
COMMENT ON TABLE stk_limit IS '涨跌停价格表，提供每日价格限制参考';
COMMENT ON TABLE suspend_info IS '停复牌信息表，用于风险控制';
```

#### 2.2 扩展Tushare Provider

文件位置：`/core/src/providers/tushare/provider.py`

在现有的TushareProvider类中添加以下方法：

```python
def get_daily_basic(self, ts_code=None, trade_date=None,
                   start_date=None, end_date=None):
    """
    获取每日指标数据
    积分消耗：120分
    """
    return self.api_client.query('daily_basic', **locals())

def get_moneyflow(self, ts_code=None, trade_date=None,
                 start_date=None, end_date=None):
    """
    获取个股资金流向
    积分消耗：2000分
    """
    return self.api_client.query('moneyflow', **locals())

def get_adj_factor(self, ts_code=None, trade_date=None,
                   start_date=None, end_date=None):
    """
    获取复权因子
    积分消耗：120分
    """
    return self.api_client.query('adj_factor', **locals())

def get_hk_hold(self, code=None, ts_code=None, trade_date=None,
                start_date=None, end_date=None, exchange=None):
    """
    获取沪深港通持股数据
    积分消耗：300分
    """
    return self.api_client.query('hk_hold', **locals())

def get_margin_detail(self, ts_code=None, trade_date=None,
                      start_date=None, end_date=None):
    """
    获取融资融券详细数据
    积分消耗：300分
    """
    return self.api_client.query('margin_detail', **locals())

def get_block_trade(self, ts_code=None, trade_date=None,
                    start_date=None, end_date=None):
    """
    获取大宗交易数据
    积分消耗：300分
    """
    return self.api_client.query('block_trade', **locals())

def get_stk_limit(self, ts_code=None, trade_date=None,
                  start_date=None, end_date=None):
    """
    获取每日涨跌停价格
    积分消耗：120分
    """
    return self.api_client.query('stk_limit', **locals())

def get_suspend(self, ts_code=None, suspend_date=None,
                resume_date=None):
    """
    获取停复牌信息
    积分消耗：120分
    """
    return self.api_client.query('suspend', **locals())
```

#### 2.3 创建同步服务

新建文件：`/backend/app/services/extended_sync_service.py`

```python
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncio
from .base_sync_service import BaseSyncService
from core.src.database import DataInsertManager

class ExtendedDataSyncService(BaseSyncService):
    """扩展数据同步服务"""

    def __init__(self):
        super().__init__()
        self.insert_manager = DataInsertManager()

    async def sync_daily_basic(self,
                               trade_date: Optional[str] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        同步每日指标数据
        优先级：P0
        调用频率：每日17:00
        """
        task_id = self.generate_task_id("daily_basic")

        try:
            # 获取数据
            provider = self.create_data_provider()
            data = provider.get_daily_basic(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            # 数据验证和插入
            if data is not None and len(data) > 0:
                self.insert_manager.insert_daily_basic(data)

            return {
                "task_id": task_id,
                "status": "success",
                "records": len(data) if data else 0
            }
        except Exception as e:
            self.logger.error(f"同步每日指标失败: {str(e)}")
            raise

    async def sync_moneyflow(self,
                             trade_date: Optional[str] = None,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        同步资金流向数据
        优先级：P0
        调用频率：每日17:30
        注意：高积分消耗，需要控制调用频率
        """
        task_id = self.generate_task_id("moneyflow")

        try:
            provider = self.create_data_provider()

            # 分批获取，避免单次请求数据量过大
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")

            # 获取活跃股票列表（如涨跌幅前100）
            active_stocks = await self._get_active_stocks(trade_date)

            total_records = 0
            for stock in active_stocks:
                data = provider.get_moneyflow(
                    ts_code=stock,
                    trade_date=trade_date
                )
                if data is not None and len(data) > 0:
                    self.insert_manager.insert_moneyflow(data)
                    total_records += len(data)

                # 控制请求频率
                await asyncio.sleep(0.5)

            return {
                "task_id": task_id,
                "status": "success",
                "records": total_records
            }
        except Exception as e:
            self.logger.error(f"同步资金流向失败: {str(e)}")
            raise

    async def sync_hk_hold(self,
                           trade_date: Optional[str] = None) -> Dict[str, Any]:
        """
        同步北向资金持股数据
        优先级：P1
        调用频率：每日18:00
        """
        task_id = self.generate_task_id("hk_hold")

        try:
            provider = self.create_data_provider()

            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")

            # 分别获取沪股通和深股通数据
            sh_data = provider.get_hk_hold(trade_date=trade_date, exchange='SH')
            sz_data = provider.get_hk_hold(trade_date=trade_date, exchange='SZ')

            total_records = 0
            if sh_data is not None and len(sh_data) > 0:
                self.insert_manager.insert_hk_hold(sh_data)
                total_records += len(sh_data)

            if sz_data is not None and len(sz_data) > 0:
                self.insert_manager.insert_hk_hold(sz_data)
                total_records += len(sz_data)

            return {
                "task_id": task_id,
                "status": "success",
                "records": total_records
            }
        except Exception as e:
            self.logger.error(f"同步北向资金失败: {str(e)}")
            raise

    async def _get_active_stocks(self, trade_date: str) -> List[str]:
        """获取活跃股票列表（内部方法）"""
        # 这里可以根据涨跌幅、成交量等筛选活跃股票
        # 暂时返回前100只股票
        query = """
            SELECT ts_code
            FROM stock_daily
            WHERE trade_date = %s
            ORDER BY amount DESC
            LIMIT 100
        """
        # 实现查询逻辑
        return []
```

#### 2.4 创建Celery任务

新建文件：`/backend/app/tasks/extended_sync_tasks.py`

```python
from celery import shared_task
from backend.app.services.extended_sync_service import ExtendedDataSyncService
import asyncio

@shared_task(name="extended.sync_daily_basic",
             bind=True,
             max_retries=3,
             soft_time_limit=600)
def sync_daily_basic_task(self, trade_date=None):
    """同步每日指标任务"""
    try:
        service = ExtendedDataSyncService()
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            service.sync_daily_basic(trade_date=trade_date)
        )
        return result
    except Exception as e:
        self.retry(countdown=60)

@shared_task(name="extended.sync_moneyflow",
             bind=True,
             max_retries=2,
             soft_time_limit=1200)
def sync_moneyflow_task(self, trade_date=None):
    """同步资金流向任务（高积分消耗，谨慎使用）"""
    try:
        service = ExtendedDataSyncService()
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            service.sync_moneyflow(trade_date=trade_date)
        )
        return result
    except Exception as e:
        self.retry(countdown=300)

@shared_task(name="extended.sync_hk_hold",
             bind=True,
             max_retries=3,
             soft_time_limit=600)
def sync_hk_hold_task(self, trade_date=None):
    """同步北向资金任务"""
    try:
        service = ExtendedDataSyncService()
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            service.sync_hk_hold(trade_date=trade_date)
        )
        return result
    except Exception as e:
        self.retry(countdown=60)

@shared_task(name="extended.sync_margin",
             bind=True,
             max_retries=3,
             soft_time_limit=600)
def sync_margin_task(self, trade_date=None):
    """同步融资融券任务"""
    try:
        service = ExtendedDataSyncService()
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            service.sync_margin_detail(trade_date=trade_date)
        )
        return result
    except Exception as e:
        self.retry(countdown=60)

@shared_task(name="extended.sync_stk_limit",
             bind=True,
             max_retries=3,
             soft_time_limit=300)
def sync_stk_limit_task(self, trade_date=None):
    """同步涨跌停价格任务"""
    try:
        service = ExtendedDataSyncService()
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            service.sync_stk_limit(trade_date=trade_date)
        )
        return result
    except Exception as e:
        self.retry(countdown=60)
```

### 第二阶段：API接口开发（第2周）

#### 2.5 创建API端点

新建文件：`/backend/app/api/endpoints/extended_data.py`

```python
from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional, List
from datetime import date, datetime
from backend.app.core_adapters.data_adapter import DataAdapter

router = APIRouter()

@router.get("/daily-basic/{ts_code}")
async def get_daily_basic(
    ts_code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, le=1000, description="返回记录数")
):
    """
    获取股票每日指标
    - 换手率、市盈率、市净率等
    - 用于短线选股和风险评估
    """
    adapter = DataAdapter()
    try:
        data = await adapter.get_daily_basic(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return {
            "code": 0,
            "data": data,
            "msg": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/moneyflow/{ts_code}")
async def get_moneyflow(
    ts_code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, le=500, description="返回记录数")
):
    """
    获取个股资金流向
    - 大单、中单、小单资金流向
    - 判断主力资金动向
    """
    adapter = DataAdapter()
    try:
        data = await adapter.get_moneyflow(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return {
            "code": 0,
            "data": data,
            "msg": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hk-hold")
async def get_hk_hold(
    trade_date: Optional[date] = Query(None, description="交易日期"),
    top: int = Query(50, le=200, description="返回前N条")
):
    """
    获取北向资金持股数据
    - 沪股通、深股通持股
    - 外资动向重要参考
    """
    adapter = DataAdapter()
    try:
        data = await adapter.get_hk_hold(
            trade_date=trade_date,
            limit=top
        )
        return {
            "code": 0,
            "data": data,
            "msg": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/margin/{ts_code}")
async def get_margin_detail(
    ts_code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期")
):
    """
    获取融资融券数据
    - 两融余额变化
    - 市场情绪指标
    """
    adapter = DataAdapter()
    try:
        data = await adapter.get_margin_detail(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        return {
            "code": 0,
            "data": data,
            "msg": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/limit-prices")
async def get_limit_prices(
    trade_date: date = Query(..., description="交易日期")
):
    """
    获取涨跌停价格
    - 当日所有股票的涨跌停价格
    - 用于交易参考
    """
    adapter = DataAdapter()
    try:
        data = await adapter.get_stk_limit(trade_date=trade_date)
        return {
            "code": 0,
            "data": data,
            "msg": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/block-trade")
async def get_block_trade(
    trade_date: Optional[date] = Query(None, description="交易日期"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取大宗交易数据
    - 机构大额交易
    - 判断机构动向
    """
    adapter = DataAdapter()
    try:
        data = await adapter.get_block_trade(
            trade_date=trade_date,
            ts_code=ts_code
        )
        return {
            "code": 0,
            "data": data,
            "msg": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/trigger")
async def trigger_sync(
    data_type: str = Query(..., description="数据类型：daily_basic|moneyflow|hk_hold|margin|stk_limit"),
    trade_date: Optional[str] = Query(None, description="交易日期")
):
    """
    手动触发数据同步
    需要管理员权限
    """
    from backend.app.tasks import extended_sync_tasks

    task_map = {
        "daily_basic": extended_sync_tasks.sync_daily_basic_task,
        "moneyflow": extended_sync_tasks.sync_moneyflow_task,
        "hk_hold": extended_sync_tasks.sync_hk_hold_task,
        "margin": extended_sync_tasks.sync_margin_task,
        "stk_limit": extended_sync_tasks.sync_stk_limit_task
    }

    if data_type not in task_map:
        raise HTTPException(status_code=400, detail="不支持的数据类型")

    task = task_map[data_type]
    result = task.delay(trade_date=trade_date)

    return {
        "code": 0,
        "data": {"task_id": result.id},
        "msg": "同步任务已提交"
    }
```

#### 2.6 定时任务配置与管理

##### 数据库配置

添加到数据库的SQL脚本：

```sql
-- 定时任务配置
-- 需要在scheduled_tasks表中添加

-- 每日指标同步（每日17:00）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params
) VALUES (
    'sync_daily_basic',
    'extended.sync_daily_basic',
    '同步每日指标数据（换手率、PE等）',
    '0 17 * * *',
    true,
    '{"points_consumption": 120}'
);

-- 资金流向同步（每日17:30，仅同步活跃股票）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params
) VALUES (
    'sync_moneyflow',
    'extended.sync_moneyflow',
    '同步资金流向数据（高积分消耗）',
    '30 17 * * *',
    false, -- 默认关闭，因为积分消耗高
    '{"points_consumption": 2000, "strategy": "top100"}'
);

-- 北向资金同步（每日18:00）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params
) VALUES (
    'sync_hk_hold',
    'extended.sync_hk_hold',
    '同步北向资金持股数据',
    '0 18 * * *',
    true,
    '{"points_consumption": 300}'
);

-- 融资融券同步（每日18:30）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params
) VALUES (
    'sync_margin',
    'extended.sync_margin',
    '同步融资融券数据',
    '30 18 * * *',
    true,
    '{"points_consumption": 300}'
);

-- 涨跌停价格同步（每日9:00）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params
) VALUES (
    'sync_stk_limit',
    'extended.sync_stk_limit',
    '同步涨跌停价格数据',
    '0 9 * * *',
    true,
    '{"points_consumption": 120}'
);

-- 复权因子同步（每周一）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params
) VALUES (
    'sync_adj_factor',
    'extended.sync_adj_factor',
    '同步复权因子',
    '0 2 * * 1',
    true,
    '{"points_consumption": 120}'
);

-- 大宗交易同步（每日19:00）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params
) VALUES (
    'sync_block_trade',
    'extended.sync_block_trade',
    '同步大宗交易数据',
    '0 19 * * *',
    false,
    '{"points_consumption": 300}'
);
```

##### 在Admin界面中管理

通过Admin界面 `http://localhost:3002/settings/scheduler` 可以：

1. **查看所有扩展数据同步任务**
   - 任务会自动显示在任务列表中
   - 显示积分消耗提醒
   - 实时查看下次执行时间

2. **动态启用/禁用任务**
   - 通过开关控制任务启用状态
   - 修改立即生效，无需重启服务
   - 高积分消耗任务默认关闭

3. **编辑任务参数**
   - 修改Cron表达式调整执行时间
   - 编辑任务参数（如同步策略）
   - 更新任务描述

4. **监控任务执行**
   - 查看最后执行时间
   - 查看执行状态（成功/失败）
   - 查看执行次数统计

### 第三阶段：前端界面开发（第3周）

#### 2.7 Admin管理界面集成方案

##### 1. 定时任务管理页面改进
**位置**：`/admin/app/(dashboard)/settings/scheduler/page.tsx`

**需要更新的功能**：

1. **扩展任务模块标签映射**
在 `getModuleLabel` 函数中添加新的数据类型：
```typescript
const getModuleLabel = (module: string) => {
  const labels: Record<string, string> = {
    // 现有任务
    'stock_list': '股票列表',
    'new_stocks': '新股列表',
    'delisted_stocks': '退市列表',
    'daily': '日线数据',
    'minute': '分时数据',
    'realtime': '实时行情',

    // 新增扩展数据任务
    'extended.sync_daily_basic': '每日指标',
    'extended.sync_moneyflow': '资金流向',
    'extended.sync_hk_hold': '北向资金',
    'extended.sync_margin': '融资融券',
    'extended.sync_stk_limit': '涨跌停价格',
    'extended.sync_block_trade': '大宗交易',
    'extended.sync_adj_factor': '复权因子',
    'extended.sync_suspend': '停复牌信息'
  }
  return labels[module] || module
}
```

2. **添加任务分组显示**
将任务按类型分组，便于管理：
```typescript
// 任务分组配置
const taskGroups = {
  '基础数据': ['stock_list', 'new_stocks', 'delisted_stocks'],
  '行情数据': ['daily', 'minute', 'realtime'],
  '扩展数据': [
    'extended.sync_daily_basic',
    'extended.sync_moneyflow',
    'extended.sync_hk_hold',
    'extended.sync_margin'
  ],
  '价格数据': ['extended.sync_stk_limit', 'extended.sync_adj_factor'],
  '风险数据': ['extended.sync_block_trade', 'extended.sync_suspend']
}
```

3. **积分消耗提示**
对于高积分消耗的任务，添加警告标识：
```typescript
const getPointsConsumption = (module: string) => {
  const points: Record<string, number> = {
    'extended.sync_daily_basic': 120,
    'extended.sync_moneyflow': 2000,  // 高消耗
    'extended.sync_hk_hold': 300,
    'extended.sync_margin': 300,
    'extended.sync_stk_limit': 120,
    'extended.sync_block_trade': 300,
    'extended.sync_adj_factor': 120
  }
  return points[module] || 0
}

// 在任务列表中显示积分消耗
{getPointsConsumption(task.module) > 1000 && (
  <span className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded">
    高积分消耗: {getPointsConsumption(task.module)}分
  </span>
)}
```

##### 2. 数据源设置页面改进
**位置**：`/admin/app/(dashboard)/settings/datasource/page.tsx`

**需要新增的配置项**：

1. **扩展数据源配置区域**
在现有配置下方添加新的配置区块：

```typescript
// 新增状态
const [extendedDataEnabled, setExtendedDataEnabled] = useState(false)
const [dailyBasicSource, setDailyBasicSource] = useState<'tushare'>('tushare')
const [moneyflowSource, setMoneyflowSource] = useState<'tushare'>('tushare')
const [hkHoldSource, setHkHoldSource] = useState<'tushare'>('tushare')
const [marginSource, setMarginSource] = useState<'tushare'>('tushare')
const [blockTradeSource, setBlockTradeSource] = useState<'tushare'>('tushare')
```

2. **添加扩展数据配置卡片**
```jsx
{/* 扩展数据配置卡片 */}
<Card className="mt-6">
  <CardHeader>
    <CardTitle>扩展数据配置（短线交易专用）</CardTitle>
    <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
      配置短线交易所需的高级数据源，这些数据仅支持 Tushare Pro
    </p>
  </CardHeader>
  <CardContent>
    {/* 总开关 */}
    <div className="flex items-center justify-between mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
      <div>
        <Label>启用扩展数据同步</Label>
        <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
          开启后将同步资金流向、每日指标等高级数据
        </p>
      </div>
      <Switch
        checked={extendedDataEnabled}
        onCheckedChange={setExtendedDataEnabled}
      />
    </div>

    {extendedDataEnabled && (
      <div className="space-y-4">
        {/* 每日指标数据源 */}
        <div className="space-y-2">
          <Label>每日指标（换手率、PE等）</Label>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">Tushare Pro</Badge>
            <span className="text-xs text-yellow-600">消耗 120 积分/次</span>
          </div>
          <p className="text-xs text-gray-600">
            包含换手率、市盈率、市净率等关键指标
          </p>
        </div>

        {/* 资金流向数据源 */}
        <div className="space-y-2">
          <Label>资金流向</Label>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">Tushare Pro</Badge>
            <span className="text-xs text-red-600 font-semibold">
              ⚠️ 高消耗：2000 积分/次
            </span>
          </div>
          <Alert className="mt-2">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="text-xs">
              资金流向数据积分消耗高，建议仅同步活跃股票
            </AlertDescription>
          </Alert>
        </div>

        {/* 北向资金数据源 */}
        <div className="space-y-2">
          <Label>北向资金（沪深港通）</Label>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">Tushare Pro</Badge>
            <span className="text-xs text-yellow-600">消耗 300 积分/次</span>
          </div>
          <p className="text-xs text-gray-600">
            追踪外资动向，重要参考指标
          </p>
        </div>

        {/* 融资融券数据源 */}
        <div className="space-y-2">
          <Label>融资融券</Label>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">Tushare Pro</Badge>
            <span className="text-xs text-yellow-600">消耗 300 积分/次</span>
          </div>
          <p className="text-xs text-gray-600">
            两融余额变化，市场情绪指标
          </p>
        </div>

        {/* 积分消耗预估 */}
        <Alert className="mt-6">
          <Info className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-1">
              <p className="font-semibold">积分消耗预估</p>
              <p className="text-xs">日消耗：约 1,240 积分</p>
              <p className="text-xs">月消耗：约 37,200 积分</p>
              <p className="text-xs text-blue-600">
                建议申请 5万积分/月 的配额
              </p>
            </div>
          </AlertDescription>
        </Alert>
      </div>
    )}
  </CardContent>
</Card>
```

3. **添加数据同步策略配置**
```jsx
{/* 同步策略配置 */}
<Card className="mt-6">
  <CardHeader>
    <CardTitle>同步策略配置</CardTitle>
  </CardHeader>
  <CardContent>
    <div className="space-y-4">
      {/* 资金流向同步���略 */}
      <div>
        <Label>资金流向同步策略</Label>
        <RadioGroup value={moneyflowStrategy} onValueChange={setMoneyflowStrategy}>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="top100" id="top100" />
            <Label htmlFor="top100" className="text-sm">
              仅同步成交额前100（推荐）
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="active" id="active" />
            <Label htmlFor="active" className="text-sm">
              同步涨跌幅前200
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="all" id="all" />
            <Label htmlFor="all" className="text-sm">
              同步全部（消耗大量积分）
            </Label>
          </div>
        </RadioGroup>
      </div>

      {/* 历史数据回补 */}
      <div>
        <Label>历史数据回补</Label>
        <Select value={backfillDays} onValueChange={setBackfillDays}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="0">不回补</SelectItem>
            <SelectItem value="7">最近7天</SelectItem>
            <SelectItem value="30">最近30天</SelectItem>
            <SelectItem value="90">最近90天</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-gray-600 mt-1">
          首次启用时是否同步历史数据
        </p>
      </div>
    </div>
  </CardContent>
</Card>
```

##### 3. 新增数据展示页面

**资金流向分析页面**
路径：`/admin/app/(dashboard)/analysis/moneyflow/page.tsx`

主要功能：
- 个股资金流向实时图表
- 主力资金净流入排行榜
- 板块资金流向热力图
- 资金异动预警列表

**北向资金监控页面**
路径：`/admin/app/(dashboard)/analysis/north-bound/page.tsx`

主要功能：
- 北向资金实时流入流出曲线
- 持股变化TOP20
- 历史累计趋势图
- 行业分布饼图

**融资融券分析页面**
路径：`/admin/app/(dashboard)/analysis/margin/page.tsx`

主要功能：
- 两融余额变化趋势
- 融资买入排行榜
- 融券卖出监控
- 两融余额占比分析

##### 4. 数据同步状态监控页面

**扩展数据同步监控**
路径：`/admin/app/(dashboard)/sync/extended/page.tsx`

```jsx
export default function ExtendedSyncMonitor() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="扩展数据同步监控"
        description="实时监控短线交易数据同步状态"
      />

      {/* 同步状态卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* 每日指标卡片 */}
        <SyncStatusCard
          title="每日指标"
          module="extended.sync_daily_basic"
          points={120}
          lastSync="2024-03-17 17:00"
          status="success"
          records={4850}
        />

        {/* 资金流向卡片 */}
        <SyncStatusCard
          title="资金流向"
          module="extended.sync_moneyflow"
          points={2000}
          lastSync="2024-03-17 17:30"
          status="running"
          records={100}
          warning="高积分消耗"
        />

        {/* 北向资金卡片 */}
        <SyncStatusCard
          title="北向资金"
          module="extended.sync_hk_hold"
          points={300}
          lastSync="2024-03-17 18:00"
          status="pending"
          records={0}
        />
      </div>

      {/* 积分消耗统计 */}
      <Card>
        <CardHeader>
          <CardTitle>积分消耗统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex justify-between">
              <span>今日已消耗</span>
              <span className="font-semibold">1,240 积分</span>
            </div>
            <div className="flex justify-between">
              <span>本月累计</span>
              <span className="font-semibold">28,560 积分</span>
            </div>
            <div className="flex justify-between">
              <span>剩余配额</span>
              <span className="font-semibold text-green-600">21,440 积分</span>
            </div>
            <Progress value={57} className="h-2" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
```

##### 5. 导航菜单更新

在 `/admin/config/navigation.ts` 中添加新的菜单项：

```typescript
export const navigation = [
  // ... 现有菜单

  {
    title: '扩展数据',
    icon: Database,
    children: [
      {
        title: '同步监控',
        href: '/sync/extended',
        icon: Activity
      },
      {
        title: '资金流向',
        href: '/analysis/moneyflow',
        icon: TrendingUp
      },
      {
        title: '北向资金',
        href: '/analysis/north-bound',
        icon: Globe
      },
      {
        title: '融资融券',
        href: '/analysis/margin',
        icon: CreditCard
      }
    ]
  }
]
```

### 第四阶段：数据质量保证（第3-4周）

#### 2.8 数据验证器

新建文件：`/core/src/data/validators/extended_validator.py`

```python
import pandas as pd
from typing import Optional, List, Dict, Any

class ExtendedDataValidator:
    """扩展数据验证器"""

    def validate_daily_basic(self, df: pd.DataFrame) -> tuple[bool, List[str]]:
        """
        验证每日指标数据
        """
        errors = []

        # 检查必要字段
        required_fields = ['ts_code', 'trade_date', 'turnover_rate']
        for field in required_fields:
            if field not in df.columns:
                errors.append(f"缺少必要字段: {field}")

        # 换手率合理性检查 (0-100)
        if 'turnover_rate' in df.columns:
            invalid_turnover = df[
                (df['turnover_rate'] < 0) |
                (df['turnover_rate'] > 100)
            ]
            if not invalid_turnover.empty:
                errors.append(f"换手率异常: {len(invalid_turnover)}条记录")

        # PE合理性检查 (-1000, 1000)
        if 'pe' in df.columns:
            invalid_pe = df[(df['pe'] < -1000) | (df['pe'] > 1000)]
            if not invalid_pe.empty:
                errors.append(f"市盈率异常: {len(invalid_pe)}条记录")

        # 市值逻辑检查
        if 'total_mv' in df.columns and 'circ_mv' in df.columns:
            invalid_mv = df[df['circ_mv'] > df['total_mv']]
            if not invalid_mv.empty:
                errors.append(f"市值逻辑错误: 流通市值大于总市值")

        return len(errors) == 0, errors

    def validate_moneyflow(self, df: pd.DataFrame) -> tuple[bool, List[str]]:
        """
        验证资金流向数据
        """
        errors = []

        # 买卖平衡检查
        buy_cols = ['buy_sm_amount', 'buy_md_amount',
                   'buy_lg_amount', 'buy_elg_amount']
        sell_cols = ['sell_sm_amount', 'sell_md_amount',
                    'sell_lg_amount', 'sell_elg_amount']

        if all(col in df.columns for col in buy_cols + sell_cols):
            df['total_buy'] = df[buy_cols].sum(axis=1)
            df['total_sell'] = df[sell_cols].sum(axis=1)

            # 买卖总额应该大致相等（允许5%误差）
            imbalanced = df[
                abs(df['total_buy'] - df['total_sell']) /
                df[['total_buy', 'total_sell']].mean(axis=1) > 0.05
            ]
            if not imbalanced.empty:
                errors.append(f"买卖金额不平衡: {len(imbalanced)}条记录")

        # 净流入检查
        if 'net_mf_amount' in df.columns:
            df['calc_net'] = df['total_buy'] - df['total_sell']
            invalid_net = df[
                abs(df['net_mf_amount'] - df['calc_net']) > 0.01
            ]
            if not invalid_net.empty:
                errors.append(f"净流入计算错误: {len(invalid_net)}条记录")

        return len(errors) == 0, errors
```

### 第五阶段：测试与优化（第4周）

#### 2.9 单元测试

创建测试文件：`/tests/unit/test_extended_sync.py`

```python
import pytest
from datetime import datetime
from backend.app.services.extended_sync_service import ExtendedDataSyncService

@pytest.mark.asyncio
async def test_sync_daily_basic():
    """测试每日指标同步"""
    service = ExtendedDataSyncService()
    result = await service.sync_daily_basic(
        trade_date="20240315"
    )
    assert result['status'] == 'success'
    assert result['records'] > 0

@pytest.mark.asyncio
async def test_sync_moneyflow():
    """测试资金流向同步"""
    service = ExtendedDataSyncService()
    # 只测试单只股票，避免消耗过多积分
    result = await service.sync_moneyflow(
        ts_code="000001.SZ",
        trade_date="20240315"
    )
    assert result['status'] == 'success'

@pytest.mark.asyncio
async def test_sync_hk_hold():
    """测试北向资金同步"""
    service = ExtendedDataSyncService()
    result = await service.sync_hk_hold(
        trade_date="20240315"
    )
    assert result['status'] == 'success'
    assert result['records'] > 0
```

#### 2.10 性能优化策略

1. **批量插入优化**
   - 使用PostgreSQL的COPY协议
   - 批次大小：1000-5000条/批

2. **数据压缩**
   - TimescaleDB自动压缩策略
   - 保留近3个月原始数据，历史数据压缩

3. **查询优化**
   - 合理使用索引
   - 分区查询优化
   - 使用物化视图加速常用查询

4. **缓存策略**
   - Redis缓存热点数据
   - 缓存时间：5-15分钟

## 三、实施时间表

| 阶段 | 时间 | 主要任务 | 交付物 |
|------|------|---------|--------|
| 第1周 | Day 1-3 | 数据库设计与迁移 | SQL脚本、表结构 |
| | Day 4-5 | Provider扩展开发 | Tushare接口实现 |
| 第2周 | Day 6-8 | 同步服务开发 | 同步服务、Celery任务 |
| | Day 9-10 | API接口开发 | RESTful API端点 |
| 第3周 | Day 11-13 | 前端界面开发 | 管理界面、数据展示 |
| | Day 14-15 | 数据验证器 | 质量保证机制 |
| 第4周 | Day 16-17 | 单元测试 | 测试用例 |
| | Day 18-19 | 集成测试与优化 | 性能优化 |
| | Day 20 | 生产部署 | 上线运行 |

## 四、资源需求

### 4.1 Tushare积分预算

| 数据类型 | 单次积分 | 调用频率 | 日消耗 | 月消耗 |
|---------|---------|---------|--------|--------|
| 每日指标 | 120 | 1次/天 | 120 | 3,600 |
| 资金流向 | 2000 | 0.2次/天 | 400 | 12,000 |
| 北向资金 | 300 | 1次/天 | 300 | 9,000 |
| 融资融券 | 300 | 1次/天 | 300 | 9,000 |
| 涨跌停价格 | 120 | 1次/天 | 120 | 3,600 |
| **合计** | - | - | 1,240 | 37,200 |

建议：申请5万积分/月的配额

### 4.2 存储空间预算

| 数据类型 | 每日数据量 | 年数据量 |
|---------|-----------|----------|
| 每日指标 | 20MB | 7GB |
| 资金流向 | 40MB | 14GB |
| 北向资金 | 5MB | 2GB |
| 融资融券 | 10MB | 4GB |
| 其他 | 10MB | 4GB |
| **合计** | 85MB | 31GB |

建议：预留100GB存储空间

### 4.3 服务器资源

- CPU：建议4核以上
- 内存：建议16GB以上
- 磁盘：SSD 200GB以上
- 网络：稳定的网络连接

## 五、风险管理

### 5.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Tushare API限流 | 数据同步失败 | 实现重试机制、错峰调用 |
| 积分耗尽 | 无法获取数据 | 监控积分使用、优先级控制 |
| 数据质量问题 | 分析结果错误 | 多层验证、异常检测 |
| 系统性能瓶颈 | 响应缓慢 | 优化查询、增加缓存 |

### 5.2 业务风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 数据延迟 | 决策滞后 | 设置数据时效性提醒 |
| 数据缺失 | 分析不完整 | 数据补全机制 |
| 合规风险 | 法律问题 | 遵守数据使用协议 |

## 六、监控与维护

### 6.1 监控指标

- **数据同步监控**
  - 同步成功率
  - 数据延迟
  - 积分消耗

- **系统性能监控**
  - API响应时间
  - 数据库查询性能
  - 内存/CPU使用率

- **数据质量监控**
  - 数据完整性
  - 异常值检测
  - 数据一致性

### 6.2 维护计划

- **日常维护**
  - 检查同步任务状态
  - 监控积分使用情况
  - 处理异常告警

- **定期维护**（每周）
  - 数据质量检查
  - 性能优化
  - 备份验证

- **版本更新**（每月）
  - 功能优化
  - Bug修复
  - 新数据源接入

## 七、项目收益

### 7.1 业务价值

1. **完整的数据支撑**：为短线交易提供全面的数据基础
2. **实时性提升**：关键数据实时更新，决策更及时
3. **风险控制增强**：多维度数据支持更好的风险评估
4. **AI分析能力**：丰富的数据为AI模型提供更好的输入

### 7.2 技术价值

1. **架构优化**：完善的数据同步架构，易于扩展
2. **数据质量**：多层验证保证数据准确性
3. **性能提升**：优化的查询和存储策略
4. **可维护性**：清晰的代码结构和文档

## 八、Admin界面集成要点总结

### 8.1 定时任务管理（已有页面改进）

**页面位置**：`http://localhost:3002/settings/scheduler`

**关键改进点**：
1. **任务自动识别**：新增的扩展数据任务会自动出现在列表中
2. **积分消耗提示**：高消耗任务（>1000积分）显示红色警告标签
3. **动态配置**：所有修改30秒内自动生效，无需重启服务
4. **分组展示**：按数据类型分组，便于管理

### 8.2 数据源配置（已有页面扩展）

**页面位置**：`http://localhost:3002/settings/datasource`

**关键扩展**：
1. **扩展数据总开关**：一键启用/禁用所有扩展数据同步
2. **积分消耗预警**：实时显示日/月积分消耗预估
3. **同步策略配置**：
   - 资金流向：选择同步范围（TOP100/活跃股/全部）
   - 历史回补：选择回补天数（0/7/30/90天）
4. **数据源说明**：每个数据类型都标注Tushare专属和积分消耗

### 8.3 新增监控页面

1. **扩展数据同步监控** `/sync/extended`
   - 实时同步状态
   - 积分消耗统计
   - 同步历史记录

2. **资金流向分析** `/analysis/moneyflow`
   - 主力资金流向图表
   - 个股资金排行榜

3. **北向资金监控** `/analysis/north-bound`
   - 北向资金趋势
   - 持股变化分析

4. **融资融券分析** `/analysis/margin`
   - 两融余额变化
   - 融资融券排行

### 8.4 用户操作流程

#### 初始配置步骤

1. **配置Tushare Token**
   - 访问 `http://localhost:3002/settings/datasource`
   - 在"Tushare API Token"输入框中输入您的Token
   - Token获取地址：https://tushare.pro/register?reg=430522
   - 点击"保存配置"

2. **启用扩展数据**
   - 在同一页面找到"扩展数据配置"卡片
   - 打开"启用扩展数据同步"开关
   - 选择资金流向同步策略（建议选择"仅同步成交额前100"）
   - 设置历史数据回补天数（首次建议选择"最近7天"）

3. **配置定时任务**
   - 访问 `http://localhost:3002/settings/scheduler`
   - 找到扩展数据相关任务（会有积分消耗标识）
   - 根据您的积分额度选择性启用：
     - ✅ 每日指标（120积分）- 建议启用
     - ⚠️ 资金流向（2000积分）- 谨慎启用
     - ✅ 北向资金（300积分）- 建议启用
     - ✅ 融资融券（300积分）- 建议启用
   - 调整执行时间避开交易高峰期

#### 日常使用指南

1. **监控数据同步**
   - 访问 `/sync/extended` 查看实时同步状态
   - 重点关注：
     - 各任务最后执行时间
     - 执行状态（成功/失败）
     - 今日/本月积分消耗统计
     - 剩余配额预警

2. **查看数据分析**
   - **资金流向** (`/analysis/moneyflow`)
     - 查看主力资金净流入TOP20
     - 分析大单资金异动
     - 监控板块资金轮动

   - **北向资金** (`/analysis/north-bound`)
     - 查看每日净买入额
     - 分析持股变化趋势
     - 关注行业偏好变化

   - **融资融券** (`/analysis/margin`)
     - 监控两融余额变化
     - 分析市场杠杆水平
     - 识别情绪拐点

3. **异常处理**
   - **积分不足**：在任务页面禁用部分高消耗任务
   - **同步失败**：检查Token有效性，查看错误日志
   - **数据延迟**：调整任务执行时间，避开API限流时段

### 8.5 实施注意事项

#### 技术要求

1. **环境依赖**
   - Node.js >= 18.0
   - PostgreSQL >= 14 with TimescaleDB
   - Redis >= 6.0
   - Python >= 3.9

2. **Tushare积分要求**
   - 最低要求：2000积分（可使用基础功能）
   - 建议配置：5000积分（可启用大部分功能）
   - 完整功能：50000积分/月（所有功能无限制）

#### 性能优化建议

1. **数据库优化**
   ```sql
   -- 为新表添加合适的索引
   CREATE INDEX CONCURRENTLY idx_daily_basic_date_code
   ON daily_basic(trade_date DESC, ts_code);

   CREATE INDEX CONCURRENTLY idx_moneyflow_net_amount
   ON moneyflow(trade_date DESC, net_mf_amount DESC);

   -- 设置自动压缩策略（30天后自动压缩）
   SELECT add_compression_policy('daily_basic',
     INTERVAL '30 days', if_not_exists => true);
   ```

2. **API调用优化**
   - 使用批量查询减少请求次数
   - 实施请求缓存（5-15分钟）
   - 错峰执行避免限流

3. **前端性能**
   - 数据表格使用虚拟滚动
   - 图表数据采样显示
   - 实施懒加载策略

### 8.6 常见问题解决

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 任务一直显示pending | Celery worker未启动 | 执行 `docker-compose restart celery` |
| 积分消耗过快 | 资金流向同步全部股票 | 修改策略为TOP100 |
| 数据延迟更新 | 任务执行时间设置不当 | 调整cron表达式 |
| Token无效错误 | Token过期或错误 | 重新获取并更新Token |
| 数据库连接超时 | 连接池耗尽 | 增加连接池大小 |

## 九、实施步骤总结

### 第一步：数据库准备（立即执行）

```bash
# 1. 进入项目目录
cd /Volumes/MacDriver/stock-analysis

# 2. 执行数据库迁移
docker-compose exec postgres psql -U postgres -d stock_analysis \
  -f /docker-entrypoint-initdb.d/tushare_extension_schema.sql

# 3. 验证表创建
docker-compose exec postgres psql -U postgres -d stock_analysis \
  -c "\dt+ daily_basic, moneyflow, hk_hold, margin_detail;"
```

### 第二步：后端开发（第1周）

1. **创建Provider扩展**
   - 文件：`/core/src/providers/tushare/provider.py`
   - 添加8个新的数据获取方法

2. **创建同步服务**
   - 文件：`/backend/app/services/extended_sync_service.py`
   - 实现各类数据的同步逻辑

3. **创建Celery任务**
   - 文件：`/backend/app/tasks/extended_sync_tasks.py`
   - 定义异步任务

4. **创建API端点**
   - 文件：`/backend/app/api/endpoints/extended_data.py`
   - 提供数据查询接口

### 第三步：前端开发（第2周）

1. **更新定时任务页面**
   - 文件：`/admin/app/(dashboard)/settings/scheduler/page.tsx`
   - 添加任务标签映射和积分提示

2. **扩展数据源配置**
   - 文件：`/admin/app/(dashboard)/settings/datasource/page.tsx`
   - 添加扩展数据配置卡片

3. **创建监控页面**
   - 文件：`/admin/app/(dashboard)/sync/extended/page.tsx`
   - 实现同步状态监控

4. **创建分析页面**
   - 资金流向：`/admin/app/(dashboard)/analysis/moneyflow/page.tsx`
   - 北向资金：`/admin/app/(dashboard)/analysis/north-bound/page.tsx`
   - 融资融券：`/admin/app/(dashboard)/analysis/margin/page.tsx`

### 第四步：测试部署（第3周）

1. **单元测试**
   ```bash
   # 运行测试
   pytest tests/unit/test_extended_sync.py -v
   pytest tests/integration/test_extended_api.py -v
   ```

2. **配置定时任务**
   ```sql
   -- 插入定时任务配置
   INSERT INTO scheduled_tasks ...
   ```

3. **重启服务**
   ```bash
   docker-compose restart backend celery
   ```

### 第五步：验收标准

#### 功能验收
- [ ] Tushare Token配置功能正常
- [ ] 扩展数据开关可用
- [ ] 定时任务正常执行
- [ ] 数据同步无错误
- [ ] API接口响应正常
- [ ] 前端页面显示正确

#### 性能验收
- [ ] 日线数据查询 < 500ms
- [ ] 资金流向查询 < 1s
- [ ] 页面加载 < 2s
- [ ] 内存使用 < 2GB

#### 数据验收
- [ ] 数据完整性 > 99%
- [ ] 数据准确性验证通过
- [ ] 积分消耗符合预期

## 十、长期规划

### 第一阶段（1-2个月）
- ✅ 完成基础扩展数据同步
- ✅ 实现Admin界面管理
- ⏳ 优化数据质量验证
- ⏳ 完善错误处理机制

### 第二阶段（3-4个月）
- 接入Level2行情数据
- 实现分钟级实时推送
- 开发智能选股系统
- 集成AI分析模块

### 第三阶段（5-6个月）
- 构建策略回测平台
- 实现模拟交易系统
- 开发风险管理模块
- 支持多账户管理

## 十一、结语

本方案提供了完整的Tushare数据同步扩展实施路径，充分考虑了：

1. **现有系统的最大化复用**
2. **Admin界面的无缝集成**
3. **积分成本的精细化控制**
4. **用户体验的持续优化**

通过分阶段实施，可以在控制风险的同时，快速为短线交易提供关键数据支持。整个实施过程透明可控，用户可以通过Web界面完成所有配置和管理操作。

## 附录

### A. 相关文档

- [Tushare Pro API文档](https://tushare.pro/document/2)
- [TimescaleDB官方文档](https://docs.timescale.com/)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Celery文档](https://docs.celeryproject.org/)

### B. 联系方式

如有问题，请联系：
- 技术支持：[项目GitHub Issues]
- 数据问题：参考Tushare官方文档

### C. 变更记录

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|---------|------|
| 2024-03-17 | v1.0 | 初始版本 | System |

---

*本文档为Tushare数据同步扩展的实施方案，将根据实际执行情况持续更新和优化。*