"""
ML-3 LightGBM 排序模型快速验证脚本

快速验证 LightGBM 模型训练和使用的完整流程
"""

import sys
from pathlib import Path
import tempfile
import shutil

import numpy as np
import pandas as pd

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def quick_test_ml3():
    """快速验证 ML-3 实现"""
    print("\n" + "=" * 70)
    print("ML-3 LightGBM 排序模型快速验证")
    print("=" * 70)

    # 检查依赖
    print("\n[1/5] 检查依赖...")
    try:
        import lightgbm
        import joblib
        print("✅ lightgbm 已安装")
        print("✅ joblib 已安装")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install lightgbm joblib")
        return False

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    print(f"✅ 临时目录: {temp_dir}")

    try:
        # 步骤 1: 创建测试数据
        print("\n[2/5] 创建测试数据...")
        dates = pd.date_range('2023-01-01', periods=200, freq='D')
        stocks = [f'STOCK_{i:03d}' for i in range(50)]

        np.random.seed(42)
        prices_data = 100 + np.cumsum(
            np.random.randn(200, 50) * 0.02, axis=0
        )
        prices = pd.DataFrame(prices_data, index=dates, columns=stocks)

        print(f"✅ 数据形状: {prices.shape}")
        print(f"✅ 日期范围: {prices.index[0].date()} ~ {prices.index[-1].date()}")

        # 步骤 2: 训练模型
        print("\n[3/5] 训练 LightGBM 模型...")
        from tools.train_stock_ranker_lgbm import StockRankerTrainer

        trainer = StockRankerTrainer(
            label_forward_days=5,
            label_threshold=0.02
        )

        X_train, y_train, groups_train = trainer.prepare_training_data(
            prices=prices,
            start_date='2023-01-20',
            end_date='2023-05-31',
            sample_freq='W'
        )

        print(f"✅ 训练样本: {len(X_train)}")
        print(f"✅ 特征数量: {X_train.shape[1]}")
        print(f"✅ 日期数: {len(groups_train)}")

        model = trainer.train_model(
            X_train=X_train,
            y_train=y_train,
            groups_train=groups_train,
            model_params={
                'n_estimators': 20,
                'learning_rate': 0.1,
                'verbose': -1
            }
        )

        print("✅ 模型训练完成")

        # 保存模型
        model_path = Path(temp_dir) / 'test_model.pkl'
        trainer.save_model(model, str(model_path))
        print(f"✅ 模型已保存: {model_path}")

        # 步骤 3: 使用模型选股
        print("\n[4/5] 使用 LightGBM 模型选股...")
        from src.strategies.three_layer.selectors.ml_selector import MLSelector

        selector = MLSelector(params={
            'mode': 'lightgbm_ranker',
            'model_path': str(model_path),
            'top_n': 20
        })

        print(f"✅ 模型加载状态: {selector.model is not None}")
        print(f"✅ 选股模式: {selector.mode}")

        # 执行选股
        test_date = pd.Timestamp('2023-06-15')
        selected_stocks = selector.select(test_date, prices)

        print(f"✅ 选股日期: {test_date.date()}")
        print(f"✅ 选出股票数: {len(selected_stocks)}")
        print(f"✅ 前10只股票: {selected_stocks[:10]}")

        # 步骤 4: 对比多因子加权
        print("\n[5/5] 对比多因子加权模式...")
        selector_weighted = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 20,
            'features': 'momentum_20d,rsi_14d,volatility_20d'
        })

        stocks_weighted = selector_weighted.select(test_date, prices)

        overlap = set(selected_stocks) & set(stocks_weighted)
        overlap_ratio = len(overlap) / max(len(selected_stocks), len(stocks_weighted))

        print(f"✅ 多因子加权: {len(stocks_weighted)} 只股票")
        print(f"✅ LightGBM: {len(selected_stocks)} 只股票")
        print(f"✅ 重叠率: {overlap_ratio:.1%}")

        # 验证成功
        print("\n" + "=" * 70)
        print("✅ ML-3 验证通过！所有功能正常工作。")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """主函数"""
    success = quick_test_ml3()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
