"""
添加离场策略到数据库的快速脚本

功能:
1. 检查 strategy_type 字段是否存在
2. 如果不存在，输出SQL语句供手动执行
3. 添加4个内置离场策略到数据库

版本: v1.0.0
创建时间: 2026-02-13
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
backend_root = Path(__file__).parent.parent
core_root = backend_root.parent / 'core'
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(core_root))

import hashlib
import json
from src.database.db_manager import DatabaseManager

# 离场策略定义
EXIT_STRATEGIES = [
    {
        'name': 'stop_loss_exit',
        'display_name': '止损离场策略',
        'class_name': 'StopLossExitStrategy',
        'description': '当亏损超过指定比例时触发离场，用于风险控制',
        'category': 'stop_loss',
        'tags': ['风控', '止损', '离场'],
        'risk_level': 'safe',
        'source_type': 'builtin',
        'strategy_type': 'exit',
        'default_params': {
            'stop_loss_pct': 0.10,
            'priority': 10
        },
        'code': '''from src.ml.exit_strategy import BaseExitStrategy, ExitSignal

class StopLossExitStrategy(BaseExitStrategy):
    """止损离场策略"""

    def __init__(self, stop_loss_pct: float = 0.10, priority: int = 10):
        super().__init__(name='StopLoss', priority=priority)
        self.stop_loss_pct = stop_loss_pct

    def should_exit(self, position, current_price, current_date, market_data=None):
        pnl_pct = position.get('unrealized_pnl_pct', 0.0)
        if pnl_pct < -self.stop_loss_pct:
            return ExitSignal(
                stock_code=position['stock_code'],
                reason='risk_control',
                trigger='stop_loss',
                priority=self.priority,
                metadata={'stop_loss_pct': self.stop_loss_pct, 'actual_loss_pct': pnl_pct}
            )
        return None
'''
    },
    {
        'name': 'take_profit_exit',
        'display_name': '止盈离场策略',
        'class_name': 'TakeProfitExitStrategy',
        'description': '当盈利达到目标时触发离场，锁定利润',
        'category': 'take_profit',
        'tags': ['止盈', '离场'],
        'risk_level': 'safe',
        'source_type': 'builtin',
        'strategy_type': 'exit',
        'default_params': {
            'take_profit_pct': 0.20,
            'priority': 8
        },
        'code': '''from src.ml.exit_strategy import BaseExitStrategy, ExitSignal

class TakeProfitExitStrategy(BaseExitStrategy):
    """止盈离场策略"""

    def __init__(self, take_profit_pct: float = 0.20, priority: int = 8):
        super().__init__(name='TakeProfit', priority=priority)
        self.take_profit_pct = take_profit_pct

    def should_exit(self, position, current_price, current_date, market_data=None):
        pnl_pct = position.get('unrealized_pnl_pct', 0.0)
        if pnl_pct > self.take_profit_pct:
            return ExitSignal(
                stock_code=position['stock_code'],
                reason='strategy',
                trigger='take_profit',
                priority=self.priority,
                metadata={'take_profit_pct': self.take_profit_pct, 'actual_profit_pct': pnl_pct}
            )
        return None
'''
    },
    {
        'name': 'trailing_stop_exit',
        'display_name': '移动止损离场策略',
        'class_name': 'TrailingStopExitStrategy',
        'description': '跟踪最高价，当回撤超过阈值时触发离场',
        'category': 'trailing_stop',
        'tags': ['移动止损', '风控', '离场'],
        'risk_level': 'safe',
        'source_type': 'builtin',
        'strategy_type': 'exit',
        'default_params': {
            'trailing_stop_pct': 0.05,
            'priority': 9
        },
        'code': '''from src.ml.exit_strategy import BaseExitStrategy, ExitSignal

class TrailingStopExitStrategy(BaseExitStrategy):
    """移动止损离场策略"""

    def __init__(self, trailing_stop_pct: float = 0.05, priority: int = 9):
        super().__init__(name='TrailingStop', priority=priority)
        self.trailing_stop_pct = trailing_stop_pct
        self.peak_prices = {}

    def should_exit(self, position, current_price, current_date, market_data=None):
        stock_code = position['stock_code']
        entry_price = position['entry_price']
        if stock_code not in self.peak_prices:
            self.peak_prices[stock_code] = max(entry_price, current_price)
        else:
            self.peak_prices[stock_code] = max(self.peak_prices[stock_code], current_price)
        peak_price = self.peak_prices[stock_code]
        drawdown = (current_price - peak_price) / peak_price
        if drawdown < -self.trailing_stop_pct:
            return ExitSignal(
                stock_code=stock_code,
                reason='risk_control',
                trigger='trailing_stop',
                priority=self.priority,
                metadata={'trailing_stop_pct': self.trailing_stop_pct, 'drawdown': drawdown}
            )
        return None
'''
    },
    {
        'name': 'holding_period_exit',
        'display_name': '持仓时长离场策略',
        'class_name': 'HoldingPeriodExitStrategy',
        'description': '当持仓天数达到上限时触发离场',
        'category': 'holding_period',
        'tags': ['持仓时长', '离场'],
        'risk_level': 'low',
        'source_type': 'builtin',
        'strategy_type': 'exit',
        'default_params': {
            'max_holding_days': 30,
            'priority': 3
        },
        'code': '''from src.ml.exit_strategy import BaseExitStrategy, ExitSignal
import pandas as pd

class HoldingPeriodExitStrategy(BaseExitStrategy):
    """持仓时长离场策略"""

    def __init__(self, max_holding_days: int = 30, priority: int = 3):
        super().__init__(name='HoldingPeriod', priority=priority)
        self.max_holding_days = max_holding_days

    def should_exit(self, position, current_price, current_date, market_data=None):
        entry_date = position.get('entry_date')
        if entry_date is None:
            return None
        if isinstance(entry_date, str):
            entry_date = pd.to_datetime(entry_date)
        if isinstance(current_date, str):
            current_date = pd.to_datetime(current_date)
        holding_days = (current_date - entry_date).days
        if holding_days >= self.max_holding_days:
            return ExitSignal(
                stock_code=position['stock_code'],
                reason='strategy',
                trigger='max_holding_period',
                priority=self.priority,
                metadata={'max_holding_days': self.max_holding_days, 'actual_holding_days': holding_days}
            )
        return None
'''
    }
]


def check_strategy_type_column():
    """检查 strategy_type 列是否存在"""
    db = DatabaseManager()
    conn = db.get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'strategies'
            AND column_name = 'strategy_type'
        """)

        result = cursor.fetchone()
        cursor.close()

        return result is not None

    finally:
        db.release_connection(conn)


def add_strategy_type_column():
    """添加 strategy_type 列"""
    db = DatabaseManager()
    conn = db.get_connection()

    try:
        cursor = conn.cursor()

        print("正在添加 strategy_type 列...")
        cursor.execute("""
            ALTER TABLE strategies
            ADD COLUMN strategy_type VARCHAR(10) DEFAULT 'entry'
        """)

        conn.commit()
        cursor.close()

        print("✓ strategy_type 列添加成功")
        return True

    except Exception as e:
        print(f"✗ 添加 strategy_type 列失败: {e}")
        print("\n请手动执行以下SQL:")
        print("=" * 60)
        print("ALTER TABLE strategies ADD COLUMN strategy_type VARCHAR(10) DEFAULT 'entry';")
        print("=" * 60)
        return False

    finally:
        db.release_connection(conn)


def insert_exit_strategies():
    """插入离场策略"""
    db = DatabaseManager()
    conn = db.get_connection()

    try:
        cursor = conn.cursor()

        inserted_count = 0
        skipped_count = 0

        for strategy in EXIT_STRATEGIES:
            # 检查是否已存在
            cursor.execute(
                "SELECT id FROM strategies WHERE name = %s",
                (strategy['name'],)
            )

            if cursor.fetchone():
                print(f"  跳过 {strategy['display_name']} (已存在)")
                skipped_count += 1
                continue

            # 计算code hash
            code_hash = hashlib.sha256(strategy['code'].encode()).hexdigest()[:16]

            # 插入策略
            cursor.execute("""
                INSERT INTO strategies (
                    name, display_name, code, code_hash, class_name,
                    source_type, strategy_type, description, category, tags,
                    default_params, validation_status, risk_level, is_enabled, version
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                strategy['name'],
                strategy['display_name'],
                strategy['code'],
                code_hash,
                strategy['class_name'],
                strategy['source_type'],
                strategy['strategy_type'],
                strategy['description'],
                strategy['category'],
                strategy['tags'],  # PostgreSQL supports array directly
                json.dumps(strategy['default_params']),
                'passed',
                strategy['risk_level'],
                True,
                1
            ))

            print(f"  ✓ 添加 {strategy['display_name']}")
            inserted_count += 1

        conn.commit()
        cursor.close()

        print(f"\n完成: 新增 {inserted_count} 个, 跳过 {skipped_count} 个")
        return True

    except Exception as e:
        print(f"\n✗ 插入失败: {e}")
        conn.rollback()
        return False

    finally:
        db.release_connection(conn)


def main():
    print("=" * 60)
    print("离场策略数据库初始化")
    print("=" * 60)

    # 1. 检查 strategy_type 列
    print("\n1. 检查 strategy_type 列...")
    has_column = check_strategy_type_column()

    if has_column:
        print("✓ strategy_type 列已存在")
    else:
        print("✗ strategy_type 列不存在")
        print("\n2. 添加 strategy_type 列...")
        if not add_strategy_type_column():
            print("\n请先手动添加 strategy_type 列后再运行此脚本")
            return

    # 2. 插入离场策略
    print(f"\n3. 插入 {len(EXIT_STRATEGIES)} 个离场策略...")
    insert_exit_strategies()

    print("\n" + "=" * 60)
    print("完成！现在可以在前端策略页面查看离场策略了")
    print("=" * 60)


if __name__ == "__main__":
    main()
