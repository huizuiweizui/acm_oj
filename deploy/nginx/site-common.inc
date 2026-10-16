# HTTP / HTTPS 两种站点配置共用的部分：前端 SPA + 反代 Django。
# 被 site-http.conf / site-https.conf 在 server 块里 include。

server_tokens off;
access_log /var/log/nginx/access.log timed;
# 重定向用相对地址：宿主机映射到非 80 端口时，nginx 拼的绝对地址会丢掉端口
absolute_redirect off;
# 题目测试数据、学生名单 xlsx 等上传
client_max_body_size 50m;

# ── 反向代理到 web（gunicorn）──────────────────────────────────────────
# 用变量 + Docker 内置 DNS：web 容器重建后 IP 会变，nginx 按需重新解析，不必跟着重启
resolver 127.0.0.11 valid=10s ipv6=off;
set $django http://web:8000;

proxy_http_version 1.1;
# $http_host 保留端口：非 80 端口访问时 Django 后台的 CSRF Origin 校验才对得上
proxy_set_header Host              $http_host;
proxy_set_header X-Real-IP         $remote_addr;
# 覆盖而不是追加（$proxy_add_x_forwarded_for）：DRF 限流按 X-Forwarded-For 识别客户端，
# 追加模式下客户端自带一个伪造的头就能每次换身份，绕过登录 / 提交 / AI 接口的限流
proxy_set_header X-Forwarded-For   $remote_addr;
proxy_set_header X-Forwarded-Proto $scheme;
# 星语"大模型改造"是同步请求，生成-校验-修复最多 3 轮；前端等 180 秒，这里留足余量
proxy_read_timeout 300s;
proxy_send_timeout 300s;

location /api/ {
    proxy_pass $django;
}

# AI 问答是 SSE 流式输出：关掉代理缓冲与压缩，模型吐一个字就推给浏览器一个字
location = /api/ai/ask/ {
    proxy_pass $django;
    proxy_buffering off;
    proxy_cache off;
    gzip off;
}

location /django-admin/ {
    proxy_pass $django;
}
# 少打了结尾斜杠时补上，否则会落到 SPA 的 404 页
location = /django-admin {
    return 301 /django-admin/;
}

# Django 后台的静态文件：web 启动时 collectstatic 到共享卷，nginx 只读挂载
location /static/ {
    alias /srv/static/;
    expires 7d;
    access_log off;
}

# ── 前端 SPA ───────────────────────────────────────────────────────────
root /usr/share/nginx/html;

gzip on;
gzip_vary on;
gzip_comp_level 5;
gzip_min_length 1024;
# 不要加 text/event-stream：压缩需要攒缓冲，SSE 就不再是流式了
gzip_types text/plain text/css application/javascript application/json image/svg+xml;

# Vite 产物文件名带内容哈希，可以长期缓存
location /assets/ {
    add_header Cache-Control "public, max-age=31536000, immutable";
    access_log off;
    try_files $uri =404;
}

# 其余路径回落到 index.html，交给 Vue Router；index.html 不缓存，发版后刷新即生效
location / {
    add_header Cache-Control "no-cache";
    add_header X-Content-Type-Options "nosniff";
    add_header X-Frame-Options "SAMEORIGIN";
    add_header Referrer-Policy "same-origin";
    try_files $uri $uri/ /index.html;
}
