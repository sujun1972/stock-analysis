"""
模型注册表 (ModelRegistry) 单元测试

测试范围：
1. ModelMetadata - 元数据类（创建、序列化、反序列化）
2. ModelRegistry - 注册表主类
   - 模型保存（版本化、元数据管理）
   - 模型加载（最新版本、指定版本）
   - 模型历史查询
   - 版本对比
   - 模型删除
   - 模型导出
3. 边界情况和异常处理
4. 文件系统操作

目标覆盖率: 90%+

作者: Stock Analysis Team
创建: 2026-01-29
"""

import pytest
import pandas as pd
import numpy as np
import pickle
import json
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
import tempfile

# 导入模块
try:
    from src.models.model_registry import ModelRegistry, ModelMetadata
except ImportError:
    import sys
    core_path = Path(__file__).parent.parent.parent
    if str(core_path) not in sys.path:
        sys.path.insert(0, str(core_path))
    from src.models.model_registry import ModelRegistry, ModelMetadata


# ==================== 测试用模型类 ====================

class DummyModel:
    """可序列化的测试模型类

    用于替代 unittest.mock.Mock，因为 Mock 对象无法被 pickle 序列化。
    提供模型的基本接口（feature_names_, predict()），可以被 ModelRegistry 正常保存和加载。

    Attributes:
        feature_names_: 特征名称列表，模拟真实模型的 feature_names_ 属性
        _prediction_value: 预测返回值，用于测试模型功能是否正常
        trained: 标记模型已训练，模拟训练状态
    """

    def __init__(self, feature_names=None, prediction_value=None):
        """初始化测试模型

        Args:
            feature_names: 特征名称列表，默认 ['feature_0', 'feature_1', 'feature_2']
            prediction_value: 预测返回值，默认为随机数组
        """
        # 使用 is not None 而非 or，避免 numpy 数组的布尔判断错误
        self.feature_names_ = feature_names if feature_names is not None else ['feature_0', 'feature_1', 'feature_2']
        self._prediction_value = prediction_value if prediction_value is not None else np.random.randn(10)
        self.trained = True

    def predict(self, X=None):
        """模拟预测方法

        Args:
            X: 输入特征（本测试中不使用）

        Returns:
            预设的预测值
        """
        return self._prediction_value

    def __repr__(self):
        """字符串表示"""
        return f"DummyModel(features={len(self.feature_names_)})"


# ==================== Fixtures ====================

@pytest.fixture
def temp_registry_dir():
    """创建临时注册表目录"""
    temp_dir = tempfile.mkdtemp(prefix='test_registry_')
    yield temp_dir
    # 清理
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def registry(temp_registry_dir):
    """创建测试用的 ModelRegistry 实例"""
    return ModelRegistry(base_dir=temp_registry_dir)


@pytest.fixture
def sample_model():
    """创建示例模型（可序列化的 DummyModel）"""
    return DummyModel(
        feature_names=['feature_0', 'feature_1', 'feature_2'],
        prediction_value=np.array([1.0, 2.0, 3.0])
    )


@pytest.fixture
def sample_metadata():
    """创建示例元数据"""
    return ModelMetadata(
        model_name='test_model',
        version=1,
        timestamp='2026-01-29T10:00:00',
        model_type='lightgbm',
        feature_names=['feature_0', 'feature_1', 'feature_2'],
        performance_metrics={'train_ic': 0.95, 'test_ic': 0.92},
        training_config={'n_estimators': 100, 'learning_rate': 0.05},
        description='测试模型'
    )


# ==================== ModelMetadata 测试 ====================

class TestModelMetadata:
    """ModelMetadata 元数据类测试"""

    def test_metadata_creation(self):
        """测试元数据创建"""
        metadata = ModelMetadata(
            model_name='lgb_model',
            version=1,
            timestamp='2026-01-29T10:00:00',
            model_type='lightgbm'
        )

        assert metadata.model_name == 'lgb_model'
        assert metadata.version == 1
        assert metadata.model_type == 'lightgbm'
        assert metadata.feature_names == []
        assert metadata.performance_metrics == {}

    def test_metadata_with_all_fields(self, sample_metadata):
        """测试包含所有字段的元数据"""
        assert sample_metadata.model_name == 'test_model'
        assert sample_metadata.version == 1
        assert len(sample_metadata.feature_names) == 3
        assert sample_metadata.performance_metrics['train_ic'] == 0.95
        assert sample_metadata.training_config['n_estimators'] == 100

    def test_metadata_to_dict(self, sample_metadata):
        """测试元数据转换为字典"""
        data = sample_metadata.to_dict()

        assert isinstance(data, dict)
        assert data['model_name'] == 'test_model'
        assert data['version'] == 1
        assert data['model_type'] == 'lightgbm'
        assert 'feature_names' in data
        assert 'performance_metrics' in data

    def test_metadata_from_dict(self):
        """测试从字典创建元数据"""
        data = {
            'model_name': 'ridge_model',
            'version': 2,
            'timestamp': '2026-01-29T12:00:00',
            'model_type': 'ridge',
            'feature_names': ['f1', 'f2'],
            'performance_metrics': {'ic': 0.88},
            'training_config': {},
            'description': 'Ridge baseline'
        }

        metadata = ModelMetadata.from_dict(data)

        assert metadata.model_name == 'ridge_model'
        assert metadata.version == 2
        assert metadata.model_type == 'ridge'
        assert len(metadata.feature_names) == 2

    def test_metadata_repr(self, sample_metadata):
        """测试元数据字符串表示"""
        repr_str = repr(sample_metadata)

        assert 'test_model' in repr_str
        assert 'version=1' in repr_str
        assert 'lightgbm' in repr_str


# ==================== ModelRegistry 初始化测试 ====================

class TestModelRegistryInit:
    """ModelRegistry 初始化测试"""

    def test_registry_creation(self, temp_registry_dir):
        """测试注册表创建"""
        registry = ModelRegistry(base_dir=temp_registry_dir)

        assert registry.base_dir == Path(temp_registry_dir)
        assert registry.base_dir.exists()
        assert registry.index_file.exists()
        assert isinstance(registry.index, dict)

    def test_registry_default_base_dir(self):
        """测试默认基础目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            import os
            original_cwd = os.getcwd()
            os.chdir(temp_dir)

            try:
                registry = ModelRegistry()
                assert registry.base_dir.name == 'model_registry'
                assert registry.base_dir.exists()
            finally:
                os.chdir(original_cwd)
                if Path('model_registry').exists():
                    shutil.rmtree('model_registry')

    def test_registry_loads_existing_index(self, temp_registry_dir):
        """测试加载现有索引"""
        # 创建第一个注册表并保存模型
        registry1 = ModelRegistry(base_dir=temp_registry_dir)
        model = DummyModel()
        registry1.save_model(model, 'model1', model_type='test')

        # 创建第二个注册表，应该加载相同的索引
        registry2 = ModelRegistry(base_dir=temp_registry_dir)

        assert 'model1' in registry2.index
        assert len(registry2.index['model1']) == 1

    def test_registry_repr(self, registry):
        """测试注册表字符串表示"""
        # 保存两个模型
        model1 = DummyModel()
        model2 = DummyModel()
        registry.save_model(model1, 'model1', model_type='type1')
        registry.save_model(model2, 'model2', model_type='type2')

        repr_str = repr(registry)

        assert 'ModelRegistry' in repr_str
        assert 'models=2' in repr_str
        assert 'versions=2' in repr_str


# ==================== 模型保存测试 ====================

class TestModelSave:
    """模型保存测试"""

    def test_save_simple_model(self, registry, sample_model):
        """测试保存简单模型"""
        name, version = registry.save_model(
            model=sample_model,
            name='simple_model',
            model_type='test'
        )

        assert name == 'simple_model'
        assert version == 1
        assert 'simple_model' in registry.index
        assert len(registry.index['simple_model']) == 1

    def test_save_model_with_metadata(self, registry, sample_model):
        """测试保存带元数据的模型"""
        metadata = {
            'train_ic': 0.95,
            'test_ic': 0.92,
            'train_date': '2026-01-29'
        }

        name, version = registry.save_model(
            model=sample_model,
            name='model_with_meta',
            metadata=metadata,
            model_type='lightgbm',
            description='生产模型'
        )

        # 加载并验证
        _, loaded_meta = registry.load_model('model_with_meta')

        assert loaded_meta.performance_metrics['train_ic'] == 0.95
        assert loaded_meta.model_type == 'lightgbm'
        assert loaded_meta.description == '生产模型'

    def test_save_multiple_versions(self, registry, sample_model):
        """测试保存多个版本"""
        # 保存版本1
        name1, version1 = registry.save_model(sample_model, 'multi_ver', model_type='v1')
        # 保存版本2
        name2, version2 = registry.save_model(sample_model, 'multi_ver', model_type='v2')
        # 保存版本3
        name3, version3 = registry.save_model(sample_model, 'multi_ver', model_type='v3')

        assert version1 == 1
        assert version2 == 2
        assert version3 == 3
        assert len(registry.index['multi_ver']) == 3

    def test_save_creates_directory_structure(self, registry, sample_model):
        """测试保存创建正确的目录结构"""
        registry.save_model(sample_model, 'test_structure', model_type='test')

        model_dir = registry.base_dir / 'test_structure'
        assert model_dir.exists()
        assert (model_dir / 'v1_model.pkl').exists()
        assert (model_dir / 'v1_metadata.json').exists()

    def test_save_extracts_feature_names(self, registry):
        """测试自动提取特征名"""
        model = DummyModel(feature_names=['f1', 'f2', 'f3'])

        registry.save_model(model, 'feature_model', model_type='test')

        _, metadata = registry.load_model('feature_model')
        assert metadata.feature_names == ['f1', 'f2', 'f3']

    def test_save_updates_index(self, registry, sample_model):
        """测试保存更新索引文件"""
        registry.save_model(sample_model, 'index_test', model_type='test')

        # 读取索引文件
        with open(registry.index_file, 'r') as f:
            index_data = json.load(f)

        assert 'index_test' in index_data
        assert len(index_data['index_test']) == 1


# ==================== 模型加载测试 ====================

class TestModelLoad:
    """模型加载测试"""

    def test_load_latest_version(self, registry, sample_model):
        """测试加载最新版本"""
        # 保存3个版本
        for i in range(3):
            registry.save_model(
                sample_model,
                'versioned_model',
                metadata={'version_info': f'v{i+1}'},
                model_type='test'
            )

        # 加载最新版本
        model, metadata = registry.load_model('versioned_model')

        assert metadata.version == 3
        assert metadata.performance_metrics['version_info'] == 'v3'

    def test_load_specific_version(self, registry, sample_model):
        """测试加载指定版本"""
        # 保存3个版本
        for i in range(3):
            registry.save_model(
                sample_model,
                'specific_ver',
                metadata={'ver': i+1},
                model_type='test'
            )

        # 加载版本2
        model, metadata = registry.load_model('specific_ver', version=2)

        assert metadata.version == 2
        assert metadata.performance_metrics['ver'] == 2

    def test_load_nonexistent_model(self, registry):
        """测试加载不存在的模型"""
        with pytest.raises(ValueError, match="模型不存在"):
            registry.load_model('nonexistent_model')

    def test_load_nonexistent_version(self, registry, sample_model):
        """测试加载不存在的版本"""
        registry.save_model(sample_model, 'test_model', model_type='test')

        with pytest.raises(ValueError, match="版本不存在"):
            registry.load_model('test_model', version=99)

    def test_load_preserves_model_functionality(self, registry):
        """测试加载后模型功能正常"""
        # 创建一个有实际功能的模型
        original_model = DummyModel(prediction_value=np.array([1.0, 2.0, 3.0]))

        registry.save_model(original_model, 'func_test', model_type='test')

        # 加载并测试
        loaded_model, _ = registry.load_model('func_test')

        result = loaded_model.predict()
        np.testing.assert_array_equal(result, [1.0, 2.0, 3.0])


# ==================== 模型历史测试 ====================

class TestModelHistory:
    """模型历史测试"""

    def test_get_model_history(self, registry, sample_model):
        """测试获取模型历史"""
        # 保存3个版本，每个版本有不同的性能
        for i in range(3):
            registry.save_model(
                sample_model,
                'history_model',
                metadata={'ic': 0.9 + i * 0.01, 'epoch': i+1},
                model_type='lightgbm',
                description=f'Version {i+1}'
            )

        history = registry.get_model_history('history_model')

        assert isinstance(history, pd.DataFrame)
        assert len(history) == 3
        assert 'version' in history.columns
        assert 'timestamp' in history.columns
        assert 'ic' in history.columns
        assert list(history['version']) == [1, 2, 3]

    def test_history_contains_all_metrics(self, registry, sample_model):
        """测试历史包含所有性能指标"""
        metadata = {
            'train_ic': 0.95,
            'valid_ic': 0.93,
            'test_ic': 0.91,
            'mse': 0.001
        }

        registry.save_model(
            sample_model,
            'metrics_model',
            metadata=metadata,
            model_type='test'
        )

        history = registry.get_model_history('metrics_model')

        assert 'train_ic' in history.columns
        assert 'valid_ic' in history.columns
        assert 'test_ic' in history.columns
        assert 'mse' in history.columns

    def test_history_nonexistent_model(self, registry):
        """测试获取不存在模型的历史"""
        with pytest.raises(ValueError, match="模型不存在"):
            registry.get_model_history('nonexistent')


# ==================== 模型列表测试 ====================

class TestListModels:
    """模型列表测试"""

    def test_list_empty_registry(self, registry):
        """测试列出空注册表"""
        models = registry.list_models()

        assert isinstance(models, pd.DataFrame)
        assert len(models) == 0

    def test_list_multiple_models(self, registry, sample_model):
        """测试列出多个模型"""
        # 保存3个不同的模型
        registry.save_model(sample_model, 'model1', model_type='lightgbm')
        registry.save_model(sample_model, 'model2', model_type='ridge')
        registry.save_model(sample_model, 'model3', model_type='gru')

        models = registry.list_models()

        assert len(models) == 3
        assert 'name' in models.columns
        assert 'latest_version' in models.columns
        assert 'model_type' in models.columns
        assert set(models['name']) == {'model1', 'model2', 'model3'}

    def test_list_shows_version_count(self, registry, sample_model):
        """测试列表显示版本数量"""
        # 为一个模型保存3个版本
        for i in range(3):
            registry.save_model(sample_model, 'multi_ver', model_type='test')

        models = registry.list_models()

        model_info = models[models['name'] == 'multi_ver'].iloc[0]
        assert model_info['n_versions'] == 3
        assert model_info['latest_version'] == 3


# ==================== 版本对比测试 ====================

class TestCompareVersions:
    """版本对比测试"""

    def test_compare_two_versions(self, registry, sample_model):
        """测试对比两个版本"""
        # 保存两个版本
        registry.save_model(
            sample_model, 'compare_test',
            metadata={'ic': 0.90, 'mse': 0.002},
            model_type='test'
        )
        registry.save_model(
            sample_model, 'compare_test',
            metadata={'ic': 0.92, 'mse': 0.0015},
            model_type='test'
        )

        comparison = registry.compare_versions('compare_test', 1, 2)

        assert 'version1' in comparison
        assert 'version2' in comparison
        assert 'metric_diff' in comparison
        assert comparison['version1']['version'] == 1
        assert comparison['version2']['version'] == 2

    def test_compare_metric_differences(self, registry, sample_model):
        """测试指标差异计算"""
        registry.save_model(
            sample_model, 'diff_test',
            metadata={'ic': 0.90, 'rmse': 0.05},
            model_type='test'
        )
        registry.save_model(
            sample_model, 'diff_test',
            metadata={'ic': 0.95, 'rmse': 0.04},
            model_type='test'
        )

        comparison = registry.compare_versions('diff_test', 1, 2)

        assert comparison['metric_diff']['ic'] == pytest.approx(0.05)
        assert comparison['metric_diff']['rmse'] == pytest.approx(-0.01)

    def test_compare_nonexistent_versions(self, registry, sample_model):
        """测试对比不存在的版本"""
        registry.save_model(sample_model, 'test', model_type='test')

        with pytest.raises(ValueError):
            registry.compare_versions('test', 1, 99)


# ==================== 删除操作测试 ====================

class TestDeleteOperations:
    """删除操作测试"""

    def test_delete_specific_version(self, registry, sample_model):
        """测试删除特定版本"""
        # 保存3个版本
        for i in range(3):
            registry.save_model(sample_model, 'del_test', model_type='test')

        # 删除版本2
        registry.delete_version('del_test', 2)

        # 验证
        assert len(registry.index['del_test']) == 2
        history = registry.get_model_history('del_test')
        assert 2 not in history['version'].values

    def test_delete_last_version_removes_model(self, registry, sample_model):
        """测试删除最后一个版本会移除模型"""
        registry.save_model(sample_model, 'single_ver', model_type='test')

        registry.delete_version('single_ver', 1)

        assert 'single_ver' not in registry.index
        assert not (registry.base_dir / 'single_ver').exists()

    def test_delete_entire_model(self, registry, sample_model):
        """测试删除整个模型"""
        # 保存3个版本
        for i in range(3):
            registry.save_model(sample_model, 'del_all', model_type='test')

        registry.delete_model('del_all')

        assert 'del_all' not in registry.index
        assert not (registry.base_dir / 'del_all').exists()

    def test_delete_nonexistent_model(self, registry):
        """测试删除不存在的模型"""
        with pytest.raises(ValueError, match="模型不存在"):
            registry.delete_model('nonexistent')

    def test_delete_nonexistent_version(self, registry):
        """测试删除不存在的版本"""
        model = DummyModel()
        registry.save_model(model, 'test', model_type='test')

        with pytest.raises(ValueError, match="版本不存在"):
            registry.delete_version('test', 99)


# ==================== 导出操作测试 ====================

class TestExportModel:
    """导出模型测试"""

    def test_export_latest_version(self, registry, sample_model, temp_registry_dir):
        """测试导出最新版本"""
        registry.save_model(
            sample_model, 'export_test',
            metadata={'ic': 0.95},
            model_type='lightgbm'
        )

        export_dir = Path(temp_registry_dir) / 'exports'
        registry.export_model('export_test', version=None, output_path=str(export_dir))

        assert export_dir.exists()
        assert (export_dir / 'export_test_v1.pkl').exists()
        assert (export_dir / 'export_test_v1_metadata.json').exists()

    def test_export_specific_version(self, registry, sample_model, temp_registry_dir):
        """测试导出指定版本"""
        # 保存2个版本
        registry.save_model(sample_model, 'export_ver', model_type='test')
        registry.save_model(sample_model, 'export_ver', model_type='test')

        export_dir = Path(temp_registry_dir) / 'exports_v1'
        registry.export_model('export_ver', version=1, output_path=str(export_dir))

        assert (export_dir / 'export_ver_v1.pkl').exists()
        assert (export_dir / 'export_ver_v1_metadata.json').exists()

    def test_export_preserves_metadata(self, registry, sample_model, temp_registry_dir):
        """测试导出保留元数据"""
        metadata = {'train_ic': 0.95, 'test_ic': 0.92}
        registry.save_model(
            sample_model, 'meta_export',
            metadata=metadata,
            model_type='lightgbm',
            description='测试导出'
        )

        export_dir = Path(temp_registry_dir) / 'meta_exports'
        registry.export_model('meta_export', version=None, output_path=str(export_dir))

        # 读取导出的元数据
        meta_file = export_dir / 'meta_export_v1_metadata.json'
        with open(meta_file, 'r') as f:
            exported_meta = json.load(f)

        assert exported_meta['performance_metrics']['train_ic'] == 0.95
        assert exported_meta['model_type'] == 'lightgbm'
        assert exported_meta['description'] == '测试导出'


# ==================== 边界情况和异常处理测试 ====================

class TestEdgeCases:
    """边界情况测试"""

    def test_save_model_with_empty_name(self, registry, sample_model):
        """测试空名称"""
        # 这应该正常工作，因为Python允许空字符串作为字典键
        name, version = registry.save_model(sample_model, '', model_type='test')
        assert name == ''
        assert version == 1

    def test_save_model_with_special_characters(self, registry, sample_model):
        """测试特殊字符名称"""
        # 某些特殊字符可能在文件系统中有问题
        special_name = 'model-2024_v1.0'
        name, version = registry.save_model(sample_model, special_name, model_type='test')

        assert name == special_name
        assert version == 1

        # 验证可以加载
        loaded_model, _ = registry.load_model(special_name)
        assert loaded_model is not None

    def test_metadata_with_none_values(self):
        """测试 None 值的元数据"""
        metadata = ModelMetadata(
            model_name='none_test',
            version=1,
            timestamp='2026-01-29',
            model_type='test',
            feature_names=None,
            performance_metrics=None
        )

        data = metadata.to_dict()
        restored = ModelMetadata.from_dict(data)

        assert restored.feature_names == []
        assert restored.performance_metrics == {}

    def test_concurrent_save_operations(self, registry, sample_model):
        """测试并发保存操作（简单测试）"""
        # 快速连续保存多个版本
        for i in range(10):
            registry.save_model(sample_model, 'concurrent', model_type='test')

        assert len(registry.index['concurrent']) == 10
        versions = [v['version'] for v in registry.index['concurrent']]
        assert versions == list(range(1, 11))

    def test_registry_persistence_across_instances(self, temp_registry_dir, sample_model):
        """测试注册表跨实例持久化"""
        # 第一个实例：保存模型
        registry1 = ModelRegistry(base_dir=temp_registry_dir)
        registry1.save_model(sample_model, 'persist_test', model_type='test')

        # 第二个实例：验证可以访问
        registry2 = ModelRegistry(base_dir=temp_registry_dir)
        model, metadata = registry2.load_model('persist_test')

        assert model is not None
        assert metadata.model_name == 'persist_test'

    def test_large_metadata(self, registry, sample_model):
        """测试大型元数据"""
        # 创建包含大量信息的元数据
        large_metadata = {
            f'metric_{i}': np.random.rand() for i in range(100)
        }

        registry.save_model(
            sample_model, 'large_meta',
            metadata=large_metadata,
            model_type='test'
        )

        # 验证可以正确加载
        _, loaded_meta = registry.load_model('large_meta')
        assert len(loaded_meta.performance_metrics) == 100


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试 - 完整工作流"""

    def test_complete_model_lifecycle(self, registry, sample_model):
        """测试完整的模型生命周期"""
        # 1. 保存初始版本
        name, v1 = registry.save_model(
            sample_model, 'lifecycle',
            metadata={'ic': 0.90},
            model_type='lightgbm',
            description='初始版本'
        )
        assert v1 == 1

        # 2. 保存改进版本
        _, v2 = registry.save_model(
            sample_model, 'lifecycle',
            metadata={'ic': 0.92},
            model_type='lightgbm',
            description='改进版本'
        )
        assert v2 == 2

        # 3. 查看历史
        history = registry.get_model_history('lifecycle')
        assert len(history) == 2

        # 4. 对比版本
        comparison = registry.compare_versions('lifecycle', 1, 2)
        assert comparison['metric_diff']['ic'] == pytest.approx(0.02)

        # 5. 列出所有模型
        models = registry.list_models()
        assert 'lifecycle' in models['name'].values

        # 6. 加载最新版本
        model, metadata = registry.load_model('lifecycle')
        assert metadata.version == 2
        assert metadata.description == '改进版本'

        # 7. 加载旧版本
        old_model, old_meta = registry.load_model('lifecycle', version=1)
        assert old_meta.version == 1
        assert old_meta.description == '初始版本'

    def test_multi_model_management(self, registry, sample_model):
        """测试多模型管理"""
        models_config = [
            ('ridge_baseline', 'ridge', {'ic': 0.85}),
            ('lightgbm_v1', 'lightgbm', {'ic': 0.92}),
            ('lightgbm_v2', 'lightgbm', {'ic': 0.94}),
            ('gru_model', 'gru', {'ic': 0.91})
        ]

        # 保存所有模型
        for name, model_type, metadata in models_config:
            registry.save_model(
                sample_model, name,
                metadata=metadata,
                model_type=model_type
            )

        # 验证
        all_models = registry.list_models()
        assert len(all_models) == 4

        # 找到最佳模型
        best_model = None
        best_ic = 0
        for name, model_type, metadata in models_config:
            _, meta = registry.load_model(name)
            if meta.performance_metrics['ic'] > best_ic:
                best_ic = meta.performance_metrics['ic']
                best_model = name

        assert best_model == 'lightgbm_v2'
        assert best_ic == 0.94


# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试"""

    def test_save_load_speed(self, registry, sample_model):
        """测试保存和加载速度"""
        import time

        # 测试保存
        start = time.time()
        for i in range(10):
            registry.save_model(sample_model, f'perf_test_{i}', model_type='test')
        save_time = time.time() - start

        # 测试加载
        start = time.time()
        for i in range(10):
            registry.load_model(f'perf_test_{i}')
        load_time = time.time() - start

        # 基本性能断言（应该很快）
        assert save_time < 5.0  # 10个模型保存应该在5秒内
        assert load_time < 5.0  # 10个模型加载应该在5秒内

    def test_index_query_speed(self, registry, sample_model):
        """测试索引查询速度"""
        # 创建多个模型和版本
        for i in range(5):
            for j in range(3):
                registry.save_model(sample_model, f'query_test_{i}', model_type='test')

        import time
        start = time.time()

        # 执行多次查询
        for _ in range(100):
            registry.list_models()

        query_time = time.time() - start

        # 100次查询应该很快
        assert query_time < 1.0


# ==================== 运行测试 ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
