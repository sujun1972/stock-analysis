# 常见问题

**Frequently Asked Questions for Stock-Analysis Core**

**版本**: v3.0.0
**最后更新**: 2026-02-01

---

## 📋 目录

- [安装与配置](#安装与配置)
- [数据获取](#数据获取)
- [特征计算](#特征计算)
- [模型训练](#模型训练)
- [策略回测](#策略回测)
- [性能优化](#性能优化)
- [错误排查](#错误排查)
- [进阶使用](#进阶使用)

---

## 安装与配置

### Q1: 支持哪些Python版本？

**A**: 推荐使用 **Python 3.9 或 3.10**。

```bash
# 检查Python版本
python --version  # 应显示 Python 3.9.x 或 3.10.x

# 如果版本不符，建议使用pyenv安装
pyenv install 3.10.13
pyenv global 3.10.13
```

**不支持**:
- Python 3.8及以下（pandas 2.0需要3.9+）
- Python 3.11+（部分依赖包可能不兼容）

---

### Q2: pip install失败怎么办？

**A**: 常见解决方案：

```bash
# 方案1: 升级pip
pip install --upgrade pip setuptools wheel

# 方案2: 使用国内镜像（推荐）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 方案3: 清除缓存重装
pip install --no-cache-dir -r requirements.txt

# 方案4: 单独安装问题包
pip install pandas==2.0.0 --no-cache-dir
```

**常见问题包**:
- **TA-Lib**: 需要先安装C库（见Q3）
- **PyTorch**: 选择正确的CUDA版本（见Q4）
- **psycopg2**: 使用 `psycopg2-binary` 替代

---

### Q3: TA-Lib安装失败？

**A**: TA-Lib需要先安装C语言库：

**macOS**:
```bash
brew install ta-lib
pip install ta-lib
```

**Linux (Ubuntu/Debian)**:
```bash
# 下载并编译
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install

# 安装Python包
pip install ta-lib
```

**Windows**:
```bash
# 下载预编译包
# 访问: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib

# 安装（替换为实际文件名）
pip install TA_Lib‑0.4.28‑cp310‑cp310‑win_amd64.whl
```

---

### Q4: 如何安装GPU版本的PyTorch？

**A**: 根据CUDA版本选择：

```bash
# 检查CUDA版本
nvidia-smi  # 查看CUDA Version

# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# CPU版本（无GPU）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 验证GPU可用性
python -c "import torch; print(f'GPU可用: {torch.cuda.is_available()}')"
```

---

### Q5: 数据库连接失败？

**A**: 逐步排查：

**1. 检查PostgreSQL是否启动**:
```bash
# macOS
brew services list | grep postgresql

# Linux
sudo systemctl status postgresql

# 启动服务
brew services start postgresql  # macOS
sudo systemctl start postgresql  # Linux
```

**2. 检查端口**:
```bash
netstat -an | grep 5432
# 应显示 LISTEN 状态
```

**3. 检查配置文件**:
```yaml
# config/database.yaml
database:
  timescaledb:
    host: localhost  # ← 检查是否正确
    port: 5432
    database: stock_analysis
    user: postgres
    password: yourpassword  # ← 检查密码
```

**4. 测试连接**:
```bash
# 命令行连接测试
psql -h localhost -U postgres -d stock_analysis

# Python测试
python -c "from src.data.database_manager import DatabaseManager; db = DatabaseManager(); print(db.test_connection())"
```

**5. 常见错误**:
- `connection refused`: PostgreSQL未启动
- `authentication failed`: 密码错误
- `database does not exist`: 需先创建数据库
  ```bash
  createdb stock_analysis
  ```

---

## 数据获取

### Q6: 如何获取免费的A股数据？

**A**: 推荐使用 **AkShare**（完全免费）:

```python
from src.providers import DataProviderFactory

# 创建AkShare提供者
provider = DataProviderFactory.create_provider('akshare')

# 获取日线数据
data = provider.get_daily_data(
    stock_code='000001.SZ',
    start_date='2023-01-01',
    end_date='2023-12-31'
)

print(f"获取了 {len(data)} 条数据")
```

**优点**:
- ✅ 完全免费，无需注册
- ✅ 覆盖A股、港股、美股
- ✅ 数据更新及时

**注意事项**:
- 有频率限制（约10次/秒）
- 历史数据可能有延迟

---

### Q7: Tushare数据获取失败？

**A**: 检查以下几点：

**1. 确认Token有效**:
```python
# 访问 https://tushare.pro 注册并获取Token

# 设置Token
import tushare as ts
ts.set_token('YOUR_TOKEN_HERE')

# 测试
pro = ts.pro_api()
df = pro.daily(ts_code='000001.SZ', start_date='20230101', end_date='20231231')
print(len(df))
```

**2. 检查积分限制**:
- Tushare根据积分限制接口调用频率
- 访问 [个人中心](https://tushare.pro/user/token) 查看积分

**3. 配置文件**:
```yaml
# config/data_sources.yaml
data_sources:
  tushare:
    enabled: true
    token: "YOUR_TOKEN"  # ← 替换为真实Token
    rate_limit: 200
```

---

### Q8: 如何下载沪深300成分股数据？

**A**: 使用内置工具：

```python
from src.utils.stock_utils import get_index_components
from src.providers import DataProviderFactory

# 获取沪深300成分股列表
hs300_codes = get_index_components('000300.SH')
print(f"沪深300成分股数量: {len(hs300_codes)}")

# 批量下载
provider = DataProviderFactory.create_provider('akshare')

for code in hs300_codes:
    try:
        data = provider.get_daily_data(code, '2023-01-01', '2023-12-31')
        print(f"✅ {code}: {len(data)} 条数据")
    except Exception as e:
        print(f"❌ {code}: {e}")
```

**其他指数**:
- 上证50: `'000016.SH'`
- 中证500: `'000905.SH'`
- 创业板指: `'399006.SZ'`

---

### Q9: 数据有缺失值怎么办？

**A**: 使用数据清洗工具：

```python
from src.data.data_cleaner import DataCleaner

cleaner = DataCleaner()

# 方法1: 前向填充（推荐）
data_filled = cleaner.forward_fill(data)

# 方法2: 线性插值
data_interpolated = cleaner.interpolate(data, method='linear')

# 方法3: 删除缺失值（谨慎使用）
data_dropped = cleaner.drop_missing(data, threshold=0.1)  # 缺失>10%删除

# 方法4: 使用均值填充
data_mean = cleaner.fill_with_mean(data)
```

---

## 特征计算

### Q10: 如何加速特征计算？

**A**: 多种优化方法：

**方法1: 使用向量化**:
```python
# ❌ 慢速（循环）
momentum = []
for i in range(len(prices)):
    if i >= 20:
        momentum.append(prices[i] / prices[i-20] - 1)
    else:
        momentum.append(np.nan)

# ✅ 快速（向量化）
momentum = prices / prices.shift(20) - 1  # 11倍加速
```

**方法2: 并行计算**:
```python
from src.features import AlphaFactors

# 使用多核
alpha = AlphaFactors(data, n_jobs=4)  # 使用4个CPU核心
features = alpha.calculate_all_alpha_factors()
```

**方法3: 缓存结果**:
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_features(stock_code, start_date):
    return calculate_features(stock_code, start_date)

# 第二次调用直接从缓存读取
features = cached_features('000001.SZ', '2023-01-01')
```

**方法4: 使用Parquet格式**:
```python
# 保存
features.to_parquet('features.parquet')  # 比CSV快5-10倍

# 读取
features = pd.read_parquet('features.parquet')
```

---

### Q11: 特征计算出现NaN？

**A**: 这是正常现象，解决方法：

**原因**: 滚动窗口计算前期不足

```python
# 例如：20日动量因子
momentum_20 = prices / prices.shift(20) - 1
# 前20行为NaN（数据不足）

# 解决方案1: 删除NaN行
features = features.dropna()

# 解决方案2: 前向填充
features = features.fillna(method='ffill')

# 解决方案3: 设置min_periods
momentum_20 = prices.pct_change(periods=20, fill_method=None)
```

**建议**:
- 训练模型时删除NaN
- 实盘使用时前向填充

---

### Q12: 如何选择最有效的因子？

**A**: 使用因子分析工具：

```python
from src.analysis import ICCalculator, FactorAnalyzer

# 1. 计算IC（信息系数）
ic_calc = ICCalculator()
ic_results = ic_calc.calculate_ic(factors, returns)

# 查看IC值
print(ic_results.sort_values('mean_ic', ascending=False))

# 2. 选择高IC因子
good_factors = ic_results[ic_results['mean_ic'] > 0.05]
print(f"有效因子: {len(good_factors)}/{len(ic_results)}")

# 3. 因子优化
analyzer = FactorAnalyzer()
best_factors = analyzer.select_best_factors(
    factors,
    returns,
    method='forward',  # 前向逐步选择
    max_factors=20
)
```

**IC值参考**:
- IC > 0.05: 较好
- IC > 0.08: 优秀
- IC > 0.10: 非常优秀

---

## 模型训练

### Q13: 模型训练很慢怎么办？

**A**: 优化建议：

**1. 使用GPU**:
```python
config = TrainingConfig(
    model_type='gru',
    use_gpu=True  # 启用GPU（20倍加速）
)
```

**2. 减少特征数量**:
```python
# 使用特征选择
from sklearn.feature_selection import SelectKBest, f_regression

selector = SelectKBest(f_regression, k=50)  # 选择前50个特征
X_selected = selector.fit_transform(X, y)
```

**3. 减少样本数量**:
```python
# 采样训练
X_sample = X.sample(frac=0.5, random_state=42)  # 使用50%样本
```

**4. 调整超参数**:
```python
config = TrainingConfig(
    model_type='lightgbm',
    hyperparameters={
        'n_estimators': 50,  # 减少树的数量（默认100）
        'max_depth': 3       # 减小树深度（默认5）
    }
)
```

---

### Q14: 模型过拟合怎么办？

**A**: 防止过拟合的方法：

**1. 交叉验证**:
```python
from sklearn.model_selection import cross_val_score

scores = cross_val_score(model, X, y, cv=5)
print(f"交叉验证R²: {scores.mean():.4f} ± {scores.std():.4f}")
```

**2. 正则化**:
```python
config = TrainingConfig(
    model_type='lightgbm',
    hyperparameters={
        'reg_alpha': 0.1,  # L1正则化
        'reg_lambda': 0.1  # L2正则化
    }
)
```

**3. Early Stopping**:
```python
config = TrainingConfig(
    model_type='lightgbm',
    hyperparameters={
        'early_stopping_rounds': 50  # 50轮无提升则停止
    }
)
```

**4. 特征工程**:
```python
# 删除高相关特征
corr_matrix = features.corr().abs()
upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
to_drop = [column for column in upper.columns if any(upper[column] > 0.95)]
features = features.drop(columns=to_drop)
```

---

### Q15: 如何评估模型性能？

**A**: 多维度评估：

```python
from src.models.model_trainer import ModelTrainer

trainer = ModelTrainer(config)
# ... 训练模型 ...

# 评估
eval_response = trainer.evaluate(X_test, y_test)
metrics = eval_response.data

print(f"R²: {metrics['r2']:.4f}")      # 拟合优度
print(f"MSE: {metrics['mse']:.6f}")    # 均方误差
print(f"MAE: {metrics['mae']:.6f}")    # 平均绝对误差
print(f"IC: {metrics['ic']:.4f}")      # 信息系数
```

**指标参考**:
- **R²**: >0.05（金融数据）
- **IC**: >0.05（有预测能力）
- **MSE**: 越小越好

**重要**: 金融数据R²普遍较低（0.05-0.15），不要期望达到0.9+

---

## 策略回测

### Q16: 回测结果太好，是否过拟合？

**A**: 检查以下几点：

**1. 未来数据泄漏**:
```python
# ❌ 错误：使用了未来数据
signals = data['close'].shift(-1) > data['close']  # 使用了明天的数据

# ✅ 正确：只使用历史数据
signals = data['close'].shift(1) > data['close'].shift(2)
```

**2. 交易成本**:
```python
# ✅ 确保包含真实成本
engine = BacktestEngine(
    commission_rate=0.0003,  # 万3佣金
    slippage_rate=0.001,     # 0.1%滑点
    stamp_tax_rate=0.001     # 0.1%印花税（卖出）
)
```

**3. 样本外测试**:
```python
# 训练集：2020-2022
# 测试集：2023（样本外）
train_data = data[data['date'] < '2023-01-01']
test_data = data[data['date'] >= '2023-01-01']
```

**4. 滚动回测**:
```python
from src.analysis import RollingBacktest

roller = RollingBacktest(window_size=252, step_size=63)
results = roller.run(strategy, data)
```

---

### Q17: 如何设置合理的交易成本？

**A**: A股市场参考：

```python
engine = BacktestEngine(
    # 佣金（双向）
    commission_rate=0.0003,  # 万3（散户普遍水平）
                             # 万2.5（活跃账户）
                             # 万1（机构或大资金）

    # 印花税（仅卖出）
    stamp_tax_rate=0.001,    # 千1（固定）

    # 滑点
    slippage_rate=0.001,     # 0.1%（流动性好的大盘股）
                             # 0.2-0.5%（小盘股或科创板）

    # 其他费用
    min_commission=5         # 最低佣金5元
)
```

**总成本估算**:
- 买入：0.03% + 0.1% = 0.13%
- 卖出：0.03% + 0.1% + 0.1% = 0.23%
- **单次往返**: ~0.36%

---

### Q18: 如何评估策略的稳定性？

**A**: 多角度评估：

**1. 滚动回测**:
```python
from src.analysis import RollingBacktest

roller = RollingBacktest(
    window_size=252,  # 1年窗口
    step_size=63      # 每季度滚动
)

results = roller.run(strategy, data)
roller.plot_rolling_sharpe(results)  # 查看夏普比率变化
```

**2. 分时段分析**:
```python
# 牛市、熊市、震荡市表现
bull_market = data[data['date'].between('2019-01-01', '2021-02-01')]
bear_market = data[data['date'].between('2021-02-01', '2022-10-01')]

bull_results = engine.backtest_long_only(signals, bull_market)
bear_results = engine.backtest_long_only(signals, bear_market)

print(f"牛市年化收益: {bull_results.annualized_return:.2%}")
print(f"熊市年化收益: {bear_results.annualized_return:.2%}")
```

**3. 蒙特卡洛模拟**:
```python
from src.analysis import MonteCarloSimulator

simulator = MonteCarloSimulator()
simulated_paths = simulator.run(strategy, data, n_simulations=1000)

# 分析最坏情况
worst_case = simulated_paths.min(axis=0)
```

---

## 性能优化

### Q19: 如何提升回测速度？

**A**: 性能优化技巧：

**1. 向量化计算**:
```python
# ❌ 慢速（循环）
for i in range(len(data)):
    if signals[i] == 1:
        positions[i] = 1

# ✅ 快速（向量化）
positions = np.where(signals == 1, 1, 0)  # 快100倍
```

**2. 并行回测**:
```python
from src.backtest import ParallelBacktester

backtester = ParallelBacktester(n_workers=4)
results = backtester.run(strategies, data)  # 4倍加速
```

**3. 使用Numba JIT**:
```python
from numba import jit

@jit(nopython=True)
def fast_backtest(prices, signals):
    # JIT编译的回测逻辑
    pass
```

---

### Q20: 内存不足怎么办？

**A**: 内存优化方案：

**1. 减少数据精度**:
```python
# 将float64降为float32
data = data.astype({
    'open': 'float32',
    'high': 'float32',
    'low': 'float32',
    'close': 'float32'
})  # 内存减少50%
```

**2. 分批处理**:
```python
# 按股票分批
for stock_batch in chunks(stock_codes, batch_size=100):
    process_batch(stock_batch)
```

**3. 使用生成器**:
```python
def data_generator(stock_codes):
    for code in stock_codes:
        yield load_data(code)

for data in data_generator(stock_codes):
    process(data)  # 逐个处理，不占用大量内存
```

---

## 错误排查

### Q21: ModuleNotFoundError: No module named 'src'

**A**: Python路径问题：

```bash
# 方案1: 添加PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/stock-analysis/core"

# 方案2: 在脚本开头添加
import sys
sys.path.append('/path/to/stock-analysis/core')

# 方案3: 安装为包（推荐）
pip install -e .
```

---

### Q22: 运行时警告太多？

**A**: 配置警告过滤：

```python
import warnings

# 忽略所有警告（不推荐）
warnings.filterwarnings('ignore')

# 只忽略特定警告（推荐）
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', message='.*DataFrame.*')

# 在pandas中
import pandas as pd
pd.options.mode.chained_assignment = None  # 关闭SettingWithCopyWarning
```

---

### Q23: 如何查看详细日志？

**A**: 调整日志级别：

```python
from loguru import logger

# 方法1: 代码中设置
logger.remove()  # 移除默认handler
logger.add(
    "logs/debug.log",
    level="DEBUG",  # 显示所有日志
    rotation="100 MB"
)

# 方法2: 配置文件
# config/logging.yaml
logging:
  level: DEBUG  # INFO, WARNING, ERROR
```

```bash
# 方法3: 环境变量
export LOG_LEVEL=DEBUG
python script.py
```

---

## 进阶使用

### Q24: 如何实现自定义策略？

**A**: 继承BaseStrategy：

```python
from src.strategies.base_strategy import BaseStrategy
import pandas as pd

class MyCustomStrategy(BaseStrategy):
    """自定义策略"""

    def generate_signals(
        self,
        data: pd.DataFrame,
        features: pd.DataFrame
    ) -> pd.Series:
        """
        生成交易信号

        Returns:
            pd.Series: 1=买入, -1=卖出, 0=持有
        """
        # 你的策略逻辑
        signals = pd.Series(0, index=data.index)

        # 示例：双均线策略
        ma5 = data['close'].rolling(5).mean()
        ma20 = data['close'].rolling(20).mean()

        signals[ma5 > ma20] = 1   # 金叉买入
        signals[ma5 < ma20] = -1  # 死叉卖出

        return signals

# 使用
strategy = MyCustomStrategy(name='MyStrategy', params={})
signals = strategy.generate_signals(data, features)
```

---

### Q25: 如何部署到生产环境？

**A**: 生产部署流程：

**1. 使用Docker**:
```bash
# 构建镜像
docker build -t stock-analysis:v3.0.0 .

# 运行容器
docker run -d \
  --name stock-analysis \
  -v /data:/app/data \
  -e DATABASE_URL=postgresql://... \
  stock-analysis:v3.0.0
```

**2. 定时任务**:
```bash
# crontab
# 每天15:30运行（收盘后）
30 15 * * 1-5 cd /path/to/project && python scripts/daily_update.py
```

**3. 监控告警**:
```python
from src.utils.monitor import Monitor

monitor = Monitor()

@monitor.alert_on_error(email='admin@example.com')
def daily_task():
    # 你的任务
    pass
```

---

## 📚 更多资源

### 相关文档

- 📖 [快速开始](quick_start.md)
- 🔧 [安装指南](installation.md)
- 📊 [CLI指南](CLI_GUIDE.md)
- 🤖 [模型使用指南](MODEL_USAGE_GUIDE.md)

### 获取帮助

- 📧 [GitHub Issues](https://github.com/your-org/stock-analysis/issues) - 报告Bug
- 💬 [Discussions](https://github.com/your-org/stock-analysis/discussions) - 技术讨论
- 📚 [完整文档](../README.md) - 文档中心

---

## 🤝 贡献FAQ

发现文档中未解答的问题？欢迎贡献！

1. 在 [Issues](https://github.com/your-org/stock-analysis/issues) 中提出问题
2. 等待确认后，提交PR添加到本FAQ
3. PR格式：
   ```markdown
   ### Q26: 你的问题？

   **A**: 详细解答...
   ```

---

**文档版本**: v3.0.0
**维护团队**: Quant Team
**最后更新**: 2026-02-01
