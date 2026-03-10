# 情绪周期量化计算模块 - 完整实现方案

> **模块功能**: 赚钱效应模型 + 游资席位打标系统
> **创建时间**: 2026-03-10
> **状态**: ✅ 核心架构已完成，待集成测试

---

## 📋 目录

1. [功能概述](#功能概述)
2. [已完成文件](#已完成文件)
3. [核心实现](#核心实现)
4. [待实现文件](#待实现文件)
5. [集成步骤](#集成步骤)
6. [API接口设计](#api接口设计)
7. [使用示例](#使用示例)
8. [测试验证](#测试验证)

---

## 功能概述

### 模块一：赚钱效应模型（情绪周期识别）

根据涨停数、跌停数、连板高度等指标，将市场划分为四个阶段:

| 阶段 | 英文 | 特征 | 判断标准 |
|------|------|------|---------|
| **冰点期** | Freezing | 市场情绪极度低迷 | 跌停≥50家，涨跌比<0.5，炸板率>60% |
| **启动期** | Starting | 情绪开始回暖 | 涨停≥20家，涨跌比>1.5，炸板率<40% |
| **发酵期** | Fermenting | 情绪高涨 | 涨停≥40家，涨跌比>3，连板≥5天 |
| **退潮期** | Retreating | 情绪降温 | 炸板率>50%，连板高度下降 |

**赚钱效应指数计算公式**:
```
指数 = 涨停数(30%) + 涨跌比(25%) + 连板高度(25%) + 炸板率(20%)
归一化到 0-100 分
```

### 模块二：游资席位打标系统

建立游资字典，对龙虎榜席位进行分类:

| 标签 | 说明 | 示例 |
|------|------|------|
| **[一线顶级游资]** | 市场风向标 | 中信上海溧阳路、国泰顺德大良 |
| **[知名游资]** | 二线知名游资 | 各大券商营业部 |
| **[散户大本营]** | 散户聚集地 | 东财拉萨团结路 |
| **[机构]** | 机构专用席位 | 机构专用、基金、社保 |

**统计功能**:
- ✅ 机构净买入前三的个股
- ✅ 一线顶级游资主导打板的个股
- ✅ 游资活跃度排行榜

---

## 已完成文件

### 1. 数据库表结构

**文件**: `db_init/06_sentiment_cycle_schema.sql` (485行)

**创建的表**:
1. **market_sentiment_cycle** - 情绪周期记录表
   - 存储每日情绪周期阶段（冰点/启动/发酵/退潮）
   - 赚钱效应指数 (0-100)
   - 情绪得分、连板增长率等

2. **hot_money_seats** - 游资席位字典表
   - 席位分类（一线/知名/散户/机构）
   - 匹配关键词、优先级
   - 统计信息（上榜次数、累计金额、胜率）

3. **hot_money_operations** - 游资操作记录表
   - 记录每次游资操作
   - 用于统计分析和胜率计算

**视图**:
- `daily_sentiment_cycle_summary` - 每日情绪周期摘要
- `hot_money_activity_ranking` - 游资活跃度排行

**初始数据**:
- 已预置 20+ 知名游资席位（包括溧阳路、顺德大良等顶级游资）

### 2. 配置文件

**文件**: `core/src/sentiment/config.py` (303行)

**配置内容**:
- **CycleThresholds**: 情绪周期阶段判断阈值
- **HotMoneyDict**: 游资字典（关键词匹配规则）
- **AnalysisConfig**: 统计分析配置
- **权重配置**: 赚钱效应指数权重分配

**核心配置**:
```python
# 情绪周期阈值
CYCLE_THRESHOLDS = {
    'freezing': {'limit_down_count_min': 50, 'limit_ratio_max': 0.5},
    'starting': {'limit_up_count_min': 20, 'limit_ratio_min': 1.5},
    'fermenting': {'limit_up_count_min': 40, 'max_continuous_days_min': 5},
    'retreating': {'blast_rate_min': 0.5}
}

# 赚钱效应指数权重
MONEY_MAKING_INDEX_WEIGHTS = {
    'limit_up_count': 0.30,      # 涨停数 30%
    'limit_ratio': 0.25,         # 涨跌比 25%
    'continuous_height': 0.25,   # 连板高度 25%
    'blast_rate': 0.20,          # 炸板率 20%
}
```

### 3. 数据模型扩展

**文件**: `core/src/sentiment/models.py` (已扩展 +140行)

**新增模型**:
- `SentimentCycle` - 情绪周期数据
- `HotMoneySeat` - 游资席位信息
- `HotMoneyOperation` - 游资操作记录
- `DragonTigerAnalysis` - 龙虎榜深度分析结果
- `CycleCalculationResult` - 情绪周期计算结果

### 4. 游资席位分类器

**文件**: `core/src/sentiment/hot_money_classifier.py` (467行)

**核心功能**:

#### 4.1 席位分类
```python
classifier = HotMoneyClassifier(pool_manager)

# 单个席位分类
seat_type, seat_label = classifier.classify_seat("中信证券上海溧阳路")
# 返回: ('top_tier', '[一线顶级游资]')
```

#### 4.2 机构净买入排行
```python
# 获取机构净买入前3的个股
top_stocks = classifier.get_institution_top_stocks(
    trade_date='2026-03-10',
    limit=3
)
# 返回:
# [
#     {
#         'stock_code': '000001',
#         'stock_name': '平安银行',
#         'net_buy_amount': 50000000,
#         'institution_seats': [席位列表],
#         'institution_count': 3
#     }
# ]
```

#### 4.3 游资打板排行
```python
# 获取一线顶级游资主导打板的个股
hot_money_stocks = classifier.get_hot_money_limit_up_stocks(
    trade_date='2026-03-10',
    seat_type='top_tier',  # 'top_tier' / 'famous'
    limit=10
)
# 返回:
# [
#     {
#         'stock_code': '000001',
#         'stock_name': '平安银行',
#         'hot_money_seats': [席位列表],
#         'hot_money_count': 2,
#         'total_buy_amount': 30000000,
#         'is_limit_up': True
#     }
# ]
```

#### 4.4 游资活跃度排行
```python
# 获取最近30天活跃游资排行
ranking = classifier.get_seat_activity_ranking(days=30, limit=20)
```

---

## 核心实现

### 情绪周期计算逻辑

#### 阶段判断流程图

```
获取当日数据
    ↓
计算基础指标
    - 涨停/跌停比
    - 炸板率
    - 连板高度
    - 连板增长率
    ↓
计算赚钱效应指数
    ↓
根据阈值判断阶段
    ↓
┌─────────────────────────────────┐
│  跌停≥50 && 炸板率>60%?        │
│  → YES: 冰点期                  │
└──────────┬──────────────────────┘
           │ NO
           ↓
┌─────────────────────────────────┐
│  涨停≥20 && 涨跌比>1.5?        │
│  → YES: 启动期                  │
└──────────┬──────────────────────┘
           │ NO
           ↓
┌─────────────────────────────────┐
│  涨停≥40 && 连板≥5天?          │
│  → YES: 发酵期                  │
└──────────┬──────────────────────┘
           │ NO
           ↓
┌─────────────────────────────────┐
│  炸板率>50% && 连板下降?       │
│  → YES: 退潮期                  │
└─────────────────────────────────┘
```

#### 赚钱效应指数计算

```python
def calculate_money_making_index(data):
    """
    赚钱效应指数 =
        涨停数得分(30%) +
        涨跌比得分(25%) +
        连板高度得分(25%) +
        炸板率得分(20%)
    """
    # 1. 涨停数得分 (0-30分)
    # 归一化: 100家涨停 = 满分30
    limit_up_score = min(data['limit_up_count'] / 100 * 30, 30)

    # 2. 涨跌比得分 (0-25分)
    # 归一化: 涨跌比5.0 = 满分25
    ratio_score = min(data['limit_ratio'] / 5 * 25, 25)

    # 3. 连板高度得分 (0-25分)
    # 归一化: 10连板 = 满分25
    continuous_score = min(data['max_continuous_days'] / 10 * 25, 25)

    # 4. 炸板率得分 (0-20分)
    # 炸板率越低得分越高
    blast_score = max(0, (1 - data['blast_rate']) * 20)

    return limit_up_score + ratio_score + continuous_score + blast_score
```

### 游资识别算法

#### 优先级匹配规则

```python
# 优先级: 机构 > 一线游资 > 散户大本营 > 知名游资 > 未知

def classify_seat(seat_name):
    # 1. 精确匹配（缓存中的完整席位名）
    if seat_name in cache:
        return cache[seat_name]

    # 2. 机构关键词（最高优先级）
    if any(kw in seat_name for kw in ['机构专用', '基金', '社保']):
        return 'institution', '[机构]'

    # 3. 一线顶级游资关键词
    if any(kw in seat_name for kw in ['溧阳路', '顺德大良', '荣超商务']):
        return 'top_tier', '[一线顶级游资]'

    # 4. 散户大本营关键词
    if any(kw in seat_name for kw in ['拉萨', '西藏']):
        return 'retail_base', '[散户大本营]'

    # 5. 知名券商判断
    if any(broker in seat_name for broker in ['中信证券', '国泰君安']):
        return 'famous', '[知名游资]'

    # 6. 未识别
    return 'unknown', '[未知席位]'
```

---

## 待实现文件

以下文件需要继续实现以完成整个模块:

### 1. 情绪周期计算引擎 (高优先级)

**文件**: `core/src/sentiment/cycle_calculator.py` (预计 ~400行)

**核心类**: `SentimentCycleCalculator`

**主要方法**:
```python
class SentimentCycleCalculator:
    def __init__(self, pool_manager):
        pass

    def calculate_cycle_stage(self, trade_date: str) -> SentimentCycle:
        """计算指定日期的情绪周期阶段"""
        # 1. 获取当日和前一日数据
        # 2. 计算赚钱效应指数
        # 3. 判断情绪周期阶段
        # 4. 计算置信度
        # 5. 生成分析报告
        pass

    def _calculate_money_making_index(self, data: Dict) -> float:
        """计算赚钱效应指数"""
        pass

    def _determine_cycle_stage(self, indicators: Dict) -> Tuple[str, float]:
        """判断情绪周期阶段和置信度"""
        pass

    def _calculate_continuous_growth_rate(self, current_days, previous_days) -> float:
        """计算连板高度增长率"""
        pass

    def save_cycle_data(self, cycle_data: SentimentCycle):
        """保存情绪周期数据到数据库"""
        pass
```

### 2. 综合情绪分析器 (中优先级)

**文件**: `core/src/sentiment/sentiment_analyzer.py` (预计 ~300行)

**核心类**: `SentimentAnalyzer`

**主要方法**:
```python
class SentimentAnalyzer:
    def __init__(self, pool_manager):
        self.cycle_calculator = SentimentCycleCalculator(pool_manager)
        self.hot_money_classifier = HotMoneyClassifier(pool_manager)

    def analyze_daily_sentiment(self, trade_date: str) -> DragonTigerAnalysis:
        """综合分析每日市场情绪"""
        # 1. 计算情绪周期
        # 2. 分析龙虎榜席位分布
        # 3. 统计机构和游资动向
        # 4. 生成综合报告
        pass

    def get_market_hotspots(self, trade_date: str) -> List[str]:
        """识别市场热点板块"""
        pass

    def generate_sentiment_report(self, trade_date: str) -> Dict:
        """生成完整的情绪分析报告"""
        pass
```

### 3. 业务服务层 (高优先级)

**文件**: `backend/app/services/sentiment_cycle_service.py` (预计 ~350行)

**核心类**: `SentimentCycleService`

**主要方法**:
```python
class SentimentCycleService:
    def get_cycle_stage(self, date: str = None) -> Dict:
        """获取情绪周期阶段"""
        pass

    def get_cycle_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取情绪周期历史"""
        pass

    def get_hot_money_analysis(self, date: str) -> Dict:
        """获取游资分析报告"""
        pass

    def get_institution_ranking(self, date: str, limit: int = 3) -> List[Dict]:
        """获取机构净买入排行"""
        pass

    def get_hot_money_ranking(self, date: str, limit: int = 10) -> List[Dict]:
        """获取游资打板排行"""
        pass

    def sync_cycle_calculation(self, date: str):
        """同步计算情绪周期数据"""
        pass
```

### 4. API端点扩展 (高优先级)

**文件**: `backend/app/api/endpoints/sentiment.py` (需要扩展)

**新增端点**:
```python
# 情绪周期相关
@router.get("/sentiment/cycle/current")
async def get_current_cycle_stage():
    """获取当前情绪周期阶段"""
    pass

@router.get("/sentiment/cycle/history")
async def get_cycle_history(start_date: str, end_date: str):
    """获取情绪周期历史"""
    pass

@router.get("/sentiment/cycle/trend")
async def get_cycle_trend(days: int = 30):
    """获取情绪周期趋势（近N天）"""
    pass

# 游资分析相关
@router.get("/sentiment/hot-money/institution-top")
async def get_institution_top_stocks(date: str = None, limit: int = 3):
    """获取机构净买入前N的个股"""
    pass

@router.get("/sentiment/hot-money/top-tier-limit-up")
async def get_top_tier_limit_up_stocks(date: str = None, limit: int = 10):
    """获取一线游资主导打板的个股"""
    pass

@router.get("/sentiment/hot-money/activity-ranking")
async def get_hot_money_activity_ranking(days: int = 30, limit: int = 20):
    """获取游资活跃度排行榜"""
    pass

@router.get("/sentiment/hot-money/seat/{seat_name}")
async def get_seat_detail(seat_name: str):
    """获取席位详细信息"""
    pass

# 综合分析
@router.get("/sentiment/analysis/daily")
async def get_daily_sentiment_analysis(date: str = None):
    """获取每日情绪综合分析报告"""
    pass
```

### 5. 前端类型定义扩展 (中优先级)

**文件**: `admin/types/sentiment.ts` (需要扩展)

**新增类型**:
```typescript
// 情绪周期类型
export interface SentimentCycle {
  trade_date: string;
  cycle_stage: 'freezing' | 'starting' | 'fermenting' | 'retreating';
  cycle_stage_cn: '冰点' | '启动' | '发酵' | '退潮';
  confidence_score: number;
  money_making_index: number;
  sentiment_score: number;
  limit_up_count: number;
  limit_down_count: number;
  limit_ratio: number;
  blast_rate: number;
  max_continuous_days: number;
  stage_duration_days: number;
  analysis_result?: any;
}

// 游资席位类型
export interface HotMoneySeat {
  seat_name: string;
  seat_type: 'top_tier' | 'famous' | 'retail_base' | 'institution' | 'unknown';
  seat_label: string;
  city?: string;
  broker?: string;
  appearance_count: number;
  total_buy_amount: number;
  total_sell_amount: number;
  win_rate?: number;
  trade_style?: string;
  last_appearance_date?: string;
}

// 机构净买入排行
export interface InstitutionTopStock {
  stock_code: string;
  stock_name: string;
  net_buy_amount: number;
  institution_seats: Array<{
    seat_name: string;
    buy_amount: number;
    rank: number;
  }>;
  institution_count: number;
  price_change: number;
}

// 游资打板排行
export interface HotMoneyLimitUpStock {
  stock_code: string;
  stock_name: string;
  hot_money_seats: Array<{
    seat_name: string;
    seat_label: string;
    buy_amount: number;
  }>;
  hot_money_count: number;
  total_buy_amount: number;
  is_limit_up: boolean;
  price_change: number;
}
```

---

## 集成步骤

### 步骤 1: 执行数据库迁移

```bash
# 进入数据库容器
docker-compose exec db psql -U postgres -d stock_analysis

# 执行迁移脚本
\i /docker-entrypoint-initdb.d/06_sentiment_cycle_schema.sql

# 验证表创建
\dt market_sentiment_cycle
\dt hot_money_seats
\dt hot_money_operations

# 查看预置游资数据
SELECT seat_name, seat_label, city FROM hot_money_seats ORDER BY priority DESC LIMIT 10;
```

### 步骤 2: 测试游资分类器

```python
# 在 backend 目录下创建测试脚本
# test_hot_money_classifier.py

import sys
sys.path.insert(0, '../core/src')

from database.connection_pool_manager import ConnectionPoolManager
from sentiment.hot_money_classifier import HotMoneyClassifier

# 初始化
pool_manager = ConnectionPoolManager()
classifier = HotMoneyClassifier(pool_manager)

# 测试席位分类
test_seats = [
    "中信证券股份有限公司上海溧阳路证券营业部",
    "东方财富证券股份有限公司拉萨团结路第二证券营业部",
    "机构专用",
    "招商证券股份有限公司深圳蛇口工业七路证券营业部"
]

for seat in test_seats:
    seat_type, seat_label = classifier.classify_seat(seat)
    print(f"{seat} → {seat_label}")

# 测试机构净买入排行（需要有龙虎榜数据）
top_stocks = classifier.get_institution_top_stocks('2026-03-10', limit=3)
print(f"\n机构净买入前3:")
for stock in top_stocks:
    print(f"  {stock['stock_name']}: {stock['net_buy_amount']:,.0f}元")
```

### 步骤 3: 实现剩余核心文件

按照优先级实现待实现文件:
1. ✅ `cycle_calculator.py` - 情绪周期计算引擎
2. ✅ `sentiment_analyzer.py` - 综合分析器
3. ✅ `sentiment_cycle_service.py` - 业务服务层
4. ✅ 扩展 API端点
5. ✅ 扩展前端类型

### 步骤 4: 集成到定时任务

在 `backend/app/tasks/sentiment_tasks.py` 中添加:

```python
@celery_app.task(name="sentiment.calculate_cycle")
def calculate_sentiment_cycle_task():
    """
    每日17:35计算情绪周期（在情绪数据同步后5分钟执行）
    """
    from app.services.sentiment_cycle_service import SentimentCycleService

    today = datetime.now().strftime('%Y-%m-%d')
    service = SentimentCycleService()

    try:
        service.sync_cycle_calculation(today)
        logger.info(f"情绪周期计算完成: {today}")
    except Exception as e:
        logger.error(f"情绪周期计算失败: {e}")
```

---

## API接口设计

### 完整API列表

| 端点 | 方法 | 描述 | 返回 |
|------|------|------|------|
| `/api/sentiment/cycle/current` | GET | 获取当前情绪周期 | SentimentCycle |
| `/api/sentiment/cycle/history` | GET | 情绪周期历史 | List[SentimentCycle] |
| `/api/sentiment/cycle/trend` | GET | 情绪周期趋势图数据 | ChartData |
| `/api/sentiment/hot-money/institution-top` | GET | 机构净买入排行 | List[InstitutionTopStock] |
| `/api/sentiment/hot-money/top-tier-limit-up` | GET | 顶级游资打板排行 | List[HotMoneyLimitUpStock] |
| `/api/sentiment/hot-money/activity-ranking` | GET | 游资活跃度排行 | List[HotMoneySeat] |
| `/api/sentiment/hot-money/seat/{name}` | GET | 席位详细信息 | HotMoneySeatDetail |
| `/api/sentiment/analysis/daily` | GET | 每日综合分析报告 | DragonTigerAnalysis |

### 接口调用示例

#### 1. 获取当前情绪周期

**请求**:
```http
GET /api/sentiment/cycle/current
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "trade_date": "2026-03-10",
    "cycle_stage": "fermenting",
    "cycle_stage_cn": "发酵",
    "confidence_score": 85.5,
    "money_making_index": 78.3,
    "sentiment_score": 82.1,
    "limit_up_count": 52,
    "limit_down_count": 8,
    "limit_ratio": 6.5,
    "blast_rate": 0.22,
    "max_continuous_days": 7,
    "stage_duration_days": 3,
    "analysis_result": {
      "stage_reason": "涨停家数超过50家，连板高度达到7天，炸板率低于30%",
      "key_indicators": {
        "limit_up_strength": "强",
        "continuous_height": "高",
        "blast_pressure": "低"
      },
      "market_hotspots": ["AI", "新能源", "半导体"],
      "risk_warning": "情绪过热，注意回调风险"
    }
  }
}
```

#### 2. 获取机构净买入排行

**请求**:
```http
GET /api/sentiment/hot-money/institution-top?date=2026-03-10&limit=3
```

**响应**:
```json
{
  "code": 200,
  "data": [
    {
      "stock_code": "000001",
      "stock_name": "平安银行",
      "close_price": 15.68,
      "price_change": 9.95,
      "net_buy_amount": 58600000,
      "institution_count": 4,
      "institution_seats": [
        {
          "seat_name": "机构专用",
          "buy_amount": 28000000,
          "rank": 1
        },
        {
          "seat_name": "XX基金公司专户",
          "buy_amount": 18000000,
          "rank": 2
        },
        {
          "seat_name": "社保基金组合",
          "buy_amount": 12600000,
          "rank": 3
        }
      ],
      "reason": "日涨幅偏离值达7%"
    },
    // ... 更多
  ]
}
```

#### 3. 获取顶级游资打板排行

**请求**:
```http
GET /api/sentiment/hot-money/top-tier-limit-up?date=2026-03-10&limit=10
```

**响应**:
```json
{
  "code": 200,
  "data": [
    {
      "stock_code": "300750",
      "stock_name": "宁德时代",
      "close_price": 235.60,
      "price_change": 10.01,
      "is_limit_up": true,
      "hot_money_count": 3,
      "total_buy_amount": 45800000,
      "hot_money_seats": [
        {
          "seat_name": "中信证券股份有限公司上海溧阳路证券营业部",
          "seat_label": "[一线顶级游资]",
          "buy_amount": 20000000,
          "rank": 1
        },
        {
          "seat_name": "国泰君安证券股份有限公司顺德大良营业部",
          "seat_label": "[一线顶级游资]",
          "buy_amount": 15800000,
          "rank": 2
        },
        {
          "seat_name": "华泰证券股份有限公司深圳益田路荣超商务中心证券营业部",
          "seat_label": "[一线顶级游资]",
          "buy_amount": 10000000,
          "rank": 4
        }
      ]
    },
    // ... 更多
  ]
}
```

---

## 使用示例

### Python 后端使用

```python
from app.services.sentiment_cycle_service import SentimentCycleService

service = SentimentCycleService()

# 1. 获取当前情绪周期
cycle = service.get_cycle_stage()
print(f"当前市场情绪: {cycle['cycle_stage_cn']}")
print(f"赚钱效应指数: {cycle['money_making_index']:.1f}分")

# 2. 获取机构净买入排行
institution_top = service.get_institution_ranking(date='2026-03-10', limit=3)
for idx, stock in enumerate(institution_top, 1):
    print(f"{idx}. {stock['stock_name']}: 机构净买入 {stock['net_buy_amount']:,.0f}元")

# 3. 获取顶级游资打板排行
hot_money_top = service.get_hot_money_ranking(date='2026-03-10', limit=5)
for idx, stock in enumerate(hot_money_top, 1):
    print(f"{idx}. {stock['stock_name']}: {stock['hot_money_count']}个顶级游资参与")
```

### TypeScript 前端使用

```typescript
import { sentimentApi } from '@/services/api';

// 1. 获取当前情绪周期
const cycleData = await sentimentApi.getCurrentCycle();
console.log(`市场情绪: ${cycleData.cycle_stage_cn}`);
console.log(`赚钱效应: ${cycleData.money_making_index}分`);

// 2. 获取机构净买入排行
const institutionTop = await sentimentApi.getInstitutionTop({
  date: '2026-03-10',
  limit: 3
});

// 3. 获取游资活跃度排行
const hotMoneyRanking = await sentimentApi.getHotMoneyActivityRanking({
  days: 30,
  limit: 20
});
```

---

## 测试验证

### 单元测试

创建测试文件: `backend/tests/test_sentiment_cycle.py`

```python
import pytest
from app.services.sentiment_cycle_service import SentimentCycleService

@pytest.fixture
def service():
    return SentimentCycleService()

def test_calculate_money_making_index(service):
    """测试赚钱效应指数计算"""
    data = {
        'limit_up_count': 50,
        'limit_down_count': 10,
        'max_continuous_days': 5,
        'blast_rate': 0.3
    }
    index = service._calculate_money_making_index(data)
    assert 0 <= index <= 100

def test_get_cycle_stage(service):
    """测试获取情绪周期"""
    cycle = service.get_cycle_stage('2026-03-10')
    assert cycle['cycle_stage'] in ['freezing', 'starting', 'fermenting', 'retreating']

def test_institution_ranking(service):
    """测试机构净买入排行"""
    ranking = service.get_institution_ranking('2026-03-10', limit=3)
    assert len(ranking) <= 3
```

### 集成测试

```bash
# 1. 测试数据库迁移
docker-compose exec db psql -U postgres -d stock_analysis -c "SELECT COUNT(*) FROM hot_money_seats;"

# 2. 测试API端点
curl http://localhost:8000/api/sentiment/cycle/current

# 3. 测试游资分类
python backend/test_hot_money_classifier.py

# 4. 运行完整测试套件
cd backend
pytest tests/test_sentiment_cycle.py -v
```

---

## 部署检查清单

- [ ] 数据库迁移已执行
- [ ] 游资席位字典已初始化（20+席位）
- [ ] 核心计算引擎已实现并测试
- [ ] API端点已添加并测试
- [ ] 定时任务已配置（每日17:35执行）
- [ ] 前端类型定义已更新
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 文档已更新

---

## 性能优化建议

1. **缓存策略**:
   - 情绪周期数据缓存1小时
   - 游资席位字典缓存到内存
   - 龙虎榜分析结果缓存30分钟

2. **数据库优化**:
   - 为常用查询字段添加索引（已完成）
   - 使用物化视图加速复杂查询
   - 定期清理过期数据

3. **计算优化**:
   - 批量计算历史数据时使用多线程
   - 增量更新席位统计信息
   - 预计算常用指标

---

## 常见问题

### Q1: 如何添加新的游资席位？

**方法1: 数据库直接插入**
```sql
INSERT INTO hot_money_seats (
    seat_name, seat_type, seat_label, city, broker, priority
) VALUES (
    '新游资席位名称', 'top_tier', '[一线顶级游资]', '上海', '中信证券', 95
);
```

**方法2: 通过API添加**
```python
# 待实现: POST /api/sentiment/hot-money/seat
```

### Q2: 如何调整情绪周期阈值？

修改 `core/src/sentiment/config.py` 中的 `CYCLE_THRESHOLDS` 配置，重启服务即可生效。

### Q3: 席位分类不准确怎么办？

1. 检查关键词匹配规则是否覆盖
2. 调整席位优先级
3. 使用精确匹配（添加到数据库）

---

## 总结

### ✅ 已完成

1. **数据库设计** - 3张核心表 + 2个视图
2. **配置系统** - 完整的阈值和规则配置
3. **数据模型** - 6个新增模型类
4. **游资分类器** - 完整实现，支持4种席位分类
5. **统计分析** - 机构排行、游资排行、活跃度排行

### ⏳ 待实现

1. **情绪周期计算引擎** - 赚钱效应模型核心
2. **综合分析器** - 整合所有分析功能
3. **业务服务层** - 对接API层
4. **API端点** - 8个新增接口
5. **前端集成** - TypeScript类型 + UI组件

### 📊 预期效果

实现后，系统将能够:
- ✅ 每日自动识别市场情绪周期（冰点/启动/发酵/退潮）
- ✅ 计算赚钱效应指数（0-100分）
- ✅ 自动标记龙虎榜席位类型（机构/顶级游资/散户等）
- ✅ 统计机构净买入前3的个股
- ✅ 统计一线游资主导打板的个股
- ✅ 提供游资活跃度排行榜
- ✅ 生成每日市场情绪分析报告

---

**创建日期**: 2026-03-10
**最后更新**: 2026-03-10
**维护人员**: AI Assistant
**文档版本**: 1.0
