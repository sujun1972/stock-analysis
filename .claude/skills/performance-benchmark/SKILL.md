# 性能基准测试技能 (Performance Benchmark)

**技能名称**: `performance-benchmark`
**版本**: 1.0.0
**优先级**: ⭐⭐⭐⭐⭐ (P0)
**关联任务**: 3.4 性能基准测试

---

## 🎯 技能描述

执行完整的性能基准测试，包括并发性能测试和 Locust 压力测试，生成详细的性能报告。

**适用场景**:
- 发布前性能验证
- 性能回归测试
- 系统容量规划
- 性能优化前后对比

---

## 🚀 使用方法

### 方式 1: 直接调用技能
```
/performance-benchmark
```

### 方式 2: 自然语言触发
```
运行性能基准测试
执行压力测试
测试系统性能
```

---

## 📋 执行流程

### 1. **环境检查** (30秒)
- 检查后端服务状态 (http://localhost:8000/health)
- 验证 Docker 服务运行 (timescaledb, redis, backend)
- 确认 Locust 安装状态

### 2. **并发性能测试** (2-3分钟)
运行 Pytest 并发性能测试:
```bash
docker-compose exec backend python -m pytest \
    tests/performance/test_concurrent_performance.py -v -s
```

**测试内容**:
- 并发 100 个请求响应时间测试
- 批量 API 并发性能测试
- 并发服务性能测试
- 连接池泄漏检测
- 持续负载压力测试
- 并发下载性能测试

**验收标准**:
- 并发 100 请求平均响应时间 < 500ms
- 批量获取 50 只股票 < 2s
- 并发获取 100 只股票 < 3s
- 连接池无泄漏
- 持续负载成功率 ≥ 90%

### 3. **Locust 压力测试** (5-30分钟可选)
运行 Locust 基准负载测试:
```bash
locust -f tests/performance/locustfile.py \
       --headless \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --host http://localhost:8000 \
       --html reports/baseline_$(date +%Y%m%d_%H%M%S).html
```

**测试场景**:
- 轻度负载 (50 用户, 3 分钟)
- 标准负载 (100 用户, 5 分钟) - 推荐
- 峰值负载 (500 用户, 10 分钟)
- 持续负载 (200 用户, 30 分钟)

**目标指标**:
- RPS (每秒请求数): > 500
- P95 响应时间: < 100ms
- 错误率: < 0.1%

### 4. **性能报告生成** (10秒)
生成测试报告:
- HTML 可视化报告
- CSV 原始数据
- 汇总统计信息

---

## 📊 输出结果

### 文件输出

```
tests/performance/reports/
├── pytest_20260205_150000.html          # Pytest 测试报告
├── locust_baseline_20260205_150000.html # Locust HTML 报告
├── locust_baseline_20260205_150000_stats.csv      # CSV 统计数据
├── locust_baseline_20260205_150000_failures.csv   # 失败记录
└── summary_20260205_150000.txt          # 汇总报告
```

### 终端输出示例

```
====================================
性能基准测试 - 汇总报告
====================================
测试时间: 2026-02-05 15:30:00
测试场景: 标准负载测试
并发用户: 100
运行时长: 5 分钟

关键指标:
- 总请求数: 52,341
- 失败请求: 5 (0.01%)
- RPS: 628 ✅
- P50 响应时间: 28ms
- P95 响应时间: 85ms ✅
- P99 响应时间: 180ms
- 错误率: 0.01% ✅

✅ 所有验收标准已达标
====================================
```

---

## 🔧 配置选项

### 环境变量

```bash
# .env 配置
ENVIRONMENT=testing
LOG_LEVEL=WARNING
REDIS_ENABLED=true
```

### 测试场景选择

修改 `run_performance_tests.sh` 中的参数:
```bash
USERS=100          # 并发用户数
SPAWN_RATE=10      # 启动速率
RUN_TIME="5m"      # 运行时长
```

---

## 📈 性能指标说明

| 指标 | 说明 | 目标值 | 临界值 |
|-----|------|--------|--------|
| **RPS** | 每秒请求数 | > 500 | < 200 (不合格) |
| **P50** | 中位数响应时间 | < 50ms | > 200ms |
| **P95** | 95% 请求响应时间 | < 100ms | > 500ms |
| **P99** | 99% 请求响应时间 | < 200ms | > 1000ms |
| **错误率** | 失败请求比例 | < 0.1% | > 1% |

---

## 🐛 故障排查

### 问题 1: 服务未运行
```
错误: Connection refused to http://localhost:8000
```

**解决方案**:
```bash
docker-compose up -d
curl http://localhost:8000/health
```

### 问题 2: Locust 未安装
```
错误: command not found: locust
```

**解决方案**:
```bash
pip install locust
# 或
docker-compose exec backend pip install locust
```

### 问题 3: 高错误率
```
错误率: 8.5% (超过阈值 0.1%)
```

**排查步骤**:
1. 查看 Failures 报告定位具体错误
2. 检查后端日志 `docker-compose logs backend`
3. 检查数据库连接池
4. 检查 Redis 连接

---

## 📚 相关文档

- [性能测试指南](../../../backend/tests/performance/README.md)
- [基准测试报告模板](../../../backend/tests/performance/BENCHMARK_REPORT_TEMPLATE.md)
- [优化路线图](../../../backend/docs/planning/optimization_roadmap.md)
- [Locust 官方文档](https://docs.locust.io/)

---

## 🎓 最佳实践

### 1. 测试前准备
- 确保数据库有足够测试数据 (至少 16 只股票)
- 关闭其他占用系统资源的应用
- 使用生产相似的环境配置

### 2. 测试频率
- **每次发布前**: 标准负载测试 (5 分钟)
- **每周**: 峰值负载测试 (10 分钟)
- **每月**: 持续负载测试 (30 分钟)
- **性能优化后**: 完整对比测试

### 3. 性能对比
保存历史测试结果，对比性能趋势:
```bash
# 保存基准测试
cp reports/baseline_latest.html reports/baseline_v1.0.0.html

# 优化后重新测试并对比
diff <(cat reports/baseline_v1.0.0.csv) <(cat reports/baseline_v1.1.0.csv)
```

### 4. 报告存档
```bash
# 按版本归档性能报告
mkdir -p docs/performance_reports/v1.0.0
mv tests/performance/reports/* docs/performance_reports/v1.0.0/
```

---

## 🔄 持续集成集成

### GitHub Actions 示例

```yaml
name: Performance Benchmark

on:
  schedule:
    - cron: '0 2 * * 0'  # 每周日 2AM
  workflow_dispatch:

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Start services
        run: docker-compose up -d
      - name: Run benchmark
        run: ./tests/performance/run_performance_tests.sh
      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: performance-reports
          path: tests/performance/reports/
```

---

## 📝 更新日志

### v1.0.0 (2026-02-05)
- ✅ 初始版本
- ✅ 支持 Pytest 并发性能测试
- ✅ 支持 Locust 压力测试
- ✅ 自动生成 HTML 和 CSV 报告
- ✅ 多种测试场景支持

---

**创建日期**: 2026-02-05
**最后更新**: 2026-02-05
**维护者**: Backend Team
