# Migration: execution_command_learnings

Run this migration when the database is inside a Docker container.

## Dev (docker-compose -f docker-compose.dev.yml -p bot-dev)

From the **project root** (where `docker-compose.dev.yml` lives):

```bash
# Copy SQL into the Postgres container, then run it
docker cp backend/sql/create_execution_command_learnings.sql bot-dev-postgres:/tmp/create_execution_command_learnings.sql
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -f /tmp/create_execution_command_learnings.sql
```

## Production (adjust container and database name)

Replace `bot-prod-postgres` and `troubleshooting_ai` with your prod Postgres container and DB name:

```bash
docker cp backend/sql/create_execution_command_learnings.sql bot-prod-postgres:/tmp/create_execution_command_learnings.sql
docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -f /tmp/create_execution_command_learnings.sql
```

## Verify

```bash
# Dev
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "\d execution_command_learnings"

# Prod
docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "\d execution_command_learnings"
```
