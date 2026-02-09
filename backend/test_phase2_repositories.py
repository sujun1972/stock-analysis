#!/usr/bin/env python3
"""
Phase 2: 测试新创建的Repository类
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.repositories.strategy_config_repository import StrategyConfigRepository
from app.repositories.dynamic_strategy_repository import DynamicStrategyRepository
from app.repositories.strategy_execution_repository import StrategyExecutionRepository


def test_strategy_config_repository():
    """测试策略配置Repository"""
    print("\n" + "="*60)
    print("测试 StrategyConfigRepository")
    print("="*60)

    repo = StrategyConfigRepository()

    # 1. 测试读取示例数据
    print("\n1. 读取示例配置 (ID=1)...")
    config = repo.get_by_id(1)
    if config:
        print(f"   ✓ 成功读取配置: {config['name']}")
        print(f"     - 策略类型: {config['strategy_type']}")
        print(f"     - 配置参数: {config['config']}")
    else:
        print("   ✗ 未找到配置")
        return False

    # 2. 测试列表查询
    print("\n2. 查询配置列表...")
    result = repo.list(page=1, page_size=10)
    print(f"   ✓ 共查询到 {result['meta']['total']} 个配置")
    for item in result['items']:
        print(f"     - {item['name']} ({item['strategy_type']})")

    # 3. 测试按策略类型查询
    print("\n3. 查询 momentum 策略配置...")
    configs = repo.get_by_strategy_type('momentum', limit=5)
    print(f"   ✓ 共查询到 {len(configs)} 个 momentum 配置")

    return True


def test_dynamic_strategy_repository():
    """测试动态策略Repository"""
    print("\n" + "="*60)
    print("测试 DynamicStrategyRepository")
    print("="*60)

    repo = DynamicStrategyRepository()

    # 1. 创建测试策略
    print("\n1. 创建测试动态策略...")
    test_code = """
from core.strategies.base_strategy import BaseStrategy

class TestMomentumStrategy(BaseStrategy):
    def __init__(self, lookback_period=20, top_n=10):
        self.lookback_period = lookback_period
        self.top_n = top_n

    def select_stocks(self, data):
        # 简单动量策略逻辑
        returns = data.pct_change(self.lookback_period)
        return returns.nlargest(self.top_n).index.tolist()
"""

    try:
        strategy_id = repo.create({
            'strategy_name': 'test_momentum_v1',
            'class_name': 'TestMomentumStrategy',
            'generated_code': test_code,
            'display_name': '测试动量策略',
            'description': '用于测试的简单动量策略',
            'validation_status': 'passed',
            'tags': ['test', 'momentum'],
            'created_by': 'test_script'
        })
        print(f"   ✓ 成功创建动态策略，ID: {strategy_id}")

        # 2. 读取刚创建的策略
        print("\n2. 读取刚创建的策略...")
        strategy = repo.get_by_id(strategy_id)
        if strategy:
            print(f"   ✓ 成功读取策略: {strategy['display_name']}")
            print(f"     - 策略名称: {strategy['strategy_name']}")
            print(f"     - 类名: {strategy['class_name']}")
            print(f"     - 验证状态: {strategy['validation_status']}")
            print(f"     - 代码哈希: {strategy['code_hash'][:16]}...")

        # 3. 更新验证状态
        print("\n3. 更新验证状态...")
        repo.update_validation_status(
            strategy_id,
            'passed',
            validation_warnings={'warnings': ['示例警告']}
        )
        print("   ✓ 验证状态更新成功")

        # 4. 列表查询
        print("\n4. 查询动态策略列表...")
        result = repo.list(validation_status='passed', page=1, page_size=10)
        print(f"   ✓ 共查询到 {result['meta']['total']} 个已验证的动态策略")

        # 5. 清理测试数据
        print("\n5. 清理测试数据...")
        repo.delete(strategy_id)
        print("   ✓ 测试数据已删除")

        return True

    except Exception as e:
        print(f"   ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_execution_repository():
    """测试策略执行Repository"""
    print("\n" + "="*60)
    print("测试 StrategyExecutionRepository")
    print("="*60)

    repo = StrategyExecutionRepository()

    # 1. 创建执行记录
    print("\n1. 创建执行记录...")
    try:
        execution_id = repo.create({
            'config_strategy_id': 1,
            'execution_type': 'backtest',
            'execution_params': {
                'stock_pool': ['000001.SZ', '600000.SH'],
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'initial_capital': 1000000
            },
            'executed_by': 'test_script'
        })
        print(f"   ✓ 成功创建执行记录，ID: {execution_id}")

        # 2. 更新状态
        print("\n2. 更新执行状态为 'running'...")
        repo.update_status(execution_id, 'running')
        print("   ✓ 状态更新成功")

        # 3. 更新结果
        print("\n3. 更新执行结果...")
        repo.update_result(
            execution_id,
            result={'trades': [], 'equity_curve': []},
            metrics={
                'annual_return': 0.15,
                'sharpe_ratio': 1.2,
                'max_drawdown': -0.10
            }
        )
        print("   ✓ 结果更新成功")

        # 4. 完成执行
        print("\n4. 标记执行完成...")
        repo.update_status(execution_id, 'completed')
        print("   ✓ 执行已完成")

        # 5. 读取执行记录
        print("\n5. 读取执行记录...")
        execution = repo.get_by_id(execution_id)
        if execution:
            print(f"   ✓ 成功读取执行记录")
            print(f"     - 状态: {execution['status']}")
            print(f"     - 执行类型: {execution['execution_type']}")
            if execution['metrics']:
                print(f"     - 年化收益: {execution['metrics'].get('annual_return')}")
                print(f"     - 夏普比率: {execution['metrics'].get('sharpe_ratio')}")

        # 6. 获取统计信息
        print("\n6. 获取执行统计...")
        stats = repo.get_statistics(config_strategy_id=1)
        print(f"   ✓ 统计信息:")
        print(f"     - 总执行次数: {stats['total']}")
        print(f"     - 成功次数: {stats['completed']}")
        print(f"     - 失败次数: {stats['failed']}")

        return True

    except Exception as e:
        print(f"   ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Phase 2: Repository测试")
    print("="*60)

    results = []

    # 测试策略配置Repository
    results.append(("StrategyConfigRepository", test_strategy_config_repository()))

    # 测试动态策略Repository
    results.append(("DynamicStrategyRepository", test_dynamic_strategy_repository()))

    # 测试策略执行Repository
    results.append(("StrategyExecutionRepository", test_strategy_execution_repository()))

    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}  {name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "="*60)
    if all_passed:
        print("✅ 所有测试通过！Phase 2 完成！")
    else:
        print("❌ 部分测试失败，请检查错误信息")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
