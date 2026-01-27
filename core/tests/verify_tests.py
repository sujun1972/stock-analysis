#!/usr/bin/env python3
"""
测试文件验证脚本

快速验证测试文件的结构和语法
"""

import sys
import ast
from pathlib import Path

def verify_test_file(file_path):
    """验证测试文件"""
    print(f"\n检查文件: {file_path.name}")
    print("=" * 60)

    try:
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析 AST
        tree = ast.parse(content, filename=str(file_path))

        # 统计信息
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        test_methods = [f for f in functions if f.name.startswith('test_')]

        print(f"✓ 语法正确")
        print(f"  测试类: {len(classes)}")
        print(f"  测试方法: {len(test_methods)}")

        # 列出测试类和方法
        for cls in classes:
            if 'Test' in cls.name:
                test_funcs = [f.name for f in cls.body if isinstance(f, ast.FunctionDef) and f.name.startswith('test_')]
                print(f"\n  {cls.name} ({len(test_funcs)} 个测试):")
                for func_name in sorted(test_funcs)[:5]:  # 只显示前5个
                    print(f"    - {func_name}")
                if len(test_funcs) > 5:
                    print(f"    ... 还有 {len(test_funcs) - 5} 个测试")

        return True, len(test_methods)

    except SyntaxError as e:
        print(f"✗ 语法错误: {e}")
        return False, 0
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False, 0

def main():
    """主函数"""
    print("\n" + "="*60)
    print("Pipeline 测试文件验证")
    print("="*60)

    test_dir = Path(__file__).parent

    # 要验证的测试文件
    test_files = [
        test_dir / 'unit' / 'test_pipeline_config.py',
        test_dir / 'unit' / 'test_pipeline.py',
        test_dir / 'integration' / 'test_pipeline_integration.py',
    ]

    total_tests = 0
    total_files = 0
    success_files = 0

    for test_file in test_files:
        if test_file.exists():
            success, num_tests = verify_test_file(test_file)
            total_files += 1
            if success:
                success_files += 1
                total_tests += num_tests
        else:
            print(f"\n⚠ 文件不存在: {test_file.name}")

    # 总结
    print("\n" + "="*60)
    print("验证总结")
    print("="*60)
    print(f"检查文件: {total_files}")
    print(f"验证通过: {success_files}")
    print(f"总测试数: {total_tests}")

    if success_files == total_files:
        print("\n✓ 所有测试文件验证通过！")
        return 0
    else:
        print(f"\n✗ 有 {total_files - success_files} 个文件验证失败")
        return 1

if __name__ == '__main__':
    sys.exit(main())
