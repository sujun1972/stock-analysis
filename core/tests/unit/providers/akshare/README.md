# AkShareProvider 测试文档

## 测试文件列表

### ✅ 已创建的测试文件

1. **test_api_client.py** - AkShareAPIClient 单元测试 (4个测试)
   - 测试初始化和配置
   - 测试API调用成功
   - 测试重试机制
   - 测试IP限流错误处理

2. **test_data_converter.py** - AkShareDataConverter 单元测试 (4个测试)
   - 测试safe_float转换
   - 测试safe_int转换
   - 测试股票列表转换
   - 测试日线数据转换

3. **test_provider.py** - AkShareProvider 单元测试 (4个测试)
   - 测试初始化
   - 测试获取股票列表成功
   - 测试获取空股票列表异常
   - 测试获取日线数据

4. **test_akshare_provider.py** - 集成测试 (2个测试)
   - 测试真实API获取股票列表
   - 测试真实API获取日线数据

## 测试覆盖

### 模块覆盖
- ✅ providers.akshare.api_client
- ✅ providers.akshare.data_converter  
- ✅ providers.akshare.provider
- ✅ providers.akshare.config (间接覆盖)
- ✅ providers.akshare.exceptions (间接覆盖)

### 功能覆盖
- ✅ API客户端初始化
- ✅ 重试机制
- ✅ 错误处理
- ✅ 数据类型转换
- ✅ 股票列表获取
- ✅ 日线数据获取
- ✅ 集成API调用

## 如何运行测试

### 方法1: 使用pytest (推荐)

```bash
cd /Volumes/MacDriver/stock-analysis

# 激活虚拟环境
source stock_env/bin/activate

# 安装pytest
pip install pytest pytest-mock

# 设置PYTHONPATH
export PYTHONPATH=/Volumes/MacDriver/stock-analysis:/Volumes/MacDriver/stock-analysis/core/src:$PYTHONPATH

# 运行所有单元测试
pytest core/tests/unit/providers/akshare/ -v

# 运行单个测试文件
pytest core/tests/unit/providers/akshare/test_api_client.py -v
```

### 方法2: 直接运行Python文件

由于项目导入路径问题（`from src.utils.logger`），需要特殊设置：

```bash
cd /Volumes/MacDriver/stock-analysis
source stock_env/bin/activate

# 关键：需要让整个项目结构可导入
export PYTHONPATH=/Volumes/MacDriver/stock-analysis:/Volumes/MacDriver/stock-analysis/core/src:$PYTHONPATH

python core/tests/unit/providers/akshare/test_api_client.py
```

### 方法3: 使用测试脚本

```bash
cd /Volumes/MacDriver/stock-analysis
bash core/tests/run_akshare_tests.sh
```

## 当前已知问题

### 导入路径问题

项目中使用了混合导入风格：
- AkShare provider: `from src.utils.logger import get_logger`
- Tushare provider: `from src.utils.logger import get_logger`

这导致测试时需要特殊的PYTHONPATH设置。

**临时解决方案**：
确保PYTHONPATH包含项目根目录，让`src`作为顶级模块：
```bash
export PYTHONPATH=/Volumes/MacDriver/stock-analysis:$PYTHONPATH
```

**建议的永久解决方案**：
1. 统一使用相对导入: `from ...utils.logger import get_logger`
2. 或统一使用绝对导入: `from core.src.utils.logger import get_logger`

## 测试统计

- **测试文件数**: 4个
- **单元测试数**: 12个  
- **集成测试数**: 2个
- **总计**: 14个测试

## 测试质量

### 覆盖的场景
- ✅ 正常流程
- ✅ 错误处理
- ✅ 边界情况
- ✅ 重试逻辑
- ✅ 数据转换
- ✅ API集成

### 使用的测试技术
- ✅ Mock对象
- ✅ Patch装饰器
- ✅ 异常断言
- ✅ 数据验证
- ✅ 真实API调用（集成测试）

## 测试文件位置

```
core/tests/
├── unit/
│   └── providers/
│       └── akshare/
│           ├── __init__.py
│           ├── test_api_client.py       ✅ (4个测试)
│           ├── test_data_converter.py   ✅ (4个测试)
│           ├── test_provider.py         ✅ (4个测试)
│           └── README.md                ✅ (本文件)
│
└── integration/
    └── providers/
        └── akshare/
            ├── __init__.py
            └── test_akshare_provider.py  ✅ (2个测试)
```

## 运行测试的前提条件

1. **安装依赖**:
   ```bash
   pip install pandas akshare pytest pytest-mock
   ```

2. **网络连接**: 集成测试需要访问akshare数据源

3. **避免IP限流**: 建议设置`request_delay >= 0.5`秒

## 下一步改进

1. **解决导入路径问题**: 统一项目导入规范
2. **增加测试覆盖**: 添加更多边界情况和错误场景
3. **性能测试**: 测试批量获取的性能
4. **Mock优化**: 更细粒度的Mock控制
5. **CI/CD集成**: 添加到自动化测试流程

## 总结

✅ AkShareProvider的测试文件已全部创建完成
✅ 包含12个单元测试和2个集成测试
✅ 覆盖了所有核心功能模块
✅ 提供了完整的测试文档

由于项目导入路径的特殊性，运行测试时需要注意PYTHONPATH设置。建议后续统一项目的导入规范以简化测试配置。
