# 加 HTTPS 的最短清单（Certbot 一把过）

前置条件：
- 已完成 `docs/deploy-shortlist-from-zero.md`，HTTP 可访问；
- 域名 DNS 已解析到服务器公网 IP；
- 80/443 端口已放行。

## 1) 安装 Certbot

```bash
apt update
apt install -y certbot python3-certbot-nginx
```

## 2) 确认 Nginx 站点配置可被识别

> 保持一个 `server_name your-domain.com;` 的 HTTP 站点（80端口）即可。

```bash
nginx -t && systemctl reload nginx
```

## 3) 申请并自动配置证书

```bash
certbot --nginx -d your-domain.com
```

执行过程中建议选择：
- 同意自动跳转 HTTP -> HTTPS（redirect）

## 4) 验证证书与自动续期

```bash
certbot certificates
systemctl status certbot.timer
certbot renew --dry-run
```

## 5) 验证线上访问

```bash
curl -I https://your-domain.com/api/v1/tm/health
```

若返回 `200`（或网关定义的正常状态码）即完成。

## 6) 建议的 HTTPS Nginx 收敛（可选但推荐）
- 仅允许 TLS1.2/1.3；
- 保留安全响应头（`X-Frame-Options`、`X-Content-Type-Options` 等）；
- 对 `/api/v1/tm-core/*`、`/api/v1/tm-connector/*` 做内网/IP 白名单限制；
- 如有前端静态站点，统一强制 HTTPS 与缓存策略。

## 7) 常见失败排查
- 证书申请失败（超时/连接失败）：
  - 检查 DNS 是否生效到正确 IP；
  - 检查安全组/防火墙是否放行 80/443；
  - 检查 Nginx 是否已占用并正常响应 80。
- `certbot --nginx` 找不到可用 server block：
  - 确保 Nginx 配置中存在正确 `server_name`；
  - `nginx -t` 无报错后重试。
