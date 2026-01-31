#!/usr/bin/env python3
"""
性能基准测试运行器

运行所有性能基准测试并生成详细报告

使用方法:
    python run_benchmarks.py                    # 运行所有测试
    python run_benchmarks.py --category feature # 只运行特征计算测试
    python run_benchmarks.py --report-only      # 只生成报告

作者: Stock Analysis Team
创建: 2026-01-31
"""

import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
import json

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='运行性能基准测试')

    parser.add_argument(
        '--category',
        choices=['all', 'feature', 'backtest', 'database', 'model'],
        default='all',
        help='测试类别'
    )

    parser.add_argument(
        '--report-only',
        action='store_true',
        help='只生成报告，不运行测试'
    )

    parser.add_argument(
        '--output',
        default='benchmark_report.html',
        help='报告输出文件'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='详细输出'
    )

    return parser.parse_args()


def run_pytest_benchmarks(category: str, verbose: bool = False):
    """
    运行pytest基准测试

    Args:
        category: 测试类别
        verbose: 详细输出
    """
    test_files = {
        'all': [
            'test_feature_calculation_benchmarks.py',
            'test_backtest_benchmarks.py',
            'test_database_and_model_benchmarks.py',
        ],
        'feature': ['test_feature_calculation_benchmarks.py'],
        'backtest': ['test_backtest_benchmarks.py'],
        'database': ['test_database_and_model_benchmarks.py'],
        'model': ['test_database_and_model_benchmarks.py'],
    }

    tests = test_files.get(category, test_files['all'])

    # 构建pytest命令
    cmd = [
        'pytest',
        '-v' if verbose else '-q',
        '--tb=short',
        '--disable-warnings',
    ]

    # 添加测试文件
    tests_dir = Path(__file__).parent
    for test_file in tests:
        test_path = tests_dir / test_file
        if test_path.exists():
            cmd.append(str(test_path))

    # 运行测试
    print("=" * 80)
    print(f"运行性能基准测试 - 类别: {category}")
    print("=" * 80)
    print(f"命令: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=project_root)

    return result.returncode


def generate_html_report(output_file: str):
    """
    生成HTML性能报告

    Args:
        output_file: 输出文件路径
    """
    from benchmarks import performance_reporter

    print("\n" + "=" * 80)
    print("生成性能基准测试报告")
    print("=" * 80)

    # 生成文本报告
    text_report = performance_reporter.generate_report()
    print(text_report)

    # 生成HTML报告
    html_content = generate_html_from_results(performance_reporter.results)

    # 写入文件
    output_path = Path(output_file)
    output_path.write_text(html_content, encoding='utf-8')

    print(f"\nHTML报告已生成: {output_path.absolute()}")


def generate_html_from_results(results):
    """从结果生成HTML报告"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 计算统计信息
    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    # 按类别分组
    categories = {}
    for result in results:
        cat = result['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(result)

    # 生成HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>性能基准测试报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }}

        header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}

        header .timestamp {{
            opacity: 0.9;
            font-size: 14px;
        }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}

        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
        }}

        .summary-card .value {{
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }}

        .summary-card .label {{
            color: #666;
            font-size: 14px;
        }}

        .summary-card.pass .value {{ color: #28a745; }}
        .summary-card.fail .value {{ color: #dc3545; }}
        .summary-card.total .value {{ color: #007bff; }}
        .summary-card.rate .value {{ color: #17a2b8; }}

        .category {{
            padding: 30px;
            border-bottom: 1px solid #e9ecef;
        }}

        .category:last-child {{
            border-bottom: none;
        }}

        .category h2 {{
            color: #495057;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}

        thead {{
            background: #f8f9fa;
        }}

        th {{
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #495057;
            border-bottom: 2px solid #dee2e6;
        }}

        td {{
            padding: 12px;
            border-bottom: 1px solid #e9ecef;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .status {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}

        .status.pass {{
            background: #d4edda;
            color: #155724;
        }}

        .status.fail {{
            background: #f8d7da;
            color: #721c24;
        }}

        .margin-positive {{
            color: #28a745;
            font-weight: 600;
        }}

        .margin-negative {{
            color: #dc3545;
            font-weight: 600;
        }}

        .details {{
            color: #6c757d;
            font-size: 13px;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>性能基准测试报告</h1>
            <div class="timestamp">生成时间: {timestamp}</div>
        </header>

        <div class="summary">
            <div class="summary-card total">
                <div class="label">总测试数</div>
                <div class="value">{total}</div>
            </div>
            <div class="summary-card pass">
                <div class="label">通过</div>
                <div class="value">{passed}</div>
            </div>
            <div class="summary-card fail">
                <div class="label">失败</div>
                <div class="value">{failed}</div>
            </div>
            <div class="summary-card rate">
                <div class="label">通过率</div>
                <div class="value">{pass_rate:.1f}%</div>
            </div>
        </div>
"""

    # 添加每个类别的结果
    for category, results_list in categories.items():
        html += f"""
        <div class="category">
            <h2>{category}</h2>
            <table>
                <thead>
                    <tr>
                        <th>测试名称</th>
                        <th>状态</th>
                        <th>耗时</th>
                        <th>阈值</th>
                        <th>性能余量</th>
                        <th>详情</th>
                    </tr>
                </thead>
                <tbody>
"""

        for r in results_list:
            status_class = 'pass' if r['passed'] else 'fail'
            status_text = '✓ 通过' if r['passed'] else '✗ 失败'
            margin_class = 'margin-positive' if r['passed'] else 'margin-negative'
            margin_sign = '+' if r['passed'] else ''

            details_str = ', '.join([f"{k}={v}" for k, v in r.get('details', {}).items()])

            html += f"""
                    <tr>
                        <td>{r['test_name']}</td>
                        <td><span class="status {status_class}">{status_text}</span></td>
                        <td>{r['elapsed']:.3f}s</td>
                        <td>{r['threshold']:.3f}s</td>
                        <td class="{margin_class}">{margin_sign}{r['margin_pct']:.1f}%</td>
                        <td class="details">{details_str}</td>
                    </tr>
"""

        html += """
                </tbody>
            </table>
        </div>
"""

    html += """
    </div>
</body>
</html>
"""

    return html


def main():
    """主函数"""
    args = parse_args()

    # 运行测试
    if not args.report_only:
        exit_code = run_pytest_benchmarks(args.category, args.verbose)

        if exit_code != 0:
            print("\n⚠ 部分测试失败")
        else:
            print("\n✓ 所有测试通过")

    # 生成报告
    try:
        generate_html_report(args.output)
    except Exception as e:
        print(f"\n生成报告时出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
