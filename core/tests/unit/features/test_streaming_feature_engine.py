"""
StreamingFeatureEngine 单元测试

测试内容:
- 流式特征计算基本功能
- 分批处理逻辑
- 断点续传功能
- 内存优化效果
- 不同输出格式

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil
import json
from datetime import datetime

from src.features.streaming_feature_engine import (
    StreamingFeatureEngine,
    StreamingConfig,
    StreamingStats
)


@pytest.fixture
def temp_output_dir():
    """创建临时输出目录"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_stock_data():
    """生成示例股票数据"""
    def create_stock_data(stock_code):
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(hash(stock_code) % (2**32))

        data = pd.DataFrame({
            'open': np.random.uniform(10, 20, 100),
            'high': np.random.uniform(15, 25, 100),
            'low': np.random.uniform(8, 15, 100),
            'close': np.random.uniform(10, 20, 100),
            'volume': np.random.uniform(1e6, 1e7, 100),
        }, index=dates)

        return data

    return create_stock_data


@pytest.fixture
def sample_feature_calculator():
    """简单的特征计算函数"""
    def calculate_features(df: pd.DataFrame) -> pd.DataFrame:
        features = pd.DataFrame(index=df.index)

        # 简单动量因子
        features['momentum_5'] = df['close'].pct_change(5)
        features['momentum_10'] = df['close'].pct_change(10)

        # 简单波动率
        features['volatility_10'] = df['close'].pct_change().rolling(10).std()

        # 成交量变化
        features['volume_change'] = df['volume'].pct_change()

        return features

    return calculate_features


class TestStreamingConfig:
    """测试流式配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = StreamingConfig()

        assert config.batch_size == 50
        assert config.output_format == 'parquet'
        assert config.compression == 'snappy'
        assert config.checkpoint_enabled is True
        assert config.auto_gc is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = StreamingConfig(
            batch_size=100,
            output_format='hdf5',
            compression='gzip',
            checkpoint_enabled=False
        )

        assert config.batch_size == 100
        assert config.output_format == 'hdf5'
        assert config.compression == 'gzip'
        assert config.checkpoint_enabled is False

    def test_config_validation(self):
        """测试配置验证"""
        # 有效配置
        config = StreamingConfig(batch_size=50)
        config.validate()  # 应该不抛出异常

        # 无效batch_size
        config_invalid = StreamingConfig(batch_size=0)
        with pytest.raises(AssertionError):
            config_invalid.validate()

        # 无效输出格式
        config_invalid_format = StreamingConfig(output_format='invalid')
        with pytest.raises(AssertionError):
            config_invalid_format.validate()


class TestStreamingStats:
    """测试统计信息"""

    def test_progress_calculation(self):
        """测试进度计算"""
        stats = StreamingStats(total_stocks=100, processed_stocks=50)

        assert stats.get_progress() == 50.0

        stats.processed_stocks = 75
        assert stats.get_progress() == 75.0

    def test_elapsed_time(self):
        """测试耗时计算"""
        stats = StreamingStats()
        stats.start_time = datetime(2023, 1, 1, 10, 0, 0)
        stats.end_time = datetime(2023, 1, 1, 10, 5, 30)

        assert stats.get_elapsed_time() == 330.0  # 5分30秒

    def test_to_dict(self):
        """测试转换为字典"""
        stats = StreamingStats(
            total_stocks=100,
            processed_stocks=95,
            failed_stocks=5,
            total_batches=10,
            completed_batches=10
        )

        result = stats.to_dict()

        assert result['total_stocks'] == 100
        assert result['processed_stocks'] == 95
        assert result['failed_stocks'] == 5
        assert result['success_rate'] == 0.95


class TestStreamingFeatureEngine:
    """测试流式特征计算引擎"""

    def test_initialization(self, temp_output_dir):
        """测试初始化"""
        engine = StreamingFeatureEngine(output_dir=temp_output_dir)

        assert engine.output_dir == temp_output_dir
        assert engine.config.batch_size == 50
        assert temp_output_dir.exists()

    def test_basic_streaming_computation(
        self,
        temp_output_dir,
        sample_stock_data,
        sample_feature_calculator
    ):
        """测试基本流式计算"""
        # 创建引擎
        config = StreamingConfig(
            batch_size=3,  # 小批次便于测试
            checkpoint_enabled=False  # 禁用checkpoint简化测试
        )
        engine = StreamingFeatureEngine(
            config=config,
            output_dir=temp_output_dir
        )

        # 准备数据
        stock_codes = [f"00000{i}.SZ" for i in range(1, 8)]  # 7只股票

        # 执行流式计算
        result_path = engine.compute_features_streaming(
            stock_codes=stock_codes,
            data_loader=sample_stock_data,
            feature_calculator=sample_feature_calculator
        )

        # 验证结果
        assert result_path.exists()
        assert result_path.suffix == '.parquet'

        # 读取结果
        features = pd.read_parquet(result_path)

        assert not features.empty
        assert 'stock_code' in features.columns
        assert 'momentum_5' in features.columns
        assert 'momentum_10' in features.columns
        assert len(features['stock_code'].unique()) == 7

        # 验证统计信息
        stats = engine.get_stats()
        assert stats.total_stocks == 7
        assert stats.processed_stocks == 7
        assert stats.failed_stocks == 0
        assert stats.total_batches == 3  # ceil(7/3) = 3

    def test_date_filtering(
        self,
        temp_output_dir,
        sample_stock_data,
        sample_feature_calculator
    ):
        """测试日期过滤"""
        config = StreamingConfig(batch_size=5, checkpoint_enabled=False)
        engine = StreamingFeatureEngine(
            config=config,
            output_dir=temp_output_dir
        )

        stock_codes = [f"00000{i}.SZ" for i in range(1, 6)]

        # 指定日期范围
        result_path = engine.compute_features_streaming(
            stock_codes=stock_codes,
            data_loader=sample_stock_data,
            feature_calculator=sample_feature_calculator,
            start_date='2023-02-01',
            end_date='2023-03-01'
        )

        # 读取结果
        features = pd.read_parquet(result_path)

        # 验证日期范围
        if 'date' in features.columns:
            features['date'] = pd.to_datetime(features['date'])
            assert features['date'].min() >= pd.Timestamp('2023-02-01')
            assert features['date'].max() <= pd.Timestamp('2023-03-01')

    def test_checkpoint_functionality(
        self,
        temp_output_dir,
        sample_stock_data,
        sample_feature_calculator
    ):
        """测试断点续传功能"""
        config = StreamingConfig(
            batch_size=2,
            checkpoint_enabled=True
        )
        engine = StreamingFeatureEngine(
            config=config,
            output_dir=temp_output_dir
        )

        stock_codes = [f"00000{i}.SZ" for i in range(1, 7)]  # 6只股票

        # 模拟中断：手动保存checkpoint
        checkpoint_file = temp_output_dir / ".checkpoint.json"
        checkpoint_data = {
            'completed_batches': [0, 1],  # 前两批已完成
            'timestamp': datetime.now().isoformat(),
            'stats': {}
        }
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f)

        # 创建假的批次文件（模拟已完成的批次）
        # 注意：列顺序必须匹配实际计算结果（特征列在前，stock_code和date在后）
        for batch_idx in [0, 1]:
            fake_df = pd.DataFrame({
                'momentum_5': [0.01],
                'momentum_10': [0.02],
                'volatility_10': [0.001],
                'volume_change': [0.05],
                'stock_code': [f'00000{batch_idx+1}.SZ'],
                'date': [pd.Timestamp('2023-01-01')]
            })
            # 确保列顺序正确
            fake_df = fake_df[['momentum_5', 'momentum_10', 'volatility_10', 'volume_change', 'stock_code', 'date']]
            batch_path = temp_output_dir / f"batch_{batch_idx:04d}.parquet"
            fake_df.to_parquet(batch_path, index=False)

        # 运行（应该跳过前两批）
        result_path = engine.compute_features_streaming(
            stock_codes=stock_codes,
            data_loader=sample_stock_data,
            feature_calculator=sample_feature_calculator
        )

        # 验证checkpoint被读取
        assert result_path.exists()

        # 验证统计
        stats = engine.get_stats()
        assert stats.completed_batches == 3  # 总共3批

    def test_different_output_formats(
        self,
        temp_output_dir,
        sample_stock_data,
        sample_feature_calculator
    ):
        """测试不同输出格式"""
        stock_codes = [f"00000{i}.SZ" for i in range(1, 4)]

        # 测试Parquet格式
        config_parquet = StreamingConfig(
            batch_size=5,
            output_format='parquet',
            checkpoint_enabled=False
        )
        engine_parquet = StreamingFeatureEngine(
            config=config_parquet,
            output_dir=temp_output_dir / 'parquet'
        )
        result_parquet = engine_parquet.compute_features_streaming(
            stock_codes=stock_codes,
            data_loader=sample_stock_data,
            feature_calculator=sample_feature_calculator
        )
        assert result_parquet.suffix == '.parquet'
        assert result_parquet.exists()

        # 测试CSV格式
        config_csv = StreamingConfig(
            batch_size=5,
            output_format='csv',
            compression='none',
            checkpoint_enabled=False
        )
        engine_csv = StreamingFeatureEngine(
            config=config_csv,
            output_dir=temp_output_dir / 'csv'
        )
        result_csv = engine_csv.compute_features_streaming(
            stock_codes=stock_codes,
            data_loader=sample_stock_data,
            feature_calculator=sample_feature_calculator
        )
        assert result_csv.suffix == '.csv'
        assert result_csv.exists()

    def test_error_handling(
        self,
        temp_output_dir,
        sample_stock_data,
        sample_feature_calculator
    ):
        """测试错误处理"""
        def failing_data_loader(code):
            if code == "000003.SZ":
                raise ValueError("模拟数据加载失败")
            return sample_stock_data(code)

        config = StreamingConfig(batch_size=2, checkpoint_enabled=False)
        engine = StreamingFeatureEngine(
            config=config,
            output_dir=temp_output_dir
        )

        stock_codes = ["000001.SZ", "000002.SZ", "000003.SZ", "000004.SZ"]

        # 执行（应该跳过失败的股票）
        result_path = engine.compute_features_streaming(
            stock_codes=stock_codes,
            data_loader=failing_data_loader,
            feature_calculator=sample_feature_calculator
        )

        # 验证：失败的股票被跳过
        features = pd.read_parquet(result_path)
        unique_stocks = features['stock_code'].unique()

        assert "000003.SZ" not in unique_stocks
        assert len(unique_stocks) == 3

        # 验证统计
        stats = engine.get_stats()
        assert stats.failed_stocks >= 1  # 至少有1只失败

    def test_memory_efficiency(
        self,
        temp_output_dir,
        sample_stock_data,
        sample_feature_calculator
    ):
        """测试内存效率（简单验证）"""
        config = StreamingConfig(
            batch_size=5,
            auto_gc=True,
            checkpoint_enabled=False
        )
        engine = StreamingFeatureEngine(
            config=config,
            output_dir=temp_output_dir
        )

        # 较多股票
        stock_codes = [f"{i:06d}.SZ" for i in range(1, 51)]  # 50只股票

        result_path = engine.compute_features_streaming(
            stock_codes=stock_codes,
            data_loader=sample_stock_data,
            feature_calculator=sample_feature_calculator
        )

        # 验证结果完整性
        features = pd.read_parquet(result_path)
        assert len(features['stock_code'].unique()) == 50

        # 验证峰值内存被记录
        stats = engine.get_stats()
        assert stats.peak_memory_mb > 0

    def test_empty_data_handling(
        self,
        temp_output_dir,
        sample_feature_calculator
    ):
        """测试空数据处理"""
        def empty_data_loader(code):
            return pd.DataFrame()  # 返回空DataFrame

        config = StreamingConfig(batch_size=5, checkpoint_enabled=False)
        engine = StreamingFeatureEngine(
            config=config,
            output_dir=temp_output_dir
        )

        stock_codes = ["000001.SZ", "000002.SZ"]

        result_path = engine.compute_features_streaming(
            stock_codes=stock_codes,
            data_loader=empty_data_loader,
            feature_calculator=sample_feature_calculator
        )

        # 应该创建空文件或没有数据
        if result_path.exists():
            features = pd.read_parquet(result_path)
            # 应该为空或没有有效数据
            assert len(features) == 0 or features.empty


@pytest.mark.integration
class TestStreamingFeatureEngineIntegration:
    """集成测试"""

    def test_end_to_end_workflow(
        self,
        temp_output_dir,
        sample_stock_data,
        sample_feature_calculator
    ):
        """端到端工作流测试"""
        # 模拟实际场景：100只股票，分10批处理
        config = StreamingConfig(
            batch_size=10,
            output_format='parquet',
            compression='snappy',
            checkpoint_enabled=True,
            auto_gc=True
        )

        engine = StreamingFeatureEngine(
            config=config,
            output_dir=temp_output_dir
        )

        stock_codes = [f"{i:06d}.SZ" for i in range(1, 101)]

        # 执行完整流程
        result_path = engine.compute_features_streaming(
            stock_codes=stock_codes,
            data_loader=sample_stock_data,
            feature_calculator=sample_feature_calculator,
            start_date='2023-01-01',
            end_date='2023-12-31'
        )

        # 验证结果
        assert result_path.exists()

        features = pd.read_parquet(result_path)
        assert not features.empty
        assert len(features['stock_code'].unique()) == 100

        # 验证特征列
        expected_features = ['momentum_5', 'momentum_10', 'volatility_10', 'volume_change']
        for feat in expected_features:
            assert feat in features.columns

        # 验证统计
        stats = engine.get_stats()
        assert stats.total_stocks == 100
        assert stats.processed_stocks == 100
        assert stats.total_batches == 10
        assert stats.completed_batches == 10
        assert stats.get_progress() == 100.0

        # 验证临时文件已清理
        batch_files = list(temp_output_dir.glob("batch_*.parquet"))
        assert len(batch_files) == 0  # 临时批次文件应该被清理

        # 验证checkpoint文件已清理
        checkpoint_file = temp_output_dir / ".checkpoint.json"
        assert not checkpoint_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
