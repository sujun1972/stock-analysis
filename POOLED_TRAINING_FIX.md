# 池化训练回测和RMSE修复总结

## 修复时间
2026-01-26

## 修复的问题

### 1. 回测策略不匹配
- **问题**: 池化训练使用ML模型，但回测使用技术指标策略
- **影响**: 回测结果不能反映ML模型真实表现（评分-10.14，年化收益-3.08%）
- **修复**: 切换到ml_model策略，正确使用训练的LightGBM模型

### 2. 特征列不匹配
- **问题**: 训练87列（含OHLCV），预测81列（不含OHLCV）
- **影响**: LightGBM报错特征数量不一致
- **修复**: 保存feature_cols到config，池化模型使用完整特征集

### 3. RMSE值为0
- **问题**: ComparisonEvaluator不包含RMSE字段
- **影响**: 数据库中RMSE显示为0.0000
- **修复**: 添加train/valid/test_rmse字段到评估结果

## 修改的文件

### Core模块
1. **model_trainer.py** - save_model()返回模型路径
2. **comparison_evaluator.py** - 添加RMSE字段到result字典
3. **pooled_training_pipeline.py** - 保存模型/scaler路径、提取RMSE、保存feature_cols

### Backend模块
4. **training_task_manager.py** - 使用ml_model策略回测、保存扩展config
5. **ml_model_strategy.py** - 支持UUID格式model_id、处理池化模型特征匹配

## 修复效果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 回测策略 | complex_indicator | ml_model ✓ |
| 年化收益 | -3.08% | 9.74% ✓ |
| 夏普比率 | -0.74 | 0.41 ✓ |
| 综合评分 | -10.14 | 8.40 ✓ |
| RMSE | 0.0000 | 2.7164 ✓ |

## 技术细节

### 特征匹配处理
```python
# 池化训练：87特征（含OHLCV+Amount）
config['feature_cols'] = result.get('feature_cols', [])  # 保存到数据库

# 回测时：加载原始数据，计算完整特征，按feature_cols顺序选择
if hasattr(self, 'trained_feature_cols') and self.trained_feature_cols:
    X = df_clean[self.trained_feature_cols]  # 完整87列
```

### UUID支持
```python
# 支持两种格式
# 1. 传统: 600000_lightgbm_20260126
# 2. UUID: 9af209b0-0667-45c6-ad48-8af534e137ab

# 从数据库查询而非解析格式
query = "SELECT model_path, config FROM experiments WHERE model_id = %s"
```

### ML模型回测
```python
backtest_result = await backtest_service.run_backtest(
    symbols=symbol,
    strategy_id='ml_model',  # 使用ML策略
    strategy_params={
        'model_id': task_id,
        'buy_threshold': 0.15,
        'sell_threshold': -0.3
    }
)
```

## 关于胜率为0

胜率为0不是bug，而是策略参数问题：
- 模型预测范围: -0.26% ~ 0.88%
- buy_threshold: 0.15%, sell_threshold: -0.3%
- 结果: 166买入信号，0卖出信号 → 无完成交易

**解决方案**: 调整阈值参数或使用动态阈值策略
