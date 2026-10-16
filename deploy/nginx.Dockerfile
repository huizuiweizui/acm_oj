# syntax=docker/dockerfile:1
# nginx 镜像：在 Linux 下构建前端（frontend/ → dist），把产物烤进 nginx。
# 站点配置不进镜像，由 docker-compose.yml 从 deploy/nginx/ 挂载，改配置不必重新构建。
# 构建上下文是仓库根目录：docker build -f deploy/nginx.Dockerfile -t acm-oj-nginx .

ARG NODE_IMAGE=node:22-bookworm-slim
ARG NGINX_IMAGE=nginx:1.30-alpine

FROM ${NODE_IMAGE} AS build
ARG NPM_REGISTRY=https://registry.npmjs.org
# devDependencies 里有 playwright（前端自动化用），构建镜像不需要浏览器
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --registry="${NPM_REGISTRY}" --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM ${NGINX_IMAGE}
COPY --from=build /src/dist /usr/share/nginx/html
