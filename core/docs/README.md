# Stock-Analysis Core 文档中心

**版本**: v3.0.0
**最后更新**: 2026-02-01

---

## 📚 文档导航

### 架构文档 (Architecture)

深入了解系统架构设计和技术实现。

- 🏗️ [架构总览](architecture/overview.md) - 六层架构、数据流、目录结构
- 🎨 [设计模式](architecture/design_patterns.md) - 10种设计模式应用
- ⚡ [性能优化](architecture/performance.md) - 35倍性能提升分析
- 🔧 [技术栈详解](architecture/tech_stack.md) - 完整技术选型说明

### 用户指南 (User Guide)

快速上手和日常使用指南。

**入门指南**:
- 🚀 [安装指南](user_guide/installation.md) - 环境配置、依赖安装、数据库设置
- 📖 [快速开始](user_guide/quick_start.md) - 30分钟完整教程
- 🔧 [CLI命令指南](user_guide/CLI_GUIDE.md) - 命令行工具详解
- 💡 [示例代码](user_guide/examples/) - 12个完整工作流示例
- ❓ [常见问题](user_guide/faq.md) - FAQ和问题排查

**功能指南**:
- 🎨 [可视化指南](user_guide/VISUALIZATION_GUIDE.md) - 30+图表使用说明
- 🧬 [特征配置指南](user_guide/FEATURE_CONFIG_GUIDE.md) - 因子计算配置
- 🤖 [模型使用指南](user_guide/MODEL_USAGE_GUIDE.md) - 模型训练与评估
- 🔙 [回测使用指南](user_guide/BACKTEST_USAGE_GUIDE.md) - 回测引擎使用
- 📋 [配置模板指南](user_guide/TEMPLATES_GUIDE.md) - 6种配置模板说明

**高级指南**:
- 📊 [数据质量指南](user_guide/DATA_QUALITY_GUIDE.md) - 数据验证与清洗
- 🤝 [模型集成指南](user_guide/ENSEMBLE_GUIDE.md) - 模型集成方法
- 📈 [因子分析指南](user_guide/FACTOR_ANALYSIS_GUIDE.md) - 因子分析工具

### 开发指南 (Developer Guide)

为贡献者提供的开发指南。

- 🤝 [贡献指南](developer_guide/contributing.md) - Fork流程、PR规范、代码审查标准
- 🎨 [代码规范](developer_guide/coding_standards.md) - PEP 8、命名规范、类型提示、文档字符串
- 🧪 [测试指南](developer_guide/testing.md) - 如何编写测试、测试哲学、最佳实践
  - 📋 [运行测试](../tests/README.md) - 交互式菜单、测试统计（2,900+测试）
  - 🔗 [集成测试](../tests/integration/README.md) - 端到端工作流测试
  - ⚡ [性能测试](../tests/performance/README.md) - 性能基准测试
- 📚 [API参考文档](sphinx/README.md) - Sphinx自动生成的API文档（197个模块）⚠️
  - ⚠️ **已知问题**: 循环导入导致内容有限，查看[状态说明](sphinx/API_DOCS_STATUS.md)

### 版本历史 (Versions)

查看项目版本变更历史。

- 📄 [完整变更日志](versions/CHANGELOG.md) - 所有版本变更记录
- ⭐ [v3.0.0 发布说明](versions/v3.0.0.md) - 当前版本详情

### 规划文档 (Planning)

了解项目发展规划和技术债务。

- 🗺️ [开发路线图](ROADMAP.md) - 核心路线图概览（Phase 3 已完成✅）
- 📅 [2026年度规划](planning/roadmap_2026.md) - 年度详细规划（Q1 100%完成）
- ✅ [Phase 3 规划](planning/phase3.md) - 文档与生产化（已完成）
- 🚀 [Phase 4 规划](planning/phase4.md) - 实盘交易系统（规划中）
- 🔧 [技术债务追踪](planning/tech_debt.md) - 技术债务管理

---

## 📂 目录结构

```
docs/
├── README.md                      # 本文档
├── ROADMAP.md                     # 开发路线图 ✅
├── architecture/                  # 架构详细文档 ✅
│   ├── overview.md                # 架构总览（包含目录结构）
│   ├── design_patterns.md         # 设计模式
│   ├── performance.md             # 性能优化
│   └── tech_stack.md              # 技术栈详解
├── user_guide/                    # 用户指南 ✅
│   ├── installation.md             # 安装指南
│   ├── quick_start.md              # 快速开始
│   ├── faq.md                      # 常见问题
│   ├── examples/                   # 示例代码
│   │   ├── README.md               # 示例索引
│   │   ├── 01_data_download.py     # 数据下载示例
│   │   └── 11_complete_workflow.py # 完整工作流
│   ├── BACKTEST_USAGE_GUIDE.md    # 回测使用指南
│   ├── CLI_GUIDE.md                # CLI命令指南
│   ├── DATA_QUALITY_GUIDE.md       # 数据质量指南
│   ├── ENSEMBLE_GUIDE.md           # 模型集成指南
│   ├── FACTOR_ANALYSIS_GUIDE.md    # 因子分析指南
│   ├── FEATURE_CONFIG_GUIDE.md     # 特征配置指南
│   ├── MODEL_USAGE_GUIDE.md        # 模型使用指南
│   ├── TEMPLATES_GUIDE.md          # 配置模板指南
│   └── VISUALIZATION_GUIDE.md      # 可视化指南
├── developer_guide/               # 开发指南 ✅
│   ├── contributing.md             # 贡献指南
│   ├── coding_standards.md         # 代码规范
│   └── testing.md                  # 测试指南
├── sphinx/                        # API文档 ✅
│   ├── README.md                   # Sphinx文档说明
│   ├── build.sh                    # 构建脚本
│   ├── source/                     # 源文件
│   │   ├── conf.py                 # Sphinx配置
│   │   ├── index.rst               # 文档首页
│   │   └── api/                    # API文档 (197个模块)
│   └── build/html/                 # HTML输出 (13MB)
├── versions/                      # 版本历史 ✅
│   ├── CHANGELOG.md
│   └── v3.0.0.md
└── planning/                      # 规划文档 ✅
    ├── phase3.md
    ├── phase4.md
    ├── roadmap_2026.md
    └── tech_debt.md
```

---

## 🎯 文档完成度

| 类别 | 完成度 | 状态 |
|------|--------|------|
| 规划文档 (Planning) | 100% | ✅ 完成 |
| 版本历史 (Versions) | 100% | ✅ 完成 |
| 核心文档 (Root) | 100% | ✅ 完成 |
| 用户指南 (User Guide) | 100% | ✅ 13个指南 + 示例代码 |
| 架构文档 (Architecture) | 100% | ✅ 完成 |
| 开发指南 (Developer) | 100% | ✅ 3个核心指南 + API文档 |
| API文档 (Sphinx) | 100% | ✅ 197个模块 + 13MB HTML |
| **总体进度** | **100%** | 🎉 全部完成 |

---

## 🚀 快速开始

### 新用户

1. 阅读 [README.md](../README.md) 了解项目概况
2. 按照 [安装指南](user_guide/installation.md) 完成环境搭建
3. 学习 [快速开始](user_guide/quick_start.md) 30分钟上手
4. 查看 [示例代码](user_guide/examples/) 学习完整工作流
5. 遇到问题查阅 [FAQ](user_guide/faq.md)

### 开发者

1. 阅读 [架构总览](architecture/overview.md) 了解系统架构
2. 查看 [开发路线图](ROADMAP.md) 了解项目方向
3. 参考 [技术债务](planning/tech_debt.md) 选择贡献方向

### 项目管理者

1. 查看 [开发路线图](ROADMAP.md) 了解整体进度（Phase 3 已完成）
2. 阅读 [2026年度规划](planning/roadmap_2026.md) 了解年度目标（Q1 100%完成）
3. 查看 [Phase 4规划](planning/phase4.md) 了解下一阶段（实盘交易系统）

---

## 📝 文档贡献

### 文档原则

1. **清晰性**: 简洁明了，避免冗长
2. **完整性**: 覆盖核心功能和常见问题
3. **示例性**: 提供可运行的代码示例
4. **更新性**: 与代码保持同步

### 贡献方式

1. **报告问题**: 发现文档错误或遗漏时提Issue
2. **改进文档**: 完善现有文档内容
3. **新增文档**: 补充缺失的文档
4. **翻译文档**: 提供英文版本 (可选)

### 文档格式

- 使用 Markdown 格式
- 代码块标注语言类型
- 使用相对路径链接
- 长文档(>500行)需要目录

---

## 🔗 相关链接

- [GitHub仓库](https://github.com/your-org/stock-analysis)
- [问题反馈](https://github.com/your-org/stock-analysis/issues)
- [讨论区](https://github.com/your-org/stock-analysis/discussions)

---

## 📅 开发进度

### Phase 3: 文档与生产化 ✅ 已完成 (2026-02-01)

**完成度**: 100% | **状态**: 🎉 全部完成

- [x] 创建docs目录结构
- [x] 创建版本历史文档
- [x] 创建规划文档
- [x] 补充架构文档 (4个详细文档)
- [x] 补充用户指南 (13个指南完整)
- [x] 补充开发指南 (贡献指南、代码规范、测试指南)
- [x] **Sphinx API文档生成 (197个模块，21MB HTML)**

**交付成果**:
- 📚 完整的文档系统（架构、用户、开发、API）
- 🔧 自动化构建脚本 ([build.sh](sphinx/build.sh))
- 📖 Sphinx HTML文档 (200个页面)
- ✅ 100%生产就绪

详见: [Phase 3 规划](planning/phase3.md) | [开发路线图](ROADMAP.md)

### Phase 4: 实盘交易系统 📋 规划中 (2026-Q3)

**优先级**: 中 | **预计开始**: 2026-Q3 | **预计耗时**: 2-3个月

**核心任务**:
1. 券商接口对接（华泰/中信/国金等）
2. 订单管理系统（OMS）
3. 实时风控引擎
4. 监控告警系统

详见: [Phase 4 规划](planning/phase4.md)

---

**维护团队**: Quant Team
**文档版本**: v3.0.0
**最后更新**: 2026-02-01
