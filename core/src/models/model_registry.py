"""
模型注册表和版本管理

提供模型的持久化、版本管理和元数据追踪功能：
1. 模型版本化存储
2. 元数据管理（训练时间、性能指标、特征列表等）
3. 模型加载和验证
4. 模型历史追踪

使用示例:
    from models import ModelRegistry

    # 创建注册表
    registry = ModelRegistry(base_dir='models')

    # 保存模型
    registry.save_model(
        model=my_model,
        name='lightgbm_v1',
        metadata={'train_ic': 0.95, 'test_ic': 0.92}
    )

    # 加载最新版本
    model = registry.load_model('lightgbm_v1')

    # 查看历史
    history = registry.get_model_history('lightgbm_v1')
"""

import pickle
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger
import pandas as pd


class ModelMetadata:
    """模型元数据类"""

    def __init__(
        self,
        model_name: str,
        version: int,
        timestamp: str,
        model_type: str,
        feature_names: Optional[List[str]] = None,
        performance_metrics: Optional[Dict[str, float]] = None,
        training_config: Optional[Dict] = None,
        description: str = ""
    ):
        """
        初始化元数据

        参数:
            model_name: 模型名称
            version: 版本号
            timestamp: 时间戳
            model_type: 模型类型（'ridge', 'lightgbm', 'gru', 'ensemble'）
            feature_names: 特征列表
            performance_metrics: 性能指标字典
            training_config: 训练配置
            description: 描述
        """
        self.model_name = model_name
        self.version = version
        self.timestamp = timestamp
        self.model_type = model_type
        self.feature_names = feature_names or []
        self.performance_metrics = performance_metrics or {}
        self.training_config = training_config or {}
        self.description = description

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'model_name': self.model_name,
            'version': self.version,
            'timestamp': self.timestamp,
            'model_type': self.model_type,
            'feature_names': self.feature_names,
            'performance_metrics': self.performance_metrics,
            'training_config': self.training_config,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelMetadata':
        """从字典创建"""
        return cls(**data)

    def __repr__(self):
        return (f"ModelMetadata(name={self.model_name}, "
                f"version={self.version}, "
                f"type={self.model_type}, "
                f"timestamp={self.timestamp})")


class ModelRegistry:
    """模型注册表"""

    def __init__(self, base_dir: str = 'model_registry'):
        """
        初始化模型注册表

        参数:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # 索引文件
        self.index_file = self.base_dir / 'index.json'
        self.index = self._load_index()

        logger.info(f"初始化模型注册表: {self.base_dir}")

    def _load_index(self) -> Dict:
        """加载索引文件"""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                return json.load(f)
        # 如果不存在，创建空索引文件
        empty_index = {}
        with open(self.index_file, 'w') as f:
            json.dump(empty_index, f, indent=2)
        return empty_index

    def _save_index(self):
        """保存索引文件"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)

    def _get_model_dir(self, model_name: str) -> Path:
        """获取模型目录"""
        model_dir = self.base_dir / model_name
        model_dir.mkdir(exist_ok=True)
        return model_dir

    def _get_next_version(self, model_name: str) -> int:
        """获取下一个版本号"""
        if model_name not in self.index:
            return 1

        versions = [v['version'] for v in self.index[model_name]]
        return max(versions) + 1 if versions else 1

    def save_model(
        self,
        model: Any,
        name: str,
        metadata: Optional[Dict] = None,
        model_type: str = 'unknown',
        description: str = "",
        auto_version: bool = True
    ):
        """
        保存模型

        参数:
            model: 模型对象
            name: 模型名称
            metadata: 元数据字典（性能指标等）
            model_type: 模型类型
            description: 描述
            auto_version: 是否自动版本号

        返回:
            Response对象，成功时data包含:
            {
                'model_name': 模型名称,
                'version': 版本号,
                'model_path': 模型文件路径,
                'metadata_path': 元数据文件路径
            }
        """
        from src.utils.response import Response
        import time

        try:
            start_time = time.time()

            # 获取版本号
            version = self._get_next_version(name) if auto_version else 1

            # 创建模型目录
            model_dir = self._get_model_dir(name)

            # 保存模型文件
            model_path = model_dir / f'v{version}_model.pkl'
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)

            logger.info(f"保存模型: {name} v{version} -> {model_path}")

            # 提取特征名（如果可用）
            feature_names = None
            if hasattr(model, 'feature_names_'):
                feature_names = model.feature_names_
            elif hasattr(model, 'model') and hasattr(model.model, 'feature_name_'):
                feature_names = model.model.feature_name_()

            # 创建元数据
            model_metadata = ModelMetadata(
                model_name=name,
                version=version,
                timestamp=datetime.now().isoformat(),
                model_type=model_type,
                feature_names=feature_names,
                performance_metrics=metadata or {},
                training_config=getattr(model, 'config', {}),
                description=description
            )

            # 保存元数据
            metadata_path = model_dir / f'v{version}_metadata.json'
            with open(metadata_path, 'w') as f:
                json.dump(model_metadata.to_dict(), f, indent=2)

            # 更新索引
            if name not in self.index:
                self.index[name] = []

            self.index[name].append({
                'version': version,
                'timestamp': model_metadata.timestamp,
                'model_path': str(model_path),
                'metadata_path': str(metadata_path)
            })

            self._save_index()

            elapsed_time = time.time() - start_time
            logger.info(f"✓ 模型保存成功: {name} v{version}")

            return Response.success(
                data={
                    'model_name': name,
                    'version': version,
                    'model_path': str(model_path),
                    'metadata_path': str(metadata_path)
                },
                message=f"模型保存成功: {name} v{version}",
                model_type=model_type,
                n_features=len(feature_names) if feature_names else 0,
                elapsed_time=f"{elapsed_time:.2f}s"
            )

        except Exception as e:
            logger.exception(f"保存模型时发生异常: {e}")
            return Response.error(
                error=f"保存模型失败: {str(e)}",
                error_code="MODEL_SAVE_ERROR",
                model_name=name,
                model_type=model_type
            )

    def load_model(
        self,
        name: str,
        version: Optional[int] = None
    ):
        """
        加载模型

        参数:
            name: 模型名称
            version: 版本号（None=最新版本）

        返回:
            Response对象，成功时data包含:
            {
                'model': 模型对象,
                'metadata': 元数据对象
            }
        """
        from src.utils.response import Response
        import time

        try:
            start_time = time.time()

            if name not in self.index:
                return Response.error(
                    error=f"模型不存在: {name}",
                    error_code="MODEL_NOT_FOUND",
                    model_name=name,
                    available_models=list(self.index.keys())
                )

            # 获取版本
            if version is None:
                # 加载最新版本
                versions = sorted(self.index[name], key=lambda x: x['version'])
                model_info = versions[-1]
                version_type = "latest"
            else:
                # 加载指定版本
                model_info = next(
                    (m for m in self.index[name] if m['version'] == version),
                    None
                )
                if model_info is None:
                    available_versions = [m['version'] for m in self.index[name]]
                    return Response.error(
                        error=f"版本不存在: {name} v{version}",
                        error_code="VERSION_NOT_FOUND",
                        model_name=name,
                        requested_version=version,
                        available_versions=available_versions
                    )
                version_type = "specified"

            # 加载模型
            model_path = Path(model_info['model_path'])
            with open(model_path, 'rb') as f:
                model = pickle.load(f)

            # 加载元数据
            metadata_path = Path(model_info['metadata_path'])
            with open(metadata_path, 'r') as f:
                metadata = ModelMetadata.from_dict(json.load(f))

            elapsed_time = time.time() - start_time
            logger.info(f"加载模型: {name} v{metadata.version}")

            return Response.success(
                data={
                    'model': model,
                    'metadata': metadata
                },
                message=f"模型加载成功: {name} v{metadata.version}",
                model_name=name,
                version=metadata.version,
                version_type=version_type,
                model_type=metadata.model_type,
                elapsed_time=f"{elapsed_time:.2f}s"
            )

        except FileNotFoundError as e:
            return Response.error(
                error=f"模型文件不存在: {str(e)}",
                error_code="MODEL_FILE_NOT_FOUND",
                model_name=name,
                version=version
            )
        except Exception as e:
            logger.exception(f"加载模型时发生异常: {e}")
            return Response.error(
                error=f"加载模型失败: {str(e)}",
                error_code="MODEL_LOAD_ERROR",
                model_name=name,
                version=version
            )

    def get_model_history(self, name: str) -> pd.DataFrame:
        """
        获取模型历史

        参数:
            name: 模型名称

        返回:
            history_df: 历史记录DataFrame
        """
        if name not in self.index:
            raise ValueError(f"模型不存在: {name}")

        history = []
        for model_info in self.index[name]:
            # 加载元数据
            metadata_path = Path(model_info['metadata_path'])
            with open(metadata_path, 'r') as f:
                metadata = ModelMetadata.from_dict(json.load(f))

            # 提取关键信息
            record = {
                'version': metadata.version,
                'timestamp': metadata.timestamp,
                'model_type': metadata.model_type,
                'description': metadata.description,
                **metadata.performance_metrics
            }
            history.append(record)

        return pd.DataFrame(history)

    def list_models(self) -> pd.DataFrame:
        """
        列出所有模型

        返回:
            models_df: 模型列表DataFrame
        """
        models = []

        for name in self.index.keys():
            # 获取最新版本信息
            latest = max(self.index[name], key=lambda x: x['version'])

            metadata_path = Path(latest['metadata_path'])
            with open(metadata_path, 'r') as f:
                metadata = ModelMetadata.from_dict(json.load(f))

            models.append({
                'name': name,
                'latest_version': metadata.version,
                'model_type': metadata.model_type,
                'last_updated': metadata.timestamp,
                'n_versions': len(self.index[name])
            })

        return pd.DataFrame(models)

    def delete_version(self, name: str, version: int):
        """
        删除指定版本

        参数:
            name: 模型名称
            version: 版本号
        """
        if name not in self.index:
            raise ValueError(f"模型不存在: {name}")

        # 找到版本
        model_info = next(
            (m for m in self.index[name] if m['version'] == version),
            None
        )

        if model_info is None:
            raise ValueError(f"版本不存在: {name} v{version}")

        # 删除文件
        model_path = Path(model_info['model_path'])
        metadata_path = Path(model_info['metadata_path'])

        if model_path.exists():
            model_path.unlink()

        if metadata_path.exists():
            metadata_path.unlink()

        # 更新索引
        self.index[name] = [
            m for m in self.index[name] if m['version'] != version
        ]

        # 如果没有版本了，删除模型条目
        if not self.index[name]:
            del self.index[name]

            # 删除目录
            model_dir = self._get_model_dir(name)
            if model_dir.exists():
                shutil.rmtree(model_dir)

        self._save_index()

        logger.info(f"✓ 删除版本: {name} v{version}")

    def delete_model(self, name: str):
        """
        删除模型（所有版本）

        参数:
            name: 模型名称
        """
        if name not in self.index:
            raise ValueError(f"模型不存在: {name}")

        # 删除目录
        model_dir = self._get_model_dir(name)
        if model_dir.exists():
            shutil.rmtree(model_dir)

        # 更新索引
        del self.index[name]
        self._save_index()

        logger.info(f"✓ 删除模型: {name} (所有版本)")

    def compare_versions(
        self,
        name: str,
        version1: int,
        version2: int
    ):
        """
        对比两个版本

        参数:
            name: 模型名称
            version1: 版本1
            version2: 版本2

        返回:
            Response对象，成功时data包含对比结果
        """
        from src.utils.response import Response

        try:
            # 加载两个版本的元数据
            response1 = self.load_model(name, version1)
            if not response1.is_success():
                return response1

            response2 = self.load_model(name, version2)
            if not response2.is_success():
                return response2

            metadata1 = response1.data['metadata']
            metadata2 = response2.data['metadata']

            comparison = {
                'version1': {
                    'version': metadata1.version,
                    'timestamp': metadata1.timestamp,
                    'metrics': metadata1.performance_metrics
                },
                'version2': {
                    'version': metadata2.version,
                    'timestamp': metadata2.timestamp,
                    'metrics': metadata2.performance_metrics
                },
                'metric_diff': {}
            }

            # 计算指标差异
            for metric in metadata1.performance_metrics.keys():
                if metric in metadata2.performance_metrics:
                    diff = (metadata2.performance_metrics[metric] -
                            metadata1.performance_metrics[metric])
                    comparison['metric_diff'][metric] = diff

            return Response.success(
                data=comparison,
                message=f"版本对比完成: {name} v{version1} vs v{version2}",
                model_name=name
            )

        except Exception as e:
            logger.exception(f"对比版本时发生异常: {e}")
            return Response.error(
                error=f"对比版本失败: {str(e)}",
                error_code="VERSION_COMPARE_ERROR",
                model_name=name,
                version1=version1,
                version2=version2
            )

    def export_model(self, name: str, version: Optional[int], output_path: str):
        """
        导出模型（模型文件+元数据）

        参数:
            name: 模型名称
            version: 版本号（None=最新）
            output_path: 输出路径

        返回:
            Response对象，成功时data包含导出路径信息
        """
        from src.utils.response import Response

        try:
            response = self.load_model(name, version)
            if not response.is_success():
                return response

            model = response.data['model']
            metadata = response.data['metadata']

            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            # 保存模型
            model_path = output_dir / f'{name}_v{metadata.version}.pkl'
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)

            # 保存元数据
            metadata_path = output_dir / f'{name}_v{metadata.version}_metadata.json'
            with open(metadata_path, 'w') as f:
                json.dump(metadata.to_dict(), f, indent=2)

            logger.info(f"✓ 导出模型到: {output_dir}")

            return Response.success(
                data={
                    'output_dir': str(output_dir),
                    'model_path': str(model_path),
                    'metadata_path': str(metadata_path)
                },
                message=f"模型导出成功: {name} v{metadata.version}",
                model_name=name,
                version=metadata.version
            )

        except Exception as e:
            logger.exception(f"导出模型时发生异常: {e}")
            return Response.error(
                error=f"导出模型失败: {str(e)}",
                error_code="MODEL_EXPORT_ERROR",
                model_name=name,
                version=version
            )

    def __repr__(self):
        n_models = len(self.index)
        n_versions = sum(len(v) for v in self.index.values())
        return f"ModelRegistry(base_dir={self.base_dir}, models={n_models}, versions={n_versions})"
