import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E 测试配置
 *
 * 用于测试三层架构回测系统的完整流程
 */
export default defineConfig({
  // 测试目录
  testDir: './e2e',

  // 最大测试失败次数
  fullyParallel: true,

  // 重试失败的测试
  retries: process.env.CI ? 2 : 0,

  // 并行执行测试
  workers: process.env.CI ? 1 : undefined,

  // 测试报告
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['list']
  ],

  // 全局配置
  use: {
    // 基础 URL
    baseURL: process.env.BASE_URL || 'http://localhost:3000',

    // 截图：失败时自动截图
    screenshot: 'only-on-failure',

    // 视频：失败时保留
    video: 'retain-on-failure',

    // 追踪：失败时保留
    trace: 'retain-on-failure',

    // 超时时间（30秒）
    actionTimeout: 30000,

    // 导航超时时间（30秒）
    navigationTimeout: 30000,
  },

  // 浏览器配置
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // 开发服务器配置
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },

  // 测试超时时间（60秒）
  timeout: 60000,

  // 预期超时时间（10秒）
  expect: {
    timeout: 10000,
  },
})
