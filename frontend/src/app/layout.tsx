import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "sonner";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { MobileNav } from "@/components/mobile-nav";
import { DesktopNav } from "@/components/desktop-nav";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { StockSearch } from "@/components/stock-search";
import { BacktestTaskProvider } from "@/contexts/BacktestTaskContext";
import { AIGenerationTaskProvider } from "@/contexts/AIGenerationTaskContext";
import { AIGenerationTaskMonitor } from "@/components/AIGenerationTaskMonitor";

// 拉丁字符走 Inter（next/font 自托管 + 子集化），中文落到系统字体栈（见 tailwind.config.ts fontFamily.sans）
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

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
    <html lang="zh-CN" suppressHydrationWarning className={inter.variable}>
      <body className="font-sans antialiased">
        <ErrorBoundary>
          <QueryProvider>
            <BacktestTaskProvider>
              <AIGenerationTaskProvider>
                <ThemeProvider
                  attribute="class"
                  defaultTheme="system"
                  enableSystem
                  disableTransitionOnChange
                >
                <div className="min-h-screen flex flex-col">
                {/* 全局AI生成任务监控器 */}
                <AIGenerationTaskMonitor />
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

                {/* 股票搜索 */}
                <div className="hidden md:block">
                  <StockSearch />
                </div>

                {/* 主题切换 */}
                <ThemeToggle />
              </div>
            </div>
          </header>

          {/* 桌面端导航栏 - 在中等屏幕及以上显示 */}
          <DesktopNav />

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
                <Toaster position="top-right" richColors closeButton theme="system" />
                </ThemeProvider>
              </AIGenerationTaskProvider>
            </BacktestTaskProvider>
          </QueryProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
