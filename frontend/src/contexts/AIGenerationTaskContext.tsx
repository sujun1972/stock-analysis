'use client'

/**
 * 全局AI策略生成任务监控上下文
 *
 * 功能：
 * - 在后台持续监控AI生成任务
 * - 即使用户离开创建策略页面，监控仍继续
 * - 任务完成时显示全局Toast通知
 * - 限制同一时间只能有一个AI生成任务（防止资源浪费）
 * - 持久化到localStorage（页面刷新后恢复）
 * - 缓存生成结果供页面使用
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api-client'
import { Button } from '@/components/ui/button'

interface AIGenerationResult {
  strategy_code: string
  strategy_metadata: any
  tokens_used: number
  generation_time: number
  provider_used: string
}

interface AITask {
  taskId: string
  status: 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILURE' | 'CANCELLED'
  message: string
  startTime: number
  providerUsed?: string
  // 缓存的生成结果
  cachedResult?: AIGenerationResult
}

interface AIGenerationTaskContextType {
  activeTasks: Map<string, AITask>
  addTask: (taskId: string, providerUsed?: string) => void
  removeTask: (taskId: string) => void
  cancelTask: (taskId: string) => Promise<void>
  hasActiveTasks: () => boolean
  getTaskResult: (taskId: string) => AIGenerationResult | undefined
  clearCachedResult: (taskId: string) => void
}

const AIGenerationTaskContext = createContext<AIGenerationTaskContextType | undefined>(undefined)

const STORAGE_KEY = 'ai_generation_active_tasks'
const POLL_INTERVAL = 2000 // 2秒轮询
const TASK_TIMEOUT = 5 * 60 * 1000 // 5分钟超时

export function AIGenerationTaskProvider({ children }: { children: React.ReactNode }) {
  const { toast } = useToast()
  const [activeTasks, setActiveTasks] = useState<Map<string, AITask>>(new Map())

  // 添加新任务
  const addTask = useCallback((taskId: string, providerUsed?: string) => {
    setActiveTasks((prev) => {
      // 检查是否已有活跃任务（限制同时只能有一个）
      const hasActiveTask = Array.from(prev.values()).some(
        (task) => task.status === 'PENDING' || task.status === 'PROGRESS'
      )

      if (hasActiveTask) {
        toast({
          title: '⚠️ 已有AI生成任务在进行中',
          description: '请等待当前任务完成后再提交新任务',
          variant: 'destructive'
        })
        return prev // 不添加新任务
      }

      const newTasks = new Map(prev)
      newTasks.set(taskId, {
        taskId,
        status: 'PENDING',
        message: '任务已提交，等待AI服务响应...',
        startTime: Date.now(),
        providerUsed
      })
      return newTasks
    })
  }, [toast])

  // 移除任务
  const removeTask = useCallback((taskId: string) => {
    setActiveTasks((prev) => {
      const newTasks = new Map(prev)
      newTasks.delete(taskId)
      return newTasks
    })
  }, [])

  // 取消任务
  const cancelTask = useCallback(async (taskId: string) => {
    try {
      await apiClient.cancelAIGeneration(taskId)

      setActiveTasks((prev) => {
        const newTasks = new Map(prev)
        const task = newTasks.get(taskId)
        if (task) {
          newTasks.set(taskId, {
            ...task,
            status: 'CANCELLED',
            message: '任务已取消'
          })
        }
        return newTasks
      })

      toast({
        title: '✅ 任务已取消',
        description: `AI生成任务已成功取消`
      })

      // 延迟移除
      setTimeout(() => removeTask(taskId), 3000)
    } catch (error) {
      console.error('取消任务失败:', error)
      toast({
        title: '❌ 取消失败',
        description: error instanceof Error ? error.message : '未知错误',
        variant: 'destructive'
      })
    }
  }, [toast, removeTask])

  // 检查是否有活跃任务
  const hasActiveTasks = useCallback(() => {
    return Array.from(activeTasks.values()).some(
      (task) => task.status === 'PENDING' || task.status === 'PROGRESS'
    )
  }, [activeTasks])

  // 获取缓存的任务结果
  const getTaskResult = useCallback((taskId: string): AIGenerationResult | undefined => {
    return activeTasks.get(taskId)?.cachedResult
  }, [activeTasks])

  // 清除缓存结果
  const clearCachedResult = useCallback((taskId: string) => {
    setActiveTasks((prev) => {
      const newTasks = new Map(prev)
      const task = newTasks.get(taskId)
      if (task) {
        newTasks.set(taskId, {
          ...task,
          cachedResult: undefined
        })
      }
      return newTasks
    })
  }, [])

  // 全局轮询所有活跃任务（持续监控，即使离开页面）
  useEffect(() => {
    if (activeTasks.size === 0) {
      return
    }

    const pollInterval = setInterval(async () => {
      const tasksToCheck = Array.from(activeTasks.entries())

      for (const [taskId, task] of tasksToCheck) {
        // 跳过已完成的任务
        if (task.status === 'SUCCESS' || task.status === 'FAILURE' || task.status === 'CANCELLED') {
          continue
        }

        try {
          const statusData = await apiClient.getAIGenerationStatus(taskId)

          // 更新任务状态
          setActiveTasks((prev) => {
            const newTasks = new Map(prev)
            const existingTask = newTasks.get(taskId)
            if (existingTask) {
              newTasks.set(taskId, {
                ...existingTask,
                status: statusData.status,
                message: statusData.message,
                providerUsed: statusData.provider_used || existingTask.providerUsed
              })
            }
            return newTasks
          })

          // 处理成功
          if (statusData.status === 'SUCCESS') {
            // 缓存生成结果
            const result: AIGenerationResult = {
              strategy_code: statusData.strategy_code!,
              strategy_metadata: statusData.strategy_metadata!,
              tokens_used: statusData.tokens_used || 0,
              generation_time: statusData.generation_time || 0,
              provider_used: statusData.provider_used || 'unknown'
            }

            setActiveTasks((prev) => {
              const newTasks = new Map(prev)
              const existingTask = newTasks.get(taskId)
              if (existingTask) {
                newTasks.set(taskId, {
                  ...existingTask,
                  cachedResult: result
                })
              }
              return newTasks
            })

            // 显示成功通知（全局Toast，即使不在策略页面也能看到）
            toast({
              title: '✅ AI策略生成成功',
              description: `使用 ${result.provider_used} 生成，耗时 ${result.generation_time}秒`,
              duration: 15000, // 15秒后自动关闭
              action: (
                <Button
                  size="sm"
                  onClick={() => {
                    // 跳转到创建策略页面
                    window.location.href = '/strategies/create'
                  }}
                >
                  查看结果
                </Button>
              )
            })

            // 延迟移除任务（保留结果15秒供用户查看）
            setTimeout(() => {
              removeTask(taskId)
            }, 15000)
          }
          // 处理失败
          else if (statusData.status === 'FAILURE') {
            toast({
              title: '❌ AI策略生成失败',
              description: statusData.error || '未知错误',
              variant: 'destructive',
              duration: 10000
            })

            // 延迟移除任务
            setTimeout(() => {
              removeTask(taskId)
            }, 10000)
          }
        } catch (error) {
          console.error('轮询AI任务状态失败:', taskId, error)

          // 超时保护：超过5分钟自动移除
          const taskAge = Date.now() - task.startTime
          if (taskAge > TASK_TIMEOUT) {
            console.warn('AI任务超时，停止监控:', taskId)
            toast({
              title: '⚠️ 任务超时',
              description: 'AI生成任务超过5分钟未完成，已自动取消',
              variant: 'destructive'
            })
            removeTask(taskId)
          }
        }
      }
    }, POLL_INTERVAL)

    return () => clearInterval(pollInterval)
  }, [activeTasks, toast, removeTask])

  // 持久化到 localStorage（页面刷新后恢复）
  useEffect(() => {
    if (typeof window === 'undefined') return

    // 保存到 localStorage
    const tasksArray = Array.from(activeTasks.entries()).map(([key, value]) => [key, value])
    if (tasksArray.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(tasksArray))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [activeTasks])

  // 从 localStorage 恢复任务（首次加载）
  useEffect(() => {
    if (typeof window === 'undefined') return

    const savedTasks = localStorage.getItem(STORAGE_KEY)
    if (savedTasks) {
      try {
        const tasksArray = JSON.parse(savedTasks)
        const restoredTasks = new Map<string, AITask>(tasksArray)

        // 过滤掉超时的任务
        const validTasks = new Map<string, AITask>()
        const now = Date.now()

        restoredTasks.forEach((task, taskId) => {
          const taskAge = now - task.startTime
          if (taskAge < TASK_TIMEOUT) {
            validTasks.set(taskId, task)
          }
        })

        setActiveTasks(validTasks)

        if (validTasks.size > 0) {
          toast({
            title: '🔄 已恢复AI生成任务',
            description: `检测到 ${validTasks.size} 个未完成的AI生成任务，继续监控中...`
          })
        }
      } catch (error) {
        console.error('恢复AI任务失败:', error)
        localStorage.removeItem(STORAGE_KEY)
      }
    }
  }, []) // 仅首次加载时执行

  return (
    <AIGenerationTaskContext.Provider
      value={{
        activeTasks,
        addTask,
        removeTask,
        cancelTask,
        hasActiveTasks,
        getTaskResult,
        clearCachedResult
      }}
    >
      {children}
    </AIGenerationTaskContext.Provider>
  )
}

export function useAIGenerationTask() {
  const context = useContext(AIGenerationTaskContext)
  if (!context) {
    throw new Error('useAIGenerationTask must be used within AIGenerationTaskProvider')
  }
  return context
}
