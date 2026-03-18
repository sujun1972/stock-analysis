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

### 响应式设计规范

Admin项目全面支持移动端访问，采用移动优先的响应式设计：

#### 断点定义
- `sm` (640px): 手机横屏及平板竖屏
- `md` (768px): 平板横屏
- `lg` (1024px): 小屏幕桌面
- `xl` (1280px): 标准桌面
- `2xl` (1536px): 大屏幕桌面

#### DataTable 组件分页优化
- **移动端（<640px）**：
  - 垂直3行布局：显示信息、分页控制、快速跳转
  - 页数>7时显示紧凑页码指示器："第 X / Y 页"
  - 上下页按钮仅显示图标，无文字
  - 智能过滤超过总数的分页选项
- **桌面端（≥640px）**：
  - 水平布局，完整分页控制
  - 显示首页、上一页、页码、下一页、末页按钮
  - 页数>10时显示快速跳转输入框

#### 页面响应式设计模式
1. **卡片布局**：使用 `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` 等自适应网格
2. **文字大小**：移动端使用 `text-xs`，桌面端使用 `text-sm` 或更大
3. **按钮组**：
   - 桌面端：完整按钮组横向排列
   - 移动端：使用下拉菜单（DropdownMenu）整合操作
4. **表单控件**：移动端使用 `w-full` 确保全宽显示
5. **导航模式**：
   - 移动端：卡片式导航或底部标签栏
   - 桌面端：传统标签页或侧边栏
6. **移动端数据展示最佳实践**（参考沪深港通页面）：
   - 自定义移动端视图，不依赖DataTable的mobileCard
   - 使用 `divide-y` 分割线区分数据行
   - 斑马纹背景：偶数行白色/深灰，奇数行浅灰/更深灰
   - 交互反馈：`hover:bg-blue-50` 和 `active:bg-blue-100`（淡蓝色）
   - 每行数据添加适当padding（`p-4`）
   - 数据项垂直堆叠，每项单独一行
   - 独立的移动端分页控件

#### 关键优化技巧
- 使用 `truncate` 和 `line-clamp-*` 处理文本溢出
- 使用 `flex-wrap` 防止元素挤压变形
- 使用 `break-all` 处理长URL或代码的换行
- 移动端优先使用垂直布局（`flex-col`）
- 合理使用 `hidden sm:block` 和 `block sm:hidden` 控制元素显示
- 图表组件响应式：
  - 设置 `minWidth` 防止过度压缩
  - X轴标签旋转45度避免重叠（`angle={-45}`）
  - 调整 margin 为标签预留空间（`bottom: 40`）
  - 使用 `overflow-x-auto` 允许横向滚动
- 日期选择器：
  - 优先使用 `@/components/ui/date-picker`（弹出式日历）
  - 避免使用HTML5原生 `<input type="date">`
  - 日期控件对齐：使用 `items-end` 让按钮与输入框底部对齐

### 定时任务页面优化
定时任务配置页面（`/settings/scheduler`）已优化任务名称显示：
- **任务名称映射**：技术性的任务名称（如`daily_stock_list_sync`）自动映射为友好的中文名称（如"每日股票列表"）
- **任务分类**：任务按功能分为基础数据、行情数据、扩展数据、市场情绪、盘前分析、质量监控、报告通知、系统维护等类别
- **智能降级**：未在映射表中的任务会使用后端描述或原始名称，确保新增任务也能正常显示

注意：DataTable 组件使用 `accessor` 函数而非 `render` 来自定义列渲染。

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

## 数据质量保证

### 数据验证器
项目实现了完整的数据验证体系：
- **位置**: `/core/src/data/validators/`
- **功能**: 自动验证和修复Tushare扩展数据
- **支持的数据类型**: daily_basic, moneyflow, moneyflow_hsgt, margin_detail, stk_limit, adj_factor

### 沪深港通资金流向
- **API端点**: `/api/moneyflow-hsgt`
- **前端页面**: `/admin/app/(dashboard)/data/moneyflow-hsgt/page.tsx`
- **数据内容**: 沪股通、深股通、港股通(上海)、港股通(深圳)的每日资金流向
- **特点**: 支持2026年及以后的最新数据，替代了仅支持到2025年的北向资金持股明细(hk_hold)
- **积分消耗**: 2000积分/次（Tushare Pro接口）
- **页面功能**:
  - 统计卡片：北向资金均值、累计净流入、北向最大流入、南向最大流出
  - 趋势图表：北向和南向资金流向可视化
  - 日期筛选：使用弹出式日历选择器（`@/components/ui/date-picker`）
  - 数据单位：统一使用亿元（原始数据为百万元）
  - 响应式布局：
    - 桌面端：表格视图，简化列头
    - 移动端：卡片视图，垂直堆叠展示，斑马纹背景，淡蓝色交互反馈

### 性能优化
1. **批量插入**: 使用PostgreSQL COPY协议，性能提升10倍
2. **数据压缩**: TimescaleDB自动压缩，节省60%存储
3. **查询缓存**: Redis缓存热点数据，命中率80%
4. **索引优化**: 针对高频查询创建专门索引

### 服务位置
- **性能优化器**: `/backend/app/services/performance_optimizer.py`
- **缓存服务**: `/backend/app/services/cache_service.py`
- **数据质量服务**: `/backend/app/services/data_quality_service.py`

## 开发提示

1. 修改代码后，前端项目（admin）会自动热重载
2. 后端项目（FastAPI）在开发模式下也支持自动重载
3. 数据库使用 TimescaleDB，端口默认为 5432
4. 数据同步时会自动进行质量验证和修复