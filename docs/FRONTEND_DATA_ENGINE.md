# 前端数据引擎界面说明

## 📦 已创建的前端页面

### 1. 系统设置页面 ✅
**路径**: `/settings`
**文件**: [frontend/src/app/settings/page.tsx](../frontend/src/app/settings/page.tsx)

#### 功能特性:
- ✅ 数据源选择 (AkShare / Tushare)
- ✅ Tushare Token 配置
- ✅ 数据源对比说明表格
- ✅ 实时配置保存
- ✅ 成功/错误消息提示
- ✅ 暗黑模式支持

#### 界面元素:
1. **数据源单选按钮组**
   - AkShare (免费，标签标识)
   - Tushare Pro (需要积分，标签标识)
   - 每个选项包含详细说明和特性列表

2. **Tushare Token 输入框**
   - 仅在选择 Tushare 时显示
   - 带注册链接
   - 必填验证

3. **数据源对比表格**
   - 使用成本
   - 日线数据
   - 分钟数据
   - 实时行情
   - 数据质量
   - 频率限制

---

### 2. 数据同步管理页面 ✅
**路径**: `/sync`
**文件**: [frontend/src/app/sync/page.tsx](../frontend/src/app/sync/page.tsx)

#### 功能特性:
- ✅ 实时同步状态监控
- ✅ 同步股票列表
- ✅ 批量同步日线数据
- ✅ 更新实时行情
- ✅ 进度条显示
- ✅ 自动状态刷新 (每5秒)

#### 界面元素:
1. **同步状态卡片**
   - 当前状态 (空闲/同步中/完成/失败)
   - 最后同步日期
   - 进度显示 (已完成/总数)
   - 进度条可视化

2. **同步操作区域** (4个卡片)
   - **同步股票列表**: 一键同步全部 A 股列表
   - **批量同步日线数据**:
     - 可配置股票数量 (1-5000)
     - 可选择历史年数 (1/3/5/10年)
   - **更新实时行情**:
     - 获取所有股票实时数据
     - AkShare 会显示速度提示
   - **数据源设置**: 跳转到设置页面

3. **使用提示卡片**
   - 蓝色背景提示框
   - 5 条使用建议
   - 帮助用户正确使用同步功能

---

### 3. API Client 更新 ✅
**文件**: [frontend/src/lib/api-client.ts](../frontend/src/lib/api-client.ts)

#### 新增接口方法:

```typescript
// ========== 配置管理 ==========
async getDataSourceConfig()           // 获取数据源配置
async updateDataSourceConfig(params)  // 更新数据源配置
async getAllConfigs()                 // 获取所有配置

// ========== 数据同步 ==========
async getSyncStatus()                 // 获取同步状态
async syncStockList()                 // 同步股票列表
async syncDailyBatch(params)          // 批量同步日线数据
async syncDailyStock(code, years)     // 同步单只股票
async syncMinuteData(code, params)    // 同步分时数据
async syncRealtimeQuotes(codes?)      // 更新实时行情
async getSyncHistory(params?)         // 获取同步历史
```

**新增代码**: ~120 行 TypeScript

---

### 4. 导航菜单更新 ✅
**文件**: [frontend/src/app/layout.tsx](../frontend/src/app/layout.tsx)

#### 新增导航项:
- 🔄 **数据同步** (`/sync`) - 数据同步管理页面
- ⚙️ **系统设置** (`/settings`) - 数据源配置页面

#### 完整导航结构:
```
首页 → 股票列表 → 数据同步 → 数据分析 → 策略回测 → 系统设置
```

---

## 🎨 UI/UX 设计特点

### 1. 一致的设计语言
- 使用统一的 `card` 样式类
- 统一的按钮样式 (`btn-primary`, `btn-secondary`)
- 统一的输入框样式 (`input-field`)

### 2. 状态反馈
- ✅ 成功消息 (绿色背景)
- ❌ 错误消息 (红色背景)
- 🔄 加载状态 (旋转动画)
- 📊 进度条可视化

### 3. 交互优化
- 禁用状态管理 (防止重复提交)
- 自动刷新 (同步进行时每 5 秒刷新)
- 自动消息清除 (5 秒后自动隐藏成功消息)
- 即时验证 (Tushare 必填 Token)

### 4. 暗黑模式支持
- 所有组件支持 `dark:` 前缀样式
- 自动适配系统主题
- 确保可读性和对比度

---

## 📱 响应式设计

### 网格布局:
```typescript
// 在小屏幕上单列，中等及以上屏幕多列
grid grid-cols-1 md:grid-cols-2 gap-6
grid grid-cols-1 md:grid-cols-3 gap-4
```

### 自适应组件:
- 表格支持横向滚动 (`overflow-x-auto`)
- 弹性盒子布局适配移动端
- 触摸友好的按钮尺寸

---

## 🔧 使用流程

### 场景 1: 首次配置系统

```
1. 访问 /settings (系统设置)
   ↓
2. 选择数据源 (AkShare 或 Tushare)
   ↓
3. 如选择 Tushare，填写 Token
   ↓
4. 点击 "保存配置"
   ↓
5. 访问 /sync (数据同步)
   ↓
6. 点击 "同步股票列表"
   ↓
7. 等待同步完成 (约 5000+ 只股票)
   ↓
8. 配置批量同步参数 (100 只股票, 5 年)
   ↓
9. 点击 "开始批量同步"
   ↓
10. 观察进度条，等待完成
```

### 场景 2: 切换数据源

```
1. 访问 /settings
   ↓
2. 选择新的数据源
   ↓
3. 填写必要配置 (如 Tushare Token)
   ↓
4. 保存配置
   ↓
5. 后续同步自动使用新数据源
```

### 场景 3: 定期更新数据

```
1. 访问 /sync
   ↓
2. 查看当前同步状态
   ↓
3. 点击 "更新实时行情" (交易时段)
   ↓
4. 或使用 "批量同步日线数据" (增量更新)
```

---

## 🎯 API 对接状态

| 接口 | 前端方法 | 后端接口 | 状态 |
|------|---------|---------|------|
| 获取数据源配置 | `getDataSourceConfig()` | `GET /api/config/source` | ⏳ 待实现 |
| 更新数据源配置 | `updateDataSourceConfig()` | `POST /api/config/source` | ⏳ 待实现 |
| 获取同步状态 | `getSyncStatus()` | `GET /api/sync/status` | ⏳ 待实现 |
| 同步股票列表 | `syncStockList()` | `POST /api/sync/stock-list` | ⏳ 待实现 |
| 批量同步日线 | `syncDailyBatch()` | `POST /api/sync/daily/batch` | ⏳ 待实现 |
| 同步单只股票 | `syncDailyStock()` | `POST /api/sync/daily/{code}` | ⏳ 待实现 |
| 同步分时数据 | `syncMinuteData()` | `POST /api/sync/minute/{code}` | ⏳ 待实现 |
| 更新实时行情 | `syncRealtimeQuotes()` | `POST /api/sync/realtime` | ⏳ 待实现 |
| 同步历史记录 | `getSyncHistory()` | `GET /api/sync/history` | ⏳ 待实现 |

**说明**: 前端已完成，等待后端 API 实现（参考 `docs/API_IMPLEMENTATION_GUIDE.md`）

---

## 📊 前端代码统计

```
API Client 更新:     ~120 行 TypeScript
系统设置页面:        ~340 行 TypeScript (TSX)
数据同步管理页面:    ~470 行 TypeScript (TSX)
导航菜单更新:        ~10 行 TypeScript (TSX)
文档说明:           本文档

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总计:              ~940 行前端代码
```

---

## 🎁 特色功能

### 1. 智能状态管理
```typescript
// 自动刷新同步状态
useEffect(() => {
  const interval = setInterval(() => {
    if (syncStatus?.status === 'running') {
      loadSyncStatus()  // 仅在同步进行时刷新
    }
  }, 5000)

  return () => clearInterval(interval)
}, [syncStatus?.status])
```

### 2. 进度可视化
```typescript
<div className="w-full bg-gray-200 rounded-full h-2">
  <div
    className="bg-blue-600 h-2 rounded-full transition-all"
    style={{ width: `${syncStatus.progress}%` }}
  ></div>
</div>
```

### 3. 动态表单验证
```typescript
// Tushare 必填验证
if (dataSource === 'tushare' && !tushareToken.trim()) {
  setError('使用 Tushare 数据源需要提供 API Token')
  return
}
```

### 4. 条件渲染
```typescript
{dataSource === 'akshare' && (
  <span className="text-yellow-600">
    ⚠ AkShare 实时行情获取较慢（约 20-30 秒）
  </span>
)}
```

---

## 🚀 本地测试

### 1. 启动开发服务器
```bash
cd frontend
npm run dev
```

### 2. 访问页面
- 系统设置: http://localhost:3000/settings
- 数据同步: http://localhost:3000/sync

### 3. 模拟数据 (可选)
在后端 API 未实现前，可以使用 Mock 数据测试 UI：

```typescript
// 临时 Mock 数据
const mockSyncStatus = {
  status: 'running',
  last_sync_date: '2026-01-20',
  progress: 45,
  total: 100,
  completed: 45
}
```

---

## 📝 下一步工作

### 高优先级
- [ ] 实现后端 API 接口 (参考 API_IMPLEMENTATION_GUIDE.md)
- [ ] 连接前后端，测试完整流程
- [ ] 添加错误边界和异常处理
- [ ] 优化加载状态和用户体验

### 中优先级
- [ ] 添加同步历史记录页面
- [ ] 实现 WebSocket 实时推送进度
- [ ] 添加数据可视化图表
- [ ] 支持自定义同步参数

### 低优先级
- [ ] 国际化支持 (i18n)
- [ ] 主题切换器 UI
- [ ] 高级筛选和搜索
- [ ] 导出配置功能

---

## 💡 使用提示

1. **首次使用**: 先访问 `/settings` 配置数据源
2. **开始同步**: 再访问 `/sync` 执行同步任务
3. **监控进度**: 页面会自动刷新同步状态
4. **切换数据源**: 随时可在设置页面切换
5. **查看股票**: 同步完成后在 `/stocks` 查看

---

**前端界面已完成，等待后端 API 对接！** 🎉
