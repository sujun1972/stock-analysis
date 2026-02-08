"""
ResourceLimiter 单元测试

测试资源限制器的资源使用控制功能
"""

import pytest
import time
import sys
from strategies.security.resource_limiter import ResourceLimiter, ResourceLimitError


class TestResourceLimiter:
    """测试 ResourceLimiter 类"""

    @pytest.fixture
    def limiter(self):
        """创建 ResourceLimiter 实例"""
        return ResourceLimiter(
            max_memory_mb=512,
            max_cpu_time=30,
            max_wall_time=5  # 5秒超时，方便测试
        )

    def test_initialization(self, limiter):
        """测试初始化"""
        assert limiter.max_memory_mb == 512
        assert limiter.max_cpu_time == 30
        assert limiter.max_wall_time == 5

    def test_normal_execution(self, limiter):
        """测试正常执行 - 在资源限制内"""
        with limiter.limit_resources():
            # 快速执行，不应超时
            result = sum(range(1000))

        assert result == 499500

    @pytest.mark.skipif(
        sys.platform == 'win32',
        reason="Windows 不支持 signal.SIGALRM"
    )
    def test_timeout_error(self):
        """测试超时错误"""
        limiter = ResourceLimiter(max_wall_time=1)  # 1秒超时

        with pytest.raises((TimeoutError, ResourceLimitError)):
            with limiter.limit_resources():
                # 睡眠2秒，应该超时
                time.sleep(2)

    def test_successful_context_exit(self, limiter):
        """测试上下文管理器正常退出"""
        executed = False

        with limiter.limit_resources():
            executed = True

        assert executed is True

    def test_check_memory_usage(self, limiter):
        """测试内存使用检查"""
        usage = limiter.check_memory_usage()

        assert 'current_mb' in usage
        assert 'limit_mb' in usage
        assert 'usage_percent' in usage

        # 验证限制值
        assert usage['limit_mb'] == 512

        # 当前使用应该是正数（如果 psutil 可用）
        if usage['current_mb'] > 0:
            assert usage['usage_percent'] >= 0

    def test_resource_limiter_multiple_calls(self, limiter):
        """测试多次调用资源限制"""
        for _ in range(3):
            with limiter.limit_resources():
                result = sum(range(100))

            assert result == 4950

    def test_nested_context_not_recommended(self, limiter):
        """测试嵌套上下文（不推荐但应该可以工作）"""
        # 注意: 嵌套使用可能导致信号处理器被覆盖
        with limiter.limit_resources():
            result1 = sum(range(100))

            # 嵌套调用（不推荐）
            with limiter.limit_resources():
                result2 = sum(range(50))

            assert result2 == 1225

        assert result1 == 4950

    def test_exception_in_context(self, limiter):
        """测试上下文中的异常处理"""
        with pytest.raises(ValueError):
            with limiter.limit_resources():
                raise ValueError("测试异常")

        # 验证资源限制已恢复
        # 如果没有正确恢复，下次调用可能会失败

    def test_memory_limit_configuration(self):
        """测试不同的内存限制配置"""
        limiter_small = ResourceLimiter(max_memory_mb=128)
        limiter_large = ResourceLimiter(max_memory_mb=2048)

        assert limiter_small.max_memory_mb == 128
        assert limiter_large.max_memory_mb == 2048

    def test_cpu_time_configuration(self):
        """测试CPU时间限制配置"""
        limiter = ResourceLimiter(max_cpu_time=60)
        assert limiter.max_cpu_time == 60

    @pytest.mark.skipif(
        sys.platform == 'darwin',
        reason="macOS 不支持 RLIMIT_AS 内存限制"
    )
    def test_memory_limit_exceeded(self):
        """测试内存超限 - 仅在支持的平台上运行"""
        limiter = ResourceLimiter(max_memory_mb=10)  # 非常小的限制

        with pytest.raises((MemoryError, ResourceLimitError)):
            with limiter.limit_resources():
                # 尝试分配大量内存
                huge_list = [0] * (10 * 1024 * 1024)  # 约40MB

    def test_default_parameters(self):
        """测试默认参数"""
        limiter = ResourceLimiter()

        assert limiter.max_memory_mb == 512
        assert limiter.max_cpu_time == 30
        assert limiter.max_wall_time == 60

    def test_custom_parameters(self):
        """测试自定义参数"""
        limiter = ResourceLimiter(
            max_memory_mb=1024,
            max_cpu_time=60,
            max_wall_time=120
        )

        assert limiter.max_memory_mb == 1024
        assert limiter.max_cpu_time == 60
        assert limiter.max_wall_time == 120
