import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { BacktestTaskProvider } from "@/contexts/BacktestTaskContext";
import { AIGenerationTaskProvider } from "@/contexts/AIGenerationTaskContext";
import { AppShell } from "@/components/AppShell";

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
                  <AppShell>{children}</AppShell>
                </ThemeProvider>
              </AIGenerationTaskProvider>
            </BacktestTaskProvider>
          </QueryProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
