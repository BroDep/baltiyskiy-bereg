# Deploy Solution to VPS

## Purpose
Deploy code changes from a feature branch to the VPS via CI/CD pipeline and verify the deployment worked correctly.

## When to Use
- After completing a feature or fix and wanting to deploy it to production
- When testing CI/CD pipeline
- When needing to verify deployment on VPS

## Input
- `[branch_name]`: Feature branch name to deploy (e.g., `feature/my-feature`)
- `[pr_title]`: Title for the pull request
- `[pr_description]`: Description of changes

## Output
- Pull request created and merged to dev
- CI/CD pipeline triggered and completed
- Containers on VPS rebuilt and restarted
- Verification that services are running

## Steps

### 1. Prepare Changes
```bash
# Make sure you're on dev and it has latest
git checkout dev
git pull origin dev

# Create feature branch from dev
git checkout -b feature/[feature-name]
```

### 2. Commit and Push
```bash
# Add changes
git add .

# Commit with clear message
git commit -m "feat: describe your changes"

# Push branch
git push -u origin feature/[feature-name]
```

### 3. Create and Merge Pull Request
```bash
# Create PR to dev
gh pr create --base dev --head feature/[feature-name] \
  --title "[title]" --body "[description]"

# Merge PR (or do it via web UI)
gh pr merge [pr-number] --merge --delete-branch
```

### 4. Wait for CI/CD
```bash
# Wait for CI to complete (~30-60s)
sleep 30

# Check workflow status
gh run list --branch dev --limit 3

# Get detailed status
gh run view [run-id]
```

### 5. Verify Deployment on VPS
```bash
# SSH to VPS
ssh -i ~/.ssh/baltiyskiy_bereg_new theimage01@111.88.159.116

# Check running containers
docker ps

# Check container status
docker compose -f /home/theimage01/baltiyskiy-bereg/docker-compose.yml ps

# Check logs for errors
docker compose logs --tail=20

# Test API health endpoint
curl http://localhost:8000/health
```

### 6. Ensure Git is Initialized on VPS (if first time)
```bash
# If git not initialized on server:
cd /home/theimage01/baltiyskiy-bereg
git init
git remote add origin https://github.com/BroDep/baltiyskiy-bereg.git
git fetch origin
git checkout -f origin/dev
```

## Examples

### Example 1: Deploying a Simple API Server
**Input:**
- Branch: `feature/simple-api-server`
- PR Title: "Add simple FastAPI server for CI/CD testing"

**Steps:**
1. Create branch and add Dockerfile + docker-compose.yml
2. Push and create PR
3. Merge PR
4. Wait for CD workflow to complete (~2 min)
5. Verify containers: `docker ps` shows api running
6. Test: `curl http://localhost:8000/health` returns `{"status":"healthy"}`

## Best Practices
- Always create PR from feature branch to dev (never push directly to dev)
- Wait for CI/CD to complete before verifying
- Check both container status AND logs for errors
- Test the health endpoint to verify the app is actually working

## Common Pitfalls
- **Git not initialized on VPS** → CI/CD fails because `git fetch` doesn't work → Initialize git manually on server first time
- **Old container still running** → Check for orphan containers → Remove with `docker rm -f [container-name]`
- **Docker build fails** → Check logs for Python/dependency errors → May need to fix Dockerfile or requirements
- **Health check passes but app broken** → Check application logs, not just container status

## Self-Improvement Notes
- [2026-04-17] Created: Initial version based on CI/CD testing
- [2026-04-17] Added VPS git initialization step after first deployment failed