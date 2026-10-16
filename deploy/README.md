# 生产部署（阿里云 ECS · Docker Compose）

一台 Linux 服务器上用 Docker Compose 跑起整个平台（含星语模块）：

```
浏览器 ──80/443──▶ nginx ─┬─ /                     前端 SPA（构建时烤进 nginx 镜像）
                          ├─ /static/              Django 后台的静态文件（与 web 共享的卷）
                          └─ /api/  /django-admin/ ──▶ web：gunicorn（gthread）:8000
                                                        ├─ db：MySQL 8.4
                                                        ├─ redis：限流计数（多进程共享）
                                                        └─ /var/run/docker.sock ──▶ 宿主机 Docker
                                                                                      └─ 每次评测起一个沙箱容器
```

只有 nginx 对外发布端口；MySQL、Redis、gunicorn 都只在编排内部网络里可达。

| 文件 | 作用 |
|------|------|
| `docker-compose.yml` | 编排：db / redis / web / nginx，外加只构建不启动的 sandbox 镜像 |
| `web.Dockerfile` | 后端镜像：Python 3.11 + 依赖 + gunicorn + docker 命令行客户端 |
| `web-entrypoint.sh` | web 启动前自动 `migrate`、`collectstatic`、清理残留临时目录、检查沙箱镜像 |
| `gunicorn.conf.py` | worker 模型、超时、进程数；重启后恢复未完成的评测 |
| `nginx.Dockerfile` | 在 Linux 下 `npm ci && npm run build`，把 `dist` 烤进 nginx 镜像 |
| `nginx/site-http.conf` | 默认站点（HTTP，公网 IP 直接访问） |
| `nginx/site-https.conf` | HTTPS 站点（有域名和证书时启用） |
| `nginx/site-common.inc` | 两种站点共用：SPA 回退、反代、SSE、超时 |
| `env.production.example` | 生产环境变量模板，复制为 `deploy/.env` 后填写 |
| `../Dockerfile.sandbox` | 评测沙箱镜像（gcc / g++ / JDK / Python） |

所有 `docker compose` 命令都在 **`deploy/` 目录**下执行。

---

## 一、从空服务器到能访问

下文假设以 root 登录（ECS 默认），代码放在 `/srv/acm_oj`。

### 0. 准备服务器

- **规格**：2 vCPU / 4 GiB 起（Java 编译 + MySQL + 首次构建前端都吃内存），系统盘 40 GiB。
  只有 2 GiB 内存时先加 swap（见「七、常见问题」）。
- **系统**：Ubuntu 22.04 / 24.04 64 位；Alibaba Cloud Linux 3 也可以（安装命令见下）。
- **安全组**入方向放行 22、80；启用 HTTPS 时再放行 443。不要放行 3306 / 6379 / 8000——编排里它们本来就不对外。
- **地域与备案**：中国内地地域的服务器用**域名**访问需要 ICP 备案（流程以周计）；比赛演示直接用
  **公网 IP + HTTP** 访问，不受影响。

### 1. 安装 Docker（含 compose 插件）

Ubuntu：

```bash
apt-get update && apt-get install -y ca-certificates curl git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Alibaba Cloud Linux 3：

```bash
dnf config-manager --add-repo=https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
dnf -y install dnf-plugin-releasever-adapter --repo alinux3-plus
dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin git
systemctl enable --now docker
```

确认：`docker compose version` 能输出版本号。

**Docker Hub 镜像加速**（中国内地服务器基本必需）：在阿里云控制台「容器镜像服务 ACR → 镜像工具 →
镜像加速器」拿到专属地址，然后：

```bash
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{ "registry-mirrors": ["https://<你的加速器ID>.mirror.aliyuncs.com"] }
EOF
systemctl daemon-reload && systemctl restart docker
docker pull redis:7-alpine    # 能拉下来就说明加速生效
```

仍然拉不动时：换中国香港 / 海外地域的服务器；或在能访问 Docker Hub 的机器上
`docker pull` 后 `docker save` 打包，传到服务器 `docker load`。用到的基础镜像：
`mysql:8.4`、`redis:7-alpine`、`python:3.11-slim-bookworm`、`docker:29-cli`、
`node:22-bookworm-slim`、`nginx:1.30-alpine`、`debian:bookworm-slim`。

### 2. 获取代码

部署用的分支需要**已提交并推送**（包含 `deploy/` 目录）。

```bash
git clone -b <分支名> https://github.com/huizuiweizui/acm_oj.git /srv/acm_oj
```

服务器访问 GitHub 不稳定（或仓库是私有的）时，在本机（Windows PowerShell，仓库根目录）打包上传：

```powershell
# -c core.autocrlf=false：保持仓库里的 LF 换行。否则 Windows 上打出来的包是 CRLF，
# 脚本和由模板复制出的 deploy/.env 在 Linux 上可能出错
git -c core.autocrlf=false archive --format=tar.gz -o acm_oj.tar.gz HEAD
scp acm_oj.tar.gz root@<公网IP>:/srv/
```

```bash
mkdir -p /srv/acm_oj && tar -xzf /srv/acm_oj.tar.gz -C /srv/acm_oj
```

`git archive` 只打包已提交的内容，`.env`、`accounts.xlsx` 等被 git 忽略的文件不会带上——这正是想要的。

### 3. 填写 `deploy/.env`

```bash
cd /srv/acm_oj/deploy
cp env.production.example .env && chmod 600 .env
# 随机生成密钥与数据库密码（十六进制，不含 $ 等特殊字符）
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32)|" .env
sed -i "s|^MYSQL_ROOT_PASSWORD=.*|MYSQL_ROOT_PASSWORD=$(openssl rand -hex 16)|" .env
sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -hex 16)|" .env
# 访问地址：把占位符换成公网 IP（同时改 ALLOWED_HOSTS 与 CORS_ORIGINS）
sed -i "s|your-server-ip|<公网IP>|g" .env
# 最后手动填大模型密钥：LLM_API_KEY=sk-...（DeepSeek 的地址与模型名模板里已写好）
vi .env
```

注意：

- 模板里 `DEBUG=False`、`USE_DOCKER_SANDBOX=True`、`REDIS_URL` 等由 `docker-compose.yml` 强制注入，
  即使 `.env` 写错也不会生效。
- `MYSQL_ROOT_PASSWORD` / `DB_PASSWORD` **只在 MySQL 第一次初始化（空数据卷）时生效**。之后再改 `.env`
  不会改掉数据库里的密码，Django 反而会连不上。要换密码请进 MySQL 用 `ALTER USER` 改，再同步 `.env`。
- `deploy/.env` 被 `.gitignore` 排除。真实密钥只存在服务器上，不要提交、不要写回模板。

### 4. 构建镜像

```bash
cd /srv/acm_oj/deploy
docker compose --profile sandbox build
```

一次构建三个镜像：`acm-oj-web`、`acm-oj-nginx`（含前端构建）、`acm-oj-sandbox`（评测沙箱）。
首次 10–30 分钟，主要花在下载 JDK、Python 依赖和 npm 包上。`.env` 末尾的
`APT_MIRROR` / `PIP_INDEX_URL` / `NPM_REGISTRY` 默认指向阿里云 / npmmirror 镜像；海外服务器可以清空，走官方源。

### 5. 启动

```bash
docker compose up -d
docker compose ps             # db、redis、web 显示 healthy，nginx 显示 running
docker compose logs -f web    # 看到 "Listening at: http://0.0.0.0:8000" 即就绪，Ctrl+C 退出查看
```

首次启动 MySQL 要初始化（约 1 分钟），web 会等它健康后再起；web 启动时会自动执行
`migrate` 和 `collectstatic`。若日志里出现 `WARNING: 无法使用评测沙箱镜像`，说明第 4 步没构建
sandbox，补跑 `docker compose --profile sandbox build sandbox` 即可（不用重启 web）。

### 6. 初始化数据

```bash
cd /srv/acm_oj/deploy

# 6.1（可选）导入本机数据库——要导就最先导，导入会整表覆盖（做法见「六、日常运维」）

# 6.2 管理员账号（/django-admin/ 与前端管理端）
docker compose exec web python manage.py createsuperuser

# 6.3 星语演示数据：15 道入门题、演示账号、画像与已审核任务（幂等，可重复执行）
docker compose exec web python manage.py seed_star --password '<自定义演示密码>'
```

`seed_star` 会用评测沙箱实跑每道题的参考解，所以它跑通也就验证了「web → docker.sock → 沙箱容器」整条链路。
生成的演示账号（密码都是 `--password` 指定的值）：

| 角色 | 用户名 | 说明 |
|------|--------|------|
| 教师 | `star_teacher` | 星语老师，创建了团队「星语示范班」 |
| 学生 | `star_hang` | 小航，启蒙层 |
| 学生 | `star_duo` | 朵朵，启蒙层 |
| 学生 | `star_jie` | 阿杰，入门层 |
| 学生 | `star_yu` | 小雨，入门层 |

可选：

```bash
# 提前用大模型生成演示任务草稿，录屏 / 答辩时不必现场等待（需 LLM_API_KEY；耗时几分钟，建议在 tmux 里跑）
docker compose exec web python manage.py star_pregen

# 平台其余内容（算法知识库、知识图谱、RAG 向量）。题库本身不在这里，需要的话导入本机数据库
docker compose exec web python manage.py seed_algorithms
docker compose exec web python manage.py seed_edges
docker compose exec web python manage.py build_graph
docker compose exec web python manage.py build_chunks
docker compose exec web python manage.py build_embeddings   # 需要 .env 里配置 EMBED_*
```

### 7. 验收清单

- [ ] `http://<公网IP>/` 打开首页，刷新任意子页面（如 `/star`）不出现 404
- [ ] `star_teacher` 登录教师端，对一名学生发起「大模型改造」，能在 3 分钟内返回草稿
- [ ] 学生账号做一道入门层排序题，提交后能判对错（走评测沙箱）
- [ ] 题库里任选一题提交 C++ / Java / Python 代码，状态从 Pending 变为 AC / WA
- [ ] 算法详情页的 AI 问答逐字流式输出，而不是等很久后一次性出现
- [ ] `http://<公网IP>/django-admin/` 登录后台，页面样式正常（静态文件由 nginx 提供）
- [ ] `docker compose exec web python manage.py check --deploy` 只剩下文「四」列出的预期警告

---

## 二、更新代码后重新部署

```bash
cd /srv/acm_oj && git pull                  # 或重新上传、解压 tar 包覆盖
cd deploy
docker compose build                        # 改了 Dockerfile.sandbox 时加 --profile sandbox
docker compose up -d                        # 只重建有变化的容器；web 启动时自动 migrate + collectstatic
docker compose logs -f web
docker image prune -f                       # 清理旧镜像层，防止磁盘越积越多
```

- **只改了 nginx 配置**（`deploy/nginx/*`）：`docker compose restart nginx`，不必重建。
- **改了 `deploy/.env`**：用 `docker compose up -d`（会重建受影响的容器）。`docker compose restart`
  **不会**重新读取 `.env`。
- **更新了星语题目素材 / 演示数据**：再跑一次 `seed_star --password '<同一个密码>'`（幂等；
  加 `--reset-tasks` 会删掉演示学生的任务与作答记录后重建）。
- **发版时机**：web 重建时进行中的请求会被中断（最多等 60 秒收尾）；排队中、评测中的提交会在新进程启动后
  自动重新评测。尽量避开演示 / 比赛进行时。

---

## 三、关键设计与取舍

### 3.1 评测沙箱：挂载 docker.sock，而不是在宿主机直接跑 web

评测沙箱（`judge/services/sandbox.py`）对每次编译、运行都执行一次 `docker run`。web 无论放在哪里，
都必须能指挥 Docker 守护进程。评估过两种方案：

| | A. web 在容器里，挂载 `/var/run/docker.sock`（**采用**） | B. web 直接跑在宿主机（systemd + venv） |
|---|---|---|
| web 被攻破的后果 | 经 docker.sock 起特权容器 → 宿主机 root | web 用户在 docker 组 → 同样等价宿主机 root |
| web 进程身份 | 必须是 root（见下），但只是**容器内** root | 必须是 root，而且是**宿主机** root |
| 部署 / 一致性 | 一条 `docker compose up`，Python 版本与依赖固定在镜像里 | 宿主机装 Python 3.11、编译 mysqlclient、写 systemd，环境容易漂移 |
| 额外注意 | 评测临时目录要在宿主机与容器里同路径挂载 | 无 |

**为什么 web 必须以 root 运行**：沙箱的编译容器以 root 身份、在 `--cap-drop=ALL` 下运行，
没有 `CAP_DAC_OVERRIDE`，它只能写入**属主是 root** 的目录；而评测临时目录由 web 进程用
`tempfile.mkdtemp()` 创建（权限 0700，属主就是 web 进程的用户）。web 若以普通用户运行，所有编译都会因
Permission denied 失败。方案 B 因此只能让 gunicorn 以宿主机 root 运行——比 A 的「容器内 root」更糟。

结论：两种方案的特权本质相同（能控制 Docker 就等于 root），A 不会更不安全，却更简单、更可复现，所以选 A。

**不受这个选择影响的部分**：学生代码的隔离边界是沙箱容器本身——`--network=none`、`--cap-drop=ALL`、
`no-new-privileges`、只读根文件系统、`nobody` 用户、内存 / CPU / 进程数上限。面对不可信代码，防线在这里。

**剩余风险与缓解**：Django 或 gunicorn 若出现远程代码执行漏洞，攻击者经 docker.sock 可拿到宿主机 root。
本编排的缓解措施：

- 只有 nginx 发布端口，web / MySQL / Redis 均不对外；
- `DEBUG=False`、`USE_DOCKER_SANDBOX=True` 由编排强制，避免误配成「在 web 容器里直接执行学生代码」；
- 密钥与数据库密码随机生成；MySQL root 密码不注入 web 容器；
- 安全组只放行 22 / 80 / 443；定期 `docker compose build --pull` 更新基础镜像。

**进一步加固（本次未做）**：rootless Docker（容器内 root 不再等于宿主机 root，但 `--memory` / `--cpus`
需要 cgroup v2 委派）；评测机与 web 拆到两台机器；把沙箱编译阶段改为 `--user <web 进程 uid>`，
web 就能以非 root 运行（需改 `judge/services/sandbox.py`）。docker socket 代理作用有限——
只要允许创建带 bind mount 的容器，就仍等价 root。

**同路径挂载 `TMPDIR`**：评测、自定义运行、星语排序题的临时目录都来自 `tempfile.mkdtemp()`，即 `$TMPDIR`
（`settings.JUDGE_TEMP_DIR` 实际没被使用）。沙箱容器由宿主机 Docker 创建，`-v <临时目录>:/sandbox`
按**宿主机路径**解析，所以编排把宿主机的 `/var/lib/acm-oj/judge_tmp` 以**同一路径**挂进 web 容器，
并设 `TMPDIR` 指向它。要换位置就在 `.env` 里设 `JUDGE_TMP_DIR`（两侧会一起变）。

### 3.2 gunicorn：worker 模型、超时与评测并发

**gthread（多进程 × 每进程多线程）**。本项目有三类长请求：星语教师端「大模型改造」是同步请求
（生成 → 校验 → 修复最多 3 轮，前端等 180 秒）；AI 问答 `/api/ai/ask/` 是 SSE 流；自定义运行 /
星语排序题在请求线程里等沙箱跑完。sync worker 一个长请求就占死一个进程，gthread 只占一个线程。

**超时**：`timeout=300`（≥ 180）。gthread 下它是 worker 心跳超时，不限制单个请求时长（主循环每秒心跳），
所以 3 分钟的大模型请求不会被杀；万一换回 sync worker，这个值就成了请求时长上限，同样盖得住。
`graceful_timeout=60` 是重启时给在途请求的收尾时间，编排里 web 的 `stop_grace_period: 75s` 比它大。

**进程数与评测并发**：评测线程池、自定义运行名额、AI 反馈池都是**每个 gunicorn 进程各一份**
（见 `judge/services/judge_queue.py` 顶部注释）：

| 指标 | 公式 |
|------|------|
| 评测总并发 | `GUNICORN_WORKERS × JUDGE_WORKERS` |
| 自定义运行 / 星语排序题总并发 | `GUNICORN_WORKERS × JUDGE_RUN_WORKERS`（0 表示取 `JUDGE_WORKERS` 的一半，至少 1） |
| AI 反馈总并发 | `GUNICORN_WORKERS × AI_FEEDBACK_WORKERS` |
| 同时处理的请求 | `GUNICORN_WORKERS × GUNICORN_THREADS` |

每个评测容器约占 1 核（`--cpus=1`），评测总并发按 CPU 核数配：

| ECS 规格 | `GUNICORN_WORKERS` | `GUNICORN_THREADS` | `JUDGE_WORKERS` | 评测总并发 | 自定义运行总并发 |
|----------|---:|---:|---:|---:|---:|
| 2 vCPU 4 GiB（默认） | 2 | 8 | 1 | 2 | 2 |
| 4 vCPU 8 GiB | 2 | 8 | 2 | 4 | 2 |
| 8 vCPU 16 GiB | 4 | 8 | 2 | 8 | 4 |

刻意不开的选项：`max_requests`（评测队列只在进程内存里，定期回收 worker 会丢掉排队中的评测）、
`preload_app`（线程池与数据库连接必须在 fork 之后创建）。

**重启后恢复评测**：`judge/apps.py` 的 `ready()` 只认 argv 里恰好等于 `gunicorn` 的参数，而 gunicorn 的
argv[0] 是完整路径，所以在 gunicorn 下它不会触发恢复。`gunicorn.conf.py` 用两个钩子补上：
master 启动时（`when_ready`）放一个令牌文件，第一个初始化完的 worker（`post_worker_init`）删掉它并调用
`recover_pending()`——保证每次启动只在一个 worker 里执行（每个 worker 都执行会重复评测，
AC 数和 Rating 被加两次）。

### 3.3 nginx

- `/` 托管前端，`try_files $uri $uri/ /index.html` 回退给 Vue Router；`index.html` 不缓存、
  `/assets/*`（文件名带哈希）缓存一年。
- `/api/`、`/django-admin/` 反代到 web；`/static/` 直接读 `collectstatic` 的共享卷。
- `proxy_read_timeout 300s`：大于前端给「大模型改造」的 180 秒，超时由浏览器一侧先发生。
- `/api/ai/ask/` 单独一个 location：`proxy_buffering off`、`gzip off`，SSE 逐字推送
  （Django 也带了 `X-Accel-Buffering: no`，双保险）。
- `X-Forwarded-For` **覆盖**为 `$remote_addr`，不用追加模式：DRF 限流按这个头识别客户端，追加模式下
  客户端自带一个伪造的头就能每次换身份，绕过登录 / 提交 / AI 接口的限流。若以后在 nginx 前面再加
  SLB / CDN，需要改用 nginx 的 `real_ip` 模块取真实 IP，否则所有人会共用同一个限流额度。
- 上游地址通过 Docker 内置 DNS 动态解析：web 容器重建换了 IP，nginx 无需重启。

### 3.4 MySQL 空闲连接超时

评测线程池的线程常驻进程，各自长期持有一条数据库连接，评测前后不回收
（`judge_queue._judge_task` 没有调用 `close_old_connections()`）。MySQL 默认 8 小时断开空闲连接，
之后这些线程每次评测都会报 `MySQL server has gone away`，提交一直停在 Pending——演示机放一晚上就会中招。
编排把 `wait_timeout` 放宽到最大值（一年）规避；连接数有上限（约「进程数 ×（线程池 + 请求线程）」，
远低于 `max_connections=151`）。同理，db 容器重启后这些旧连接全部失效，需要随手
`docker compose restart web`。代码层面的根治是在 `_judge_task` 首尾调用 `close_old_connections()`。

---

## 四、`manage.py check --deploy` 的警告

在容器里执行：`docker compose exec web python manage.py check --deploy`。

| 警告 | HTTP 演示（默认） | `USE_HTTPS=True` 后 |
|------|------------------|---------------------|
| W004 `SECURE_HSTS_SECONDS` 未设置 | **预期存在**：HSTS 只能在 HTTPS 下启用 | 已处理：默认 3600 秒，可用 `SECURE_HSTS_SECONDS` 调整 |
| W008 `SECURE_SSL_REDIRECT` 不是 True | **预期存在**：没有 HTTPS 可跳转 | 已处理（nginx 的 80 端口也会 301 跳转） |
| W012 `SESSION_COOKIE_SECURE` 不是 True | **预期存在**：HTTP 下设为 True 会导致 Django 后台无法登录。接口用 JWT（`Authorization` 头），会话 cookie 只用于 `/django-admin/` | 已处理 |
| W016 `CSRF_COOKIE_SECURE` 不是 True | **预期存在**：同上 | 已处理 |
| W005 `SECURE_HSTS_INCLUDE_SUBDOMAINS` | — | **有意不开**：会强制该域名下所有子域名都只能走 HTTPS |
| W021 `SECURE_HSTS_PRELOAD` | — | **有意不开**：提交浏览器预加载列表后几乎无法撤回 |

其余部署检查均已通过：`DEBUG=False`（编排强制）、`SECRET_KEY` 为 64 位随机串、`ALLOWED_HOSTS` 已设置；
`SecurityMiddleware`、`X-Frame-Options`、`nosniff`、`Referrer-Policy`、COOP 使用 Django 4.2 的安全默认值。
（以上结论来自在本机用生产环境变量运行 `check --deploy` 的结果。）

---

## 五、启用 HTTPS（可选）

1. 域名解析到服务器公网 IP（内地服务器需已备案）。
2. 申请证书（阿里云免费证书或 Let's Encrypt），下载 Nginx 格式，放到：
   `deploy/nginx/certs/fullchain.pem`、`deploy/nginx/certs/privkey.pem`（该目录已被 git 忽略）。
3. 修改 `deploy/.env`：

   ```ini
   NGINX_SITE_CONF=site-https.conf
   USE_HTTPS=True
   ALLOWED_HOSTS=oj.example.com
   CORS_ORIGINS=https://oj.example.com
   ```

4. 安全组放行 443，`docker compose up -d`。
5. `check --deploy` 应只剩 W005 / W021。

---

## 六、日常运维

```bash
cd /srv/acm_oj/deploy
docker compose ps                         # 状态
docker compose logs -f --tail=200 web     # Django / gunicorn 日志（500 错误的堆栈也在这里）
docker compose logs -f --tail=200 nginx   # 访问日志，rt= 是请求耗时
docker compose restart web                # 重启后端（不重新读 .env）
docker compose exec web python manage.py shell
docker compose exec web python manage.py changepassword star_teacher
```

**备份数据库**：

```bash
docker compose exec -T db sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --default-character-set=utf8mb4 acm_oj' > /srv/acm_oj-$(date +%F).sql
```

**导入本机数据库**（题库、算法知识库、向量等都在里面）。在本机 PowerShell 导出——务必用
`--result-file`，PowerShell 5 的 `>` 会写成 UTF-16，导入时报错：

```powershell
mysqldump -u root -p --single-transaction --default-character-set=utf8mb4 --set-gtid-purged=OFF --result-file=acm_oj.sql acm_oj
scp acm_oj.sql root@<公网IP>:/srv/
```

服务器上导入（整表覆盖），再重启 web 补跑迁移：

```bash
cd /srv/acm_oj/deploy
docker compose exec -T db sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 acm_oj' < /srv/acm_oj.sql
docker compose restart web
```

导入后本机的账号会一并上线：公网环境请改掉弱密码，再执行 6.2 / 6.3。

**星语消融实验的输出**写在容器里，跑完拷出来：
`docker compose cp web:/app/star_eval_results ./star_eval_results`。

**彻底重来**（删除数据库数据，不可恢复）：`docker compose down -v`。

---

## 七、常见问题

| 现象 | 原因与处理 |
|------|-----------|
| 页面能开，接口全部 400 Bad Request | `ALLOWED_HOSTS` 没包含访问时用的 IP / 域名；改 `.env` 后 `docker compose up -d` |
| 502 Bad Gateway | web 还没就绪或崩溃了：`docker compose logs web` |
| web 日志反复出现数据库连接失败 | 改过 `.env` 里的数据库密码（只在首次初始化生效，见第 3 步） |
| 所有提交都是 CE，信息里有 `Unable to find image` | 沙箱镜像没构建：`docker compose --profile sandbox build sandbox` |
| 所有提交都是 CE，信息里有 `Permission denied` | web 没以 root 运行，或宿主机 SELinux 处于 Enforcing（`getenforce` 查看） |
| 提交一直停在 Pending | `docker compose logs web` 看评测线程的异常；数据库连接问题见「3.4」 |
| 重启过 db（或 MySQL 崩溃重启）后评测全部卡住 | 评测线程手里的旧连接都断了且不会自动重连，`docker compose restart web` 即可（原因见「3.4」） |
| 构建时拉镜像超时 | 配置 Docker Hub 加速（第 1 步）|
| 构建前端时被 Killed（内存不足） | 加 swap：`fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile`，并把 `/swapfile none swap sw 0 0` 写入 `/etc/fstab` |
| 「大模型改造」超时 | 先看 `LLM_API_KEY` 是否填写、服务器能否访问 `api.deepseek.com`；nginx 等 300 秒、前端等 180 秒 |
| Django 后台登录提示 CSRF 校验失败 | 在 nginx 前面又套了反代 / CDN 时，把站点地址填进 `CSRF_TRUSTED_ORIGINS` |
| 多人同时登录被限流（429） | 同一出口 IP 共享额度，调大 `THROTTLE_LOGIN` 后 `docker compose up -d` |
| 改了 `.env` 没生效 | 要用 `docker compose up -d`，`restart` 不会重新读取 `.env` |
