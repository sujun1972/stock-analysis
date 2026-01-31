# 配置模板使用指南

**版本**: v2.0
**创建日期**: 2026-01-31

---

## 目录

- [一、模板系统介绍](#一模板系统介绍)
- [二、预设模板](#二预设模板)
- [三、使用模板](#三使用模板)
- [四、自定义模板](#四自定义模板)
- [五、模板最佳实践](#五模板最佳实践)
- [六、常见问题](#六常见问题)

---

## 一、模板系统介绍

### 1.1 什么是配置模板

配置模板是预先定义好的配置组合，可以快速应用到项目中，无需手动编辑大量配置项。

**核心特性**:
- ✅ 场景化配置（开发、生产、研究等）
- ✅ 模板继承（复用基础配置）
- ✅ 一键应用（自动生成 .env 文件）
- ✅ 配置建议（最佳实践提示）
- ✅ 版本管理（模板版本控制）

### 1.2 模板的优势

**相比手动配置的优势**:

| 特性 | 手动配置 | 使用模板 |
|------|---------|---------|
| 配置时间 | 15-30 分钟 | 30 秒 |
| 错误率 | 较高 | 极低 |
| 最佳实践 | 需要查阅文档 | 内置建议 |
| 场景切换 | 需要重新配置 | 一键切换 |
| 版本管理 | 需要手动管理 | 自动管理 |

### 1.3 使用场景

- **快速上手**: 新用户使用 `minimal` 模板快速开始
- **开发调试**: 使用 `development` 模板启用调试功能
- **生产部署**: 使用 `production` 模板确保性能和安全
- **因子研究**: 使用 `research` 模板启用完整因子库
- **模型训练**: 使用 `training` 模板优化 GPU 性能
- **策略回测**: 使用 `backtest` 模板优化回测速度

---

## 二、预设模板

Stock-Analysis Core 提供 6 个预设模板，覆盖常见使用场景。

### 2.1 minimal - 最小配置

**适用场景**: 快速上手、初次体验

**特点**:
- 最简配置，使用所有默认值
- 使用免费的 AkShare 数据源
- 启用调试模式便于学习

**配置摘要**:
```yaml
app:
  environment: development
  debug: true
  log_level: INFO

database:
  host: localhost
  database: stock_analysis

data_source:
  provider: akshare  # 免费数据源
```

**使用建议**:
- 首次使用建议下载 30 天数据测试
- 更多配置选项可参考文档或运行高级向导

### 2.2 development - 开发环境

**适用场景**: 本地开发、功能调试

**特点**:
- 启用调试模式和详细日志
- 使用 threading 后端（方便调试）
- 较小的并发数和数据集

**配置摘要**:
```yaml
app:
  environment: development
  debug: true
  log_level: DEBUG

performance:
  parallel:
    backend: threading  # 便于调试
    n_workers: 4
  gpu:
    enable_gpu: false
```

**使用建议**:
- 使用小数据集（30天）快速迭代
- 可以禁用特征缓存测试最新代码
- threading 后端避免多进程调试复杂度

### 2.3 production - 生产环境

**适用场景**: 生产部署、长期运行

**特点**:
- 关闭调试模式，提升性能
- 高并发配置（multiprocessing）
- 完整的监控和错误追踪
- 使用环境变量保护敏感信息

**配置摘要**:
```yaml
app:
  environment: production
  debug: false
  log_level: INFO

database:
  host: ${DB_HOST}  # 从环境变量读取
  password: ${DB_PASSWORD}

performance:
  parallel:
    backend: multiprocessing
    n_workers: 15
  gpu:
    enable_gpu: true
  memory:
    enable_streaming: true

monitoring:
  enabled: true
  metrics_collection: true
```

**使用建议**:
- 必须关闭调试模式
- 使用强密码并定期更换
- 启用监控和告警系统
- 定期备份数据库和模型文件

### 2.4 research - 研究环境

**适用场景**: 因子挖掘、策略研究

**特点**:
- 启用完整因子库（125+ 因子）
- 使用 Tushare 数据源（更全面）
- 独立的研究数据库和目录

**配置摘要**:
```yaml
app:
  environment: research

database:
  database: stock_analysis_research

data_source:
  provider: tushare
  tushare_token: ${TUSHARE_TOKEN}

paths:
  data_dir: /data/research
  models_dir: /data/research/models

features:
  technical_indicators:
    enabled: true
    ma_periods: [5, 10, 20, 30, 60, 120]
  alpha_factors:
    enabled: true
    categories: [momentum, reversal, volatility, volume]
```

**使用建议**:
- 建议使用 Tushare 获取更全面的数据
- 启用因子缓存加速重复计算
- 定期导出研究结果和模型版本

### 2.5 backtest - 回测优化

**适用场景**: 大规模策略回测

**特点**:
- 继承 production 配置
- 向量化计算优化
- 高并发、大批量处理
- 内存优化（流式处理）

**配置摘要**:
```yaml
extends: production  # 继承生产环境配置

performance:
  parallel:
    n_workers: 12
    chunk_size: 10000
  memory:
    enable_streaming: true

backtest:
  vectorized: true
  enable_cache: true
  parallel_strategies: true
```

**使用建议**:
- 使用向量化计算提升速度
- 启用流式处理节省内存
- 多进程并行回测多个策略
- 启用结果缓存避免重复计算

### 2.6 training - 模型训练

**适用场景**: 机器学习模型训练

**特点**:
- GPU 加速（CUDA 或 Apple MPS）
- 混合精度训练
- 自动批次大小
- 早停和检查点

**配置摘要**:
```yaml
app:
  environment: training

performance:
  parallel:
    backend: threading  # GPU 训练使用 threading
  gpu:
    enable_gpu: true
    device_id: 0
    mixed_precision: true

training:
  batch_size: auto
  auto_tune: true
  early_stopping: true
  save_checkpoints: true
```

**使用建议**:
- 建议启用 GPU 加速
- 混合精度训练可额外加速 1.5-2 倍
- 使用自动批次大小优化 GPU 利用率
- 定期保存训练检查点

---

## 三、使用模板

### 3.1 列出所有模板

```bash
# 查看所有可用模板
stock-cli config templates-list

# JSON 格式输出
stock-cli config templates-list -f json
```

**输出示例**:
```
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ 模板名称     ┃ 描述                 ┃ 版本 ┃ 标签                ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ minimal      │ 最简配置，快速上手…  │ 2.0  │ minimal, beginner   │
│ development  │ 适合本地开发和调试…  │ 2.0  │ development, debug  │
│ production   │ 适合生产部署…        │ 2.0  │ production          │
└──────────────┴──────────────────────┴──────┴─────────────────────┘
```

### 3.2 查看模板详情

```bash
# 查看模板基本信息
stock-cli config templates-show development

# 查看完整配置内容
stock-cli config templates-show development --settings
```

### 3.3 应用模板

```bash
# 预览模式（不实际写入文件）
stock-cli config templates-apply development --dry-run

# 实际应用（会备份现有 .env 文件）
stock-cli config templates-apply development

# 应用到指定路径
stock-cli config templates-apply production -o /path/to/.env
```

**应用流程**:

1. **预览配置** (可选):
   ```bash
   stock-cli config templates-apply minimal --dry-run
   ```

2. **确认应用**:
   - 如果 `.env` 已存在，会自动备份为 `.env.backup_TIMESTAMP`
   - 生成新的 `.env` 文件

3. **查看建议**:
   - 应用成功后会显示配置建议

### 3.4 对比模板

```bash
# 对比两个模板的差异
stock-cli config templates-diff development production

# JSON 格式输出
stock-cli config templates-diff minimal backtest -f json
```

**输出示例**:
```
╭─────────────── 模板对比 ───────────────╮
│     development vs production          │
╰────────────────────────────────────────╯

新增配置:
  + monitoring.enabled: true
  + performance.gpu.enable_gpu: true

修改配置:
  ~ app.debug: true → false
  ~ app.log_level: DEBUG → INFO
  ~ performance.parallel.n_workers: 4 → 15

总差异数: 5
```

---

## 四、自定义模板

### 4.1 导出当前配置为模板

如果你已经手动配置好了 `.env` 文件，可以导出为模板以便复用。

```bash
# 基本导出
stock-cli config templates-export my-template -d "我的自定义配置"

# 指定版本和标签
stock-cli config templates-export my-prod \
    -d "我的生产配置" \
    -v "2.0" \
    -t "production,custom"

# 从指定 .env 文件导出
stock-cli config templates-export my-config \
    -d "测试配置" \
    --env-file /path/to/.env
```

**导出后的模板位置**:
```
src/config/templates/presets/my-template.yaml
```

### 4.2 创建模板文件

你也可以直接创建 YAML 模板文件。

**模板结构**:
```yaml
name: "模板名称"
description: "模板描述"
version: "1.0"
tags: ["tag1", "tag2"]

# 可选：继承其他模板
extends: "base_template"

# 配置内容
settings:
  app:
    environment: "development"
    debug: true

  database:
    host: "localhost"
    port: 5432

  # ... 更多配置

# 可选：使用建议
recommendations:
  - "建议 1"
  - "建议 2"
```

**保存位置**:
```
src/config/templates/presets/your-template.yaml
```

### 4.3 模板继承

模板可以继承其他模板，实现配置复用。

**示例 - 创建自定义生产模板**:

```yaml
name: "我的生产配置"
description: "基于标准生产配置的自定义版本"
version: "1.0"
extends: "production"  # 继承 production 模板

settings:
  # 只需要覆盖需要修改的配置
  database:
    database: "my_stock_db"  # 自定义数据库名

  performance:
    parallel:
      n_workers: 20  # 增加并发数

  # 新增自定义配置
  custom:
    feature: "enabled"
```

**继承规则**:
- 子模板会继承父模板的所有配置
- 子模板的配置会覆盖父模板的同名配置
- 嵌套字典会深度合并（不是整体替换）

### 4.4 导入外部模板

如果你从其他地方获得了模板文件，可以导入到系统中。

```bash
# 导入模板
stock-cli config import-template /path/to/external-template.yaml
```

---

## 五、模板最佳实践

### 5.1 命名规范

**建议的命名方式**:
- 使用小写字母和连字符: `my-template`
- 避免使用特殊字符
- 名称要能反映用途: `prod-gpu`, `dev-debug`

**不推荐**:
- `MyTemplate` (大写)
- `my_template` (下划线)
- `template-123` (纯数字)

### 5.2 版本管理

**版本号格式**: `主版本.次版本`

- 主版本变更: 配置结构有重大变化
- 次版本变更: 增加新配置或微调

**示例**:
```yaml
version: "2.1"  # 在 2.0 基础上增加了监控配置
```

### 5.3 标签使用

**推荐标签**:
- 环境类型: `development`, `production`, `staging`
- 用途: `training`, `backtest`, `research`
- 特性: `gpu`, `distributed`, `monitoring`
- 难度: `beginner`, `advanced`

**示例**:
```yaml
tags: ["production", "gpu", "monitoring", "advanced"]
```

### 5.4 配置建议

每个模板都应该包含使用建议，帮助用户正确使用。

**好的建议示例**:
```yaml
recommendations:
  - "生产环境必须关闭调试模式"
  - "建议使用强密码并定期更换"
  - "定期备份数据库和模型文件"
  - "监控磁盘空间，至少保留 10 GB"
```

### 5.5 环境变量引用

对于敏感信息或环境特定的配置，使用环境变量引用。

**示例**:
```yaml
settings:
  database:
    host: "${DB_HOST}"          # 引用环境变量
    password: "${DB_PASSWORD}"  # 敏感信息

  data_source:
    tushare_token: "${TUSHARE_TOKEN}"
```

**使用时设置环境变量**:
```bash
export DB_HOST=prod.database.com
export DB_PASSWORD=secure_password
export TUSHARE_TOKEN=your_token

stock-cli config templates-apply production
```

---

## 六、常见问题

### 6.1 如何切换环境?

**场景**: 从开发环境切换到生产环境

```bash
# 1. 备份当前配置
cp .env .env.dev.backup

# 2. 应用新模板
stock-cli config templates-apply production

# 3. 设置环境特定的变量
export DB_HOST=prod.example.com
export DB_PASSWORD=secure_password
```

### 6.2 模板应用后如何修改个别配置?

应用模板后，直接编辑 `.env` 文件即可。

**方式 1 - 直接编辑** (推荐):
```bash
# 编辑 .env 文件
vim .env

# 修改特定配置
DATABASE_HOST=custom.host.com
```

**方式 2 - 环境变量覆盖**:
```bash
# 环境变量优先级高于 .env 文件
export DATABASE_HOST=custom.host.com
```

### 6.3 如何恢复之前的配置?

每次应用模板都会自动备份。

```bash
# 查看备份文件
ls -la .env.backup_*

# 恢复备份
cp .env.backup_20260131_094523 .env
```

### 6.4 模板中的配置项不全怎么办?

模板只包含常用配置。如需更多配置项:

**方式 1 - 手动添加**:
直接编辑 `.env` 文件，添加所需配置项。

**方式 2 - 导出后修改**:
```bash
# 1. 应用基础模板
stock-cli config templates-apply development

# 2. 手动添加配置项
echo "CUSTOM_CONFIG=value" >> .env

# 3. 导出为新模板
stock-cli config templates-export my-custom -d "自定义模板"
```

### 6.5 如何共享自定义模板?

**方式 1 - 导出 YAML 文件**:
```bash
# 模板文件位置
src/config/templates/presets/my-template.yaml

# 直接复制分享
cp src/config/templates/presets/my-template.yaml /path/to/share/
```

**方式 2 - 通过版本控制**:
将 `.env` 文件（脱敏后）提交到项目的 `config/templates/` 目录。

### 6.6 生产环境如何保护敏感信息?

**推荐做法**:

1. 使用环境变量引用:
   ```yaml
   database:
     password: "${DB_PASSWORD}"
   ```

2. 不要将敏感信息写入模板文件

3. 在部署时设置环境变量:
   ```bash
   export DB_PASSWORD=secure_password
   ```

4. 使用密钥管理工具（如 AWS Secrets Manager、HashiCorp Vault）

---

## 附录

### A. 命令速查表

```bash
# 列出所有模板
stock-cli config templates-list

# 查看模板详情
stock-cli config templates-show <name>
stock-cli config templates-show <name> --settings

# 应用模板
stock-cli config templates-apply <name>
stock-cli config templates-apply <name> --dry-run
stock-cli config templates-apply <name> -o /path/to/.env

# 对比模板
stock-cli config templates-diff <name1> <name2>
stock-cli config templates-diff <name1> <name2> -f json

# 导出模板
stock-cli config templates-export <name> -d "描述"
stock-cli config templates-export <name> -d "描述" -v "2.0" -t "tag1,tag2"

# 查看当前配置
stock-cli config show
stock-cli config show -f json

# 帮助
stock-cli config help
```

### B. 模板文件格式参考

```yaml
# ==================== 必需字段 ====================
name: "模板名称"
description: "模板描述"
version: "1.0"

# ==================== 可选字段 ====================
extends: "parent_template"  # 继承其他模板
tags: ["tag1", "tag2"]      # 标签列表
author: "作者名称"           # 作者信息

# ==================== 配置内容 ====================
settings:
  # 应用配置
  app:
    environment: "development"
    debug: true
    log_level: "DEBUG"

  # 数据库配置
  database:
    host: "localhost"
    port: 5432
    database: "stock_analysis"
    user: "stock_user"
    password: "${DB_PASSWORD}"  # 环境变量引用

  # 数据源配置
  data_source:
    provider: "akshare"
    tushare_token: "${TUSHARE_TOKEN}"

  # 路径配置
  paths:
    data_dir: "/data"
    models_dir: "/data/models"
    cache_dir: "/data/cache"
    results_dir: "/data/results"

  # 机器学习配置
  ml:
    default_target_period: 5
    default_scaler_type: "robust"
    cache_features: true
    feature_version: "v2.0"

  # 性能配置
  performance:
    parallel:
      backend: "threading"
      n_workers: 4
      chunk_size: 1000
    gpu:
      enable_gpu: false
      device_id: 0
    memory:
      enable_streaming: false
      memory_limit_gb: 8

# ==================== 使用建议 ====================
recommendations:
  - "建议 1: 使用小数据集进行快速迭代"
  - "建议 2: 启用缓存加速计算"
  - "建议 3: 定期备份数据和模型"
```

### C. 相关文档

- [配置系统完整指南](CONFIG_GUIDE.md) - 详细的配置说明
- [CLI 使用指南](CLI_GUIDE.md) - 命令行工具使用
- [开发文档](DEVELOPMENT.md) - 开发者指南

---

**文档版本**: v2.0
**更新日期**: 2026-01-31
**作者**: Stock-Analysis Team
