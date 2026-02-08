# Backend 规划文档

本目录包含 Backend 项目的规划和设计文档。

---

## 📋 文档索引

### 策略管理系统

#### 1. [策略参数配置管理系统](./strategy_config_management.md)
**状态**: 📋 设计阶段
**版本**: v1.0.0
**日期**: 2026-02-08

**概述**: 基于参数配置的策略管理方案

**核心功能**:
- ✅ 策略配置持久化 (PostgreSQL)
- ✅ Web UI 管理策略配置
- ✅ 配置版本管理
- ✅ 策略模板系统
- ✅ CRUD API 接口

**适用场景**:
- 标准策略 (动量、均值回归、多因子等)
- 新手用户
- 快速调参和优化

**技术栈**:
- Backend: FastAPI + PostgreSQL
- Frontend: React + Ant Design
- Core: 配置加载器

---

#### 2. [AI驱动的策略代码生成系统](./ai_strategy_generation.md)
**状态**: 📋 设计阶段
**版本**: v1.0.0
**日期**: 2026-02-08

**概述**: 通过自然语言生成完整策略代码

**核心功能**:
- ✅ 自然语言输入 (用户描述策略逻辑)
- ✅ DeepSeek API 生成代码
- ✅ 多层代码验证 (语法、安全、接口)
- ✅ 动态代码加载
- ✅ 沙箱测试执行

**适用场景**:
- 创新策略
- 高级用户
- 快速原型开发

**技术栈**:
- AI模型: DeepSeek Coder
- Backend: FastAPI + PostgreSQL + DeepSeek API
- Frontend: React + Monaco Editor
- Core: 动态代码加载器 + 安全模块

---

#### 3. [策略和模型管理 (已有)](./strategy_and_model_management.md)
**状态**: 📋 早期规划
**版本**: v0.1.0
**日期**: 2026-01-24

**概述**: 早期的策略和ML模型管理思路

**备注**: 此文档为历史参考，新设计请参考上面两个文档

---

### 其他规划

#### 4. [选股器 API 重构计划](./stock_selector_api_refactoring_plan.md)
**状态**: 📋 规划中

**概述**: 选股器 API 架构重构设计

---

## 🔗 相关文档

### Core 层文档
- **[Core 策略系统改造方案](../../../core/docs/planning/core_strategy_system_refactoring.md)** ⭐ 重要
  - Core 层如何支持两种策略管理方案
  - Core 层独立的安全防护措施
  - 策略加载器、安全模块实现

### 关系图

```
Backend 规划文档
├── strategy_config_management.md (方案1: 参数配置)
│   └── 描述 Backend 如何管理策略配置
│
├── ai_strategy_generation.md (方案2: AI代码生成)
│   └── 描述 Backend 如何调用 DeepSeek 生成代码
│
└── Core 实现文档
    └── core/docs/planning/core_strategy_system_refactoring.md
        └── 描述 Core 如何同时支持两种方案 + 安全防护
```

### 职责划分

| 职责 | Backend | Core |
|------|---------|------|
| **方案1: 参数配置** |
| 配置管理 (CRUD) | ✅ | ❌ |
| 配置存储 (DB) | ✅ | ❌ |
| 配置加载 | ❌ | ✅ |
| 策略实例化 | ❌ | ✅ |
| **方案2: AI代码生成** |
| AI Prompt 构建 | ✅ | ❌ |
| DeepSeek API 调用 | ✅ | ❌ |
| 初次代码验证 | ✅ | ❌ |
| 代码存储 (DB) | ✅ | ❌ |
| **Core独立验证** | ❌ | ✅ |
| 代码动态加载 | ❌ | ✅ |
| 运行时安全隔离 | ❌ | ✅ |
| **共同职责** |
| 审计日志 | ✅ | ✅ |
| 性能监控 | ✅ | ✅ |

---

## 📅 实施计划

### 建议优先级

1. **Phase 1**: 参数配置方案 (2-3周)
   - 更成熟、风险低
   - 能快速满足标准策略需求

2. **Phase 2**: Core 层改造 (3-4周)
   - 并行实施，准备基础设施
   - 安全模块、加载器

3. **Phase 3**: AI代码生成方案 (4-6周)
   - 创新功能
   - 需要更多测试和优化

### 依赖关系

```
策略参数配置方案
    ↓ 需要
Core 配置加载器
    ↓ 依赖
Core 安全基础设施
    ↑ 同时支持
AI代码生成方案
    ↓ 需要
Core 动态加载器 + 完整安全模块
```

---

## 🔐 安全性说明

两个方案都遵循**零信任原则**和**多层防御**:

### Backend 职责 (第一道防线)
- 参数配置: 参数类型和范围验证
- AI代码: Prompt过滤、AST分析、沙箱测试

### Core 职责 (第二道防线) ⭐ 关键
- 独立的代码验证 (不信任Backend)
- 运行时资源限制
- 受限命名空间
- 完整审计日志

**原因**: 即使Backend被攻破，Core仍能拦截恶意代码

---

## 📞 联系方式

**维护团队**: Architecture Team
**问题反馈**: [GitHub Issues](https://github.com/your-org/stock-analysis/issues)
**最后更新**: 2026-02-08
