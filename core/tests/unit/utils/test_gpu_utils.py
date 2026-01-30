"""
GPU工具单元测试

测试GPU环境检测、设备选择、内存管理等功能
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# 添加src到路径
src_path = Path(__file__).parent.parent.parent.parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from utils.gpu_utils import (
    GPUManager,
    GPUConfig,
    gpu_manager,
    gpu_memory_monitor,
    GPUMemoryManager,
    PYTORCH_AVAILABLE
)


class TestGPUConfig:
    """测试GPU配置"""

    def test_gpu_config_defaults(self):
        """测试GPU配置默认值"""
        config = GPUConfig()

        assert config.enabled is True
        assert config.device_id == 0
        assert config.memory_fraction == 0.8
        assert config.allow_growth is True

    def test_gpu_config_custom(self):
        """测试自定义GPU配置"""
        config = GPUConfig(
            enabled=False,
            device_id=1,
            memory_fraction=0.5,
            allow_growth=False
        )

        assert config.enabled is False
        assert config.device_id == 1
        assert config.memory_fraction == 0.5
        assert config.allow_growth is False


class TestGPUManager:
    """测试GPU管理器"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = GPUManager()
        manager2 = GPUManager()

        assert manager1 is manager2
        assert manager1 is gpu_manager

    def test_gpu_manager_initialization(self):
        """测试GPU管理器初始化"""
        manager = gpu_manager

        assert hasattr(manager, 'config')
        assert hasattr(manager, 'cuda_available')
        assert hasattr(manager, 'device_count')
        assert hasattr(manager, 'device_name')
        assert hasattr(manager, 'cuda_version')

        # 检查config是GPUConfig实例
        assert isinstance(manager.config, GPUConfig)

    def test_get_device_cpu(self):
        """测试获取CPU设备"""
        manager = gpu_manager

        # 强制使用CPU
        device = manager.get_device(prefer_gpu=False)
        assert device == "cpu"

    @pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch未安装")
    def test_get_device_gpu(self):
        """测试获取GPU设备"""
        import torch
        manager = gpu_manager

        device = manager.get_device(prefer_gpu=True)

        if torch.cuda.is_available() and manager.config.enabled:
            assert "cuda" in device
        else:
            assert device == "cpu"

    @pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch未安装")
    def test_get_memory_info_cpu(self):
        """测试CPU模式下获取内存信息"""
        import torch
        manager = gpu_manager

        if not torch.cuda.is_available():
            mem_info = manager.get_memory_info()
            assert mem_info == {}

    @pytest.mark.skipif(
        not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
        reason="需要GPU"
    )
    def test_get_memory_info_gpu(self):
        """测试GPU模式下获取内存信息"""
        manager = gpu_manager
        mem_info = manager.get_memory_info()

        assert 'total_gb' in mem_info
        assert 'allocated_gb' in mem_info
        assert 'reserved_gb' in mem_info
        assert 'free_gb' in mem_info
        assert 'utilization' in mem_info

        # 检查值的合理性
        assert mem_info['total_gb'] > 0
        assert mem_info['allocated_gb'] >= 0
        assert mem_info['free_gb'] >= 0
        assert 0 <= mem_info['utilization'] <= 100

    @pytest.mark.skipif(
        not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
        reason="需要GPU"
    )
    def test_clear_cache(self):
        """测试清空GPU缓存"""
        manager = gpu_manager

        # 执行清理（应该不抛出异常）
        manager.clear_cache()

        # 再次获取内存信息确认正常工作
        mem_info = manager.get_memory_info()
        assert 'total_gb' in mem_info

    def test_get_optimal_batch_size(self):
        """测试自动批次大小计算"""
        manager = gpu_manager

        batch_size = manager.get_optimal_batch_size(
            model_size_mb=100,
            sample_size_mb=0.5,
            safety_factor=0.7
        )

        # 批次大小应该在合理范围内
        assert 16 <= batch_size <= 1024
        assert isinstance(batch_size, int)

    def test_get_optimal_batch_size_large_model(self):
        """测试大模型的批次大小计算"""
        manager = gpu_manager

        # 超大模型应该返回最小批次
        batch_size = manager.get_optimal_batch_size(
            model_size_mb=100000,  # 100GB
            sample_size_mb=1.0
        )

        assert batch_size >= 16

    def test_get_system_info(self):
        """测试获取系统信息"""
        manager = gpu_manager
        info = manager.get_system_info()

        # 检查基本字段
        assert 'platform' in info
        assert 'python_version' in info
        assert 'pytorch_available' in info
        assert 'cuda_available' in info

        # 如果PyTorch可用，应该有版本信息
        if PYTORCH_AVAILABLE:
            assert 'pytorch_version' in info


class TestGPUMemoryMonitor:
    """测试GPU内存监控装饰器"""

    @gpu_memory_monitor
    def _dummy_function(self):
        """虚拟函数用于测试"""
        return "success"

    @gpu_memory_monitor
    def _gpu_allocation_function(self):
        """测试GPU内存分配"""
        if PYTORCH_AVAILABLE:
            import torch
            if torch.cuda.is_available():
                # 分配一些GPU内存
                tensor = torch.zeros(1000, 1000).cuda()
                return tensor
        return None

    def test_memory_monitor_decorator(self):
        """测试内存监控装饰器基本功能"""
        result = self._dummy_function()
        assert result == "success"

    @pytest.mark.skipif(
        not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
        reason="需要GPU"
    )
    def test_memory_monitor_gpu_allocation(self):
        """测试内存监控GPU分配"""
        result = self._gpu_allocation_function()
        assert result is not None


class TestGPUMemoryManager:
    """测试GPU内存管理器"""

    def test_context_manager(self):
        """测试上下文管理器基本功能"""
        with GPUMemoryManager() as manager:
            assert manager is not None

    @pytest.mark.skipif(
        not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
        reason="需要GPU"
    )
    def test_context_manager_clear_cache(self):
        """测试上下文管理器清理缓存"""
        import torch

        # 分配一些内存
        tensor = torch.zeros(1000, 1000).cuda()

        mem_before = gpu_manager.get_memory_info()

        with GPUMemoryManager():
            # 在上下文中分配更多内存
            tensor2 = torch.zeros(1000, 1000).cuda()
            del tensor2

        # 退出后应该清理缓存
        mem_after = gpu_manager.get_memory_info()

        # 清理tensor
        del tensor
        torch.cuda.empty_cache()

    def test_context_manager_with_reserved_memory(self):
        """测试指定预留内存的上下文管理器"""
        with GPUMemoryManager(reserved_gb=2.0) as manager:
            assert manager.reserved_gb == 2.0


class TestGPUIntegration:
    """GPU集成测试"""

    def test_global_gpu_manager_instance(self):
        """测试全局GPU管理器实例"""
        from utils.gpu_utils import gpu_manager as gm1
        from utils.gpu_utils import gpu_manager as gm2

        assert gm1 is gm2
        assert gm1 is gpu_manager

    def test_gpu_manager_config_modification(self):
        """测试修改GPU管理器配置"""
        manager = gpu_manager

        # 保存原始配置
        original_enabled = manager.config.enabled

        # 修改配置
        manager.config.enabled = False
        assert manager.config.enabled is False

        # 恢复配置
        manager.config.enabled = original_enabled

    @pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch未安装")
    def test_device_selection_logic(self):
        """测试设备选择逻辑"""
        import torch
        manager = gpu_manager

        # 测试优先GPU
        device_gpu = manager.get_device(prefer_gpu=True)
        if torch.cuda.is_available() and manager.config.enabled:
            assert "cuda" in device_gpu
        else:
            assert device_gpu == "cpu"

        # 测试强制CPU
        device_cpu = manager.get_device(prefer_gpu=False)
        assert device_cpu == "cpu"


# ==================== 性能基准测试（可选） ====================

@pytest.mark.benchmark
@pytest.mark.skipif(
    not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
    reason="需要GPU进行基准测试"
)
class TestGPUPerformance:
    """GPU性能基准测试"""

    def test_memory_allocation_speed(self):
        """测试内存分配速度"""
        import torch
        import time

        start = time.time()
        tensor = torch.zeros(10000, 10000).cuda()
        allocation_time = time.time() - start

        del tensor
        torch.cuda.empty_cache()

        # 内存分配应该很快（< 1秒）
        assert allocation_time < 1.0

    def test_memory_clear_speed(self):
        """测试内存清理速度"""
        import torch
        import time

        # 分配一些内存
        tensors = [torch.zeros(1000, 1000).cuda() for _ in range(10)]

        start = time.time()
        for t in tensors:
            del t
        torch.cuda.empty_cache()
        clear_time = time.time() - start

        # 清理应该很快（< 0.5秒）
        assert clear_time < 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
