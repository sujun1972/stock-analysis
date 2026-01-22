# AI 策略实验舱 - 实现文档

## 概述

AI 策略实验舱是一个完整的全栈机器学习可视化平台，将后端的 DataPipeline 和机器学习模型（LightGBM/GRU）完全可视化，提供从模型训练到策略回测的一站式解决方案。

## 技术栈

### Backend (FastAPI)
- FastAPI BackgroundTasks：异步训练任务执行
- SSE (Server-Sent Events)：实时进度推送
- Pydantic：数据验证和序列化
- 集成 DataPipeline：自动化特征工程

### Frontend (Next.js + React)
- Next.js 14 (App Router)
- Zustand：轻量级状态管理
- ECharts：专业数据可视化
- Tailwind CSS：现代化UI设计
- TypeScript：类型安全

## 核心功能模块

### 1. 后端 API (backend/app/api/endpoints/ml.py)

#### 训练任务管理
- `POST /api/ml/train` - 创建训练任务
- `GET /api/ml/tasks/{task_id}` - 获取任务状态
- `GET /api/ml/tasks` - 列出所有任务
- `DELETE /api/ml/tasks/{task_id}` - 删除任务

#### 实时进度推送
- `GET /api/ml/tasks/{task_id}/stream` - SSE 流式推送训练进度

#### 模型管理
- `GET /api/ml/models` - 列出训练完成的模型
- `POST /api/ml/predict` - 使用模型进行预测

#### 特征管理
- `GET /api/ml/features/available` - 获取可用特征列表
- `GET /api/ml/features/snapshot` - 获取指定日期的特征快照

### 2. 训练服务 (backend/app/services/ml_training_service.py)

#### 核心流程
1. 数据获取：使用 DataPipeline 自动获取特征和标签
2. 数据处理：特征缩放、样本平衡
3. 模型训练：支持 LightGBM 和 GRU
4. 模型评估：计算 RMSE, R², IC, Rank IC
5. 模型保存：持久化模型文件和元数据
6. 特征重要性：提取并保存特征重要性排名

#### 7步训练流程
```python
Step 1: 数据获取 (0% -> 20%)
Step 2: 数据清洗 (20% -> 30%)
Step 3: 特征工程 (30% -> 40%)
Step 4: 模型训练 (40% -> 80%)
Step 5: 模型评估 (80% -> 90%)
Step 6: 保存模型 (90% -> 95%)
Step 7: 生成报告 (95% -> 100%)
```

### 3. 前端组件

#### TrainingConfigPanel (训练配置面板)
**文件**: `frontend/src/components/ai-lab/TrainingConfigPanel.tsx`

功能：
- 股票代码和日期范围选择
- 模型类型选择（LightGBM/GRU）
- 目标周期配置（5/10/20天）
- 数据处理参数（scaler、样本平衡）
- GRU特定参数（sequence length、epochs）
- 一键开始训练
- 实时状态轮询（2秒间隔）

#### TrainingMonitor (训练监控)
**文件**: `frontend/src/components/ai-lab/TrainingMonitor.tsx`

功能：
- 实时进度条显示
- 训练状态指示器（运行中/完成/失败）
- 当前步骤展示
- 性能指标展示（RMSE, R², IC, Rank IC）
- 错误信息显示

#### FeatureImportance (特征重要性可视化)
**文件**: `frontend/src/components/ai-lab/FeatureImportance.tsx`

功能：
- ECharts 横向柱状图
- Top 20 特征排名
- 按 Gain 值排序
- 渐变色彩设计
- 响应式图表

#### PredictionChart (预测值 VS 实际值对齐图)
**文件**: `frontend/src/components/ai-lab/PredictionChart.tsx`

功能：
- 实际收益率曲线（灰色）
- 预测上涨曲线（红色，预测值 > 0）
- 预测下跌曲线（蓝色，预测值 ≤ 0）
- 数据下采样（最多500个点，优化性能）
- 缩放和拖动支持（DataZoom）
- 交互式 Tooltip

技术亮点：
```typescript
// 数据下采样
const downsample = (data: any[], maxPoints: number) => {
  if (data.length <= maxPoints) return data;
  const step = Math.ceil(data.length / maxPoints);
  return data.filter((_, i) => i % step === 0);
};

// 按涨跌分离预测值
const upPredictions = predictedValues.map((val) => val > 0 ? val : null);
const downPredictions = predictedValues.map((val) => val <= 0 ? val : null);
```

#### ModelList (模型仓库)
**文件**: `frontend/src/components/ai-lab/ModelList.tsx`

功能：
- 模型卡片展示（symbol、类型、性能指标）
- 模型选择（高亮显示）
- 过滤（按股票代码、模型类型）
- 一键运行预测
- 删除模型
- 刷新列表

#### FeatureSnapshotViewer (特征快照查看器)
**文件**: `frontend/src/components/ai-lab/FeatureSnapshotViewer.tsx`

功能：
- 日期选择网格（从预测结果中选择）
- 模态框展示所有特征值
- 特征分类显示（基础行情、移动平均线、技术指标、Alpha因子）
- 异常值检测（NaN/Inf 高亮）
- 目标值和预测值对比

使用场景：
- 调试数据异常（如股票停牌导致的 NaN）
- 理解模型决策依据
- 验证特征工程正确性

#### BacktestIntegration (回测集成)
**文件**: `frontend/src/components/ai-lab/BacktestIntegration.tsx`

功能：
- 一键回测（使用默认参数）
- 高级回测（跳转到回测页面自定义参数）
- 自动配置策略参数
- 集成现有回测系统

默认策略配置：
```typescript
{
  strategy_type: 'ml_model',
  strategy_params: {
    model_id: selectedModel.model_id,
    buy_threshold: 1.0,   // 预测上涨 > 1% 买入
    sell_threshold: -1.0,  // 预测下跌 < -1% 卖出
  },
  initial_capital: 100000,
  commission: 0.0003,     // 万三
  slippage: 0.001,        // 0.1%
  stop_loss: 0.05,        // 5%
  take_profit: 0.10,      // 10%
}
```

### 4. 状态管理 (frontend/src/store/mlStore.ts)

#### 核心状态
```typescript
interface MLStore {
  // 配置
  config: MLTrainingConfig;
  setConfig: (config: Partial<MLTrainingConfig>) => void;

  // 训练任务
  currentTask: MLTrainingTask | null;
  tasks: MLTrainingTask[];

  // 模型
  models: MLModel[];
  selectedModel: MLModel | null;

  // 预测结果
  predictions: PredictionResult[];
}
```

#### 默认配置
```typescript
{
  symbol: '000001',
  start_date: '20200101',
  end_date: '20231231',
  model_type: 'lightgbm',
  target_period: 5,
  train_ratio: 0.7,
  valid_ratio: 0.15,
  scaler_type: 'robust',
  balance_samples: false,
  seq_length: 20,
  batch_size: 64,
  epochs: 100,
  early_stopping_rounds: 50,
}
```

## 数据流

### 训练流程
```
用户配置参数
  ↓
TrainingConfigPanel 发起 POST /api/ml/train
  ↓
后端创建任务 → 返回 task_id
  ↓
BackgroundTask 启动训练
  ↓
前端轮询 GET /api/ml/tasks/{task_id} (每2秒)
  ↓
TrainingMonitor 显示实时进度
  ↓
训练完成 → FeatureImportance 显示结果
```

### 预测流程
```
用户选择模型
  ↓
ModelList 发起 POST /api/ml/predict
  ↓
后端加载模型 → 使用 DataPipeline 获取数据
  ↓
模型推理 → 返回预测结果
  ↓
PredictionChart 可视化展示
  ↓
FeatureSnapshotViewer 提供深度观察
```

### 回测流程
```
用户选择模型
  ↓
BacktestIntegration 配置策略参数
  ↓
POST /api/backtest/run (使用 ml_model 策略)
  ↓
跳转到回测页面
  ↓
查看回测结果（收益曲线、指标等）
```

## API 请求示例

### 创建训练任务
```bash
POST http://localhost:8000/api/ml/train
Content-Type: application/json

{
  "symbol": "000001",
  "start_date": "20200101",
  "end_date": "20231231",
  "model_type": "lightgbm",
  "target_period": 5,
  "scaler_type": "robust",
  "balance_samples": false,
  "use_technical_indicators": true,
  "use_alpha_factors": true
}
```

响应：
```json
{
  "task_id": "abc123...",
  "status": "pending",
  "progress": 0,
  "current_step": "等待启动",
  "created_at": "2024-01-20T10:00:00"
}
```

### 获取任务状态
```bash
GET http://localhost:8000/api/ml/tasks/abc123
```

响应：
```json
{
  "task_id": "abc123",
  "status": "running",
  "progress": 45,
  "current_step": "模型训练中",
  "metrics": null,
  "feature_importance": null
}
```

### 运行预测
```bash
POST http://localhost:8000/api/ml/predict
Content-Type: application/json

{
  "model_id": "abc123",
  "symbol": "000001",
  "start_date": "20230101",
  "end_date": "20231231"
}
```

响应：
```json
{
  "predictions": [
    {
      "date": "20230103",
      "prediction": 2.34,
      "actual": 1.89
    },
    ...
  ],
  "metrics": {
    "rmse": 1.234,
    "r2": 0.678
  }
}
```

### 获取特征快照
```bash
GET http://localhost:8000/api/ml/features/snapshot?symbol=000001&date=20230103&model_id=abc123
```

响应：
```json
{
  "date": "20230103",
  "features": {
    "open": 10.50,
    "close": 10.80,
    "ma_5": 10.65,
    "rsi_14": 62.3,
    "momentum_20": 3.45,
    ...
  },
  "target": 1.89,
  "prediction": 2.34
}
```

## 性能优化

### 1. 数据下采样
PredictionChart 对超过 500 个数据点的序列进行下采样，避免渲染卡顿。

### 2. 轮询优化
使用 2 秒间隔轮询任务状态，平衡实时性和服务器压力。

### 3. 缓存机制
DataPipeline 使用 Parquet 缓存，避免重复计算特征（30x 加速）。

### 4. 异步训练
使用 FastAPI BackgroundTasks，训练过程不阻塞 API 响应。

### 5. 图表响应式
所有 ECharts 图表监听 window resize 事件，自动调整大小。

## 目录结构

```
backend/
├── app/
│   ├── api/endpoints/
│   │   └── ml.py                    # ML API 端点
│   ├── services/
│   │   └── ml_training_service.py   # 训练服务
│   └── models/
│       └── ml_models.py             # Pydantic 模型

frontend/
├── src/
│   ├── app/ai-lab/
│   │   └── page.tsx                 # 主页面
│   ├── components/ai-lab/
│   │   ├── TrainingConfigPanel.tsx
│   │   ├── TrainingMonitor.tsx
│   │   ├── FeatureImportance.tsx
│   │   ├── PredictionChart.tsx
│   │   ├── ModelList.tsx
│   │   ├── FeatureSnapshotViewer.tsx
│   │   └── BacktestIntegration.tsx
│   └── store/
│       └── mlStore.ts               # Zustand 状态管理
```

## 使用指南

### 1. 启动训练
1. 访问 `/ai-lab` 页面
2. 在左侧配置面板设置参数
3. 点击"开始训练"按钮
4. 观察训练监控面板的实时进度
5. 训练完成后查看特征重要性

### 2. 查看模型
1. 在模型仓库中浏览已训练模型
2. 点击模型卡片选中
3. 查看模型性能指标（RMSE, R², IC）

### 3. 运行预测
1. 选中目标模型
2. 点击"运行预测"按钮
3. 在预测对齐图中查看结果
4. 红色线表示预测上涨，蓝色线表示预测下跌

### 4. 查看特征快照
1. 运行预测后，特征快照查看器会显示可用日期
2. 点击任意交易日
3. 弹窗显示该日期的所有特征值
4. 检查是否存在异常值（NaN/Inf）

### 5. 一键回测
1. 选中目标模型
2. 在回测集成面板点击"一键回测"
3. 系统自动创建回测任务并跳转
4. 查看策略回测结果

## 注意事项

1. **训练时长**：GRU 模型训练时间较长（可能数小时），建议先使用 LightGBM 测试
2. **数据质量**：股票停牌会导致特征缺失，使用特征快照查看器检查
3. **模型泛化**：训练集和测试集时间要严格分离，避免未来数据泄漏
4. **回测偏差**：回测结果仅供参考，实盘需考虑滑点、冲击成本等

## 扩展功能（未来计划）

1. **实时 WebSocket 推送**：替代轮询，降低服务器压力
2. **多模型对比**：同时训练多个模型并对比性能
3. **超参数调优**：集成 Optuna 自动寻优
4. **模型集成**：多模型投票或加权平均
5. **在线学习**：定期使用新数据更新模型
6. **特征选择器**：UI 界面手动选择特征
7. **Loss 曲线**：GRU 训练过程的 Loss 可视化

## 技术亮点总结

✅ 完整的全栈 ML 可视化平台
✅ 实时训练进度推送（SSE）
✅ 专业数据可视化（ECharts）
✅ 深度观察工具（特征快照）
✅ 一键回测集成
✅ 数据下采样优化性能
✅ 响应式设计（Dark Mode 支持）
✅ 类型安全（TypeScript）
✅ 模块化组件设计
✅ 集成 DataPipeline（自动化特征工程）

---

**开发完成日期**: 2024-01-20
**版本**: v1.0.0
**技术栈**: FastAPI + Next.js + ECharts + Zustand + DataPipeline
