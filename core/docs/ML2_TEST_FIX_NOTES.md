# ML-2 测试修复说明

> **修复日期**: 2026-02-06
> **修复原因**: 测试用例中的 `top_n` 参数值不符合参数验证要求

---

## 问题描述

在运行 `TestMLSelectorMultiFactorWeightedEnhanced` 测试类时，发现 4 个测试用例失败：

```
FAILED test_integration_multi_factor_with_custom_weights
FAILED test_integration_multi_factor_with_groups
FAILED test_different_normalization_methods_comparison
FAILED test_edge_case_all_features_same_value
```

**错误信息**:
```
ValueError: 参数 'top_n' 的值 2 不能小于 5
```

## 根本原因

MLSelector 的 `top_n` 参数定义中设置了最小值限制：

```python
SelectorParameter(
    name="top_n",
    label="选股数量",
    type="integer",
    default=50,
    min_value=5,  # ← 最小值为 5
    max_value=200,
    description="选出评分最高的前 N 只股票"
)
```

但测试用例中使用了 `top_n=2`，违反了参数验证规则。

## 修复方案

将所有使用 `top_n=2` 的测试用例修改为 `top_n=5`。

### 修复清单

| 测试用例 | 修改前 | 修改后 | 状态 |
|---------|--------|--------|------|
| `test_integration_multi_factor_with_custom_weights` | `top_n=2` | `top_n=5` | ✅ 已修复 |
| `test_integration_multi_factor_with_groups` | `top_n=2` | `top_n=5` | ✅ 已修复 |
| `test_different_normalization_methods_comparison` | `top_n=2` | `top_n=5` | ✅ 已修复 |
| `test_edge_case_all_features_same_value` | `top_n=2` | `top_n=5` | ✅ 已修复 |

### 修改示例

**修改前**:
```python
selector = MLSelector(params={
    'mode': 'multi_factor_weighted',
    'features': 'momentum_20d,rsi_14d',
    'factor_weights': weights_config,
    'normalization_method': 'z_score',
    'top_n': 2  # ❌ 小于最小值 5
})

selected = selector.select(self.test_date, self.prices_df)
assert len(selected) <= 2
```

**修改后**:
```python
selector = MLSelector(params={
    'mode': 'multi_factor_weighted',
    'features': 'momentum_20d,rsi_14d',
    'factor_weights': weights_config,
    'normalization_method': 'z_score',
    'top_n': 5  # ✅ 符合最小值要求
})

selected = selector.select(self.test_date, self.prices_df)
assert len(selected) <= 5  # 对应修改断言
```

## 验证

修复后，所有测试用例应该能够正常通过：

```bash
# 运行修复的测试用例
cd core && python3 -m pytest \
  tests/unit/strategies/three_layer/selectors/test_ml_selector.py::TestMLSelectorMultiFactorWeightedEnhanced::test_integration_multi_factor_with_custom_weights \
  tests/unit/strategies/three_layer/selectors/test_ml_selector.py::TestMLSelectorMultiFactorWeightedEnhanced::test_integration_multi_factor_with_groups \
  tests/unit/strategies/three_layer/selectors/test_ml_selector.py::TestMLSelectorMultiFactorWeightedEnhanced::test_different_normalization_methods_comparison \
  tests/unit/strategies/three_layer/selectors/test_ml_selector.py::TestMLSelectorMultiFactorWeightedEnhanced::test_edge_case_all_features_same_value \
  -v
```

**期望结果**: 全部通过 ✅

## 影响范围

- ✅ **功能无影响** - 仅修改测试用例，不影响实际功能
- ✅ **测试覆盖无变化** - 测试逻辑保持不变
- ✅ **向后兼容** - 不影响其他测试用例

## 经验教训

1. **参数验证的重要性** - 参数定义中的 `min_value` 和 `max_value` 约束会在实例化时被强制验证
2. **测试用例与参数定义的一致性** - 编写测试时应参考参数定义，确保测试值在有效范围内
3. **边界测试的考虑** - 如果需要测试边界情况，应该使用有效的边界值（如 `min_value=5`）

## 总结

✅ **所有测试用例已修复完成**

修复后的测试用例：
- 符合参数验证要求
- 保持测试逻辑不变
- 保证测试覆盖率

---

**文档版本**: v1.0
**最后更新**: 2026-02-06
**修复者**: Claude Code
