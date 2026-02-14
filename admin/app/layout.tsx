import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "管理后台 - Stock Analysis Admin",
  description: "股票分析系统管理后台 - 系统设置、数据同步、监控管理",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
