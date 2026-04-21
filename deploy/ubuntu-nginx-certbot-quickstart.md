# Ubuntu 24.04 Nginx + Certbot 快速部署清单

适用前提：
- 服务器：Ubuntu 24.04
- 部署用户：`root`
- 项目路径：`/opt/tm-assistant-monorepo`
- 目标：同域名下通过 `path` 代理多个服务，并启用 HTTPS

---

## 0) 准备变量（先替换）

```bash
export DOMAIN="your-domain.com"
export EMAIL="you@example.com"
export PROJECT_DIR="/opt/tm-assistant-monorepo"
```

---

## 1) 安装 Nginx 与 Certbot

```bash
apt update
apt install -y nginx certbot python3-certbot-nginx
```

检查版本：

```bash
nginx -v
certbot --version
```

---

## 2) 放置 Nginx 配置模板

将仓库中的 HTTPS 模板复制到 Nginx 目录：

```bash
cp "${PROJECT_DIR}/deploy/nginx/tm-assistant.https.conf.example" "/etc/nginx/sites-available/tm-assistant.conf"
```

替换域名：

```bash
sed -i "s/your-domain.com/${DOMAIN}/g" "/etc/nginx/sites-available/tm-assistant.conf"
```

如果前端静态目录不是 `/opt/tm-assistant-monorepo/console-web-dist`，请手动编辑：

```bash
nano /etc/nginx/sites-available/tm-assistant.conf
```

---

## 3) 启用站点并测试配置

```bash
ln -sf "/etc/nginx/sites-available/tm-assistant.conf" "/etc/nginx/sites-enabled/tm-assistant.conf"
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
systemctl enable nginx
```

---

## 4) 申请 HTTPS 证书（Let's Encrypt）

> 确保 `80/443` 对公网开放，且域名 A 记录已指向当前服务器。

```bash
certbot --nginx -d "${DOMAIN}" -m "${EMAIL}" --agree-tos --no-eff-email --redirect
```

证书自动续期测试：

```bash
certbot renew --dry-run
```

---

## 5) 运行后端服务（示意）

确保以下服务已启动并监听本机端口：
- `127.0.0.1:18000`（api-gateway）
- `127.0.0.1:18001`（assistant-core）
- `127.0.0.1:18002`（connector-service）

可用性检查：

```bash
ss -lntp | rg "18000|18001|18002"
```

---

## 6) 验证访问

公网验证：

```bash
curl -I "https://${DOMAIN}/"
curl -s "https://${DOMAIN}/api/v1/tm/health"
```

如果需要验证被保护路径（应返回 403，除非在白名单）：

```bash
curl -i "https://${DOMAIN}/api/v1/tm-core/health"
```

---

## 7) 常见问题排查

1. `nginx -t` 失败  
   - 检查配置文件语法、证书路径是否存在

2. `certbot` 失败  
   - 检查域名解析是否指向当前服务器
   - 检查防火墙是否放行 `80/443`

3. `/api/v1/tm/*` 502  
   - 检查 `18000` 服务是否存活
   - 查看日志：`journalctl -u nginx -n 200 --no-pager`

4. 内部路径无法访问  
   - `tm-core/tm-connector` 默认开启白名单限制，公网访问返回 403 属于预期

