---
name: test-api
description: 测试所有 FastAPI 后端端点的可用性、响应正确性和性能
user-invocable: true
disable-model-invocation: false
---

# API 端点测试技能

你是一个 API 测试专家，负责全面测试 FastAPI 后端服务的所有端点。

## 任务目标

执行完整的 API 测试，包括：

1. **健康检查**
   - 服务是否运行
   - 数据库连接是否正常

2. **端点功能测试**
   - 股票列表 API
   - 数据下载和查询 API
   - 特征计算 API
   - 模型训练和预测 API（如已实现）
   - 回测 API（如已实现）

3. **响应验证**
   - HTTP 状态码
   - 响应格式（JSON schema）
   - 数据完整性
   - 错误处理

4. **性能测试**
   - 响应时间
   - 并发处理能力

## API 端点清单

### 基础端点
- `GET /health` - 健康检查
- `GET /` - 根路径

### 股票相关
- `GET /api/stocks/list` - 获取股票列表
- `GET /api/stocks/{code}` - 获取单只股票信息
- `POST /api/stocks/update` - 更新股票列表

### 数据管理
- `GET /api/data/daily/{code}` - 获取日线数据
- `POST /api/data/download` - 下载股票数据
- `GET /api/data/download/status/{task_id}` - 查询下载状态

### 特征工程
- `GET /api/features/{code}` - 获取特征数据
- `POST /api/features/calculate/{code}` - 计算特征

### 模型管理（如已实现）
- `POST /api/models/train` - 训练模型
- `GET /api/models/predict/{code}` - 获取预测结果

### 回测（如已实现）
- `POST /api/backtest/run` - 运行回测
- `GET /api/backtest/result/{task_id}` - 获取回测结果

## 执行步骤

### 第一步：环境准备

```bash
# 确保 backend 服务正在运行
docker-compose ps backend

# 如果未运行，启动服务
docker-compose up -d backend

# 等待服务完全启动（约5-10秒）
sleep 10
```

### 第二步：健康检查测试

```bash
echo "=== 健康检查测试 ==="

# 1. 基础健康检查
echo "1. GET /health"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:8000/health)
echo "$response"
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$http_code" = "200" ]; then
    echo "✅ 健康检查通过"
else
    echo "❌ 健康检查失败: HTTP $http_code"
fi

# 2. 根路径测试
echo -e "\n2. GET /"
curl -s http://localhost:8000/ | head -20
echo "✅ 根路径可访问"
```

### 第三步：股票列表 API 测试

```bash
echo -e "\n=== 股票列表 API 测试 ==="

# 1. 获取股票列表（默认参数）
echo "1. GET /api/stocks/list"
response=$(curl -s "http://localhost:8000/api/stocks/list")
echo "$response" | jq '.'

# 验证响应格式
total=$(echo "$response" | jq -r '.total')
data_length=$(echo "$response" | jq -r '.data | length')

if [ "$total" -gt 0 ] && [ "$data_length" -gt 0 ]; then
    echo "✅ 股票列表 API 正常 (共 $total 只股票, 返回 $data_length 条)"
else
    echo "❌ 股票列表 API 异常"
fi

# 2. 测试分页参数
echo -e "\n2. GET /api/stocks/list?limit=5&skip=0"
response=$(curl -s "http://localhost:8000/api/stocks/list?limit=5&skip=0")
data_length=$(echo "$response" | jq -r '.data | length')

if [ "$data_length" = "5" ]; then
    echo "✅ 分页参数正常"
else
    echo "⚠️  分页参数可能有问题 (预期5条，实际$data_length条)"
fi

# 3. 获取单只股票信息
echo -e "\n3. GET /api/stocks/000001"
response=$(curl -s "http://localhost:8000/api/stocks/000001")
stock_code=$(echo "$response" | jq -r '.code')

if [ "$stock_code" = "000001" ]; then
    echo "✅ 单只股票查询正常"
    echo "$response" | jq '.'
else
    echo "❌ 单只股票查询失败"
fi
```

### 第四步：数据管理 API 测试

```bash
echo -e "\n=== 数据管理 API 测试 ==="

# 1. 获取日线数据
echo "1. GET /api/data/daily/000001"
response=$(curl -s "http://localhost:8000/api/data/daily/000001?limit=10")
record_count=$(echo "$response" | jq '. | length')

if [ "$record_count" -gt 0 ]; then
    echo "✅ 日线数据查询正常 (返回 $record_count 条记录)"
    echo "$response" | jq '.[0]'
else
    echo "⚠️  未找到日线数据（可能需要先下载）"
fi

# 2. 测试日期范围查询
echo -e "\n2. GET /api/data/daily/000001?start_date=2024-01-01&end_date=2024-12-31"
response=$(curl -s "http://localhost:8000/api/data/daily/000001?start_date=2024-01-01&end_date=2024-12-31")
record_count=$(echo "$response" | jq '. | length')
echo "✅ 日期范围查询: $record_count 条记录"

# 3. 测试数据下载 API（POST请求）
echo -e "\n3. POST /api/data/download"
response=$(curl -s -X POST "http://localhost:8000/api/data/download" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["000001", "000002"],
    "years": 1
  }')

task_id=$(echo "$response" | jq -r '.task_id')
if [ "$task_id" != "null" ]; then
    echo "✅ 下载任务已创建: $task_id"

    # 4. 查询下载状态
    echo -e "\n4. GET /api/data/download/status/$task_id"
    sleep 2
    status_response=$(curl -s "http://localhost:8000/api/data/download/status/$task_id")
    echo "$status_response" | jq '.'
else
    echo "⚠️  下载任务创建可能失败（或该API未实现）"
fi
```

### 第五步：特征工程 API 测试

```bash
echo -e "\n=== 特征工程 API 测试 ==="

# 1. 获取特征数据
echo "1. GET /api/features/000001"
response=$(curl -s "http://localhost:8000/api/features/000001")

if [ "$(echo "$response" | jq 'type')" = '"object"' ] || [ "$(echo "$response" | jq 'type')" = '"array"' ]; then
    echo "✅ 特征数据查询正常"
    echo "$response" | jq '.' | head -30
else
    echo "⚠️  未找到特征数据（可能需要先计算）"
fi

# 2. 计算特征
echo -e "\n2. POST /api/features/calculate/000001"
response=$(curl -s -X POST "http://localhost:8000/api/features/calculate/000001" \
  -H "Content-Type: application/json" \
  -d '{
    "feature_types": ["technical"],
    "save_to_db": false
  }')

if [ "$(echo "$response" | jq -r '.status')" = "success" ] || [ "$response" != "" ]; then
    echo "✅ 特征计算 API 正常"
    echo "$response" | jq '.'
else
    echo "⚠️  特征计算 API 可能未实现"
fi
```

### 第六步：错误处理测试

```bash
echo -e "\n=== 错误处理测试 ==="

# 1. 测试不存在的股票代码
echo "1. GET /api/stocks/INVALID"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:8000/api/stocks/INVALID)
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$http_code" = "404" ] || [ "$http_code" = "400" ]; then
    echo "✅ 404错误处理正常"
else
    echo "⚠️  错误码: $http_code (预期 404 或 400)"
fi

# 2. 测试无效的日期格式
echo -e "\n2. GET /api/data/daily/000001?start_date=invalid"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "http://localhost:8000/api/data/daily/000001?start_date=invalid")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$http_code" = "422" ] || [ "$http_code" = "400" ]; then
    echo "✅ 参数验证正常"
else
    echo "⚠️  错误码: $http_code (预期 422 或 400)"
fi

# 3. 测试空请求体
echo -e "\n3. POST /api/data/download (空请求体)"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "http://localhost:8000/api/data/download" \
  -H "Content-Type: application/json")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$http_code" = "422" ]; then
    echo "✅ ��求体验证正常"
else
    echo "⚠️  错误码: $http_code (预期 422)"
fi
```

### 第七步：性能测试

```bash
echo -e "\n=== 性能测试 ==="

# 1. 响应时间测试
echo "1. 响应时间测试"
for i in {1..5}; do
    time=$(curl -s -w "%{time_total}" -o /dev/null http://localhost:8000/api/stocks/list)
    echo "  请求 $i: ${time}s"
done

# 2. 并发测试（简单版）
echo -e "\n2. 并发测试 (5个并发请求)"
start_time=$(date +%s)
for i in {1..5}; do
    curl -s http://localhost:8000/api/stocks/list > /dev/null &
done
wait
end_time=$(date +%s)
duration=$((end_time - start_time))
echo "✅ 5个并发请求完成，耗时: ${duration}秒"
```

## 输出格式

生成一份 API 测试报告：

### 1. 执行摘要
```
================================================================================
                          API 端点测试报告
================================================================================
测试时间: 2026-01-26 14:00:00
服务地址: http://localhost:8000
测试端点数: 12
```

### 2. 健康检查
```
健康检查:
✅ GET /health                    200 OK (0.023s)
✅ GET /                          200 OK (0.015s)
✅ 数据库连接                     正常
```

### 3. 功能测试结果
```
功能测试结果:
端点名称                           状态      响应时间    备注
--------------------------------------------------------------------------------
✅ GET /api/stocks/list           200 OK    0.145s     返回 3500+ 股票
✅ GET /api/stocks/{code}         200 OK    0.032s     正常
✅ GET /api/data/daily/{code}     200 OK    0.089s     返回 1234 条记录
✅ POST /api/data/download        202 OK    0.156s     异步任务已创建
✅ GET /api/features/{code}       200 OK    0.234s     正常
⚠️  POST /api/features/calculate  501 NA    -          未实现
⚠️  POST /api/models/train        404 NA    -          端点不存在
⚠️  POST /api/backtest/run        404 NA    -          端点不存在
--------------------------------------------------------------------------------
通过: 5/8 (62.5%)
```

### 4. 错误处理测试
```
错误处理:
✅ 不存在的资源                   404 Not Found
✅ 无效参数                       422 Unprocessable Entity
✅ 空请求体                       422 Unprocessable Entity
✅ 错误响应包含详细信息           正常
```

### 5. 性能指标
```
性能测试:
  平均响应时间:    0.127s
  最快响应:        0.015s (GET /)
  最慢响应:        0.234s (GET /api/features/{code})
  并发处理 (5):    1.2s
  吞吐量:          ~4 req/s

性能评级: B+ (良好)
```

### 6. 数据完整性
```
数据完整性检查:
✅ 股票列表包含必需字段 (code, name, market)
✅ 日线数据包含 OHLCV
✅ 响应格式符合 JSON Schema
✅ 日期格式统一 (ISO 8601)
✅ 数值类型正确
```

### 7. 问题列表
```
发现的问题:

高优先级:
- 无

中优先级:
1. 部分 API 端点未实现 (features/calculate, models/*, backtest/*)
2. 响应时间偏慢 (> 0.2s for /api/features)

低优先级:
1. 缺少 API 文档链接
2. 错误消息可以更友好
```

### 8. 改进建议
```
建议:
1. 实现缺失的 API 端点 (features, models, backtest)
2. 优化查询性能（添加数据库索引）
3. 添加请求速率限制
4. 实现 API 版本控制
5. 添加 OpenAPI 文档自动生成
6. 配置 CORS 策略
7. 添加请求日志记录
8. 实现健康检查详细信息（数据库版本、连接池状态等）
```

### 9. 自动化测试脚本

提供可复用的测试脚本：

```bash
# 保存为 test_api.sh
#!/bin/bash

API_BASE="http://localhost:8000"
PASS=0
FAIL=0

test_endpoint() {
    local method=$1
    local endpoint=$2
    local expected_code=$3
    local description=$4

    echo -n "Testing: $description ... "

    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X $method "$API_BASE$endpoint")
    http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)

    if [ "$http_code" = "$expected_code" ]; then
        echo "✅ PASS ($http_code)"
        ((PASS++))
    else
        echo "❌ FAIL (Expected $expected_code, got $http_code)"
        ((FAIL++))
    fi
}

# 运行测试
test_endpoint "GET" "/health" "200" "Health check"
test_endpoint "GET" "/api/stocks/list" "200" "Stock list"
test_endpoint "GET" "/api/stocks/000001" "200" "Single stock"
test_endpoint "GET" "/api/data/daily/000001" "200" "Daily data"
test_endpoint "GET" "/api/stocks/INVALID" "404" "Invalid stock (404)"

# 汇总
echo ""
echo "========================================="
echo "Total: $((PASS + FAIL))"
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo "Success Rate: $(echo "scale=2; $PASS * 100 / ($PASS + $FAIL)" | bc)%"
echo "========================================="
```

使用方法：
```bash
chmod +x test_api.sh
./test_api.sh
```

## 集成到 CI/CD

GitHub Actions 配置示例：

```yaml
# .github/workflows/api-test.yml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Start services
        run: docker-compose up -d

      - name: Wait for API
        run: |
          timeout 60 bash -c 'until curl -s http://localhost:8000/health; do sleep 2; done'

      - name: Run API tests
        run: bash test_api.sh

      - name: Cleanup
        run: docker-compose down
```

## 相关文档

- [backend/README.md](../../backend/README.md) - Backend 文档
- [FastAPI 测试文档](https://fastapi.tiangolo.com/tutorial/testing/)
- [API 文档](http://localhost:8000/api/docs) - Swagger UI
