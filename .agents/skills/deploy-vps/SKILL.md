---
name: deploy-vps
description: Push the current branch to GitHub, sync the repo on the Baltiyskiy Bereg VPS, verify .env/data/docker prerequisites, and start or restart the target service with checks.
---

## When to use
- User wants to deploy current work to the VPS
- Need to sync the server checkout with the current git branch
- Need to start or restart docker services on VPS

## VPS details
- Host: `111.88.159.116`
- User: `theimage01`
- SSH key: `~/.ssh/baltiyskiy_bereg_new`
- Project path on VPS: `/home/theimage01/baltiyskiy-bereg`

## Preconditions
- Working tree is in a deployable state
- Branch name is known
- If there are uncommitted changes, ask whether to commit first
- For this repo, default target is the Docker stack from `docker-compose.yml`

## Current repo deployment assumptions
- Main deployable unit in this repo is `docker compose`
- `docker-compose.yml` expects `./data/cleaned.bak`
- `.env` must exist on VPS and contain at least `MSSQL_SA_PASSWORD`
- `restore-db.sh` restores database from `/var/opt/mssql/backup/cleaned.bak` on first run

## Steps

### 1. Push branch to GitHub
```bash
git push -u origin <branch>
```

### 2. Connect to VPS
```bash
ssh -i ~/.ssh/baltiyskiy_bereg_new theimage01@111.88.159.116
```

### 3. Sync repository on VPS
```bash
cd /home/theimage01/baltiyskiy-bereg
git status
git fetch origin
git checkout <branch>
git pull --ff-only origin <branch>
```

If VPS checkout has unexpected local changes, stop and ask user before overriding anything.

### 4. Verify deployment prerequisites on VPS

Check required files before starting anything:

```bash
test -f .env && echo ".env exists"
test -f data/cleaned.bak && echo "backup exists"
test -f docker-compose.yml && echo "compose exists"
test -f restore-db.sh && echo "restore script exists"
```

Validate critical env variable:

```bash
grep '^MSSQL_SA_PASSWORD=' .env
```

Optional sanity check for compose interpolation:

```bash
docker compose config > /tmp/baltbereg-compose-check.yaml
```

If any of these checks fail, stop and report the exact missing prerequisite.

### 5. Start the right service

#### Default — Docker stack
```bash
docker compose up -d
docker compose ps
```

Only use custom non-docker start commands if the repo actually contains such services and the user explicitly asks for them.

## Verification

After start, verify all relevant checks:
- `docker compose ps`
- `docker logs mssql-baltbereg --tail=50`
- `docker inspect --format='{{.State.Health.Status}}' mssql-baltbereg`

Optional DB readiness check:

```bash
docker exec mssql-baltbereg /opt/mssql-tools/bin/sqlcmd \
  -S localhost -U SA -P "$MSSQL_SA_PASSWORD" \
  -Q "SELECT TOP 1 name FROM sys.databases"
```

## Output
- Branch deployed on VPS
- Prerequisite check results reported
- Service status reported
- Any follow-up action clearly listed

## Safety rules
- Prefer `git pull --ff-only` over reset/rebase
- Do not delete server files unless user explicitly asks
- Do not overwrite `.env` silently
- Do not assume `data/cleaned.bak` can be recreated automatically
- If service fails to start, capture logs and report exact error
