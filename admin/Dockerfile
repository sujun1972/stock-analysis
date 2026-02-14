# 阶段1: 依赖安装
FROM node:18-alpine AS deps
WORKDIR /app

# 复制依赖文件
COPY package.json package-lock.json* ./
RUN npm ci

# 阶段2: 构建阶段
FROM node:18-alpine AS builder
WORKDIR /app

# 从deps阶段复制node_modules
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 设置环境变量
ENV NEXT_TELEMETRY_DISABLED 1
ENV NODE_ENV production

# 构建Next.js应用
RUN npm run build

# 阶段3: 运行阶段
FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# 添加非root用户
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# 复制必要文件
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# 修改文件所有者
RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3002

ENV PORT 3002
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
