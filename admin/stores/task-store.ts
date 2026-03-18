/**
 * 异步任务管理 Store (Zustand)
 *
 * 功能:
 * 1. 管理所有异步任务的状态（同步、AI分析、回测等）
 * 2. 提供添加、更新、删除任务的方法
 * 3. 支持任务分组和过滤
 * 4. 从后端API加载和同步任务历史
 * 5. 自动轮询更新活动任务状态
 */

import { create } from 'zustand'

export type TaskType = 'sync' | 'sentiment' | 'ai_analysis' | 'backtest' | 'premarket' | 'scheduler' | 'other'
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

interface TaskStore {
  // 任务列表（使用 Map 提高查找效率）
  tasks: Map<string, Task>

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
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: new Map(),

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
        newTasks.set(taskId, { ...task, ...updates })
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
  }
}))
