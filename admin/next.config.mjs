/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,

  // 启用TypeScript和ESLint检查确保代码质量
  typescript: {
    ignoreBuildErrors: false,
  },
  eslint: {
    ignoreDuringBuilds: false,
  },

  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://backend:8000/api/:path*',
      },
    ]
  },

  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },

  compiler: {
    removeConsole: process.env.NODE_ENV === 'production' ? { exclude: ['error', 'warn'] } : false,
  },

  // 忽略开发环境的特定路径404错误
  experimental: {
    // 优化包导入，减少打包大小
    optimizePackageImports: [
      'lucide-react',
      'date-fns',
      '@radix-ui/react-dialog',
      '@radix-ui/react-dropdown-menu',
      '@radix-ui/react-popover',
      '@radix-ui/react-select',
      '@radix-ui/react-tabs',
    ],
  },

  // Webpack 配置 - 代码分割优化
  webpack: (config, { isServer }) => {
    if (!isServer) {
      // 客户端代码分割策略
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: 'all',
          cacheGroups: {
            // Recharts 单独打包（图表库较大）
            recharts: {
              test: /[\\/]node_modules[\\/]recharts/,
              name: 'recharts',
              priority: 30,
              reuseExistingChunk: true,
            },
            // Monaco Editor 单独打包（编辑器较大）
            monaco: {
              test: /[\\/]node_modules[\\/](@monaco-editor|monaco-editor)/,
              name: 'monaco-editor',
              priority: 30,
              reuseExistingChunk: true,
            },
            // Radix UI 组件打包
            radixUI: {
              test: /[\\/]node_modules[\\/]@radix-ui/,
              name: 'radix-ui',
              priority: 25,
              reuseExistingChunk: true,
            },
            // TanStack 库（React Query + Virtual）
            tanstack: {
              test: /[\\/]node_modules[\\/]@tanstack/,
              name: 'tanstack',
              priority: 25,
              reuseExistingChunk: true,
            },
            // React 核心库
            react: {
              test: /[\\/]node_modules[\\/](react|react-dom|scheduler)/,
              name: 'react-vendor',
              priority: 40,
              reuseExistingChunk: true,
            },
            // 其他第三方库
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendor',
              priority: 10,
              reuseExistingChunk: true,
            },
            // 公共组件代码
            common: {
              minChunks: 2,
              priority: 5,
              reuseExistingChunk: true,
              name: 'common',
            },
          },
        },
      }
    }

    return config
  },
}

export default nextConfig
