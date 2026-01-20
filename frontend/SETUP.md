# Frontend 安装和启动指南

## 快速开始

### 方式一：使用 Docker（推荐）

从项目根目录运行：

```bash
# 启动完整服务栈（Frontend + Backend + Database）
docker-compose up -d

# 只启动前端
docker-compose up -d frontend

# 查看前端日志
docker-compose logs -f frontend

# 访问前端
open http://localhost:3000
```

### 方式二：本地开发

```bash
# 1. 进入frontend目录
cd frontend

# 2. 安装依赖
npm install

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，确保 NEXT_PUBLIC_API_URL 指向正确的后端地址

# 4. 启动开发服务器
npm run dev

# 5. 访问应用
open http://localhost:3000
```

## 环境变量配置

创建 `.env` 文件：

```env
# 后端API地址
# 本地开发使用：
NEXT_PUBLIC_API_URL=http://localhost:8000

# Docker环境使用：
# NEXT_PUBLIC_API_URL=http://backend:8000
```

## 验证安装

访问 http://localhost:3000，你应该看到：

1. **首页**：显示系统概览和功能介绍
2. **系统状态**：显示后端服务连接状态
3. **导航栏**：可以访问股票列表、数据分析、策略回测等页面

## 功能说明

### 已实现的功能

- ✅ **首页** (`/`)
  - 系统概览和功能介绍
  - 后端服务健康检查
  - 快速开始指南

- ✅ **股票列表** (`/stocks`)
  - 显示所有A股股票
  - 支持搜索（股票代码、名称）
  - 支持市场筛选（上海主板、深圳主板、创业板、科创板）
  - 分页浏览
  - 跳转到分析页面

### 待实现的功能

- ⏳ **数据分析页面** (`/analysis`)
  - 股票数据可视化
  - K线图表
  - 技术指标展示

- ⏳ **策略回测页面** (`/backtest`)
  - 回测参数配置
  - 回测结果展示
  - 绩效分析图表

## 开发说明

### 项目结构

```
frontend/src/
├── app/              # Next.js App Router
│   ├── layout.tsx    # 根布局（包含导航栏）
│   ├── page.tsx      # 首页
│   ├── stocks/       # 股票列表页
│   └── globals.css   # 全局样式
├── lib/              # 工具库
│   └── api-client.ts # API客户端封装
├── store/            # Zustand状态管理
│   └── stock-store.ts
├── types/            # TypeScript类型定义
│   └── stock.ts
├── components/       # 可复用组件（待添加）
└── hooks/            # 自定义Hooks（待添加）
```

### 技术栈

- **Next.js 14** (App Router)
- **TypeScript** - 类型安全
- **Tailwind CSS** - 样式框架
- **Zustand** - 状态管理
- **Axios** - HTTP客户端

### 常用命令

```bash
# 开发
npm run dev         # 启动开发服务器

# 构建
npm run build       # 构建生产版本
npm start           # 启动生产服务器

# 代码质量
npm run lint        # 运行ESLint检查
```

## 故障排除

### 问题1: 无法连接后端

**症状**: 首页显示"后端服务连接失败"

**解决方案**:
1. 确认后端服务正在运行：`docker-compose ps backend`
2. 检查后端健康状态：`curl http://localhost:8000/health`
3. 检查 `.env` 中的 `NEXT_PUBLIC_API_URL` 配置

### 问题2: npm install 失败

**症状**: 依赖安装时出错

**解决方案**:
1. 确认 Node.js 版本 >= 20: `node --version`
2. 清理缓存：`rm -rf node_modules package-lock.json && npm cache clean --force`
3. 重新安装：`npm install`

### 问题3: 端口冲突

**症状**: 无法启动，端口3000已被占用

**解决方案**:
1. 查找占用端口的进程：`lsof -i :3000`
2. 杀死进程：`kill -9 <PID>`
3. 或使用其他端口：`PORT=3001 npm run dev`

### 问题4: Docker构建失败

**症状**: `docker-compose build frontend` 失败

**解决方案**:
1. 检查 Dockerfile 是否存在
2. 确认 Node.js 版本兼容性
3. 查看构建日志：`docker-compose logs frontend`
4. 删除旧镜像重新构建：`docker-compose build --no-cache frontend`

## API集成说明

前端通过 `src/lib/api-client.ts` 与后端通信。所有API调用都应使用这个客户端：

```typescript
import { apiClient } from '@/lib/api-client'

// 获取股票列表
const response = await apiClient.getStockList({ limit: 20 })

// 获取单只股票
const stock = await apiClient.getStock('000001')

// 下载数据
await apiClient.downloadData({ stock_codes: ['000001'], years: 5 })
```

## 后续开发计划

1. **数据可视化**
   - 集成 Recharts 实现K线图
   - 技术指标图表展示
   - 实时数据更新

2. **用户体验优化**
   - 添加加载骨架屏
   - 优化移动端响应式
   - 添加深色模式切换

3. **功能扩展**
   - 实现数据分析页面
   - 实现策略回测页面
   - 添加用户认证功能

---

**最后更新**: 2026-01-20
