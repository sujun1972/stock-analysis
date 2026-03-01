# AI策略生成功能

本项目提供了完整的 AI 辅助策略生成功能，帮助用户快速创建量化交易策略。

## 📚 相关文档

- **[AI策略快速上手](../AI_STRATEGY_QUICKSTART.md)** - 5分钟快速上手指南，包含完整流程
- **[AI策略提示词模板](../AI_STRATEGY_PROMPT.md)** - 详细的提示词模板和使用说明
- **[策略示例代码](./examples/strategies/)** - 完整的策略示例代码

## 🎯 功能特点

### 1. 智能提示词生成
- 标准化的策略提示词模板
- 可编辑的策略需求输入
- 一键复制，快速生成代码

### 2. 多 AI 工具支持
- Claude 3.5 Sonnet（推荐）
- ChatGPT-4
- Gemini Pro
- 通义千问 / 文心一言

### 3. 代码质量保证
通过优化的提示词模板，确保生成的代码：
- ✅ 正确的配置参数访问方式
- ✅ 安全的信号赋值方法
- ✅ 完善的数据验证
- ✅ 规范的错误处理

### 4. 前端集成
在策略创建页面（`/strategies/create?source=custom`）直接提供 AI 助手组件：
- 填写策略需求
- 查看/编辑提示词模板
- 复制生成的提示词
- 粘贴到 AI 工具获取代码

## 🚀 快速使用

1. 访问策略创建页面
2. 在 AI 策略生成助手中填写需求
3. 点击"复制提示词"
4. 粘贴到 AI 工具
5. 将 AI 生成的代码和元信息填入表单
6. 验证并保存

## 📝 提示词模板更新日志

### v1.1 (2026-03-01)
- ✨ 增强配置参数访问说明，防止 `self.config.get()` 错误
- ✨ 新增信号赋值正确方式说明，避免索引错误
- ✨ 新增数据验证要求，提升代码健壮性
- 📝 更新错误处理部分，提供具体代码示例

### v1.0
- 初始版本，提供基础提示词模板

## 🔗 相关组件

- **前端组件**: [`AIStrategyPromptHelper.tsx`](../frontend/src/components/strategies/AIStrategyPromptHelper.tsx)
- **策略基类**: [`BaseStrategy`](../core/src/strategies/base_strategy.py)
- **策略验证**: [`validate_strategy_code()`](../backend/app/api/v1/endpoints/strategies.py)

---

最后更新: 2026-03-01
