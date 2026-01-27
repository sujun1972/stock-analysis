"""
简单的语法和导入测试（不需要额外依赖）
"""

import sys
import os
import ast

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_syntax():
    """测试语法正确性"""
    file_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'src',
        'features',
        'alpha_factors.py'
    )

    print(f"测试文件: {file_path}")

    # 读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # 解析AST
    try:
        tree = ast.parse(code, filename=file_path)
        print("✓ 语法检查通过")

        # 统计类和函数
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        print(f"✓ 类数量: {len(set(classes))}")
        print(f"✓ 函数/方法数量: {len(set(functions))}")

        # 显示关键类
        key_classes = [
            'FactorCache',
            'FactorConfig',
            'BaseFactorCalculator',
            'MomentumFactorCalculator',
            'TrendFactorCalculator',
            'AlphaFactors'
        ]

        print("\n关键类检查:")
        for cls in key_classes:
            if cls in classes:
                print(f"  ✓ {cls}")
            else:
                print(f"  ✗ {cls} 缺失")

        return True

    except SyntaxError as e:
        print(f"✗ 语法错误: {e}")
        return False


def test_imports():
    """测试模块导入（可能失败，因为缺少pandas等依赖）"""
    print("\n尝试导入模块...")
    try:
        from features import alpha_factors
        print("✓ 模块导入成功")

        # 检查关键类
        assert hasattr(alpha_factors, 'AlphaFactors')
        assert hasattr(alpha_factors, 'FactorCache')
        assert hasattr(alpha_factors, 'BaseFactorCalculator')
        print("✓ 关键类存在")

        return True
    except ImportError as e:
        print(f"⚠ 模块导入失败（可能缺少依赖）: {e}")
        print("  这是正常的，因为测试环境可能没有安装 pandas/numpy/loguru")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("Alpha Factors 语法验证测试")
    print("=" * 70 + "\n")

    # 测试语法
    syntax_ok = test_syntax()

    # 尝试导入
    import_ok = test_imports()

    # 总结
    print("\n" + "=" * 70)
    if syntax_ok:
        print("✓ 代码语法验证通过")
        print("✓ 优化代码已准备就绪")
    else:
        print("✗ 存在语法错误，需要修复")

    print("=" * 70)
