# ============================================================
# FilesReadSystem Frontend - React + Vite
# 多阶段构建: Node 构建 -> Nginx 运行
# ============================================================

# === 阶段1: 构建阶段 ===
FROM node:20-alpine AS builder

WORKDIR /app

# 复制 package 文件和锁文件
COPY package.json pnpm-lock.yaml* ./

# 安装 pnpm 并安装依赖
RUN npm install -g pnpm && \
    pnpm install --frozen-lockfile

# 复制源码
COPY . .

# 构建生产版本
RUN pnpm build

# === 阶段2: 运行阶段 ===
FROM nginx:alpine

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 暴露端口
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]