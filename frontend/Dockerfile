# 构建阶段
FROM node:20-alpine AS builder

WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖（如果有package-lock.json使用ci，否则使用install）
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 生产阶段
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV production

# 创建非root用户
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 复制必要文件
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
