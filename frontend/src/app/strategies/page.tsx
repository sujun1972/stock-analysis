'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { Settings, Code2, ArrowRight, Lightbulb, CheckCircle } from 'lucide-react'

export default function StrategiesPage() {
  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      <div className="space-y-6">
        {/* 页面标题 */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">策略中心</h1>
          <p className="text-muted-foreground mt-2">
            管理您的策略配置和自定义策略代码
          </p>
        </div>

        {/* 介绍说明 */}
        <Card className="border-blue-200 bg-blue-50 dark:bg-blue-900/10">
          <CardHeader>
            <div className="flex items-start gap-3">
              <Lightbulb className="h-5 w-5 text-blue-600 mt-1" />
              <div>
                <CardTitle className="text-lg text-blue-900 dark:text-blue-100">
                  策略系统说明
                </CardTitle>
                <CardDescription className="text-blue-700 dark:text-blue-300 mt-2">
                  本系统支持两种策略类型：
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-blue-800 dark:text-blue-200">
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>
                <strong>策略配置：</strong>使用预定义的策略类型，通过调整参数来创建不同的策略实例
              </span>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>
                <strong>动态策略：</strong>编写自定义Python代码，实现完全个性化的交易逻辑
              </span>
            </div>
          </CardContent>
        </Card>

        {/* 策略类型卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 策略配置 */}
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <Settings className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <CardTitle className="text-xl">策略配置</CardTitle>
                  <CardDescription className="mt-1">
                    基于内置策略类型
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-sm text-muted-foreground space-y-2">
                <p>
                  使用系统内置的策略类型（如动量策略、均值回归等），通过配置参数来创建策略实例。
                </p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  <li>快速创建，无需编程</li>
                  <li>参数化配置，灵活调整</li>
                  <li>支持多种策略类型</li>
                  <li>配置验证和测试</li>
                </ul>
              </div>
              <Link href="/strategies/configs" className="block">
                <Button className="w-full" size="lg">
                  进入策略配置管理
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* 动态策略 */}
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                  <Code2 className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <CardTitle className="text-xl">动态策略</CardTitle>
                  <CardDescription className="mt-1">
                    自定义Python代码
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-sm text-muted-foreground space-y-2">
                <p>
                  编写自定义的Python策略代码，实现完全个性化的交易逻辑和信号生成算法。
                </p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  <li>完全自定义逻辑</li>
                  <li>代码编辑器支持</li>
                  <li>语法检查和验证</li>
                  <li>安全沙箱测试</li>
                </ul>
              </div>
              <Link href="/strategies/dynamic" className="block">
                <Button className="w-full" variant="secondary" size="lg">
                  进入动态策略管理
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        {/* 使用流程 */}
        <Card>
          <CardHeader>
            <CardTitle>使用流程</CardTitle>
            <CardDescription>
              如何使用策略系统进行回测
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="flex flex-col items-center text-center p-4 bg-muted/30 rounded-lg">
                <div className="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold mb-3">
                  1
                </div>
                <h3 className="font-semibold mb-2">创建策略</h3>
                <p className="text-sm text-muted-foreground">
                  在策略配置或动态策略页面创建新的策略
                </p>
              </div>

              <div className="flex flex-col items-center text-center p-4 bg-muted/30 rounded-lg">
                <div className="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold mb-3">
                  2
                </div>
                <h3 className="font-semibold mb-2">配置参数</h3>
                <p className="text-sm text-muted-foreground">
                  根据需求调整策略参数或编写代码
                </p>
              </div>

              <div className="flex flex-col items-center text-center p-4 bg-muted/30 rounded-lg">
                <div className="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold mb-3">
                  3
                </div>
                <h3 className="font-semibold mb-2">验证测试</h3>
                <p className="text-sm text-muted-foreground">
                  测试策略的有效性和正确性
                </p>
              </div>

              <div className="flex flex-col items-center text-center p-4 bg-muted/30 rounded-lg">
                <div className="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold mb-3">
                  4
                </div>
                <h3 className="font-semibold mb-2">回测分析</h3>
                <p className="text-sm text-muted-foreground">
                  在回测页面使用策略进行历史数据回测
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 快速链接 */}
        <Card>
          <CardHeader>
            <CardTitle>相关功能</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              <Link href="/backtest">
                <Button variant="outline" size="sm">
                  策略回测
                </Button>
              </Link>
              <Link href="/my-backtests">
                <Button variant="outline" size="sm">
                  我的回测
                </Button>
              </Link>
              <Link href="/ai-lab">
                <Button variant="outline" size="sm">
                  AI实验舱
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
