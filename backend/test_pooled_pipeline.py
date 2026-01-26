"""
测试池化训练Pipeline
验证Core容器的逻辑层升级是否正常工作
"""
import sys
sys.path.insert(0, '/app')

from src.data_pipeline.pooled_training_pipeline import PooledTrainingPipeline

print("=" * 80)
print("测试池化训练Pipeline")
print("=" * 80)

# 选择10只股票进行快速测试
test_symbols = [
    '000001', '000002', '000006', '000008', '000009',
    '000011', '000012', '000014', '000016', '000019'
]

# 创建Pipeline
pipeline = PooledTrainingPipeline(
    scaler_type='robust',
    verbose=True
)

# 运行完整Pipeline
results = pipeline.run_full_pipeline(
    symbol_list=test_symbols,
    start_date='20210101',
    end_date='20231231',
    target_period=10,
    enable_ridge_baseline=True  # 启用Ridge基准对比
)

print("\n" + "=" * 80)
print("【测试结果】")
print("=" * 80)
print(f"\n总样本数: {results['total_samples']}")
print(f"成功股票数: {results['num_symbols']}/{len(test_symbols)}")
print(f"特征数: {results['feature_count']}")
print(f"是否包含Ridge基准: {results['has_baseline']}")

if 'recommendation' in results:
    print(f"\n推荐模型: {results['recommendation'].upper()}")

print("\n✓ Core容器逻辑层升级测试完成")
