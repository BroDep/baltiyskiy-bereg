---
name: docker
description: Manage Docker containers on the VPS - check status, logs, restart, etc.
---

## When to use
- Check if services are running
- View logs for debugging
- Restart containers
- Check container health

## Connect to VPS
```bash
ssh -i ~/.ssh/baltiyskiy_bereg_new theimage01@111.88.159.116
```

## Common commands

Check running containers:
```bash
docker ps
```

Check all containers (including stopped):
```bash
docker ps -a
```

View logs (last 50 lines):
```bash
docker logs mssql-baltbereg --tail=50
```

Follow logs in real-time:
```bash
docker logs -f mssql-baltbereg
```

Restart container:
```bash
docker restart mssql-baltbereg
```

Check container resource usage:
```bash
docker stats
```

## Available containers on this VPS

- **mssql-baltbereg** - MSSQL database
- **qdrant** - Vector database
- (check with docker ps for full list)

## Troubleshooting

If container not running:
1. Check logs: docker logs <container>
2. Restart: docker restart <container>
3. If still failing, check docker-compose.yml
