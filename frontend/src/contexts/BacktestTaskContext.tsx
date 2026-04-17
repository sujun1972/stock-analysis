'use client'

/**
 * 全局回测任务监控上下文
 *
 * 功能：
 * - 在后台持续监控异步回测任务
 * - 即使用户离开回测页面，监控仍继续
 * - 任务完成时显示全局Toast通知
 * - 支持多个任务同时监控
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api-client'
import { Button } from '@/components/ui/button'

interface BacktestTask {
  taskId: string
  executionId: number
  status: 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILURE' | 'CANCELLED'
  progress?: {
    current: number
    total: number
    status: string
  }
  startTime: number
}

interface BacktestTaskContextType {
  activeTasks: Map<string, BacktestTask>
  addTask: (taskId: string, executionId: number) => void
  removeTask: (taskId: string) => void
  hasActiveTasks: () => boolean
}

const BacktestTaskContext = createContext<BacktestTaskContextType | undefined>(undefined)

export function BacktestTaskProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { toast } = useToast()
  const [activeTasks, setActiveTasks] = useState<Map<string, BacktestTask>>(new Map())

  // 添加新任务
  const addTask = useCallback((taskId: string, executionId: number) => {
    setActiveTasks(prev => {
      const newTasks = new Map(prev)
      newTasks.set(taskId, {
        taskId,
        executionId,
        status: 'PENDING',
        startTime: Date.now()
      })
      return newTasks
    })
  }, [])

  // 移除任务
  const removeTask = useCallback((taskId: string) => {
    setActiveTasks(prev => {
      const newTasks = new Map(prev)
      newTasks.delete(taskId)
      return newTasks
    })
  }, [])

  // 检查是否有活跃任务
  const hasActiveTasks = useCallback(() => {
    return activeTasks.size > 0
  }, [activeTasks])

  // 全局轮询所有活跃任务
  useEffect(() => {
    if (activeTasks.size === 0) {
      return
    }

    const pollInterval = setInterval(async () => {
      const tasksToCheck = Array.from(activeTasks.entries())

      for (const [taskId, task] of tasksToCheck) {
        // 跳过已完成或失败的任务
        if (task.status === 'SUCCESS' || task.status === 'FAILURE' || task.status === 'CANCELLED') {
          continue
        }

        try {
          const statusData = await apiClient.getBacktestStatus(taskId)

          // 更新任务状态
          setActiveTasks(prev => {
            const newTasks = new Map(prev)
            const existingTask = newTasks.get(taskId)
            if (existingTask) {
              newTasks.set(taskId, {
                ...existingTask,
                status: statusData.status,
                progress: statusData.progress
              })
            }
            return newTasks
          })

          // 处理完成状态
          if (statusData.status === 'SUCCESS') {
            const execId = statusData.execution_id || statusData.result?.execution_id || task.executionId

            // 显示成功通知
            toast({
              title: '✅ 回测完成',
              description: '点击查看详细结果',
              duration: 10000, // 10秒后自动关闭
              action: (
                <Button
                  size="sm"
                  onClick={() => {
                    router.push(`/backtest-results/${execId}`)
                  }}
                >
                  查看结果
                </Button>
              ),
            })

            // 延迟移除任务，让用户有时间看到通知
            setTimeout(() => {
              removeTask(taskId)
            }, 10000)
          } else if (statusData.status === 'FAILURE') {
            // 显示失败通知
            toast({
              title: '❌ 回测失败',
              description: statusData.error || '任务执行失败',
              variant: 'destructive',
              duration: 10000,
            })

            // 延迟移除任务
            setTimeout(() => {
              removeTask(taskId)
            }, 10000)
          }
        } catch (error) {
          console.error('轮询任务状态失败:', taskId, error)

          // 如果任务超过30分钟仍在轮询，可能是异常，移除它
          const taskAge = Date.now() - task.startTime
          if (taskAge > 30 * 60 * 1000) {
            console.warn('任务超时，停止监控:', taskId)
            removeTask(taskId)
          }
        }
      }
    }, 3000) // 每3秒轮询一次

    return () => clearInterval(pollInterval)
  }, [activeTasks, toast, router, removeTask])

  // 持久化到 localStorage（页面刷新后恢复）
  useEffect(() => {
    if (typeof window === 'undefined') return

    // 保存到 localStorage
    const tasksArray = Array.from(activeTasks.entries()).map(([key, value]) => [key, value])
    if (tasksArray.length > 0) {
      localStorage.setItem('backtest_active_tasks', JSON.stringify(tasksArray))
    } else {
      localStorage.removeItem('backtest_active_tasks')
    }
  }, [activeTasks])

  // 从 localStorage 恢复任务（首次加载）
  useEffect(() => {
    if (typeof window === 'undefined') return

    const savedTasks = localStorage.getItem('backtest_active_tasks')
    if (savedTasks) {
      try {
        const tasksArray = JSON.parse(savedTasks)
        const restoredTasks = new Map<string, BacktestTask>(tasksArray)
        setActiveTasks(restoredTasks)
      } catch (error) {
        console.error('恢复任务失败:', error)
        localStorage.removeItem('backtest_active_tasks')
      }
    }
  }, [])

  return (
    <BacktestTaskContext.Provider value={{ activeTasks, addTask, removeTask, hasActiveTasks }}>
      {children}
    </BacktestTaskContext.Provider>
  )
}

export function useBacktestTask() {
  const context = useContext(BacktestTaskContext)
  if (context === undefined) {
    throw new Error('useBacktestTask must be used within a BacktestTaskProvider')
  }
  return context
}
