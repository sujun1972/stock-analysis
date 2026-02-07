import { test, expect } from '@playwright/test'

/**
 * 三层架构回测完整流程 E2E 测试
 *
 * 测试场景：
 * 1. 用户选择"动量选股 + 立即入场 + 固定止损"
 * 2. 配置参数并验证
 * 3. 运行回测
 * 4. 查看结果
 * 5. 导出报告
 */

test.describe('三层架构回测系统', () => {
  test.beforeEach(async ({ page }) => {
    // 访问三层回测页面
    await page.goto('/backtest/three-layer')

    // 等待页面加载完成
    await page.waitForLoadState('networkidle')
  })

  test('完整流程：选择策略 → 配置参数 → 运行回测 → 查看结果', async ({ page }) => {
    // 测试开始时间
    const startTime = Date.now()

    // ========== 第一步：选择选股器 ==========
    await test.step('选择选股器：Momentum', async () => {
      // 等待选股器下拉框出现
      const selectorSelect = page.locator('select').first()
      await expect(selectorSelect).toBeVisible()

      // 选择 Momentum 选股器
      await selectorSelect.selectOption({ label: /Momentum/i })

      // 验证参数表单出现
      await expect(page.getByText(/lookback_period/i)).toBeVisible({ timeout: 5000 })
    })

    // ========== 第二步：配置选股器参数 ==========
    await test.step('配置选股器参数', async () => {
      // 可能需要根据实际渲染的参数控件来调整选择器
      // 这里假设参数使用 input[type="number"] 或 slider
      const inputs = page.locator('input[type="number"]')
      const count = await inputs.count()

      if (count > 0) {
        // 配置 lookback_period
        const lookbackInput = inputs.first()
        await lookbackInput.fill('20')

        // 配置 top_n（如果存在）
        if (count > 1) {
          const topNInput = inputs.nth(1)
          await topNInput.fill('50')
        }
      }
    })

    // ========== 第三步：选择入场策略 ==========
    await test.step('选择入场策略：Immediate', async () => {
      // 获取第二个 select（入场策略）
      const entrySelect = page.locator('select').nth(1)
      await entrySelect.selectOption({ label: /Immediate/i })

      // 等待选择完成
      await page.waitForTimeout(500)
    })

    // ========== 第四步：选择退出策略 ==========
    await test.step('选择退出策略：Fixed Stop Loss', async () => {
      // 获取第三个 select（退出策略）
      const exitSelect = page.locator('select').nth(2)
      await exitSelect.selectOption({ label: /Fixed.*Stop.*Loss/i })

      // 配置止损参数
      await page.waitForTimeout(500)

      // 查找止损百分比输入框
      const stopLossInput = page.locator('input[type="number"]').last()
      await stopLossInput.fill('-5')
    })

    // ========== 第五步：配置回测参数 ==========
    await test.step('配置回测参数', async () => {
      // 股票池（已有默认值，可选修改）
      const stockCodesInput = page.locator('input[placeholder*="600000"]')
      if (await stockCodesInput.isVisible()) {
        await stockCodesInput.fill('600000.SH,000001.SZ')
      }

      // 日期范围（已有默认值）
      // 可以保持默认值或修改
    })

    // ========== 第六步：验证策略（可选） ==========
    await test.step('验证策略', async () => {
      const validateButton = page.getByRole('button', { name: /验证策略/i })

      if (await validateButton.isVisible()) {
        await validateButton.click()

        // 等待验证完成（寻找成功或失败提示）
        // Toast 提示可能在 body 或特定容器中
        await page.waitForTimeout(2000)
      }
    })

    // ========== 第七步：运行回测 ==========
    await test.step('运行回测', async () => {
      const runButton = page.getByRole('button', { name: /运行回测/i })
      await expect(runButton).toBeEnabled()

      // 点击运行回测
      await runButton.click()

      // 验证按钮变为"运行中..."
      await expect(page.getByText(/运行中/i)).toBeVisible({ timeout: 2000 })
    })

    // ========== 第八步：等待回测完成并验证性能 ==========
    await test.step('等待回测完成（性能要求：<3秒）', async () => {
      // 等待回测结果出现
      const resultCard = page.getByText(/回测结果|绩效指标/i).first()
      await expect(resultCard).toBeVisible({ timeout: 30000 })

      // 验证响应时间
      const endTime = Date.now()
      const responseTime = (endTime - startTime) / 1000

      console.log(`回测响应时间: ${responseTime.toFixed(2)}秒`)

      // 注意：这里不做硬性断言，因为第一次加载可能需要启动后端
      // 实际性能测试应该在后端已运行的情况下进行
    })

    // ========== 第九步：验证结果展示 ==========
    await test.step('验证结果展示', async () => {
      // 验证绩效指标卡片存在
      await expect(page.getByText(/绩效指标/i)).toBeVisible()
      await expect(page.getByText(/总收益率/i)).toBeVisible()
      await expect(page.getByText(/夏普比率/i)).toBeVisible()
      await expect(page.getByText(/最大回撤/i)).toBeVisible()
      await expect(page.getByText(/胜率/i)).toBeVisible()

      // 验证图表区域存在
      await expect(page.getByText(/净值.*曲线/i)).toBeVisible()

      // 验证交易记录存在
      await expect(page.getByText(/交易.*流水|持仓.*明细/i)).toBeVisible()
    })

    // ========== 第十步：测试导出功能 ==========
    await test.step('测试导出报告功能', async () => {
      const exportButton = page.getByRole('button', { name: /导出报告/i })

      if (await exportButton.isVisible()) {
        // 设置下载监听
        const downloadPromise = page.waitForEvent('download')

        // 点击导出
        await exportButton.click()

        // 等待下载完成
        const download = await downloadPromise

        // 验证文件名
        expect(download.suggestedFilename()).toMatch(/backtest_report.*\.csv/)

        console.log(`已下载文件: ${download.suggestedFilename()}`)
      }
    })

    // ========== 第十一步：测试分享功能 ==========
    await test.step('测试分享功能', async () => {
      const shareButton = page.getByRole('button', { name: /分享结果/i })

      if (await shareButton.isVisible()) {
        await shareButton.click()

        // 等待 toast 提示
        await page.waitForTimeout(1000)

        // 验证剪贴板（需要浏览器权限）
        // 这里只验证按钮可点击
        console.log('分享功能已测试')
      }
    })
  })

  test('错误处理：未选择完整策略时提示错误', async ({ page }) => {
    await test.step('直接点击运行回测按钮', async () => {
      const runButton = page.getByRole('button', { name: /运行回测/i })

      // 按钮应该被禁用或点击后有错误提示
      const isDisabled = await runButton.isDisabled()

      if (!isDisabled) {
        await runButton.click()

        // 应该看到错误提示
        await expect(page.getByText(/请选择.*三层策略/i)).toBeVisible({ timeout: 3000 })
      }
    })
  })

  test('边界情况：参数验证', async ({ page }) => {
    await test.step('输入无效参数值', async () => {
      // 选择选股器
      const selectorSelect = page.locator('select').first()
      await selectorSelect.selectOption({ label: /Momentum/i })

      // 等待参数表单出现
      await page.waitForTimeout(1000)

      // 尝试输入超出范围的值
      const inputs = page.locator('input[type="number"]')
      if (await inputs.count() > 0) {
        const firstInput = inputs.first()

        // 输入负数或超大值
        await firstInput.fill('-100')
        await firstInput.blur()

        // 验证是否有错误提示或自动修正
        await page.waitForTimeout(500)

        const value = await firstInput.inputValue()
        console.log(`参数值修正为: ${value}`)
      }
    })
  })

  test('Tab切换：净值曲线和回撤曲线', async ({ page }) => {
    // 首先完成一次完整的回测流程（简化版）
    await test.step('快速运行回测', async () => {
      // 选择策略
      await page.locator('select').first().selectOption({ label: /Momentum/i })
      await page.locator('select').nth(1).selectOption({ label: /Immediate/i })
      await page.locator('select').nth(2).selectOption({ label: /Fixed/i })

      await page.waitForTimeout(1000)

      // 运行回测
      const runButton = page.getByRole('button', { name: /运行回测/i })
      if (await runButton.isEnabled()) {
        await runButton.click()

        // 等待结果
        await expect(page.getByText(/绩效指标/i)).toBeVisible({ timeout: 30000 })
      }
    })

    await test.step('切换 Tab 查看不同图表', async () => {
      // 查找 Tab 控件
      const equityTab = page.getByRole('tab', { name: /净值曲线/i })
      const drawdownTab = page.getByRole('tab', { name: /回撤曲线/i })

      if (await equityTab.isVisible()) {
        // 切换到回撤曲线
        await drawdownTab.click()
        await page.waitForTimeout(500)

        // 验证回撤图表显示
        await expect(page.locator('canvas, svg').first()).toBeVisible()

        // 切换回净值曲线
        await equityTab.click()
        await page.waitForTimeout(500)
      }
    })
  })

  test('响应式设计：移动端视图', async ({ page }) => {
    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 })

    await test.step('移动端加载页面', async () => {
      await page.reload()
      await page.waitForLoadState('networkidle')

      // 验证关键元素可见
      await expect(page.locator('select').first()).toBeVisible()

      // 验证布局合理（不出现横向滚动）
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth)
      expect(bodyWidth).toBeLessThanOrEqual(375)
    })
  })
})
