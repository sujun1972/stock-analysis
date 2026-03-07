# 策略系统设计概览

**项目**: Stock-Analysis
**版本**: v1.0.0
**日期**: 2026-02-08
**状态**: 📋 设计完成，待实施

---

## 📋 文档结构

```
stock-analysis/
│
├── backend/docs/planning/
│   ├── README.md ⭐ Backend规划总览
│   ├── strategy_config_management.md (方案1: 参数配置)
│   ├── ai_strategy_generation.md (方案2: AI代码生成)
│   └── ...
│
└── core/docs/planning/
    ├── core_strategy_system_refactoring.md ⭐ Core层改造方案
    └── tech_debt.md
```

---

## 🎯 双方案设计

### 方案1: 策略参数配置管理
**文档**: [backend/docs/planning/strategy_config_management.md](backend/docs/planning/strategy_config_management.md)

**核心思路**: 预定义策略类型 + 参数化配置

```
用户在Web UI配置参数
    ↓
保存到 strategy_configs 表
    ↓
Core 从数据库加载配置
    ↓
实例化为预定义策略类 (MomentumStrategy等)
```

**适用场景**:
- ✅ 标准策略 (动量、均值回归、多因子)
- ✅ 新手用户
- ✅ 快速调参

**优势**:
- 简单安全
- 快速实施
- 稳定可靠

---

### 方案2: AI驱动的策略代码生成
**文档**: [backend/docs/planning/ai_strategy_generation.md](backend/docs/planning/ai_strategy_generation.md)

**核心思路**: 自然语言描述 → AI生成完整代码 → 动态加载执行

```
用户输入: "小盘股,市盈率<30,股价<20日均线"
    ↓
Backend 调用 DeepSeek API 生成代码
    ↓
多层验证 (语法、安全、接口)
    ↓
保存到 ai_strategies 表
    ↓
Core 动态加载并安全执行
```

**适用场景**:
- ✅ 创新策略
- ✅ 高级用户
- ✅ 快速原型

**优势**:
- 极致灵活
- 创新友好
- 降低开发门槛

---

### 两个方案的关系

**互补共存**，不是互斥：

| 维度 | 方案1 (参数配置) | 方案2 (AI代码生成) |
|------|-----------------|-------------------|
| **灵活性** | ⭐⭐⭐ 受限于预定义策略 | ⭐⭐⭐⭐⭐ 可生成任意策略 |
| **安全性** | ⭐⭐⭐⭐⭐ 非常安全 | ⭐⭐⭐⭐ 需要多层防护 |
| **易用性** | ⭐⭐⭐⭐⭐ 表单配置 | ⭐⭐⭐⭐ 自然语言输入 |
| **成熟度** | ⭐⭐⭐⭐⭐ 成熟方案 | ⭐⭐⭐ 创新方案 |
| **实施难度** | ⭐⭐⭐ 较容易 | ⭐⭐⭐⭐⭐ 复杂 |
| **用户群体** | 新手、标准需求 | 高级用户、创新需求 |

**建议**: 两个都实现，优先级: 方案1 → 方案2

---

## 🏗️ Core层统一架构

**文档**: [core/docs/planning/core_strategy_system_refactoring.md](core/docs/planning/core_strategy_system_refactoring.md)

### 统一的策略工厂

```python
from core.strategies import StrategyFactory

factory = StrategyFactory()

# 方式1: 预定义策略 (现有方式)
strategy = factory.create('momentum', {'lookback_period': 20})

# 方式2: 从配置加载 (参数配置方案)
strategy = factory.create_from_config(config_id=123)

# 方式3: 从AI代码加载 (AI代码生成方案)
strategy = factory.create_from_code(strategy_id=456)

# 统一使用
signals = strategy.generate_signals(prices)
```

### 核心新增模块

```
core/src/strategies/
│
├── loaders/ (加载器) ⭐新增
│   ├── config_loader.py          # 方案1专用
│   ├── dynamic_loader.py         # 方案2专用
│   └── loader_factory.py         # 统一接口
│
├── security/ (安全模块) ⭐新增
│   ├── code_sanitizer.py         # 代码净化
│   ├── permission_checker.py     # 权限检查
│   ├── resource_limiter.py       # 资源限制
│   └── audit_logger.py           # 审计日志
│
└── predefined/ (预定义策略) ⭐重组
    ├── momentum_strategy.py
    ├── mean_reversion_strategy.py
    └── multi_factor_strategy.py
```

---

## 🔐 多层安全防护

### 为什么Core需要独立安全验证？

**零信任原则**: 不信任Backend的验证结果

**防护场景**:
1. 数据库被攻破 → 恶意代码直接写入
2. Backend被绕过 → 攻击者直接调用Core
3. 代码被篡改 → 传输过程中修改

### 四层防御体系

```
┌─────────────────────────────────────────┐
│ 第1层: Backend验证 (初次检查)            │
│  - AI生成时的Prompt过滤                  │
│  - 代码保存前的AST分析                   │
│  - 沙箱测试                              │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 第2层: Core加载时验证 ⭐ (独立验证)      │
│  - 代码签名/哈希验证                     │
│  - 再次AST分析                           │
│  - 导入白名单检查                        │
│  - 危险函数检测                          │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 第3层: 运行时隔离 ⭐ (沙箱执行)          │
│  - 受限命名空间 (只能访问安全函数)       │
│  - 禁用危险内置函数 (eval/exec/open)     │
│  - 资源限制 (CPU 30s / 内存 512MB)       │
│  - 系统调用监控                          │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 第4层: 审计与监控 ⭐ (完整追踪)          │
│  - 所有操作完整日志                      │
│  - 异常行为告警                          │
│  - 性能指标收集                          │
│  - 自动回滚机制                          │
└─────────────────────────────────────────┘
```

### 核心安全措施

#### 1. 代码完整性验证
```python
# 验证代码未被篡改
if calculate_hash(code) != expected_hash:
    raise SecurityError("代码哈希不匹配，可能被篡改")
```

#### 2. 受限命名空间
```python
# 只允许访问安全的函数和模块
safe_globals = {
    '__builtins__': {'abs', 'len', 'min', 'max'},  # 安全函数
    'pd': pandas,
    'np': numpy,
}

exec(code, safe_globals)  # 不能访问 os, sys, eval等
```

#### 3. 资源限制
```python
with ResourceLimiter(max_memory=512MB, max_cpu=30s):
    strategy.generate_signals(prices)  # 自动终止超限操作
```

#### 4. 审计日志
```json
{
  "event": "strategy_load",
  "strategy_id": 456,
  "code_hash": "abc123...",
  "validation": {"safe": true, "risk_level": "low"},
  "timestamp": "2026-02-08T10:00:00Z"
}
```

---

## 📊 职责划分

| 职责 | Backend | Core |
|------|---------|------|
| **策略配置管理** | ✅ CRUD API | ❌ |
| **AI代码生成** | ✅ DeepSeek API | ❌ |
| **初次验证** | ✅ 语法检查 | ❌ |
| **代码存储** | ✅ PostgreSQL | ❌ |
| **配置加载** | ❌ | ✅ ConfigLoader |
| **代码动态加载** | ❌ | ✅ DynamicLoader |
| **独立安全验证** ⭐ | ❌ | ✅ Security模块 |
| **运行时隔离** ⭐ | ❌ | ✅ 受限命名空间 |
| **资源限制** ⭐ | ❌ | ✅ ResourceLimiter |
| **策略执行** | ❌ | ✅ BacktestEngine |
| **审计日志** | ✅ | ✅ 各自记录 |

**关键**: Core有完整的独立安全验证能力，不依赖Backend

---

## 🚀 实施计划

### 总体时间线: 7-10周

```
Phase 1: 参数配置方案 (2-3周)
├─ Backend: ConfigService + API
├─ Frontend: 配置管理UI
└─ Core: ConfigLoader

Phase 2: Core安全基础设施 (3-4周) ⭐ 关键
├─ Security模块 (CodeSanitizer等)
├─ DynamicLoader
├─ ResourceLimiter
└─ AuditLogger

Phase 3: AI代码生成方案 (4-6周)
├─ Backend: DeepSeek集成 + AIService
├─ Frontend: 代码编辑器 (Monaco)
└─ 端到端测试

Phase 4: 优化与上线 (1-2周)
├─ 性能优化
├─ 安全审计
└─ 文档完善
```

### 建议优先级

**高优先级 (P0)**:
1. ✅ Core安全模块 (CodeSanitizer, PermissionChecker)
2. ✅ 参数配置方案完整实现
3. ✅ 审计日志系统

**中优先级 (P1)**:
4. ✅ DynamicLoader + 资源限制
5. ✅ AI代码生成基础功能
6. ✅ 性能优化和缓存

**低优先级 (P2)**:
7. AI Prompt优化
8. 配置市场/分享功能
9. 高级监控和告警

---

## 📈 预期收益

### 用户体验
- 🎯 **降低门槛**: 自然语言即可创建策略
- 🚀 **提升效率**: 秒级生成代码，分钟级验证
- 🎨 **增强创新**: 不受预定义策略限制

### 技术价值
- 🔒 **安全加固**: 多层防护，即使Backend被攻破也能拦截
- 📦 **架构优化**: 统一接口，易扩展
- 🔍 **可追溯**: 完整审计日志

### 业务价值
- 💡 **差异化**: AI辅助量化策略开发，市场少有
- 📊 **提高留存**: 满足高级用户需求
- 🌟 **品牌提升**: 技术创新标杆

---

## ⚠️ 风险与挑战

### 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| AI生成代码质量不稳定 | 高 | 1. 优化Prompt工程<br>2. 多次生成取最佳<br>3. 人工审核机制 |
| 动态代码安全漏洞 | 高 | 1. 多层安全验证<br>2. 沙箱隔离<br>3. 定期安全审计 |
| 性能问题 | 中 | 1. 多级缓存<br>2. 懒加载<br>3. 资源限制 |

### 业务风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 用户学习成本 | 中 | 1. 详细文档<br>2. 视频教程<br>3. 示例模板 |
| AI成本控制 | 中 | 1. Token计费<br>2. 请求限流<br>3. 缓存策略 |

---

## 📞 联系方式

**维护团队**: Architecture Team
**问题反馈**: [GitHub Issues](https://github.com/your-org/stock-analysis/issues)
**文档贡献**: 欢迎提交PR完善文档

---

## 📚 推荐阅读顺序

1. **先读概览** (本文档) - 理解整体设计
2. **Backend方案**:
   - [backend/docs/planning/README.md](backend/docs/planning/README.md) - Backend总览
   - [strategy_config_management.md](backend/docs/planning/strategy_config_management.md) - 参数配置方案
   - [ai_strategy_generation.md](backend/docs/planning/ai_strategy_generation.md) - AI代码生成方案
3. **Core实现**:
   - [core/docs/planning/core_strategy_system_refactoring.md](core/docs/planning/core_strategy_system_refactoring.md) ⭐ 关键文档
4. **现有文档**:
   - [core/docs/strategies/README.md](core/docs/strategies/README.md) - 现有策略系统文档

---

## ✅ 实施状态更新 (2026-03-07)

### 已完成：完全数据库驱动的策略系统

**实施日期**: 2026-03-07
**状态**: ✅ 已部署生产环境

#### 核心架构变更

**旧架构** (本地文件驱动):
```
Backend API → StrategyFactory → 本地 .py 文件
```

**新架构** (数据库驱动):
```
Backend API → StrategyDynamicLoader → PostgreSQL → exec() → 策略实例
```

#### 关键组件

1. **StrategyDynamicLoader** ([backend/app/services/strategy_loader.py](../backend/app/services/strategy_loader.py))
   - 统一的策略加载入口
   - 支持入场策略和离场策略
   - 代码哈希验证 (SHA-256)
   - 安全的命名空间隔离
   - 自定义配置参数覆盖

2. **数据库迁移** ([backend/migrations/V010__insert_builtin_strategies.sql](../backend/migrations/V010__insert_builtin_strategies.sql))
   - 8个内置策略完整代码存储
   - 自动处理冲突 (ON CONFLICT DO UPDATE)
   - 默认 `publish_status='approved'`

3. **简化的回测API** ([backend/app/api/endpoints/backtest.py](../backend/app/api/endpoints/backtest.py))
   - 删除 ~80 行重复代码
   - 统一使用 StrategyDynamicLoader
   - 错误处理更一致

#### 已迁移策略

**入场策略 (3个)**:
- 动量入场策略 (MomentumStrategy)
- 均值回归入场策略 (MeanReversionStrategy)
- 多因子入场策略 (MultiFactorStrategy)

**离场策略 (5个)**:
- 止损离场策略 (StopLossExitStrategy)
- 止盈离场策略 (TakeProfitExitStrategy)
- 持仓时长离场策略 (HoldingPeriodExitStrategy)
- 移动止损离场策略 (TrailingStopExitStrategy)
- 自适应离场策略 (AdaptiveExitStrategy)

#### 实现的功能

- ✅ 所有策略代码存储在数据库
- ✅ 所有策略通过动态加载运行
- ✅ 移除 Core 层对本地策略文件的依赖
- ✅ 用户可以创建/编辑/删除策略
- ✅ 系统启动时无需本地策略文件
- ✅ 代码版本可追溯 (code_hash)
- ✅ 多租户支持 (user_id 绑定)

#### 技术成果

- **代码减少**: ~300 行
- **架构灵活性**: ⬆️⬆️⬆️
- **可维护性**: ⬆️⬆️
- **用户体验**: ⬆️⬆️⬆️

#### 下一步计划

1. **安全增强** (P1):
   - [ ] 添加代码安全验证 (AST 分析)
   - [ ] 限制导入为白名单模块
   - [ ] 添加 exec() 超时限制

2. **性能优化** (P2):
   - [ ] 添加策略实例缓存
   - [ ] 优化代码加载性能

3. **用户体验** (P3):
   - [ ] 前端策略编辑器 (Monaco Editor)
   - [ ] 策略版本管理
   - [ ] 策略性能统计

---

**最后更新**: 2026-03-07
**状态**: ✅ 数据库驱动架构已完成，系统运行稳定
