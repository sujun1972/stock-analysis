#!/usr/bin/env python3
"""
数据库和模型训练性能基准测试

测试目标（基于REFACTORING_PLAN.md任务1.2.4和1.2.5）:

数据库性能:
- 单股票查询: <10ms
- 批量查询(100股): <500ms
- 特征存储写入: <1秒/1000行

模型训练性能:
- LightGBM训练: <10秒 (10万样本×125特征)
- GRU训练(CPU): <60秒
- GRU训练(GPU): <5秒

作者: Stock Analysis Team
创建: 2026-01-31
"""

import sys
import time
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import os

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from .benchmarks import (
    PerformanceBenchmarkBase,
    PerformanceThresholds,
    print_benchmark_header,
    print_benchmark_result,
    performance_reporter,
    generate_features_data,
    generate_target_data,
)


# ==================== 数据库性能测试 ====================


class TestDatabasePerformance(PerformanceBenchmarkBase):
    """数据库操作性能测试"""

    @pytest.fixture(scope='class')
    def temp_database(self):
        """创建临时数据库用于测试"""
        try:
            from data.database_manager import DatabaseManager

            # 创建临时数据库
            temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            db_path = temp_db.name
            temp_db.close()

            # 初始化数据库
            db_manager = DatabaseManager(db_path=db_path)

            # 插入测试数据
            self._insert_test_data(db_manager)

            yield db_manager

            # 清理
            db_manager.close()
            os.unlink(db_path)

        except ImportError:
            pytest.skip("DatabaseManager不可用")

    def _insert_test_data(self, db_manager):
        """插入测试数据"""
        dates = pd.date_range('2023-01-01', periods=250, freq='D')

        # 插入100只股票的数据
        for stock_id in range(100):
            stock_code = f'{stock_id:06d}'

            # 生成价格数据
            returns = np.random.normal(0.0005, 0.02, 250)
            prices = 100 * (1 + returns).cumprod()

            data = pd.DataFrame({
                'stock_code': stock_code,
                'date': dates,
                'open': prices * 0.99,
                'high': prices * 1.02,
                'low': prices * 0.98,
                'close': prices,
                'volume': np.random.uniform(1e6, 1e7, 250),
            })

            db_manager.insert_daily_data(data)

    def test_single_stock_query_benchmark(self, temp_database):
        """
        测试单股票查询性能

        性能目标: <10ms (基于REFACTORING_PLAN.md)
        """
        print_benchmark_header("单股票查询性能测试")

        db_manager = temp_database

        # 执行查询
        start = time.time()
        data = db_manager.query_stock_data('000001', '2023-01-01', '2023-12-31')
        elapsed = time.time() - start

        # 验证结果
        assert len(data) > 0

        # 性能断言
        threshold = PerformanceThresholds.DB_SINGLE_QUERY
        elapsed_ms = elapsed * 1000

        print_benchmark_result(
            f"单股票查询 ({len(data)}行)",
            elapsed,
            threshold
        )
        print(f"  查询时间: {elapsed_ms:.2f}ms")

        performance_reporter.add_result(
            category="数据库性能",
            test_name="单股票查询",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={'n_rows': len(data), 'elapsed_ms': f"{elapsed_ms:.2f}ms"}
        )

        self.assert_performance(
            elapsed,
            threshold,
            "单股票查询",
            {'n_rows': len(data), 'elapsed_ms': f"{elapsed_ms:.2f}ms"}
        )

    def test_batch_query_100_stocks_benchmark(self, temp_database):
        """
        测试批量查询100股性能

        性能目标: <500ms (基于REFACTORING_PLAN.md)
        """
        print_benchmark_header("批量查询100股性能测试")

        db_manager = temp_database

        # 批量查询
        stock_codes = [f'{i:06d}' for i in range(100)]

        start = time.time()
        results = []
        for stock_code in stock_codes:
            data = db_manager.query_stock_data(stock_code, '2023-01-01', '2023-12-31')
            results.append(data)
        elapsed = time.time() - start

        total_rows = sum(len(df) for df in results)

        # 性能断言
        threshold = PerformanceThresholds.DB_BATCH_QUERY_100
        elapsed_ms = elapsed * 1000

        print_benchmark_result(
            f"批量查询100股 (总计{total_rows}行)",
            elapsed,
            threshold
        )
        print(f"  平均单股: {elapsed_ms/100:.2f}ms")

        performance_reporter.add_result(
            category="数据库性能",
            test_name="批量查询100股",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={'n_stocks': 100, 'total_rows': total_rows}
        )

        self.assert_performance(
            elapsed,
            threshold,
            "批量查询100股",
            {'n_stocks': 100, 'total_rows': total_rows}
        )

    def test_feature_write_1000_rows_benchmark(self, temp_database):
        """
        测试特征写入性能

        性能目标: <1秒/1000行 (基于REFACTORING_PLAN.md)
        """
        print_benchmark_header("特征写入性能测试")

        db_manager = temp_database

        # 生成1000行特征数据
        features_data = generate_features_data(n_samples=1000, n_features=50)
        features_data['stock_code'] = '000001'
        features_data['date'] = pd.date_range('2023-01-01', periods=1000, freq='D')

        # 写入
        start = time.time()
        db_manager.insert_features(features_data)
        elapsed = time.time() - start

        # 性能断言
        threshold = PerformanceThresholds.DB_FEATURE_WRITE_1000

        print_benchmark_result(
            f"特征写入 ({len(features_data)}行×{len(features_data.columns)}列)",
            elapsed,
            threshold
        )

        performance_reporter.add_result(
            category="数据库性能",
            test_name="特征写入1000行",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={'n_rows': len(features_data), 'n_features': len(features_data.columns)}
        )

        self.assert_performance(
            elapsed,
            threshold,
            "特征写入1000行",
            {'n_rows': len(features_data)}
        )


# ==================== LightGBM训练性能测试 ====================


class TestLightGBMPerformance(PerformanceBenchmarkBase):
    """LightGBM模型训练性能测试"""

    def test_lightgbm_training_100k_samples(self, model_training_data):
        """
        测试LightGBM训练性能 - 10万样本

        性能目标: <10秒 (基于REFACTORING_PLAN.md)
        """
        print_benchmark_header("LightGBM训练性能测试 - 10万样本×125特征")

        X, y = model_training_data

        try:
            from models.lightgbm_model import LightGBMStockModel

            # 训练集/测试集划分
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # 训练
            start = time.time()
            model = LightGBMStockModel()
            model.train(X_train, y_train, X_test, y_test)
            elapsed = time.time() - start

            # 验证模型已训练
            assert model.model is not None

            # 性能断言
            threshold = PerformanceThresholds.LIGHTGBM_TRAIN_100K

            print_benchmark_result(
                f"LightGBM训练 ({len(X_train)}样本×{len(X_train.columns)}特征)",
                elapsed,
                threshold
            )

            performance_reporter.add_result(
                category="模型训练",
                test_name="LightGBM训练(10万样本)",
                elapsed=elapsed,
                threshold=threshold,
                passed=elapsed < threshold,
                details={'n_samples': len(X_train), 'n_features': len(X_train.columns)}
            )

            self.assert_performance(
                elapsed,
                threshold,
                "LightGBM训练(10万样本)",
                {'n_samples': len(X_train), 'n_features': len(X_train.columns)}
            )

        except ImportError:
            pytest.skip("LightGBMStockModel不可用")

    def test_lightgbm_training_small(self, model_training_data_small):
        """测试小规模LightGBM训练性能"""
        print_benchmark_header("LightGBM训练性能测试 - 1万样本×125特征")

        X, y = model_training_data_small

        try:
            from models.lightgbm_model import LightGBMStockModel

            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            start = time.time()
            model = LightGBMStockModel()
            model.train(X_train, y_train, X_test, y_test)
            elapsed = time.time() - start

            threshold = 2.0  # 小规模2秒内

            print_benchmark_result(
                f"LightGBM训练 ({len(X_train)}样本×{len(X_train.columns)}特征)",
                elapsed,
                threshold
            )

            performance_reporter.add_result(
                category="模型训练",
                test_name="LightGBM训练(1万样本)",
                elapsed=elapsed,
                threshold=threshold,
                passed=elapsed < threshold,
                details={'n_samples': len(X_train), 'n_features': len(X_train.columns)}
            )

            self.assert_performance(
                elapsed,
                threshold,
                "LightGBM训练(1万样本)",
                {'n_samples': len(X_train)}
            )

        except ImportError:
            pytest.skip("LightGBMStockModel不可用")

    def test_lightgbm_prediction_benchmark(self, model_training_data_small):
        """测试LightGBM预测性能"""
        print_benchmark_header("LightGBM预测性能测试")

        X, y = model_training_data_small

        try:
            from models.lightgbm_model import LightGBMStockModel

            # 训练模型
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            model = LightGBMStockModel()
            model.train(X_train, y_train, X_test, y_test)

            # 测试预测
            start = time.time()
            predictions = model.predict(X_test)
            elapsed = time.time() - start

            threshold = 0.1  # 预测应该很快

            print_benchmark_result(
                f"LightGBM预测 ({len(X_test)}样本)",
                elapsed,
                threshold
            )

            performance_reporter.add_result(
                category="模型训练",
                test_name="LightGBM预测",
                elapsed=elapsed,
                threshold=threshold,
                passed=elapsed < threshold,
                details={'n_samples': len(X_test)}
            )

            self.assert_performance(
                elapsed,
                threshold,
                "LightGBM预测",
                {'n_samples': len(X_test)}
            )

        except ImportError:
            pytest.skip("LightGBMStockModel不可用")


# ==================== GRU模型训练性能测试 ====================


class TestGRUPerformance(PerformanceBenchmarkBase):
    """GRU模型训练性能测试"""

    def test_gru_training_cpu_benchmark(self):
        """
        测试GRU CPU训练性能

        性能目标: <60秒 (基于REFACTORING_PLAN.md)
        """
        print_benchmark_header("GRU训练性能测试 - CPU")

        try:
            from models.gru_model import GRUStockModel
            import torch

            # 生成序列数据（小规模以加快测试）
            n_samples = 1000
            seq_length = 20
            n_features = 50

            X = np.random.randn(n_samples, seq_length, n_features).astype(np.float32)
            y = np.random.randn(n_samples).astype(np.float32)

            # 训练（CPU）
            start = time.time()
            model = GRUStockModel(
                input_size=n_features,
                hidden_size=64,
                num_layers=2
            )
            # 使用CPU设备
            device = torch.device('cpu')
            model = model.to(device)

            # 创建训练器并训练
            from models.gru_model import GRUTrainer
            trainer = GRUTrainer(model, device=device)
            trainer.train(X, y, epochs=10, batch_size=32)
            elapsed = time.time() - start

            # 性能断言（小规模数据，调整阈值）
            threshold = 30.0  # 小规模30秒内

            print_benchmark_result(
                f"GRU训练-CPU ({n_samples}样本×{seq_length}序列×{n_features}特征)",
                elapsed,
                threshold
            )

            performance_reporter.add_result(
                category="模型训练",
                test_name="GRU训练(CPU)",
                elapsed=elapsed,
                threshold=threshold,
                passed=elapsed < threshold,
                details={'n_samples': n_samples, 'device': 'CPU'}
            )

            self.assert_performance(
                elapsed,
                threshold,
                "GRU训练(CPU)",
                {'n_samples': n_samples}
            )

        except ImportError:
            pytest.skip("GRUStockModel或PyTorch不可用")

    def test_gru_training_gpu_benchmark(self):
        """
        测试GRU GPU训练性能

        性能目标: <5秒 (基于REFACTORING_PLAN.md)
        """
        print_benchmark_header("GRU训练性能测试 - GPU")

        try:
            from models.gru_model import GRUStockModel
            import torch

            # 检查GPU是否可用
            if not torch.cuda.is_available():
                pytest.skip("CUDA不可用，跳过GPU测试")

            # 生成序列数据
            n_samples = 1000
            seq_length = 20
            n_features = 50

            X = np.random.randn(n_samples, seq_length, n_features).astype(np.float32)
            y = np.random.randn(n_samples).astype(np.float32)

            # 训练（GPU）
            start = time.time()
            model = GRUStockModel(
                input_size=n_features,
                hidden_size=64,
                num_layers=2
            )
            # 使用GPU设备
            device = torch.device('cuda')
            model = model.to(device)

            # 创建训练器并训练
            from models.gru_model import GRUTrainer
            trainer = GRUTrainer(model, device=device)
            trainer.train(X, y, epochs=10, batch_size=32)
            elapsed = time.time() - start

            threshold = PerformanceThresholds.GRU_TRAIN_GPU

            print_benchmark_result(
                f"GRU训练-GPU ({n_samples}样本×{seq_length}序列×{n_features}特征)",
                elapsed,
                threshold
            )

            performance_reporter.add_result(
                category="模型训练",
                test_name="GRU训练(GPU)",
                elapsed=elapsed,
                threshold=threshold,
                passed=elapsed < threshold,
                details={'n_samples': n_samples, 'device': 'GPU'}
            )

            self.assert_performance(
                elapsed,
                threshold,
                "GRU训练(GPU)",
                {'n_samples': n_samples}
            )

        except ImportError:
            pytest.skip("GRUStockModel或PyTorch不可用")


# ==================== 特征存储性能测试 ====================


class TestFeatureStoragePerformance(PerformanceBenchmarkBase):
    """特征存储性能测试"""

    def test_csv_write_benchmark(self):
        """测试CSV写入性能"""
        print_benchmark_header("CSV写入性能测试")

        # 生成测试数据
        data = generate_features_data(n_samples=10000, n_features=125)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as f:
            temp_file = f.name

        try:
            start = time.time()
            data.to_csv(temp_file, index=False)
            elapsed = time.time() - start

            threshold = 2.0
            print_benchmark_result(
                f"CSV写入 ({len(data)}行×{len(data.columns)}列)",
                elapsed,
                threshold
            )

            performance_reporter.add_result(
                category="数据存储",
                test_name="CSV写入",
                elapsed=elapsed,
                threshold=threshold,
                passed=elapsed < threshold,
                details={'n_rows': len(data), 'n_cols': len(data.columns)}
            )

            self.assert_performance(elapsed, threshold, "CSV写入")

        finally:
            os.unlink(temp_file)

    def test_parquet_write_benchmark(self):
        """测试Parquet写入性能"""
        print_benchmark_header("Parquet写入性能测试")

        data = generate_features_data(n_samples=10000, n_features=125)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as f:
            temp_file = f.name

        try:
            start = time.time()
            data.to_parquet(temp_file, index=False)
            elapsed = time.time() - start

            threshold = 1.0  # Parquet应该更快
            print_benchmark_result(
                f"Parquet写入 ({len(data)}行×{len(data.columns)}列)",
                elapsed,
                threshold
            )

            performance_reporter.add_result(
                category="数据存储",
                test_name="Parquet写入",
                elapsed=elapsed,
                threshold=threshold,
                passed=elapsed < threshold,
                details={'n_rows': len(data), 'n_cols': len(data.columns)}
            )

            self.assert_performance(elapsed, threshold, "Parquet写入")

        finally:
            os.unlink(temp_file)


if __name__ == '__main__':
    # 运行性能测试
    pytest.main([__file__, '-v', '--tb=short'])
