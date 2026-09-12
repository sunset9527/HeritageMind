# 生产部署交接（等待域名与服务器）

本目录是可部署模板，不代表 HeritageMind 已上线、域名已解析或 HTTPS 证书已签发。

购买服务器与域名后：

1. 将域名 A/AAAA 记录指向服务器公网 IP；
2. 在服务器复制 `.env.example` 为 `.env`，填入强随机 `JWT_SECRET_KEY`、数据库密码和模型密钥；
3. 将 `DOMAIN` 与 `CERT_PATH` 替换进 `nginx/heritagemind.conf.template`；
4. 先以 HTTP 方式启动并用 Certbot 对真实域名申请证书；
5. 写入证书路径后启用 HTTPS 模板，运行 `nginx -t`，再 reload；
6. 验证 `/health`、`/api/health`、SSE 问答、上传和证书自动续期；保留上一个配置以便回滚。

不要将 `.env`、私钥或真实证书提交到 Git。
