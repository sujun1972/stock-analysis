# Claude Development Guide

## 开发环境启动

使用以下命令启动完整的开发环境：

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

这个命令会：
1. 使用基础配置文件 `docker-compose.yml`
2. 加载开发环境覆盖配置 `docker-compose.dev.yml`
3. 在后台运行容器 (`-d`)
4. 重新构建镜像 (`--build`)

## 项目结构

- `/admin` - 管理后台前端项目 (Next.js)
- `/backend` - 后端API服务 (FastAPI)
- `/core` - 核心业务逻辑
- `/db_init` - 数据库初始化脚本

## Admin 项目新增功能

### 面包屑导航

已为 Admin 项目添加了全局面包屑导航功能：

#### 组件位置
- `/admin/components/ui/breadcrumb.tsx` - 面包屑UI组件
- `/admin/hooks/useBreadcrumbs.ts` - 自动生成面包屑的Hook
- `/admin/components/layouts/AdminLayout.tsx` - 在布局层集成面包屑

#### 实现特点

1. **全局显示**：
   - 面包屑在 AdminLayout 布局层自动显示
   - 位置：顶部 Header 下方，页面内容上方
   - 所有页面自动拥有面包屑导航

2. **自动生成**：
   - 根据当前路由自动生成面包屑
   - 智能识别路由层级关系
   - 支持动态路由参数（如股票代码、策略ID等）

3. **响应式设计**：
   - 长路径在移动端自动折叠
   - 中间项折叠为下拉菜单
   - 保持首页和最后两项可见

4. **PageHeader 组件**：
   - 现在专注于页面标题、描述和操作按钮
   - 不再包含面包屑功能
   - 用法更简洁：
   ```tsx
   <PageHeader
     title="页面标题"
     description="页面描述"
     actions={<Button>操作</Button>}
   />
   ```

#### 父级导航页面
为了支持面包屑的多级导航，已创建以下父级菜单页面：
- `/settings` - 系统设置导航页
- `/sentiment` - 市场情绪导航页
- `/sync` - 数据同步导航页
- `/logs` - 日志管理导航页
- `/monitoring` - 系统监控导航页

这些页面以卡片形式展示子功能入口，解决了中间层级页面点击的问题。

### 任务管理面板

Admin项目采用统一的任务管理面板，位于Header右侧：

#### 特点
- **统一入口**：通过Header右侧的任务图标访问
- **自动刷新**：打开面板时每5秒自动刷新任务状态
- **任务分组**：按任务类型（数据同步、AI分析、策略回测等）分组显示
- **进度显示**：支持显示任务进度条
- **状态管理**：使用Zustand store统一管理任务状态
- **错误提示**：显示失败任务的错误信息

#### 相关文件
- `/admin/components/TaskPanel.tsx` - 任务面板组件
- `/admin/components/TaskStatusIcon.tsx` - Header中的任务图标
- `/admin/stores/task-store.ts` - 任务状态管理

## 常用命令

### 查看容器状态
```bash
docker-compose ps
```

### 查看日志
```bash
docker-compose logs -f [service_name]
```

### 重启服务
```bash
docker-compose restart [service_name]
```

### 停止所有服务
```bash
docker-compose down
```

## 开发提示

1. 修改代码后，前端项目（admin）会自动热重载
2. 后端项目（FastAPI）在开发模式下也支持自动重载
3. 数据库使用 TimescaleDB，端口默认为 5432