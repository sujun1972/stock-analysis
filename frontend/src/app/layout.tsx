import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { MobileNav } from "@/components/mobile-nav";

export const metadata: Metadata = {
  title: "A股AI量化交易系统",
  description: "Stock Analysis - AI量化交易分析平台",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <div className="min-h-screen flex flex-col">
          <header className="bg-blue-600 text-white shadow-lg">
            <div className="container-custom py-4">
              <div className="flex items-center justify-between gap-4">
                {/* 移动端汉堡菜单 */}
                <MobileNav />

                {/* 标题 */}
                <div className="flex-1">
                  <h1 className="text-xl sm:text-2xl font-bold">A股AI量化交易系统</h1>
                  <p className="text-blue-100 text-xs sm:text-sm hidden sm:block">Stock Analysis Platform</p>
                </div>

                {/* 主题切换 */}
                <ThemeToggle />
              </div>
            </div>
          </header>

          {/* 桌面端导航栏 - 在中等屏幕及以上显示 */}
          <nav className="bg-white dark:bg-gray-800 shadow hidden md:block">
            <div className="container-custom">
              <div className="flex space-x-8 py-4">
                <a href="/" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                  首页
                </a>
                <a href="/backtest" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                  策略回测
                </a>
                <a href="/ai-lab" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                  AI实验舱
                </a>
                <a href="/sync" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                  数据同步
                </a>
                <a href="/stocks" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                  股票列表
                </a>
                <a href="/settings" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                  系统设置
                </a>
              </div>
            </div>
          </nav>

          <main className="flex-1 bg-gray-50 dark:bg-gray-900">
            <div className="container-custom py-8">
              {children}
            </div>
          </main>

          <footer className="bg-gray-800 text-white py-6">
            <div className="container-custom text-center">
              <p className="text-sm">A股AI量化交易系统 &copy; 2026</p>
              <p className="text-xs text-gray-400 mt-2">
                仅供学习和研究使用，不构成任何投资建议
              </p>
            </div>
          </footer>
          </div>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
