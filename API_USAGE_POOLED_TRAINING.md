# 多股池化训练和Ridge基准对比 API 使用文档

## 第二阶段：Backend容器API层适配 - 完成进度

### ✅ 已完成

1. **扩展请求模型** (`MLTrainingTaskCreate`)
   - 新增 `symbols: list[str]` 支持多股票
   - 保留 `symbol: str` 向后兼容
   - 新增 `enable_pooled_training: bool` 开关
   - 新增 `enable_ridge_baseline: bool` Ridge基准对比开关
   - 新增 `ridge_params: Dict` Ridge参数配置
   - 新增 `get_symbol_list()` 统一接口方法

2. **扩展响应模型** (`MLTrainingTaskResponse`)
   - 新增 `has_baseline: bool` 是否包含基准对比
   - 新增 `baseline_metrics: Dict` Ridge指标
   - 新增 `comparison_result: Dict` 对比结果
   - 新增 `recommendation: str` 推荐模型
   - 新增 `total_samples: int` 池化后总样本数
   - 新增 `successful_symbols: list[str]` 成功加载股票

### 🔄 待实现（需要服务层集成）

3. **训练服务集成** (`ml_training_service.py`)
   - 检测 `enable_pooled_training` 标志
   - 调用 `PooledTrainingPipeline`
   - 区分日志：`[Ridge] 训练中...` / `[LightGBM] 训练中...`
   - 返回完整对比结果

4. **数据库schema更新** (experiments表)
   - 添加 `has_baseline BOOLEAN`
   - 添加 `baseline_metrics JSONB`
   - 添加 `comparison_result JSONB`
   - 添加 `recommendation VARCHAR(50)`

5. **状态流增强** (SSE/WebSocket)
   - 区分当前训练的模型
   - 推送 Ridge 和 LightGBM 的分别进度

---

## API 使用示例

### 1. 单股票训练（向后兼容）

```bash
curl -X POST "http://localhost:8000/api/ml/train" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "000001",
    "start_date": "20210101",
    "end_date": "20231231",
    "model_type": "lightgbm",
    "target_period": 10
  }'
```

**响应**:
```json
{
  "task_id": "task_xxx",
  "status": "pending",
  "config": {...},
  "has_baseline": false
}
```

---

### 2. 多股池化训练 + Ridge基准对比

```bash
curl -X POST "http://localhost:8000/api/ml/train" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["000001", "000002", "600519", "000651", "600036"],
    "start_date": "20210101",
    "end_date": "20231231",
    "model_type": "lightgbm",
    "target_period": 10,
    "enable_pooled_training": true,
    "enable_ridge_baseline": true,
    "model_params": {
      "max_depth": 3,
      "num_leaves": 7,
      "n_estimators": 200,
      "learning_rate": 0.03,
      "min_child_samples": 100,
      "reg_alpha": 2.0,
      "reg_lambda": 2.0
    },
    "ridge_params": {
      "alpha": 1.0
    }
  }'
```

**响应**:
```json
{
  "task_id": "task_xxx",
  "status": "pending",
  "config": {
    "symbols": ["000001", "000002", "600519", "000651", "600036"],
    "enable_pooled_training": true,
    "enable_ridge_baseline": true
  },
  "has_baseline": true,
  "total_samples": 3500,
  "successful_symbols": ["000001", "000002", "600519", "000651", "600036"],
  "metrics": {
    "test_ic": 0.188,
    "test_rank_ic": 0.210,
    "test_mae": 4.14,
    "overfit_ic": 0.444
  },
  "baseline_metrics": {
    "test_ic": 0.284,
    "test_rank_ic": 0.234,
    "test_mae": 4.27,
    "overfit_ic": 0.212
  },
  "comparison_result": {
    "ridge_test_ic": 0.284,
    "lgb_test_ic": 0.188,
    "ridge_overfit": 0.212,
    "lgb_overfit": 0.444
  },
  "recommendation": "ridge"
}
```

---

### 3. 仅训练Ridge模型

```bash
curl -X POST "http://localhost:8000/api/ml/train" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["000001", "000002", "600519"],
    "start_date": "20210101",
    "end_date": "20231231",
    "model_type": "ridge",
    "target_period": 10,
    "enable_pooled_training": true,
    "enable_ridge_baseline": false,
    "ridge_params": {
      "alpha": 1.5
    }
  }'
```

---

### 4. 流式获取训练进度

```bash
curl -N "http://localhost:8000/api/ml/tasks/task_xxx/stream"
```

**SSE事件流** (增强后):
```
data: {"status": "running", "progress": 10, "current_step": "[Ridge] 训练中..."}

data: {"status": "running", "progress": 50, "current_step": "[Ridge] 训练完成", "baseline_metrics": {...}}

data: {"status": "running", "progress": 60, "current_step": "[LightGBM] 训练中..."}

data: {"status": "running", "progress": 90, "current_step": "[LightGBM] 训练完成", "metrics": {...}}

data: {"status": "completed", "progress": 100, "current_step": "对比评估完成", "recommendation": "ridge"}
```

---

## 前端对接要点

### 1. 多选股票框
```typescript
interface TrainRequest {
  symbols: string[];  // 替代 symbol
  enable_pooled_training: boolean;
  enable_ridge_baseline: boolean;
  // ...
}
```

### 2. Ridge开关
```tsx
<Switch
  label="启用Ridge基准对比"
  checked={enableRidgeBaseline}
  onChange={setEnableRidgeBaseline}
/>
```

### 3. 并排对比展示
```tsx
{response.has_baseline && (
  <ComparisonTable>
    <thead>
      <tr>
        <th>指标</th>
        <th>LightGBM</th>
        <th>Ridge</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Test IC</td>
        <td>{response.metrics.test_ic}</td>
        <td>{response.baseline_metrics.test_ic}</td>
      </tr>
      <tr>
        <td>过拟合</td>
        <td>{response.metrics.overfit_ic}</td>
        <td>{response.baseline_metrics.overfit_ic}</td>
      </tr>
    </tbody>
  </ComparisonTable>
)}

{response.recommendation && (
  <Alert type="success">
    推荐使用: {response.recommendation.toUpperCase()} 模型
  </Alert>
)}
```

---

## 数据库Schema变更

```sql
-- 添加池化训练相关字段到 experiments 表
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS has_baseline BOOLEAN DEFAULT FALSE;
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS baseline_metrics JSONB;
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS comparison_result JSONB;
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS recommendation VARCHAR(50);
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS total_samples INTEGER;
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS successful_symbols TEXT[];

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_experiments_recommendation ON experiments(recommendation);
CREATE INDEX IF NOT EXISTS idx_experiments_has_baseline ON experiments(has_baseline);
```

---

## 测试命令

```bash
# 1. 测试单股票（向后兼容）
python backend/test_single_stock_training.py

# 2. 测试池化训练
python backend/test_pooled_pipeline.py

# 3. 测试API
pytest backend/tests/test_ml_api.py::test_pooled_training
```

---

## 下一步：第三阶段 Frontend UI

1. 升级 `TrainConfigPanel` 组件
2. 添加多选股票搜索框
3. 添加 Ridge 开关
4. 实现并排对比表格
5. 集成推荐提示

---

**状态**: 第二阶段模型层完成 ✅
**待办**: 服务层集成、数据库更新、前端UI
**测试**: Core层已验证通过（详见 test_pooled_pipeline.py）
