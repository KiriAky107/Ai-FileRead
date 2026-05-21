# ============================================================
# FilesReadSystem Frontend - React + Vite
# 多阶段构建: Node 构建 -> Nginx 运行
# ============================================================

# === 阶段1: 构建阶段 ===
FROM node:20-alpine AS builder

WORKDIR /app


COPY package.json ./

# 设置镜像源并安装
RUN npm config set registry https://registry.npmmirror.com && \
    npm install -g pnpm && \
    pnpm config set registry https://registry.npmmirror.com && \
    pnpm install --registry https://registry.npmmirror.com --no-frozen-lockfile

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
