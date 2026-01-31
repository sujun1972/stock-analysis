#!/usr/bin/env python3
"""
配置简化项目完整测试套件运行器

运行所有与配置相关的测试,包括:
- Task 1: 高级配置向导 + 配置迁移向导
- Task 2: 配置验证工具 + 配置诊断工具
- Task 3: 配置模板系统
- CLI 命令集成测试

使用方法:
    python run_all_config_tests.py              # 运行所有测试
    python run_all_config_tests.py --verbose    # 详细输出
    python run_all_config_tests.py --coverage   # 生成覆盖率报告
    python run_all_config_tests.py --html       # 生成HTML报告
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
import argparse


class TestRunner:
    """配置测试运行器"""

    def __init__(self, verbose=False, coverage=False, html_report=False):
        self.verbose = verbose
        self.coverage = coverage
        self.html_report = html_report
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent.parent
        self.results = {}

    def run_test_suite(self, test_file, description):
        """运行单个测试套件"""
        print(f"\n{'='*80}")
        print(f"运行: {description}")
        print(f"文件: {test_file}")
        print(f"{'='*80}\n")

        cmd = [sys.executable, "-m", "pytest", str(test_file)]

        if self.verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")

        cmd.extend(["--tb=short", "--color=yes"])

        if self.coverage:
            cmd.extend([
                "--cov=src/config",
                f"--cov-report=term-missing",
            ])

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            self.results[test_file.name] = {
                "description": description,
                "passed": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print(f"❌ 测试超时: {test_file}")
            self.results[test_file.name] = {
                "description": description,
                "passed": False,
                "error": "Timeout"
            }
            return False
        except Exception as e:
            print(f"❌ 运行测试时出错: {e}")
            self.results[test_file.name] = {
                "description": description,
                "passed": False,
                "error": str(e)
            }
            return False

    def run_all_tests(self):
        """运行所有配置测试"""
        print("\n" + "="*80)
        print("配置简化项目 - 完整测试套件")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        # 定义所有测试套件
        test_suites = [
            # Task 1: 配置向导
            (
                self.test_dir / "test_advanced_wizard.py",
                "Task 1.1: 高级配置向导测试"
            ),
            (
                self.test_dir / "test_migration_wizard.py",
                "Task 1.2: 配置迁移向导测试"
            ),

            # Task 2: 验证和诊断
            (
                self.test_dir / "test_validators.py",
                "Task 2.1: 配置验证器测试"
            ),
            (
                self.test_dir / "test_diagnostics.py",
                "Task 2.2: 配置诊断工具测试"
            ),

            # Task 3: 模板系统
            (
                self.test_dir / "test_templates_base.py",
                "Task 3.1: 配置模板基础类测试"
            ),
            (
                self.test_dir / "test_templates_manager.py",
                "Task 3.2: 配置模板管理器测试"
            ),

            # CLI 集成测试
            (
                self.test_dir / "test_cli_config.py",
                "CLI 命令集成测试"
            ),
        ]

        passed_count = 0
        failed_count = 0
        skipped_tests = []

        for test_file, description in test_suites:
            if not test_file.exists():
                print(f"\n⚠️  跳过 {description}: 文件不存在")
                skipped_tests.append((test_file.name, description))
                continue

            if self.run_test_suite(test_file, description):
                passed_count += 1
                print(f"✅ {description} - 通过")
            else:
                failed_count += 1
                print(f"❌ {description} - 失败")

        # 打印总结
        self.print_summary(passed_count, failed_count, skipped_tests)

        # 生成HTML报告(如果需要)
        if self.html_report:
            self.generate_html_report()

        # 生成覆盖率报告(如果需要)
        if self.coverage:
            self.generate_coverage_report()

        return failed_count == 0

    def print_summary(self, passed, failed, skipped):
        """打印测试总结"""
        print("\n" + "="*80)
        print("测试总结")
        print("="*80)

        total = passed + failed + len(skipped)

        print(f"\n总测试套件数: {total}")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"⚠️  跳过: {len(skipped)}")

        if skipped:
            print("\n跳过的测试:")
            for name, desc in skipped:
                print(f"  - {desc} ({name})")

        print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        if failed == 0 and passed > 0:
            print("\n🎉 所有测试通过!")
        elif failed > 0:
            print(f"\n⚠️  有 {failed} 个测试套件失败,请检查输出")

    def generate_coverage_report(self):
        """生成完整的覆盖率报告"""
        print("\n" + "="*80)
        print("生成覆盖率报告")
        print("="*80)

        # 运行coverage命令生成HTML报告
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "--cov=src/config",
            "--cov-report=html:htmlcov_config",
            "--cov-report=term",
            "-q"
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300
            )

            print(result.stdout)

            html_report = self.project_root / "htmlcov_config" / "index.html"
            if html_report.exists():
                print(f"\n✅ HTML覆盖率报告已生成: {html_report}")
            else:
                print("\n⚠️  HTML覆盖率报告生成失败")

        except Exception as e:
            print(f"\n❌ 生成覆盖率报告时出错: {e}")

    def generate_html_report(self):
        """生成HTML测试报告"""
        print("\n" + "="*80)
        print("生成HTML测试报告")
        print("="*80)

        # 使用pytest-html生成报告
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "--html=config_tests_report.html",
            "--self-contained-html",
            "-q"
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300
            )

            report_file = self.project_root / "config_tests_report.html"
            if report_file.exists():
                print(f"\n✅ HTML测试报告已生成: {report_file}")
            else:
                print("\n⚠️  HTML测试报告生成失败")
                print("提示: 请确保已安装 pytest-html: pip install pytest-html")

        except Exception as e:
            print(f"\n❌ 生成HTML报告时出错: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="配置简化项目完整测试套件运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    # 运行所有测试(简洁输出)
  %(prog)s --verbose          # 运行所有测试(详细输出)
  %(prog)s --coverage         # 运行测试并生成覆盖率报告
  %(prog)s --html             # 运行测试并生成HTML报告
  %(prog)s -v -c -html        # 全部选项
        """
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细的测试输出"
    )

    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="生成代码覆盖率报告"
    )

    parser.add_argument(
        "--html",
        action="store_true",
        help="生成HTML测试报告(需要pytest-html)"
    )

    args = parser.parse_args()

    # 创建并运行测试器
    runner = TestRunner(
        verbose=args.verbose,
        coverage=args.coverage,
        html_report=args.html
    )

    success = runner.run_all_tests()

    # 返回适当的退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
