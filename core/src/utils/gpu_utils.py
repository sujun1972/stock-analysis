"""
GPU环境检测与管理工具

提供自动设备选择、内存管理、性能监控功能

功能:
    - GPU环境检测和系统信息获取
    - 自动设备选择（GPU/CPU）
    - GPU内存监控和管理
    - 自动批次大小计算
    - LightGBM GPU支持检测
    - 内存监控装饰器
    - 上下文管理器自动内存清理

作者: Stock Analysis Team
创建: 2026-01-30
"""

import platform
import functools
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from loguru import logger

try:
    import torch
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    logger.warning("PyTorch未安装，GPU功能将不可用")


@dataclass
class GPUConfig:
    """GPU配置"""
    enabled: bool = True  # 是否启用GPU
    device_id: int = 0  # GPU设备ID
    memory_fraction: float = 0.8  # 最大内存占用比例
    allow_growth: bool = True  # 是否允许动态增长


class GPUManager:
    """
    GPU环境管理器（单例模式）

    提供GPU检测、设备选择、内存管理等功能

    属性:
        config: GPU配置对象
        cuda_available: CUDA是否可用
        device_count: GPU设备数量
        device_name: GPU设备名称
        cuda_version: CUDA版本

    示例:
        >>> from src.utils.gpu_utils import gpu_manager
        >>> device = gpu_manager.get_device()
        >>> print(f"使用设备: {device}")
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.config = GPUConfig()
            self._check_environment()
            self._initialized = True

    def _check_environment(self):
        """检查GPU环境"""
        if not PYTORCH_AVAILABLE:
            self.cuda_available = False
            self.mps_available = False
            self.device_count = 0
            self.device_name = "N/A"
            self.cuda_version = "N/A"
            return

        self.cuda_available = torch.cuda.is_available()
        self.mps_available = hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()

        if self.cuda_available:
            self.device_count = torch.cuda.device_count()
            self.device_name = torch.cuda.get_device_name(0)
            self.cuda_version = torch.version.cuda
            logger.info(f"✅ NVIDIA GPU可用: {self.device_name} (CUDA {self.cuda_version})")
            logger.info(f"   设备数量: {self.device_count}")
        elif self.mps_available:
            self.device_count = 1
            self.device_name = "Apple GPU (MPS)"
            self.cuda_version = "N/A"
            logger.info(f"✅ Apple GPU可用: Metal Performance Shaders")
            logger.info(f"   适用于Apple Silicon (M1/M2/M3)")
        else:
            self.device_count = 0
            self.device_name = "N/A"
            self.cuda_version = "N/A"
            logger.warning("⚠️  GPU不可用，将使用CPU模式")

    def get_device(self, prefer_gpu: bool = True) -> str:
        """
        自动选择计算设备

        参数:
            prefer_gpu: 是否优先使用GPU

        返回:
            设备名称 ('cuda', 'mps' 或 'cpu')

        示例:
            >>> device = gpu_manager.get_device()
            >>> print(device)  # 'cuda:0', 'mps' 或 'cpu'
        """
        if not PYTORCH_AVAILABLE:
            return "cpu"

        if prefer_gpu and self.config.enabled:
            # 优先CUDA GPU
            if self.cuda_available:
                device = f"cuda:{self.config.device_id}"
                logger.debug(f"使用NVIDIA GPU设备: {device}")
                return device
            # 其次Apple MPS
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                logger.debug("使用Apple GPU (MPS)设备")
                return "mps"

        logger.debug("使用CPU设备")
        return "cpu"

    def get_memory_info(self, device_id: int = 0) -> Dict[str, float]:
        """
        获取GPU内存信息

        参数:
            device_id: GPU设备ID

        返回:
            内存信息字典（单位：GB）
            - total_gb: 总内存
            - allocated_gb: 已分配内存
            - reserved_gb: 已保留内存
            - free_gb: 可用内存
            - utilization: 使用率（百分比）

        示例:
            >>> mem = gpu_manager.get_memory_info()
            >>> print(f"GPU使用率: {mem['utilization']:.1f}%")
        """
        if not PYTORCH_AVAILABLE or not self.cuda_available:
            return {}

        total = torch.cuda.get_device_properties(device_id).total_memory / 1e9
        allocated = torch.cuda.memory_allocated(device_id) / 1e9
        reserved = torch.cuda.memory_reserved(device_id) / 1e9
        free = total - allocated

        return {
            "total_gb": round(total, 2),
            "allocated_gb": round(allocated, 2),
            "reserved_gb": round(reserved, 2),
            "free_gb": round(free, 2),
            "utilization": round(allocated / total * 100, 2) if total > 0 else 0
        }

    def clear_cache(self):
        """
        清空GPU缓存

        示例:
            >>> gpu_manager.clear_cache()
            >>> print("GPU缓存已清空")
        """
        if PYTORCH_AVAILABLE and self.cuda_available:
            torch.cuda.empty_cache()
            logger.debug("GPU缓存已清空")

    def get_optimal_batch_size(
        self,
        model_size_mb: float,
        sample_size_mb: float,
        safety_factor: float = 0.7
    ) -> int:
        """
        估算最优批次大小

        参数:
            model_size_mb: 模型大小（MB）
            sample_size_mb: 单个样本大小（MB）
            safety_factor: 安全系数（0-1），预留部分内存

        返回:
            推荐的批次大小

        示例:
            >>> batch_size = gpu_manager.get_optimal_batch_size(
            ...     model_size_mb=100,
            ...     sample_size_mb=0.5
            ... )
            >>> print(f"推荐批次大小: {batch_size}")
        """
        if not PYTORCH_AVAILABLE or not self.cuda_available:
            return 32  # CPU默认批次

        mem_info = self.get_memory_info()
        if not mem_info:
            return 32

        available_mb = mem_info['free_gb'] * 1024 * safety_factor

        usable_mb = available_mb - model_size_mb
        if usable_mb <= 0:
            logger.warning("GPU内存不足，建议使用CPU或减小模型")
            return 16

        batch_size = int(usable_mb / sample_size_mb)
        batch_size = max(16, min(batch_size, 1024))  # 限制在16-1024之间

        logger.info(f"推荐批次大小: {batch_size}")
        return batch_size

    def check_lightgbm_gpu(self) -> bool:
        """
        检查LightGBM是否支持GPU

        返回:
            True表示支持GPU，False表示不支持

        示例:
            >>> if gpu_manager.check_lightgbm_gpu():
            ...     print("LightGBM支持GPU")
        """
        try:
            import lightgbm as lgb
            import numpy as np

            # 尝试创建一个GPU数据集
            X = np.random.rand(100, 10)
            y = np.random.rand(100)
            train_data = lgb.Dataset(X, label=y)

            params = {
                'device': 'gpu',
                'gpu_platform_id': 0,
                'gpu_device_id': 0,
                'verbosity': -1
            }

            # 尝试训练1轮
            lgb.train(params, train_data, num_boost_round=1, verbose_eval=False)
            logger.info("✅ LightGBM GPU支持已启用")
            return True

        except Exception as e:
            logger.warning(f"⚠️  LightGBM GPU不可用: {e}")
            return False

    def get_system_info(self) -> Dict:
        """
        获取完整系统信息

        返回:
            系统信息字典

        示例:
            >>> info = gpu_manager.get_system_info()
            >>> print(info)
        """
        info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "pytorch_available": PYTORCH_AVAILABLE,
            "cuda_available": self.cuda_available if PYTORCH_AVAILABLE else False,
        }

        if PYTORCH_AVAILABLE:
            info["pytorch_version"] = torch.__version__

            if self.cuda_available:
                info.update({
                    "cuda_version": self.cuda_version,
                    "device_count": self.device_count,
                    "device_name": self.device_name,
                    "memory": self.get_memory_info()
                })

        return info


def gpu_memory_monitor(func: Callable) -> Callable:
    """
    GPU内存监控装饰器

    自动记录函数执行前后的GPU内存使用情况

    参数:
        func: 被装饰的函数

    返回:
        装饰后的函数

    示例:
        >>> @gpu_memory_monitor
        ... def train_model():
        ...     model = LightGBMStockModel(use_gpu=True)
        ...     model.train(X_train, y_train)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not PYTORCH_AVAILABLE or not gpu_manager.cuda_available:
            return func(*args, **kwargs)

        # 记录初始内存
        mem_before = gpu_manager.get_memory_info()
        logger.debug(
            f"[{func.__name__}] 执行前GPU内存: "
            f"{mem_before['allocated_gb']:.2f}GB / {mem_before['total_gb']:.2f}GB"
        )

        # 执行函数
        result = func(*args, **kwargs)

        # 记录执行后内存
        mem_after = gpu_manager.get_memory_info()
        mem_used = mem_after['allocated_gb'] - mem_before['allocated_gb']

        logger.debug(
            f"[{func.__name__}] 执行后GPU内存: "
            f"{mem_after['allocated_gb']:.2f}GB / {mem_after['total_gb']:.2f}GB "
            f"(+{mem_used:.2f}GB)"
        )

        # 如果内存使用超过80%，发出警告
        if mem_after['utilization'] > 80:
            logger.warning(
                f"⚠️  GPU内存使用率过高: {mem_after['utilization']:.1f}%，"
                f"建议清理缓存或减小批次大小"
            )

        return result

    return wrapper


class GPUMemoryManager:
    """
    GPU内存自动管理器

    上下文管理器，自动在进入和退出时清理GPU缓存

    参数:
        reserved_gb: 预留内存（GB），用于系统和其他进程

    示例:
        >>> with GPUMemoryManager():
        ...     model1 = GRUStockModelWrapper(use_gpu=True)
        ...     model1.train(X1, y1)
        ...
        ...     # 自动清理内存后训练第二个模型
        ...     model2 = GRUStockModelWrapper(use_gpu=True)
        ...     model2.train(X2, y2)
    """

    def __init__(self, reserved_gb: float = 1.0):
        """
        初始化内存管理器

        参数:
            reserved_gb: 预留内存（GB），用于系统和其他进程
        """
        self.reserved_gb = reserved_gb

    def __enter__(self):
        """进入上下文时清空缓存"""
        if PYTORCH_AVAILABLE and gpu_manager.cuda_available:
            gpu_manager.clear_cache()
            mem_info = gpu_manager.get_memory_info()
            logger.debug(f"GPU内存管理器启动，可用内存: {mem_info.get('free_gb', 0):.2f}GB")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时清空缓存"""
        if PYTORCH_AVAILABLE and gpu_manager.cuda_available:
            gpu_manager.clear_cache()
            logger.debug("GPU内存已清理")


# 全局单例实例
gpu_manager = GPUManager()
