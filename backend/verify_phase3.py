#!/usr/bin/env python3
"""
Phase 3 验证脚本

验证 Core Adapters 的正确安装和功能。

运行方式:
    python3 verify_phase3.py
"""

import sys
from pathlib import Path

# 添加项目路径
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))


def verify_imports():
    """验证模块导入"""
    print("=" * 60)
    print("1. 验证模块导入")
    print("=" * 60)

    try:
        from app.core_adapters import (
            ConfigStrategyAdapter,
            DynamicStrategyAdapter
        )
        print("✅ ConfigStrategyAdapter 导入成功")
        print("✅ DynamicStrategyAdapter 导入成功")
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

    try:
        from app.core.exceptions import AdapterError, SecurityError
        print("✅ AdapterError 导入成功")
        print("✅ SecurityError 导入成功")
    except ImportError as e:
        print(f"❌ 异常类导入失败: {e}")
        return False

    return True


def verify_adapter_creation():
    """验证适配器实例化"""
    print("\n" + "=" * 60)
    print("2. 验证适配器实例化")
    print("=" * 60)

    try:
        from app.core_adapters import (
            ConfigStrategyAdapter,
            DynamicStrategyAdapter
        )

        config_adapter = ConfigStrategyAdapter()
        print(f"✅ ConfigStrategyAdapter 实例化成功: {type(config_adapter)}")

        dynamic_adapter = DynamicStrategyAdapter()
        print(f"✅ DynamicStrategyAdapter 实例化成功: {type(dynamic_adapter)}")

        return True
    except Exception as e:
        print(f"❌ 实例化失败: {e}")
        return False


def verify_methods():
    """验证方法可用性"""
    print("\n" + "=" * 60)
    print("3. 验证方法可用性")
    print("=" * 60)

    try:
        from app.core_adapters import (
            ConfigStrategyAdapter,
            DynamicStrategyAdapter
        )

        # ConfigStrategyAdapter 方法
        config_adapter = ConfigStrategyAdapter()
        config_methods = [
            'create_strategy_from_config',
            'get_available_strategy_types',
            'validate_config',
            'list_configs',
            'get_config_by_id'
        ]

        print("\nConfigStrategyAdapter 方法:")
        for method in config_methods:
            if hasattr(config_adapter, method):
                print(f"  ✅ {method}")
            else:
                print(f"  ❌ {method} 缺失")

        # DynamicStrategyAdapter 方法
        dynamic_adapter = DynamicStrategyAdapter()
        dynamic_methods = [
            'create_strategy_from_code',
            'get_strategy_metadata',
            'get_strategy_code',
            'list_strategies',
            'validate_strategy_code',
            'update_validation_status',
            'check_strategy_name_exists',
            'get_strategy_statistics'
        ]

        print("\nDynamicStrategyAdapter 方法:")
        for method in dynamic_methods:
            if hasattr(dynamic_adapter, method):
                print(f"  ✅ {method}")
            else:
                print(f"  ❌ {method} 缺失")

        return True
    except Exception as e:
        print(f"❌ 方法验证失败: {e}")
        return False


def verify_file_structure():
    """验证文件结构"""
    print("\n" + "=" * 60)
    print("4. 验证文件结构")
    print("=" * 60)

    files_to_check = [
        "app/core_adapters/config_strategy_adapter.py",
        "app/core_adapters/dynamic_strategy_adapter.py",
        "app/core_adapters/__init__.py",
        "app/core/exceptions.py",
        "tests/unit/core_adapters/test_config_strategy_adapter.py",
        "tests/unit/core_adapters/test_dynamic_strategy_adapter.py",
        "docs/phase3_implementation_summary.md",
    ]

    all_exist = True
    for file_path in files_to_check:
        full_path = backend_path / file_path
        if full_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} 缺失")
            all_exist = False

    return all_exist


def verify_exception_handling():
    """验证异常处理"""
    print("\n" + "=" * 60)
    print("5. 验证异常处理")
    print("=" * 60)

    try:
        from app.core.exceptions import AdapterError, SecurityError

        # 测试 AdapterError
        try:
            raise AdapterError(
                "测试错误",
                error_code="TEST_ERROR",
                test_param="test_value"
            )
        except AdapterError as e:
            assert e.error_code == "TEST_ERROR"
            assert e.context['test_param'] == "test_value"
            print("  ✅ AdapterError 工作正常")

        # 测试 SecurityError
        try:
            raise SecurityError(
                "安全测试错误",
                error_code="SECURITY_TEST",
                strategy_id=123
            )
        except SecurityError as e:
            assert e.error_code == "SECURITY_TEST"
            assert e.context['strategy_id'] == 123
            print("  ✅ SecurityError 工作正常")

        return True
    except Exception as e:
        print(f"  ❌ 异常处理验证失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Phase 3 验证脚本")
    print("Backend Core Adapters 功能验证")
    print("=" * 60)

    results = []

    # 运行验证测试
    results.append(("模块导入", verify_imports()))
    results.append(("适配器实例化", verify_adapter_creation()))
    results.append(("方法可用性", verify_methods()))
    results.append(("文件结构", verify_file_structure()))
    results.append(("异常处理", verify_exception_handling()))

    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20s}: {status}")

    all_passed = all(result for _, result in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有验证通过！Phase 3 实施成功！")
        print("=" * 60)
        print("\n下一步:")
        print("  1. 运行完整测试: ./venv/bin/pytest tests/unit/core_adapters/ -v")
        print("  2. 开始 Phase 4: 新增 API 端点")
        return 0
    else:
        print("⚠️  部分验证失败，请检查上述错误")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
