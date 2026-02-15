import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// 公开路径（不需要认证）
const publicPaths = ['/login']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // 检查是否为公开路径
  if (publicPaths.some(path => pathname.startsWith(path))) {
    return NextResponse.next()
  }

  // 检查是否有认证信息（从cookie或localStorage，这里简化处理）
  // 注意：中间件无法直接访问localStorage，实际认证检查在客户端进行
  // 这里主要用于SEO和初始重定向

  return NextResponse.next()
}

// 配置需要middleware的路径
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
