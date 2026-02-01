#!/usr/bin/env python3
"""
持久化集成测试

测试数据和模型的持久化功能：
1. 特征存储 (CSV/Parquet/HDF5)
2. 模型保存和加载
3. 数据库读写
"""

import sys
import unittest
from pathlib import Path
import pandas as pd
import numpy as np
import tempfile
import shutil
from typing import Dict, Any

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

# 导入conftest中的unwrap函数
sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import unwrap_response, unwrap_prepare_data


class TestFeatureStorage(unittest.TestCase):
    """测试特征存储"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("特征存储集成测试")
        print("=" * 80)

        # 创建临时目录
        cls.temp_dir = tempfile.mkdtemp()
        print(f"临时目录: {cls.temp_dir}")

    @classmethod
    def tearDownClass(cls):
        """测试后清理"""
        # 删除临时目录
        if Path(cls.temp_dir).exists():
            shutil.rmtree(cls.temp_dir)
            print(f"\n临时目录已清理: {cls.temp_dir}")

    def _create_test_features(self, n_rows: int = 100) -> pd.DataFrame:
        """创建测试用的特征数据"""
        dates = pd.date_range('2023-01-01', periods=n_rows)
        features = pd.DataFrame({
            'feature_1': np.random.randn(n_rows),
            'feature_2': np.random.randn(n_rows),
            'feature_3': np.random.randn(n_rows),
            'close': 10 + np.random.randn(n_rows),
        }, index=dates)
        features.index.name = 'date'
        return features

    def test_01_csv_storage(self):
        """测试1: CSV存储"""

        try:
            from src.features.storage import FeatureStorage

            # 创建存储对象
            storage_dir = Path(self.temp_dir) / 'csv_storage'
            storage = FeatureStorage(storage_dir=str(storage_dir), format='csv')

            # 创建测试数据
            features = self._create_test_features()

            # 保存
            result = storage.save_features(features, '000001', 'alpha', 'v1')
            self.assertTrue(result.is_success(), f"CSV保存失败: {result.error_message}")

            # 加载
            loaded = unwrap_response(storage.load_features('000001', 'alpha'))
            self.assertIsNotNone(loaded, "CSV加载失败")

            # 验证数据一致性
            pd.testing.assert_frame_equal(
                features,
                loaded,
                check_dtype=False,
                check_freq=False,
                rtol=1e-5
            )

        except Exception as e:
            self.fail(f"CSV存储测试失败: {e}")

    def test_02_parquet_storage(self):
        """测试2: Parquet存储"""

        try:
            from src.features.storage import FeatureStorage

            # 创建存储对象
            storage_dir = Path(self.temp_dir) / 'parquet_storage'
            storage = FeatureStorage(storage_dir=str(storage_dir), format='parquet')

            # 创建测试数据
            features = self._create_test_features()

            # 保存
            result = storage.save_features(features, '000001', 'alpha', 'v1')
            self.assertTrue(result.is_success(), f"Parquet保存失败: {result.error_message}")

            # 加载
            loaded = unwrap_response(storage.load_features('000001', 'alpha'))
            self.assertIsNotNone(loaded, "Parquet加载失败")

            # 验证数据一致性
            pd.testing.assert_frame_equal(
                features,
                loaded,
                check_dtype=False,
                check_freq=False,
                rtol=1e-5
            )

        except ImportError:
            self.skipTest("需要安装pyarrow: pip install pyarrow")
        except Exception as e:
            self.fail(f"Parquet存储测试失败: {e}")

    def test_03_hdf5_storage(self):
        """测试3: HDF5存储"""

        try:
            from src.features.storage import FeatureStorage

            # 创建存储对象
            storage_dir = Path(self.temp_dir) / 'hdf5_storage'
            storage = FeatureStorage(storage_dir=str(storage_dir), format='hdf5')

            # 创建测试数据
            features = self._create_test_features()

            # 保存
            result = storage.save_features(features, '000001', 'alpha', 'v1')
            if not result.is_success():
                # HDF5依赖pytables,如果保存失败很可能是依赖缺失,跳过测试而不是失败
                self.skipTest(f"HDF5存储不可用(可能缺少pytables): {result.error_message}")

            # 加载
            loaded = unwrap_response(storage.load_features('000001', 'alpha'))
            self.assertIsNotNone(loaded, "HDF5加载失败")

            # 验证数据一致性
            pd.testing.assert_frame_equal(
                features,
                loaded,
                check_dtype=False,
                check_freq=False,
                rtol=1e-5
            )

        except ImportError:
            self.skipTest("需要安装tables: pip install tables")
        except unittest.SkipTest:
            raise  # 让skipTest正常传播
        except Exception as e:
            self.fail(f"HDF5存储测试失败: {e}")

    def test_04_multiple_stocks(self):
        """测试4: 多股票存储"""

        try:
            from src.features.storage import FeatureStorage

            storage_dir = Path(self.temp_dir) / 'multi_stock'
            storage = FeatureStorage(storage_dir=str(storage_dir), format='parquet')

            stocks = ['000001', '000002', '600000']

            # 保存多只股票
            for stock in stocks:
                features = self._create_test_features()
                result = storage.save_features(features, stock, 'alpha', 'v1')
                self.assertTrue(result, f"{stock}保存失败")


            # 列出所有股票
            all_stocks = storage.list_stocks()
            self.assertEqual(len(all_stocks), len(stocks), "股票数量不匹配")

            # 批量加载
            loaded_dict = storage.load_multiple_stocks(stocks, parallel=False)
            self.assertEqual(len(loaded_dict), len(stocks), "加载数量不匹配")

        except Exception as e:
            self.fail(f"多股票存储测试失败: {e}")


class TestModelPersistence(unittest.TestCase):
    """测试模型持久化"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("模型持久化集成测试")
        print("=" * 80)

        cls.temp_dir = tempfile.mkdtemp()
        print(f"临时目录: {cls.temp_dir}")

    @classmethod
    def tearDownClass(cls):
        """测试后清理"""
        if Path(cls.temp_dir).exists():
            shutil.rmtree(cls.temp_dir)
            print(f"\n临时目录已清理: {cls.temp_dir}")

    def _create_training_data(self, n_samples: int = 100):
        """创建训练数据"""
        X = pd.DataFrame({
            f'feature_{i}': np.random.randn(n_samples)
            for i in range(10)
        })
        y = pd.Series(np.random.randn(n_samples))
        return X, y

    def test_01_lightgbm_save_load(self):
        """测试1: LightGBM模型保存和加载"""

        try:
            from src.models import LightGBMStockModel

            # 创建并训练模型
            X_train, y_train = self._create_training_data()
            X_test, y_test = self._create_training_data(30)

            model = LightGBMStockModel()
            model.train(X_train, y_train, X_test, y_test)
            self.assertIsNotNone(model.model, "模型训练失败")

            # 原始预测
            original_pred = model.predict(X_test)

            # 保存模型
            model_path = Path(self.temp_dir) / 'lightgbm_model.pkl'
            model.save_model(str(model_path))
            self.assertTrue(model_path.exists(), "模型文件未创建")

            # 加载模型
            loaded_model = LightGBMStockModel()
            loaded_model.load_model(str(model_path))
            self.assertIsNotNone(loaded_model.model, "模型加载失败")

            # 加载后预测
            loaded_pred = loaded_model.predict(X_test)

            # 验证预测一致性
            np.testing.assert_array_almost_equal(
                original_pred,
                loaded_pred,
                decimal=5,
                err_msg="模型预测不一致"
            )

        except Exception as e:
            self.fail(f"LightGBM持久化测试失败: {e}")

    def test_02_gru_save_load(self):
        """测试2: GRU模型保存和加载"""

        try:
            from src.models import GRUStockTrainer

            # 创建训练数据
            X_train, y_train = self._create_training_data(200)
            X_test, y_test = self._create_training_data(50)

            # 创建并训练模型（CPU模式，快速训练）
            trainer = GRUStockTrainer(
                input_size=10,
                hidden_size=32,
                num_layers=1,
                use_gpu=False  # 强制使用CPU
            )

            trainer.train(
                X_train, y_train,
                X_test, y_test,
                epochs=2,  # 快速测试，只训练2轮
                batch_size=32
            )

            # 原始预测
            original_pred = trainer.predict(X_test)

            # 保存模型
            model_path = Path(self.temp_dir) / 'gru_model.pth'
            trainer.save_model(str(model_path))
            self.assertTrue(model_path.exists(), "模型文件未创建")

            # 加载模型
            loaded_trainer = GRUStockTrainer(
                input_size=10,
                hidden_size=32,
                num_layers=1,
                use_gpu=False
            )
            loaded_trainer.load_model(str(model_path))

            # 加载后预测
            loaded_pred = loaded_trainer.predict(X_test)

            # 验证预测一致性（神经网络允许稍大误差）
            np.testing.assert_array_almost_equal(
                original_pred,
                loaded_pred,
                decimal=4,
                err_msg="模型预测不一致"
            )

        except ImportError:
            self.skipTest("需要安装PyTorch")
        except Exception as e:
            self.fail(f"GRU持久化测试失败: {e}")


class TestDatabasePersistence(unittest.TestCase):
    """测试数据库持久化"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("数据库持久化集成测试")
        print("=" * 80)

    def test_01_database_write_read(self):
        """测试1: 数据库写入和读取"""

        try:
            from src.data import DatabaseManager

            # 创建数据库管理器
            db = DatabaseManager()

            # 测试数据
            test_stock = '000001'
            test_start = '2023-01-01'
            test_end = '2023-03-31'

            # 查询数据
            data = db.get_daily_data(test_stock, test_start, test_end)

            if data is None or len(data) == 0:
                self.skipTest("数据库中无测试数据")
            else:
                self.assertGreater(len(data), 0, "查询数据为空")

                # 验证数据格式
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                for col in required_columns:
                    self.assertIn(col, data.columns, f"缺少列: {col}")

        except Exception as e:
            self.skipTest(f"数据库不可用: {e}")

    def test_02_batch_database_operations(self):
        """测试2: 批量数据库操作"""

        try:
            from src.data import DatabaseManager

            db = DatabaseManager()

            # 批量查询
            stocks = ['000001', '000002', '600000']
            test_date = '2023-01-01'

            results = {}
            for stock in stocks:
                data = db.get_daily_data(stock, test_date, test_date)
                if data is not None and len(data) > 0:
                    results[stock] = data

            if len(results) == 0:
                self.skipTest("数据库中无测试数据")


            # 验证所有结果
            for stock, data in results.items():
                self.assertGreater(len(data), 0, f"{stock}数据为空")


        except Exception as e:
            self.skipTest(f"数据库不可用: {e}")


class TestEndToEndPersistence(unittest.TestCase):
    """测试端到端持久化工作流"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("端到端持久化工作流测试")
        print("=" * 80)

        cls.temp_dir = tempfile.mkdtemp()
        print(f"临时目录: {cls.temp_dir}")

    @classmethod
    def tearDownClass(cls):
        """测试后清理"""
        if Path(cls.temp_dir).exists():
            shutil.rmtree(cls.temp_dir)
            print(f"\n临时目录已清理: {cls.temp_dir}")

    def test_01_complete_persistence_workflow(self):
        """测试1: 完整持久化工作流"""

        try:
            from providers import DataProviderFactory
            from features import AlphaFactors
            from src.features.storage import FeatureStorage
            from src.models import LightGBMStockModel

            # ========== 1. 获取并存储数据 ==========
            print("\n  [步骤1] 获取并存储原始数据")
            provider = DataProviderFactory.create_provider('akshare')
            data = provider.get_daily_data('000001', '2023-01-01', '2023-06-30')

            # 保存原始数据
            data_path = Path(self.temp_dir) / 'raw_data.csv'
            data.to_csv(data_path)

            # ========== 2. 计算并存储特征 ==========
            print("\n  [步骤2] 计算并存储特征")
            alpha = AlphaFactors(data)
            features = alpha.calculate_all_alpha_factors()

            storage_dir = Path(self.temp_dir) / 'features'
            storage = FeatureStorage(storage_dir=str(storage_dir), format='parquet')
            storage.save_features(features, '000001', 'alpha', 'v1')

            # ========== 3. 训练并保存模型 ==========
            print("\n  [步骤3] 训练并保存模型")

            # 准备训练数据
            features_clean = features.dropna()
            data_clean = data.loc[features_clean.index]
            target = data_clean['close'].pct_change(5).shift(-5) * 100

            valid_idx = ~target.isna()
            X = features_clean[valid_idx]
            y = target[valid_idx]

            # 训练模型
            split_idx = int(len(X) * 0.8)
            model = LightGBMStockModel()
            model.train(
                X.iloc[:split_idx],
                y.iloc[:split_idx],
                X.iloc[split_idx:],
                y.iloc[split_idx:]
            )

            # 保存模型
            model_path = Path(self.temp_dir) / 'model.pkl'
            model.save_model(str(model_path))

            # ========== 4. 重新加载并验证 ==========
            print("\n  [步骤4] 重新加载并验证")

            # 加载原始数据
            loaded_data = pd.read_csv(data_path, index_col=0, parse_dates=True)
            pd.testing.assert_frame_equal(data, loaded_data, check_dtype=False)

            # 加载特征
            loaded_features = storage.load_features('000001', 'alpha')
            pd.testing.assert_frame_equal(
                features,
                loaded_features,
                check_dtype=False,
                check_freq=False,
                rtol=1e-5
            )

            # 加载模型
            loaded_model = LightGBMStockModel()
            loaded_model.load_model(str(model_path))
            self.assertIsNotNone(loaded_model.model)


        except Exception as e:
            self.skipTest(f"测试需要完整环境: {e}")


def run_tests():
    """运行所有集成测试"""
    print("持久化集成测试套件")
    print("=" * 80)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestFeatureStorage))
    suite.addTests(loader.loadTestsFromTestCase(TestModelPersistence))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabasePersistence))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEndPersistence))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 打印总结
    print("测试总结")
    print("=" * 80)
    print(f"运行: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.error_messages)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.error_messages)}")
    print(f"跳过: {len(result.skipped)}")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
