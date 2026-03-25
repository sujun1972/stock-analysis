/**
 * 异步任务管理 Store (Zustand)
 *
 * 功能:
 * 1. 管理所有异步任务的状态（同步、AI分析、回测等）
 * 2. 提供添加、更新、删除任务的方法
 * 3. 支持任务分组和过滤
 * 4. 从后端API加载和同步任务历史
 * 5. 提供手动触发轮询的机制（用于即时更新）
 */

import { create } from 'zustand'

export type TaskType = 'sync' | 'data_sync' | 'sentiment' | 'ai_analysis' | 'backtest' | 'premarket' | 'scheduler' | 'other'
export type TaskStatus = 'pending' | 'running' | 'success' | 'failure' | 'progress'

export interface Task {
  taskId: string
  taskName: string // Celery 任务名称
  displayName: string // 显示名称
  taskType: TaskType
  status: TaskStatus
  progress?: number // 0-100
  startTime: number
  endTime?: number // 完成时间
  result?: any
  error?: string
  worker?: string
}

// 任务完成回调函数类型
export type TaskCompletionCallback = (task: Task) => void

interface TaskStore {
  // 任务列表（使用 Map 提高查找效率）
  tasks: Map<string, Task>

  // 任务完成回调（用于页面监听任务完成事件）
  completionCallbacks: Map<string, TaskCompletionCallback[]>
  registerCompletionCallback: (taskId: string, callback: TaskCompletionCallback) => void
  unregisterCompletionCallback: (taskId: string, callback: TaskCompletionCallback) => void

  // 轮询触发器（用于手动触发轮询）
  pollTrigger: (() => Promise<void>) | null
  setPollTrigger: (trigger: (() => Promise<void>) | null) => void
  triggerPoll: () => Promise<void>

  // 添加任务
  addTask: (task: Task) => void

  // 批量添加任务
  setTasks: (tasks: Task[]) => void

  // 更新任务
  updateTask: (taskId: string, updates: Partial<Task>) => void

  // 删除任务
  removeTask: (taskId: string) => void

  // 批量删除已完成任务
  clearCompletedTasks: () => void

  // 批量删除所有任务
  clearAllTasks: () => void

  // 获取活动任务（pending + running）
  getActiveTasks: () => Task[]

  // 获取已完成任务（success + failure）
  getCompletedTasks: () => Task[]

  // 根据类型获取任务
  getTasksByType: (type: TaskType) => Task[]

  // 获取任务总数
  getTaskCount: () => number

  // 获取活动任务数
  getActiveTaskCount: () => number

  // 检查指定 Celery taskName 是否有活跃任务（running 或 pending）
  isTaskRunning: (taskName: string) => boolean
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: new Map(),
  completionCallbacks: new Map(),

  // 任务完成回调管理
  registerCompletionCallback: (taskId, callback) =>
    set((state) => {
      const newCallbacks = new Map(state.completionCallbacks)
      const callbacks = newCallbacks.get(taskId) || []
      callbacks.push(callback)
      newCallbacks.set(taskId, callbacks)
      return { completionCallbacks: newCallbacks }
    }),

  unregisterCompletionCallback: (taskId, callback) =>
    set((state) => {
      const newCallbacks = new Map(state.completionCallbacks)
      const callbacks = newCallbacks.get(taskId) || []
      const filtered = callbacks.filter(cb => cb !== callback)
      if (filtered.length > 0) {
        newCallbacks.set(taskId, filtered)
      } else {
        newCallbacks.delete(taskId)
      }
      return { completionCallbacks: newCallbacks }
    }),

  // 轮询触发器
  pollTrigger: null,
  setPollTrigger: (trigger) => set({ pollTrigger: trigger }),
  triggerPoll: async () => {
    const { pollTrigger } = get()
    if (pollTrigger) {
      await pollTrigger()
    }
  },

  addTask: (task) =>
    set((state) => {
      const newTasks = new Map(state.tasks)
      newTasks.set(task.taskId, task)
      return { tasks: newTasks }
    }),

  setTasks: (tasks) =>
    set(() => {
      const newTasks = new Map()
      tasks.forEach(task => newTasks.set(task.taskId, task))
      return { tasks: newTasks }
    }),

  updateTask: (taskId, updates) =>
    set((state) => {
      const newTasks = new Map(state.tasks)
      const task = newTasks.get(taskId)
      if (task) {
        const oldStatus = task.status
        const updatedTask = { ...task, ...updates }
        newTasks.set(taskId, updatedTask)

        // 如果任务从运行中变为完成状态，触发回调
        const isCompleted = (oldStatus === 'pending' || oldStatus === 'running' || oldStatus === 'progress') &&
                           (updates.status === 'success' || updates.status === 'failure')

        if (isCompleted) {
          // 异步执行回调，避免阻塞状态更新
          setTimeout(() => {
            const callbacks = state.completionCallbacks.get(taskId)
            if (callbacks && callbacks.length > 0) {
              callbacks.forEach(callback => {
                try {
                  callback(updatedTask)
                } catch (error) {
                  console.error('任务完成回调执行失败:', error)
                }
              })
            }
          }, 0)
        }
      }
      return { tasks: newTasks }
    }),

  removeTask: (taskId) =>
    set((state) => {
      const newTasks = new Map(state.tasks)
      newTasks.delete(taskId)
      return { tasks: newTasks }
    }),

  clearCompletedTasks: () =>
    set((state) => {
      const newTasks = new Map(state.tasks)
      for (const [id, task] of newTasks) {
        if (task.status === 'success' || task.status === 'failure') {
          newTasks.delete(id)
        }
      }
      return { tasks: newTasks }
    }),

  clearAllTasks: () =>
    set(() => ({
      tasks: new Map()
    })),

  getActiveTasks: () => {
    return Array.from(get().tasks.values()).filter(
      (t) => t.status === 'pending' || t.status === 'running' || t.status === 'progress'
    )
  },

  getCompletedTasks: () => {
    return Array.from(get().tasks.values()).filter(
      (t) => t.status === 'success' || t.status === 'failure'
    )
  },

  getTasksByType: (type) => {
    return Array.from(get().tasks.values()).filter((t) => t.taskType === type)
  },

  getTaskCount: () => {
    return get().tasks.size
  },

  getActiveTaskCount: () => {
    return get().getActiveTasks().length
  },

  isTaskRunning: (taskName) => {
    return Array.from(get().tasks.values()).some(
      t => t.taskName === taskName && (t.status === 'running' || t.status === 'pending')
    )
  }
}))
