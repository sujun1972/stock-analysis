import type { Metadata } from "next";
import { Toaster } from "sonner";
import ErrorBoundary from "@/components/ErrorBoundary";
import { ProgressBar } from "@/components/ProgressBar";
import "./globals.css";
import "@/styles/nprogress.css";

export const metadata: Metadata = {
  title: "管理后台 - Stock Analysis Admin",
  description: "股票分析系统管理后台 - 系统设置、数据同步、监控管理",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const apiDomain = apiUrl.replace(/^https?:\/\//, '').split('/')[0]

  return (
    <html lang="zh-CN">
      <head>
        {/* DNS 预解析 - 提前解析 API 域名 */}
        <link rel="dns-prefetch" href={`//${apiDomain}`} />

        {/* 预连接 - 建立早期连接到 API 服务器 */}
        <link rel="preconnect" href={apiUrl} />
        <link rel="preconnect" href={apiUrl} crossOrigin="anonymous" />

        {/* 预加载关键字体（如果有） */}
        {/* <link rel="preload" href="/fonts/inter.woff2" as="font" type="font/woff2" crossOrigin="anonymous" /> */}
      </head>
      <body className="antialiased">
        <ProgressBar />
        <ErrorBoundary>
          {children}
        </ErrorBoundary>
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
