-- Migration: 009_builtin_ml_strategy.sql
-- Description: 添加内置的机器学习策略，用于ML模型回测
-- Author: System
-- Date: 2024-02-12
INSERT INTO strategies (
    name,
    display_name,
    code,
    code_hash,
    class_name,
    source_type,
    description,
    category,
    tags,
    default_params,
    validation_status,
    validation_errors,
    validation_warnings,
    risk_level,
    is_enabled,
    version,
    created_by
) VALUES (
    'ml_model',
    '机器学习模型策略',
    '# 机器学习模型策略 - 系统内置
from core.strategy.base import BaseStrategy
from typing import Dict, Any, List
import pandas as pd
import numpy as np

class MLModelStrategy(BaseStrategy):
    """
    机器学习模型策略

    使用训练好的ML模型预测未来收益，并根据预测结果进行交易决策
    """

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.model_id = params.get("model_id")
        self.buy_threshold = params.get("buy_threshold", 0.01)  # 买入阈值：预测上涨>1%
        self.sell_threshold = params.get("sell_threshold", -0.01)  # 卖出阈值：预测下跌<-1%
        self.position_size = params.get("position_size", 1.0)  # 仓位大小
        self.stop_loss = params.get("stop_loss", 0.05)  # 止损：5%
        self.take_profit = params.get("take_profit", 0.10)  # 止盈：10%

        if not self.model_id:
            raise ValueError("必须提供model_id参数")

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        生成交易信号

        Args:
            data: 包含价格和特征数据的DataFrame

        Returns:
            交易信号序列 (1=买入, 0=持有, -1=卖出)
        """
        # 这里是示例代码，实际实现会在运行时加载ML模型
        # 并使用模型的predict方法生成预测值

        signals = pd.Series(0, index=data.index)

        # 在实际运行时，这里会：
        # 1. 从数据库加载模型
        # 2. 提取特征
        # 3. 调用模型预测
        # 4. 根据预测值和阈值生成信号

        # 示例逻辑（实际会被运行时替换）:
        # predictions = self.model.predict(features)
        # signals[predictions > self.buy_threshold] = 1
        # signals[predictions < self.sell_threshold] = -1

        return signals

    def calculate_position_size(self, signal: int, current_price: float,
                               portfolio_value: float) -> float:
        """
        计算仓位大小

        Args:
            signal: 交易信号
            current_price: 当前价格
            portfolio_value: 组合价值

        Returns:
            目标仓位（股票数量）
        """
        if signal == 1:  # 买入信号
            target_value = portfolio_value * self.position_size
            return int(target_value / current_price)
        elif signal == -1:  # 卖出信号
            return 0
        else:  # 持有
            return None
',
    'e5f7a9c8b3d2a1c4e6f8b9d0a2c3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1',  -- SHA256 hash placeholder
    'MLModelStrategy',
    'builtin',  -- 内置策略
    '基于机器学习模型预测的交易策略。使用训练好的ML模型预测未来收益，并根据预测结果进行交易决策。支持自定义买入/卖出阈值、仓位管理和止损止盈。',
    'ai',
    ARRAY['机器学习', 'AI', '预测', '量化'],
    jsonb_build_object(
        'model_id', NULL,
        'buy_threshold', 0.01,
        'sell_threshold', -0.01,
        'position_size', 1.0,
        'stop_loss', 0.05,
        'take_profit', 0.10
    ),
    'passed',  -- 验证状态：已通过
    NULL,  -- 无验证错误
    NULL,  -- 无验证警告
    'medium',  -- 风险等级：中等
    true,  -- 启用状态
    1,  -- 版本号
    'system'  -- 创建者
)
ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    default_params = EXCLUDED.default_params,
    updated_at = CURRENT_TIMESTAMP;

-- 添加注释
COMMENT ON TABLE strategies IS '策略表，存储所有交易策略（包括内置、自定义和AI策略）';

-- 验证插入
DO $$
DECLARE
    ml_strategy_id INTEGER;
BEGIN
    SELECT id INTO ml_strategy_id FROM strategies WHERE name = 'ml_model';
    IF ml_strategy_id IS NULL THEN
        RAISE EXCEPTION 'ML策略插入失败';
    ELSE
        RAISE NOTICE 'ML策略已成功创建，ID: %', ml_strategy_id;
    END IF;
END $$;
