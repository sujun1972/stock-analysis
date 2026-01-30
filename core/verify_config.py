#!/usr/bin/env python3
"""
测试统一配置系统
"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 70)
print("测试统一配置系统")
print("=" * 70)

# 测试1: 导入配置模块
print("\n[测试1] 导入配置模块...")
try:
    from config import get_settings, get_config_summary, validate_config
    print("✅ 配置模块导入成功")
except Exception as e:
    print(f"❌ 配置模块导入失败: {e}")
    sys.exit(1)

# 测试2: 获取配置实例
print("\n[测试2] 获取配置实例...")
try:
    settings = get_settings()
    print("✅ 配置实例获取成功")
    print(f"   - 数据源: {settings.data_source.provider}")
    print(f"   - 数据库: {settings.database.database}")
except Exception as e:
    print(f"❌ 获取配置实例失败: {e}")
    sys.exit(1)

# 测试3: 向后兼容性
print("\n[测试3] 测试向后兼容性...")
try:
    from config import DATA_PATH, TUSHARE_TOKEN, DATABASE_CONFIG
    print("✅ 向后兼容导出成功")
    print(f"   - DATA_PATH: {DATA_PATH}")
    print(f"   - TUSHARE_TOKEN: {'***已配置***' if TUSHARE_TOKEN else '未配置'}")
    print(f"   - DATABASE_CONFIG: {DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}")
except Exception as e:
    print(f"❌ 向后兼容性测试失败: {e}")
    sys.exit(1)

# 测试4: 提供者配置
print("\n[测试4] 测试提供者配置...")
try:
    from config import get_current_provider, get_provider_config_manager
    provider = get_current_provider()
    manager = get_provider_config_manager()
    info = manager.get_provider_info()
    print("✅ 提供者配置成功")
    print(f"   - 当前提供者: {provider}")
    print(f"   - 提供者描述: {info['description']}")
    print(f"   - 是否免费: {info['free']}")
except Exception as e:
    print(f"❌ 提供者配置测试失败: {e}")
    sys.exit(1)

# 测试5: 流水线配置
print("\n[测试5] 测试流水线配置...")
try:
    from config import PipelineConfig, DEFAULT_CONFIG
    config = PipelineConfig(target_period=10)
    print("✅ 流水线配置成功")
    print(f"   - 默认目标周期: {DEFAULT_CONFIG.target_period}")
    print(f"   - 自定义目标周期: {config.target_period}")
except Exception as e:
    print(f"❌ 流水线配置测试失败: {e}")
    sys.exit(1)

# 测试6: 配置摘要
print("\n[测试6] 显示配置摘要...")
try:
    summary = get_config_summary()
    print(summary)
except Exception as e:
    print(f"❌ 配置摘要生成失败: {e}")
    sys.exit(1)

# 测试7: 配置验证
print("\n[测试7] 验证配置...")
try:
    is_valid = validate_config()
    if is_valid:
        print("✅ 配置验证通过")
    else:
        print("⚠️  配置验证有警告(但可以继续)")
except Exception as e:
    print(f"❌ 配置验证失败: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ 所有测试通过!配置系统工作正常")
print("=" * 70)
