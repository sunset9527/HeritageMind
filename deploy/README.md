# 生产部署交接（等待域名与服务器）

本目录是可部署模板，不代表 HeritageMind 已上线、域名已解析或 HTTPS 证书已签发。

## 当前交接状态（2026-10-16）

阶段 0 功能基线为 `6e6b156`，尚未部署到 ECS。线上实例不得视为当前主分支的生产验收结果。本阶段不在服务器配置 `cron`；图谱扫描只由管理员在后台按需触发。

完成阶段 0～6 和最终上线验收前，只能把本目录视为部署模板。后续需要冻结待发布提交与数据版本、创建管理员账号、验收管理后台和可选联网工具；域名具备后再完成 HTTPS 与正式 SEO canonical 配置。

购买服务器与域名后：

1. 将域名 A/AAAA 记录指向服务器公网 IP；
2. 在服务器复制 `.env.example` 为 `.env`，填入强随机 `JWT_SECRET_KEY`、数据库密码和模型密钥；
3. 将 `DOMAIN` 与 `CERT_PATH` 替换进 `nginx/heritagemind.conf.template`；
4. 先以 HTTP 方式启动并用 Certbot 对真实域名申请证书；
5. 写入证书路径后启用 HTTPS 模板，运行 `nginx -t`，再 reload；
6. 验证 `/health`、`/api/health`、SSE 问答、上传和证书自动续期；保留上一个配置以便回滚。

不要将 `.env`、私钥或真实证书提交到 Git。

## 数据迁移与独立 worker

每次发布先迁移数据库，再启动 API 与 worker：

```bash
docker compose -f docker-compose.production.yml run --rm api python -m alembic upgrade head
docker compose -f docker-compose.production.yml up -d api worker nginx
```

Windows 本地开发需另开一个 PowerShell 窗口运行消费者（API 不再内嵌消费者）：

```powershell
python -m src.workers.upload_worker
```

用 `/health` 检查 API；用 `docker compose ps` 和 `docker compose logs worker` 检查 worker。后台记录进入 `failed` 时，先查看 `error_code/error_message`，修复依赖或文件问题后再通过管理员重试接口入队，禁止直接改库凑状态。

发布失败时执行 rollback：停止新容器、恢复上一镜像与上一份活动索引清单；只有确认 007 迁移前媒体表来源后才执行 `python -m alembic downgrade 006`。上传卷先备份再回滚，禁止删除共享卷。

## 管理员初始化（首次部署后执行一次）

系统不会预置管理员账号，也不会把用户名或密码写进仓库。部署完成后，在服务器项目目录执行下列命令；将三个示例值替换成你自己的值，密码至少 12 位。

```bash
cd /opt/heritagemind
docker compose --profile production exec -T \
  -e HM_ADMIN_USERNAME=operator \
  -e HM_ADMIN_EMAIL=operator@example.com \
  -e HM_ADMIN_PASSWORD='替换为强密码' \
  api python -m src.bootstrap_admin
```

输出 `Administrator created` 后，即可使用该账号登录，进入 `/admin`。重复执行只会核验/提升同名同邮箱账号，不会创建重复管理员。

## 图谱增量扫描

当前按人工审核优先设计，**不会在阿里云 ECS 安装 cron，也不会自动定时扫描**。管理员在 `/admin` 的“图谱候选”页点击“立即扫描已发布百科”即可：系统仅从已发布百科提取候选事实，重复扫描不会重复创建；候选仍须逐条“审核合并”或“拒绝”。

## 静态预渲染与 SEO

前端发布构建使用 `npm run build:ssg`。它生成公开百科与传承人详情的静态 HTML，并写入标题、描述和 canonical 标签。域名尚未购买时不应设置 canonical 域名；域名解析完成后，在构建环境设置 `VITE_SITE_URL=https://你的真实域名` 后重新构建和部署。
