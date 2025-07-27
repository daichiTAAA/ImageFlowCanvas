```bash
# 開発用
docker compose -f deploy/compose/docker-compose.yml -f deploy/compose/docker-compose.dev.yml down web
docker compose -f deploy/compose/docker-compose.yml -f deploy/compose/docker-compose.dev.yml build --no-cache web
docker compose -f deploy/compose/docker-compose.yml -f deploy/compose/docker-compose.dev.yml up -d web
```