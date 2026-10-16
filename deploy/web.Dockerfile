# Django + gunicorn 后端镜像（deploy/docker-compose.yml 的 web 服务）。
# 构建上下文是仓库根目录：docker compose 会自动处理，手动构建时
#   docker build -f deploy/web.Dockerfile -t acm-oj-web .
#
# 镜像里带一个 docker 命令行客户端：评测沙箱（judge/services/sandbox.py）通过
# `docker run` 为每次评测起一个隔离容器，客户端经挂载进来的 /var/run/docker.sock
# 调用宿主机的 Docker。安全取舍见 deploy/README.md「评测沙箱与 docker.sock」。

ARG PYTHON_IMAGE=python:3.11-slim-bookworm
ARG DOCKER_CLI_IMAGE=docker:29-cli

FROM ${DOCKER_CLI_IMAGE} AS docker-cli

# ── 构建阶段：mysqlclient 只有源码包，需要编译器和 MySQL 客户端头文件 ──────────
FROM ${PYTHON_IMAGE} AS builder
ARG APT_MIRROR=
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN if [ -n "$APT_MIRROR" ]; then \
        sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels -i "${PIP_INDEX_URL}" -r /tmp/requirements.txt

# ── 运行阶段：只装运行时库，不带编译工具链 ────────────────────────────────────
FROM ${PYTHON_IMAGE}
ARG APT_MIRROR=
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=acm_oj.settings
RUN if [ -n "$APT_MIRROR" ]; then \
        sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends libmariadb3 tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r /tmp/requirements.txt \
    && rm -rf /wheels /tmp/requirements.txt

COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker

WORKDIR /app
# 只拷运行需要的目录，不用 `COPY . .`：.env、accounts.xlsx 之类绝不能进镜像，
# 前端由 nginx 镜像单独构建。新增顶层 Django 应用时记得在这里补一行。
COPY manage.py ./
COPY acm_oj ./acm_oj
COPY judge ./judge
COPY star ./star
# build_chunks / build_graph 读取的算法笔记
COPY algorithm ./algorithm
COPY deploy/gunicorn.conf.py deploy/web-entrypoint.sh ./deploy/
RUN sed -i 's/\r$//' deploy/web-entrypoint.sh && chmod +x deploy/web-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/deploy/web-entrypoint.sh"]
CMD ["gunicorn", "-c", "/app/deploy/gunicorn.conf.py", "acm_oj.wsgi:application"]
