# 数据同步任务开发模式 (Data Sync Task Pattern)

本文档总结了"沪深港通资金流向"同步任务的完整实现模式，为其他数据同步任务提供标准开发模板。

---

## 一、架构概览

数据同步任务采用**异步任务模式**，包含以下核心组件：

```
┌─────────────────┐
│  前端页面       │ ──┐
│  Page.tsx       │   │
└─────────────────┘   │
                      │
┌─────────────────┐   │
│  API Client     │ ──┤ 调用异步API
│  api-client.ts  │   │
└─────────────────┘   │
                      ▼
┌─────────────────────────────────────────────┐
│  后端 API Endpoint                          │
│  /api/{resource}/sync-async                 │
│  ✓ 提交 Celery 任务                         │
│  ✓ 记录到 celery_task_history 表           │
│  ✓ 立即返回任务ID（不等待完成）             │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  Celery 任务                                │
│  tasks/{resource}_tasks.py                  │
│  ✓ 使用 run_async_in_celery 辅助函数       │
│  ✓ 调用服务层异步方法                       │
│  ✓ 自动更新任务状态（通过 Celery 信号）     │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  服务层                                      │
│  services/{resource}_service.py             │
│  ✓ 实际的业务逻辑                           │
│  ✓ 数据库操作                               │
└─────────────────────────────────────────────┘
```

---

## 二、后端实现 (Backend)

### 2.1 Celery 任务层 (`/backend/app/tasks/{resource}_tasks.py`)

**模板代码**：

```python
"""
{资源名称}同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.{resource}_service import {ServiceClass}
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_{resource}")
def sync_{resource}_task(
    self,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    # ... 其他参数
):
    """
    同步{资源名称}数据

    Args:
        trade_date: 交易日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行{资源名称}同步任务: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

        service = {ServiceClass}()
        result = run_async_in_celery(
            service.sync_{resource},
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
            # ... 传递其他参数
        )

        if result["status"] == "success":
            logger.info(f"{资源名称}同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"{资源名称}同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行{资源名称}同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
```

**关键点**：
- ✅ 必须使用 `run_async_in_celery` 包装异步服务方法
- ✅ 任务名称格式：`tasks.sync_{resource}`
- ✅ 使用 `bind=True` 允许访问 `self`（用于重试等操作）
- ✅ 捕获异常并记录详细日志

---

### 2.2 API Endpoint 层 (`/backend/app/api/endpoints/{resource}.py`)

**异步同步端点模板**：

```python
@router.post("/sync-async")
async def sync_{resource}_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步{资源名称}数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        trade_date: 单个交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.{resource}_tasks import sync_{resource}_task
        from src.database.db_manager import DatabaseManager

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_{resource}_task.apply_async(
            kwargs={
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        # 记录任务到celery_task_history表，用于任务面板显示
        db_manager = DatabaseManager()
        history_query = """
            INSERT INTO celery_task_history
            (celery_task_id, task_name, display_name, task_type, user_id, status, params, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """

        task_params = {
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted
        }

        task_metadata = {
            "trigger": "manual",
            "source": "{resource}_page"
        }

        await asyncio.to_thread(
            db_manager._execute_update,
            history_query,
            (
                celery_task.id,
                'tasks.sync_{resource}',
                '{资源中文名称}',
                'data_sync',
                current_user.id,
                'pending',
                json.dumps(task_params),
                json.dumps(task_metadata)
            )
        )

        logger.info(f"{资源名称}同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data={
                "celery_task_id": celery_task.id,
                "task_name": "tasks.sync_{resource}",
                "display_name": "{资源中文名称}",
                "status": "pending"
            },
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交{资源名称}同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**关键点**：
- ✅ 端点路径：`/sync-async`（与 `/sync` 同步端点区分）
- ✅ 管理员权限：`Depends(require_admin)`
- ✅ 日期格式转换：`YYYY-MM-DD` → `YYYYMMDD`
- ✅ 必须记录到 `celery_task_history` 表
- ✅ `task_type` 应为 `'data_sync'`
- ✅ 立即返回任务ID，不等待完成

---

### 2.3 注册任务到调度器 (`/backend/app/scheduler/task_executor.py`)

在 `TASK_MAPPING` 字典中添加任务映射：

```python
TASK_MAPPING = {
    # ... 其他任务

    'tasks.sync_{resource}': {
        'task': 'tasks.sync_{resource}',
        'name': '{资源中文名称}'
    },

    # ... 其他任务
}
```

**关键点**：
- ✅ 键名 = 任务名称（`tasks.sync_{resource}`）
- ✅ `task` 字段 = Celery 任务名称
- ✅ `name` 字段 = 前端显示的中文名称

---

### 2.4 注册任务到 Celery App (`/backend/app/celery_app.py`)

确保任务模块被导入：

```python
try:
    from app.tasks import {resource}_tasks
    logger.info(f"✅ 已加载{资源名称}任务模块")
except Exception as e:
    logger.error(f"❌ 加载{资源名称}任务模块失败: {e}")
```

---

## 三、前端实现 (Admin Frontend)

### 3.1 API Client 方法 (`/admin/lib/api-client.ts`)

添加异步同步方法：

```typescript
/**
 * 异步同步{资源名称}数据
 * 通过Celery任务异步执行，立即返回任务ID
 */
async sync{Resource}Async(params?: {
  trade_date?: string  // YYYY-MM-DD
  start_date?: string  // YYYY-MM-DD
  end_date?: string    // YYYY-MM-DD
}): Promise<ApiResponse<{
  celery_task_id: string
  task_name: string
  display_name: string
  status: string
}>> {
  const response = await axiosInstance.post('/api/{resource}/sync-async', null, { params })
  return response.data
}
```

**关键点**：
- ✅ 方法名格式：`sync{Resource}Async`（驼峰命名）
- ✅ 参数日期格式：`YYYY-MM-DD`
- ✅ 返回任务ID和任务信息

---

### 3.2 数据页面 (`/admin/app/(dashboard)/data/{resource}/page.tsx`)

#### 3.2.1 导入依赖

```typescript
import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, Download } from 'lucide-react'
```

#### 3.2.2 状态管理

```typescript
const [data, setData] = useState<{Resource}Data[]>([])
const [statistics, setStatistics] = useState<Statistics | null>(null)
const [loading, setLoading] = useState(true)
const [error, setError] = useState<string | null>(null)
const [startDate, setStartDate] = useState<Date | undefined>(undefined)
const [endDate, setEndDate] = useState<Date | undefined>(undefined)
const [syncing, setSyncing] = useState(false)

// 分页状态
const [page, setPage] = useState(1)
const [pageSize, setPageSize] = useState(30)
const [total, setTotal] = useState(0)

// 存储活跃的任务回调（用于组件卸载时清理）
const activeCallbacksRef = useRef<Map<string, any>>(new Map())
```

#### 3.2.3 任务存储Hook

```typescript
const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
```

#### 3.2.4 异步同步处理函数

```typescript
/**
 * 异步同步数据
 * 通过Celery任务异步执行，不阻塞前端
 * 任务状态会在任务面板实时显示
 */
const handleSync = async () => {
  try {
    setSyncing(true)

    // 构建日期范围参数（YYYY-MM-DD格式）
    const params: {
      start_date?: string
      end_date?: string
    } = {}

    if (startDate) {
      params.start_date = startDate.toISOString().split('T')[0]
    }
    if (endDate) {
      params.end_date = endDate.toISOString().split('T')[0]
    }

    // 调用异步同步API
    const response = await apiClient.sync{Resource}Async(params)

    if (response.code === 200 && response.data) {
      const taskId = response.data.celery_task_id

      // 添加到任务存储（用于任务面板显示）
      addTask({
        taskId,
        taskName: response.data.task_name,
        displayName: response.data.display_name,
        taskType: 'data_sync',
        status: 'running',
        progress: 0,
        startTime: Date.now()
      })

      // 注册任务完成回调：自动刷新数据
      const completionCallback = (task: any) => {
        if (task.status === 'success') {
          // 任务成功完成，刷新数据
          loadData().catch(() => {
            // 静默失败
          })
          toast.success('数据同步完成', {
            description: '{资源名称}数据已更新'
          })
        } else if (task.status === 'failure') {
          // 任务失败
          toast.error('数据同步失败', {
            description: task.error || '同步过程中发生错误'
          })
        }
        // 清理回调
        unregisterCompletionCallback(taskId, completionCallback)
        activeCallbacksRef.current.delete(taskId)
      }

      // 存储回调引用
      activeCallbacksRef.current.set(taskId, completionCallback)
      registerCompletionCallback(taskId, completionCallback)

      // 立即触发轮询，更新Header任务图标状态
      triggerPoll()

      toast.success('任务已提交', {
        description: `"${response.data.display_name}" 已开始执行，可在任务面板查看进度`
      })
    } else {
      throw new Error(response.message || '同步失败')
    }
  } catch (err: any) {
    toast.error('同步失败', {
      description: err.message || '无法同步数据'
    })
  } finally {
    setSyncing(false)
  }
}
```

**关键点**：
- ✅ 添加任务到 `task-store`
- ✅ 注册完成回调（自动刷新数据）
- ✅ 调用 `triggerPoll()` 立即更新Header图标
- ✅ 组件卸载时清理回调

#### 3.2.5 组件卸载清理

```typescript
// 组件卸载时清理所有活跃的任务回调
useEffect(() => {
  return () => {
    // 复制引用以避免React Hook警告
    const callbacks = activeCallbacksRef.current
    callbacks.forEach((callback, taskId) => {
      unregisterCompletionCallback(taskId, callback)
    })
    callbacks.clear()
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [])
```

#### 3.2.6 同步按钮UI

```typescript
<Button
  variant="default"
  size="sm"
  onClick={handleSync}
  disabled={syncing}
>
  {syncing ? (
    <>
      <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
      同步中...
    </>
  ) : (
    <>
      <RefreshCw className="h-4 w-4 mr-1" />
      同步数据
    </>
  )}
</Button>
```

---

## 四、DataTable 组件正确使用方法

### 4.1 列定义规范

**正确的列定义格式**：

```typescript
import { Column } from '@/components/common/DataTable'

const columns: Column<DataType>[] = useMemo(() => [
  {
    key: 'field_name',           // 字段唯一标识
    header: '列头显示文字',       // ⚠️ 使用 header 而不是 label
    accessor: (row) => row.value  // 访问器函数（返回显示内容）
  },
  {
    key: 'date_field',
    header: '日期',               // 可以是字符串
    accessor: (row) => formatDate(row.date)
  },
  {
    key: 'exchange',
    header: (                     // 也可以是 ReactNode（响应式列头）
      <>
        <span className="sm:hidden">交</span>
        <span className="hidden sm:inline">交易所</span>
      </>
    ),
    accessor: (row) => row.exchange_id
  }
], [])
```

**❌ 错误示例**：
```typescript
// 错误：使用了 label 而不是 header
const columns: Column<DataType>[] = [
  {
    key: 'field_name',
    label: '列头',  // ❌ 错误！应该使用 header
    accessor: (row) => row.value
  }
]
```

### 4.2 DataTable 使用规范

**正确的 DataTable 属性传递**：

```typescript
<DataTable
  columns={columns}                // ✅ 列定义
  data={data}                      // ✅ 数据数组
  loading={loading}                // ✅ 加载状态
  error={error}                    // ✅ 错误信息
  emptyMessage="暂无数据"          // ✅ 空数据提示
  pagination={{                    // ✅ 分页对象（重要！）
    page,                          // 当前页码
    pageSize,                      // 每页大小
    total,                         // 总记录数
    onPageChange: (newPage) => {   // 页码变更回调
      setPage(newPage)
    },
    onPageSizeChange: (newPageSize) => {  // 每页大小变更回调
      setPageSize(newPageSize)
      setPage(1)  // 重置到第一页
    },
    pageSizeOptions: [10, 20, 30, 50, 100]  // 可选的每页大小
  }}
/>
```

**❌ 错误示例**：
```typescript
// 错误：将分页参数直接作为独立属性传递
<DataTable
  columns={columns}
  data={data}
  loading={loading}
  error={error}
  page={page}              // ❌ 错误！
  pageSize={pageSize}      // ❌ 错误！
  total={total}            // ❌ 错误！
  onPageChange={setPage}   // ❌ 错误！
/>
```

### 4.3 完整的表格布局结构

**推荐的响应式表格结构**：

```typescript
{/* 数据表格 */}
<Card className="p-0 sm:p-0 overflow-hidden">
  {/* 移动端视图（在前） */}
  <div className="sm:hidden">
    <div className="px-4 py-3 border-b bg-muted/50">
      <h3 className="text-sm font-medium">数据列表</h3>
    </div>
    <div className="divide-y divide-gray-200 dark:divide-gray-700">
      {!loading && !error && data.map((item, index) => (
        <div
          key={index}
          className={`p-4 transition-colors ${
            index % 2 === 0
              ? 'bg-white dark:bg-gray-900 hover:bg-blue-50 dark:hover:bg-blue-950/20'
              : 'bg-gray-50 dark:bg-gray-950 hover:bg-blue-50 dark:hover:bg-blue-950/20'
          }`}
        >
          {mobileCard(item)}
        </div>
      ))}
    </div>

    {/* 移动端状态显示 */}
    {loading && (
      <div className="p-8 text-center">
        <div className="flex flex-col items-center justify-center gap-2">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          <span className="text-sm text-muted-foreground">加载中...</span>
        </div>
      </div>
    )}
    {error && (
      <div className="p-8 text-center">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    )}
    {!loading && !error && data.length === 0 && (
      <div className="p-8 text-center">
        <p className="text-sm text-muted-foreground">暂无数据</p>
      </div>
    )}

    {/* 移动端分页 */}
    {!loading && !error && data.length > 0 && (
      <div className="p-4 border-t bg-muted/30">
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
          >
            上一页
          </Button>
          <span className="text-sm text-muted-foreground">
            第 {page} / {Math.ceil(total / pageSize)} 页
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(Math.min(Math.ceil(total / pageSize), page + 1))}
            disabled={page >= Math.ceil(total / pageSize)}
          >
            下一页
          </Button>
        </div>
      </div>
    )}
  </div>

  {/* 桌面端表格视图（在后） */}
  <div className="hidden sm:block">
    <DataTable
      columns={columns}
      data={data}
      loading={loading}
      error={error}
      emptyMessage="暂无数据"
      pagination={{
        page,
        pageSize,
        total,
        onPageChange: (newPage) => {
          setPage(newPage)
        },
        onPageSizeChange: (newPageSize) => {
          setPageSize(newPageSize)
          setPage(1)
        },
        pageSizeOptions: [10, 20, 30, 50, 100]
      }}
    />
  </div>
</Card>
```

**关键点**：
- ✅ Card 使用 `className="p-0 sm:p-0 overflow-hidden"`
- ✅ 移动端视图在前，桌面端在后
- ✅ 移动端需要独立的加载、错误、空数据状态显示
- ✅ 移动端需要独立的分页控件
- ✅ 桌面端使用 DataTable 组件的 pagination 对象

### 4.4 DataTable 接口定义参考

```typescript
export interface Column<T> {
  key: string                      // 列唯一标识
  header: string | ReactNode       // 列头（支持响应式）
  accessor?: (item: T) => ReactNode  // 访问器函数
  sortable?: boolean               // 是否可排序
  className?: string               // 列样式
  headerClassName?: string         // 列头样式
  cellClassName?: string           // 单元格样式
  width?: string | number          // 列宽
  align?: 'left' | 'center' | 'right'  // 对齐方式
  hideOnMobile?: boolean          // 移动端隐藏
}

export interface PaginationConfig {
  page: number                     // 当前页码
  pageSize: number                 // 每页大小
  total: number                    // 总记录数
  onPageChange: (page: number) => void         // 页码变更回调
  onPageSizeChange?: (pageSize: number) => void  // 每页大小变更回调
  pageSizeOptions?: number[]       // 可选的每页大小选项
}

export interface DataTableProps<T> {
  data: T[]                        // 数据数组
  columns: Column<T>[]             // 列定义
  loading?: boolean                // 加载状态
  error?: string | null            // 错误信息
  emptyMessage?: string | ReactNode  // 空数据提示
  pagination?: PaginationConfig    // 分页配置（可选）
  // ... 其他属性
}
```

---

## 五、移动端响应式设计

### 5.1 移动端卡片视图

参考沪深港通页面的最佳实践：

```typescript
const mobileCard = useCallback((item: {Resource}Data) => (
  <div className="space-y-2">
    {/* 主要字段 */}
    <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">日期</span>
      <span className="font-medium">{formatDate(item.trade_date)}</span>
    </div>

    {/* 其他字段 */}
    <div className="flex justify-between items-center">
      <span className="text-sm text-gray-600 dark:text-gray-400">字段名</span>
      <span className="font-medium">{item.value}</span>
    </div>

    {/* ... 更多字段 */}
  </div>
), [])
```

### 4.2 移动端数据渲染

```typescript
<div className="sm:hidden">
  {/* 移动端视图 - 卡片列表 */}
  <div className="px-4 py-3 border-b bg-muted/50">
    <h3 className="text-sm font-medium">{资源名称}数据</h3>
  </div>
  <div className="divide-y divide-gray-200 dark:divide-gray-700">
    {!loading && !error && data.map((item, index) => (
      <div
        key={index}
        className={`p-4 transition-colors ${
          index % 2 === 0
            ? 'bg-white dark:bg-gray-900 hover:bg-blue-50 dark:hover:bg-blue-950/20 active:bg-blue-100 dark:active:bg-blue-900/30'
            : 'bg-gray-50 dark:bg-gray-950 hover:bg-blue-50 dark:hover:bg-blue-950/20 active:bg-blue-100 dark:active:bg-blue-900/30'
        }`}
      >
        {mobileCard(item)}
      </div>
    ))}
  </div>

  {/* 移动端分页 */}
  {!loading && !error && data.length > 0 && (
    <div className="p-4 border-t bg-muted/30">
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPage(Math.max(1, page - 1))}
          disabled={page === 1}
        >
          上一页
        </Button>
        <span className="text-sm text-muted-foreground">
          第 {page} / {Math.ceil(total / pageSize)} 页
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPage(Math.min(Math.ceil(total / pageSize), page + 1))}
          disabled={page >= Math.ceil(total / pageSize)}
        >
          下一页
        </Button>
      </div>
    </div>
  )}
</div>
```

**关键点**：
- ✅ 斑马纹背景（偶数/奇数行不同背景色）
- ✅ 淡蓝色交互反馈（`hover:bg-blue-50`, `active:bg-blue-100`）
- ✅ 使用 `divide-y` 分割线
- ✅ 独立的移动端分页控件

---

## 五、定时任务调度集成

如果任务需要定时执行，在 `/backend/app/tasks/{resource}_tasks.py` 中添加：

```python
@celery_app.task(bind=True, name="tasks.sync_{resource}_daily")
def sync_{resource}_daily_task(self):
    """
    每日定时同步{资源名称}数据

    Returns:
        同步结果
    """
    try:
        logger.info("开始执行每日{资源名称}同步任务")

        # 不指定日期，让服务自动获取最新交易日
        return sync_{resource}_task.apply_async(
            args=[],
            kwargs={'trade_date': None, 'start_date': None, 'end_date': None}
        ).get()

    except Exception as e:
        logger.error(f"执行每日{资源名称}同步任务失败: {str(e)}")
        raise
```

然后在调度器中注册定时任务（如需要）。

---

## 六、数据库表结构

确保目标表已创建，建议包含以下字段：

```sql
CREATE TABLE {resource} (
    -- 主键和索引字段
    trade_date VARCHAR(8) NOT NULL,  -- YYYYMMDD格式
    ts_code VARCHAR(10),              -- 股票代码（如适用）

    -- 数据字段
    ...

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (trade_date, ts_code),
    INDEX idx_trade_date (trade_date DESC),
    INDEX idx_ts_code (ts_code)
);
```

---

## 七、检查清单 (Checklist)

### 后端
- [ ] 创建 Celery 任务文件 (`tasks/{resource}_tasks.py`)
- [ ] 实现 `sync_{resource}_task` 任务函数（使用 `run_async_in_celery`）
- [ ] 创建 API endpoint (`api/endpoints/{resource}.py`)
- [ ] 实现 `/sync-async` 端点
- [ ] 记录任务到 `celery_task_history` 表
- [ ] 在 `task_executor.py` 中注册任务映射
- [ ] 在 `celery_app.py` 中导入任务模块
- [ ] 创建或确认服务层方法存在

### 前端
- [ ] 在 `api-client.ts` 中添加 `sync{Resource}Async` 方法
- [ ] 创建数据页面 (`app/(dashboard)/data/{resource}/page.tsx`)
- [ ] 实现 `handleSync` 异步同步函数
- [ ] 添加任务到 `task-store`
- [ ] 注册任务完成回调
- [ ] 调用 `triggerPoll()` 触发轮询
- [ ] 实现组件卸载清理
- [ ] **DataTable 组件正确配置**：
  - [ ] 列定义使用 `header` 而不是 `label`
  - [ ] 传递 `pagination` 对象（包含 page, pageSize, total, onPageChange, onPageSizeChange）
  - [ ] 添加 `emptyMessage` 属性
- [ ] 实现移动端卡片视图（斑马纹 + 淡蓝色交互）
- [ ] 添加移动端独立的加载、错误、空数据状态显示
- [ ] 添加移动端分页控件
- [ ] 添加同步按钮UI（loading状态）
- [ ] Card容器使用 `className="p-0 sm:p-0 overflow-hidden"`

### 测试
- [ ] 测试异步同步功能（点击按钮后任务正常提交）
- [ ] 测试任务面板显示（任务出现在面板中）
- [ ] 测试Header图标更新（立即显示运行中状态）
- [ ] 测试任务完成回调（数据自动刷新）
- [ ] 测试移动端响应式布局
- [ ] 测试定时任务执行（如适用）

---

## 八、常见问题 (FAQ)

### Q1: 为什么必须使用 `run_async_in_celery`？
**A**: Celery fork pool worker 会继承父进程的事件循环和数据库引擎，但这些对象绑定到了旧的事件循环，导致 "attached to a different loop" 错误。`run_async_in_celery` 会重新创建事件循环并重置数据库引擎。

### Q2: 任务状态如何自动更新到数据库？
**A**: 通过 Celery 信号机制（`/backend/app/celery_signals.py`），在任务开始、成功、失败时自动更新 `celery_task_history` 表。

### Q3: 为什么需要 `triggerPoll()`？
**A**: 立即触发一次轮询，让Header任务图标即时显示运行状态，无需等待下一个轮询周期（5秒）。

### Q4: 为什么需要注册完成回调？
**A**: 自动监听任务完成事件，在任务成功时自动刷新页面数据，提供流畅的用户体验。

### Q5: 组件卸载为什么要清理回调？
**A**: 防止内存泄漏。如果用户在任务完成前离开页面，未清理的回调仍会尝试更新已卸载的组件，导致错误。

---

## 九、参考示例

完整的参考实现：
- **后端任务**: `/backend/app/tasks/moneyflow_hsgt_tasks.py`
- **后端API**: `/backend/app/api/endpoints/moneyflow_hsgt.py`
- **前端页面**: `/admin/app/(dashboard)/data/moneyflow-hsgt/page.tsx`
- **API客户端**: `/admin/lib/api-client.ts` (搜索 `syncMoneyflowHsgtAsync`)

---

## 十、最佳实践建议

1. **统一命名规范**
   - Celery任务：`tasks.sync_{resource}`
   - API端点：`/api/{resource}/sync-async`
   - API方法：`sync{Resource}Async`

2. **错误处理**
   - 后端：记录详细日志 + 抛出异常（Celery自动捕获）
   - 前端：使用 `toast` 显示友好错误信息

3. **用户体验**
   - 立即触发轮询（`triggerPoll()`）
   - 显示loading状态（按钮 + 任务面板）
   - 任务完成后自动刷新数据
   - 移动端友好设计（卡片视图 + 独立分页）

4. **性能优化**
   - 使用异步任务，避免阻塞前端
   - 分页加载数据
   - 避免重复轮询（全局统一轮询）

5. **可维护性**
   - 代码模块化（任务层、服务层、API层分离）
   - 统一的错误处理和日志记录
   - 清晰的任务状态管理

---

## 十一、常见错误及解决方案

### 错误 1: DataTable 列头不显示

**症状**：表格列头显示为空白或显示不正确

**原因**：列定义使用了错误的属性名 `label` 而不是 `header`

**解决方案**：
```typescript
// ❌ 错误
const columns: Column<DataType>[] = [
  { key: 'name', label: '名称', accessor: (row) => row.name }
]

// ✅ 正确
const columns: Column<DataType>[] = [
  { key: 'name', header: '名称', accessor: (row) => row.name }
]
```

### 错误 2: DataTable 分页控件不显示

**症状**：表格底部没有分页控件

**原因**：将分页参数作为独立属性传递，而不是传递 `pagination` 对象

**解决方案**：
```typescript
// ❌ 错误
<DataTable
  columns={columns}
  data={data}
  page={page}
  pageSize={pageSize}
  total={total}
  onPageChange={setPage}
/>

// ✅ 正确
<DataTable
  columns={columns}
  data={data}
  pagination={{
    page,
    pageSize,
    total,
    onPageChange: (newPage) => setPage(newPage),
    onPageSizeChange: (newPageSize) => {
      setPageSize(newPageSize)
      setPage(1)
    },
    pageSizeOptions: [10, 20, 30, 50, 100]
  }}
/>
```

### 错误 3: 批量插入数据库失败

**症状**：`'DatabaseManager' object has no attribute '_execute_values'`

**原因**：使用了不存在的 `_execute_values` 方法

**解决方案**：
```python
# ❌ 错误
await asyncio.to_thread(
    self.db_manager._execute_values,
    insert_query,
    values
)

# ✅ 正确
def _batch_insert():
    conn = self.db_manager.get_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany(insert_query, values)
        conn.commit()
        cursor.close()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        self.db_manager.release_connection(conn)

await asyncio.to_thread(_batch_insert)
```

### 错误 4: Select 组件空值错误

**症状**：`A <Select.Item /> must have a value prop that is not an empty string`

**原因**：Select 组件不接受空字符串作为 value

**解决方案**：
```typescript
// ❌ 错误
<Select value={exchangeId} onValueChange={setExchangeId}>
  <SelectItem value="">全部</SelectItem>
  <SelectItem value="SSE">上交所</SelectItem>
</Select>

// ✅ 正确
<Select
  value={exchangeId || 'ALL'}
  onValueChange={(value) => setExchangeId(value === 'ALL' ? '' : value)}
>
  <SelectItem value="ALL">全部</SelectItem>
  <SelectItem value="SSE">上交所</SelectItem>
</Select>
```

---

**最后更新**: 2026-03-19
**版本**: 1.1.0
