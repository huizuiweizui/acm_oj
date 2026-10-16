#!/bin/sh
# web 容器入口：启动 gunicorn 前做几件准备工作；其他命令（manage.py 等）原样执行。
set -e

if [ "$1" = "gunicorn" ]; then
    # 1. 数据库迁移。只有一个 web 容器，迁移幂等，每次启动跑一遍，发版时不会忘
    python manage.py migrate --noinput

    # 2. Django 后台（/django-admin/）的静态文件收集到共享卷，由 nginx 直接托管
    python manage.py collectstatic --noinput --verbosity 0

    # 3. 评测临时目录：正常评测结束会自己删；容器被强杀时可能残留，启动时清掉超过 1 小时的
    if [ -n "$TMPDIR" ] && [ -d "$TMPDIR" ]; then
        find "$TMPDIR" -mindepth 1 -maxdepth 1 -mmin +60 -exec rm -rf {} + 2>/dev/null || true
    fi

    # 4. 沙箱自检：镜像没构建或 docker.sock 没挂上时，所有评测都会失败，启动时就在日志里说清楚
    if ! docker image inspect "${JUDGE_DOCKER_IMAGE:-acm-oj-sandbox:latest}" >/dev/null 2>&1; then
        echo "WARNING: 无法使用评测沙箱镜像 ${JUDGE_DOCKER_IMAGE:-acm-oj-sandbox:latest}" \
             "（未构建，或 /var/run/docker.sock 未挂载）。" \
             "在 deploy/ 下执行：docker compose --profile sandbox build sandbox" >&2
    fi
fi

exec "$@"
