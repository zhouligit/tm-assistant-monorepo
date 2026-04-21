# SQL 初始化说明

为避免不同 MySQL 镜像版本下 `SOURCE` 路径行为差异，当前采用更稳妥的方式：

1. 启动容器后，手动执行 migration 与 seed
2. 使用仓库内 SQL 文件（推荐）

执行示例：

```bash
mysql -h 127.0.0.1 -P 3306 -u tm_app -p123456 tm_assistant < "/opt/tm-assistant-monorepo/sql/init/企业知识助手-mysql-migration-v1.1.sql"
mysql -h 127.0.0.1 -P 3306 -u tm_app -p123456 tm_assistant < "/opt/tm-assistant-monorepo/sql/init/企业知识助手-mysql-seed-v1.1.sql"
```
