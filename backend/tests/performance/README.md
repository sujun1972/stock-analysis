# 性能基准测试指南

**任务**: 3.4 性能基准测试 (P0)
**版本**: 1.0.0
**日期**: 2026-02-05
**负责人**: Backend Team

---

## 📖 目录

1. [测试概述](#测试概述)
2. [测试环境准备](#测试环境准备)
3. [性能测试工具](#性能测试工具)
4. [测试场景](#测试场景)
5. [执行测试](#执行测试)
6. [性能指标](#性能指标)
7. [结果分析](#结果分析)
8. [故障排查](#故障排查)

---

## 测试概述

本项目包含两种类型的性能测试:

### 1. **并发性能测试** (Pytest)
- 文件: `test_concurrent_performance.py`
- 目的: 单元级并发性能验证
- 适用: CI/CD 自动化测试
- 执行时间: 约 2-5 分钟

### 2. **Locust 压力测试** (Locust)
- 文件: `locustfile.py`
- 目的: 系统级性能基准测试
- 适用: 发布前完整性能评估
- 执行时间: 5-30 分钟 (可配置)

---

## 测试环境准备

### 前置条件

1. **后端服务运行**
   ```bash
   cd /Volumes/MacDriver/stock-analysis/backend

   # 启动所有服务 (推荐)
   docker-compose up -d

   # 或仅启动依赖服务
   docker-compose up -d timescaledb redis

   # 启动 FastAPI 服务
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **安装测试依赖**
   ```bash
   # 安装 Locust
   pip install locust

   # 验证安装
   locust --version
   ```

3. **准备测试数据**
   ```bash
   # 确保数据库有测试数据
   docker-compose exec backend python -c "
   from app.core_adapters.data_adapter import DataAdapter
   adapter = DataAdapter()
   # 下载测试股票数据
   adapter.download_stock_data('000001.SZ', '2023-01-01', '2024-12-31')
   "
   ```

### 环境配置

编辑 `.env` 文件:
```env
ENVIRONMENT=testing
LOG_LEVEL=WARNING
REDIS_ENABLED=true
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

---

## 性能测试工具

### 工具对比

| 工具 | 优势 | 适用场景 |
|-----|------|---------|
| **Pytest** | 集成方便、自动化 | CI/CD、回归测试 |
| **Locust** | 真实负载、详细报告 | 压力测试、容量规划 |
| **Apache JMeter** | 功能丰富、GUI | 复杂场景、企业级 |
| **wrk** | 极速、轻量 | 快速验证、基准测试 |

本项目选用 **Locust** 原因:
- ✅ Python 原生 (与项目技术栈一致)
- ✅ 编写测试脚本简单 (Python 代码)
- ✅ 实时 Web UI 监控
- ✅ 分布式测试支持
- ✅ 详细性能报告

---

## 测试场景

### 场景 1: 轻度负载测试 (Sanity Check)

**目的**: 快速验证系统基本性能

```bash
locust -f tests/performance/locustfile.py \
       --headless \
       --users 50 \
       --spawn-rate 5 \
       --run-time 3m \
       --host http://localhost:8000 \
       --html reports/sanity_test_$(date +%Y%m%d_%H%M%S).html
```

**预期指标**:
- RPS: > 200
- P95 响应时间: < 50ms
- 错误率: 0%

---

### 场景 2: 标准负载测试 (Baseline)

**目的**: 建立性能基准

```bash
locust -f tests/performance/locustfile.py \
       --headless \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --host http://localhost:8000 \
       --html reports/baseline_test_$(date +%Y%m%d_%H%M%S).html
```

**预期指标**:
- RPS: > 500
- P95 响应时间: < 100ms
- 错误率: < 0.1%

---

### 场景 3: 峰值负载测试 (Peak Load)

**目的**: 测试系统峰值承载能力

```bash
locust -f tests/performance/locustfile.py \
       --headless \
       --users 500 \
       --spawn-rate 50 \
       --run-time 10m \
       --host http://localhost:8000 \
       --html reports/peak_test_$(date +%Y%m%d_%H%M%S).html
```

**预期指标**:
- RPS: > 1000
- P95 响应时间: < 200ms
- 错误率: < 1%

---

### 场景 4: 持续负载测试 (Soak Test)

**目的**: 验证系统长时间稳定性 (内存泄漏、性能衰减)

```bash
locust -f tests/performance/locustfile.py \
       --headless \
       --users 200 \
       --spawn-rate 20 \
       --run-time 30m \
       --host http://localhost:8000 \
       --html reports/soak_test_$(date +%Y%m%d_%H%M%S).html
```

**预期指标**:
- RPS: 保持稳定 (波动 < 5%)
- 响应时间: 无持续增长
- 错误率: < 0.5%
- 内存: 无持续增长

---

### 场景 5: 压力递增测试 (Ramp-up Test)

**目的**: 找到系统性能拐点

```bash
locust -f tests/performance/locustfile.py \
       --headless \
       --users 1000 \
       --spawn-rate 10 \
       --run-time 20m \
       --host http://localhost:8000 \
       --html reports/ramp_test_$(date +%Y%m%d_%H%M%S).html
```

**观察指标**:
- 性能拐点 (响应时间突增点)
- 最大 RPS
- 系统瓶颈 (CPU/内存/数据库)

---

## 执行测试

### 方法 1: 命令行模式 (推荐自动化)

```bash
# 创建报告目录
mkdir -p tests/performance/reports

# 运行基准测试
locust -f tests/performance/locustfile.py \
       --headless \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --host http://localhost:8000 \
       --html tests/performance/reports/baseline_$(date +%Y%m%d_%H%M%S).html \
       --csv tests/performance/reports/baseline_$(date +%Y%m%d_%H%M%S)
```

### 方法 2: Web UI 模式 (推荐手动调试)

```bash
# 启动 Locust Web UI
locust -f tests/performance/locustfile.py --host http://localhost:8000

# 浏览器访问
open http://localhost:8089
```

在 Web UI 中配置:
- **Number of users**: 100
- **Spawn rate**: 10
- **Host**: http://localhost:8000

点击 **Start Swarming** 开始测试

### 方法 3: 并发性能测试 (Pytest)

```bash
# 运行所有并发性能测试
pytest tests/performance/test_concurrent_performance.py -v -s

# 运行单个测试
pytest tests/performance/test_concurrent_performance.py::TestConcurrentPerformance::test_concurrent_100_requests -v -s
```

---

## 性能指标

### 关键指标说明

| 指标 | 说明 | 目标值 | 临界值 |
|-----|------|--------|--------|
| **RPS** | 每秒请求数 | > 500 | < 200 (不合格) |
| **P50 响应时间** | 中位数响应时间 | < 50ms | > 200ms (不合格) |
| **P95 响应时间** | 95% 请求的响应时间 | < 100ms | > 500ms (不合格) |
| **P99 响应时间** | 99% 请求的响应时间 | < 200ms | > 1000ms (不合格) |
| **错误率** | 失败请求比例 | < 0.1% | > 1% (不合格) |
| **吞吐量** | 每秒数据传输量 | > 10 MB/s | < 1 MB/s (不合格) |

### Locust 报告解读

#### 1. **Statistics Tab**
```
Type     Name                    # reqs  # fails  Median  95%ile  99%ile  Avg     Max
------------------------------------------------------------------------
GET      /api/stocks/list        5000    0        25      80      150     35      280
GET      /api/data/daily/{code}  3000    2        40      120     250     55      450
POST     /api/backtest/run       500     1        200     500     800     280     1200
------------------------------------------------------------------------
Total                            8500    3        30      100     200     45      1200
```

**解读**:
- ✅ 中位数 30ms - 优秀
- ✅ P95 100ms - 达标
- ⚠️ P99 200ms - 临界
- ✅ 错误率 0.035% (3/8500) - 达标

#### 2. **Charts Tab**
- **Total Requests per Second**: 观察 RPS 曲线稳定性
- **Response Times**: 观察响应时间分布
- **Number of Users**: 观察用户增长曲线

#### 3. **Failures Tab**
```
Method  Name                    # fails  Error
-----------------------------------------------
POST    /api/backtest/run       1        Connection timeout
GET     /api/data/daily/{code}  2        500 Internal Server Error
```

**解决方案**:
- 超时错误 → 增加超时时��或优化慢查询
- 500 错误 → 检查日志定位代码问题

---

## 结果分析

### 生成性能报告

运行测试后会生成:

1. **HTML 报告** (`reports/baseline_20260205_150000.html`)
   - 图表可视化
   - 详细统计数据
   - 错误分析

2. **CSV 数据** (`reports/baseline_20260205_150000_stats.csv`)
   - 原始数据导出
   - 用于自定义分析
   - 可导入 Excel/Tableau

### 性能对比

创建 `analyze_results.py` 对比多次测试结果:

```python
import pandas as pd
import matplotlib.pyplot as plt

# 加载数据
baseline = pd.read_csv('reports/baseline_20260205_150000_stats.csv')
optimized = pd.read_csv('reports/optimized_20260206_150000_stats.csv')

# 对比响应时间
comparison = pd.DataFrame({
    'Baseline': baseline['Average Response Time'],
    'Optimized': optimized['Average Response Time']
})

# 可视化
comparison.plot(kind='bar')
plt.ylabel('Response Time (ms)')
plt.title('Performance Improvement')
plt.savefig('reports/comparison.png')
```

### 性能瓶颈分析

#### 检查系统资源

**CPU 使用率**:
```bash
# macOS
top -l 1 | grep "CPU usage"

# Linux
top -bn1 | grep "Cpu(s)"

# 持续监控
docker stats backend
```

**内存使用率**:
```bash
# macOS
vm_stat

# Linux
free -h

# Docker 容器
docker stats --no-stream
```

**数据库连接**:
```sql
-- PostgreSQL
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- 慢查询
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**Redis 监控**:
```bash
docker-compose exec redis redis-cli INFO stats
docker-compose exec redis redis-cli SLOWLOG GET 10
```

---

## 故障排查

### 常见问题

#### 1. 连接被拒绝
```
ConnectionRefusedError: [Errno 61] Connection refused
```

**解决方案**:
```bash
# 检查服务状态
docker-compose ps
curl http://localhost:8000/health

# 查看日志
docker-compose logs backend
```

#### 2. 请求超时
```
requests.exceptions.Timeout: HTTPConnectionPool: Read timed out
```

**解决方案**:
```python
# locustfile.py 增加超时时间
class MyUser(HttpUser):
    connection_timeout = 30.0
    network_timeout = 30.0
```

#### 3. 高错误率 (> 5%)
```
Error rate: 8.5% (850 failures / 10000 requests)
```

**排查步骤**:
1. 查看 Failures Tab 定位具体错误
2. 检查后端日志 `docker-compose logs backend`
3. 检查数据库连接池 `SELECT * FROM pg_stat_activity;`
4. 检查 Redis 连接 `docker-compose exec redis redis-cli PING`

#### 4. 性能不达标

**优化方向**:
- ✅ 启用 Redis 缓存
- ✅ 数据库查询优化 (索引、查询计划)
- ✅ 增加连接池大小
- ✅ 启用异步处理
- ✅ 减少外部 API 调用
- ✅ 启用 Gzip 压缩
- ✅ CDN 静态资源

---

## 自动化测试脚本

创建 `run_performance_tests.sh`:

```bash
#!/bin/bash

# 性能测试自动化脚本
# 作者: Backend Team
# 日期: 2026-02-05

set -e

echo "======================================"
echo "性能基准测试 - 自动化执行"
echo "======================================"

# 1. 检查服务状态
echo "[1/5] 检查服务状态..."
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ 后端服务未运行！请先启动: docker-compose up -d"
    exit 1
fi
echo "✅ 服务运行正常"

# 2. 创建报告目录
echo "[2/5] 创建报告目录..."
mkdir -p tests/performance/reports
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 3. 运行并发性能测试 (Pytest)
echo "[3/5] 运行并发性能测试..."
pytest tests/performance/test_concurrent_performance.py -v -s \
    --html=tests/performance/reports/pytest_${TIMESTAMP}.html \
    --self-contained-html

# 4. 运行基准负载测试 (Locust)
echo "[4/5] 运行基准负载测试..."
locust -f tests/performance/locustfile.py \
       --headless \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --host http://localhost:8000 \
       --html tests/performance/reports/locust_baseline_${TIMESTAMP}.html \
       --csv tests/performance/reports/locust_baseline_${TIMESTAMP}

# 5. 生成汇总报告
echo "[5/5] 生成汇总报告..."
cat > tests/performance/reports/summary_${TIMESTAMP}.txt <<EOF
====================================
性能测试汇总报告
====================================
测试时间: $(date)
测试场景: 基准负载测试
并发用户: 100
运行时长: 5 分钟

测试报告:
- Pytest 报告: pytest_${TIMESTAMP}.html
- Locust 报告: locust_baseline_${TIMESTAMP}.html
- CSV 数据: locust_baseline_${TIMESTAMP}_stats.csv

验收标准:
- RPS: > 500
- P95 响应时间: < 100ms
- 错误率: < 0.1%

查看报告:
  open tests/performance/reports/locust_baseline_${TIMESTAMP}.html
====================================
EOF

echo ""
echo "✅ 所有测试完成！"
echo ""
cat tests/performance/reports/summary_${TIMESTAMP}.txt
echo ""
echo "查看详细报告:"
echo "  open tests/performance/reports/locust_baseline_${TIMESTAMP}.html"
