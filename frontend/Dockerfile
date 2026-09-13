# ============ Base ============
FROM node:20-alpine AS base
WORKDIR /app
# ECS 环境下默认 npm 源偶发无响应，构建统一使用国内镜像。
ENV NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
COPY package.json ./

# ============ Development ============
FROM base AS development
RUN npm install
COPY . .
EXPOSE 5173
ENV VITE_PROXY_TARGET=http://api:8000
CMD ["npx", "vite", "--host", "0.0.0.0"]

# ============ Build ============
FROM base AS build
RUN npm install
COPY . .
RUN npm run build

# ============ Production (Nginx) ============
FROM nginx:1.27-alpine AS production
LABEL maintainer="zygao2018@163.com"
LABEL project="HeritageMind-Vue"

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
