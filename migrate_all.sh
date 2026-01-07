#!/bin/bash

# Database Migration Script
# Usage: ./migrate_all.sh [dev|prod]

ENV=${1:-dev}

if [ "$ENV" = "prod" ]; then
    DB_NAME="troubleshooting_ai"
    COMPOSE_FILE="docker-compose.production.yml"
    PROJECT_NAME=""
    echo "Running migrations for PRODUCTION environment..."
else
    DB_NAME="troubleshooting_ai_dev"
    COMPOSE_FILE="docker-compose.dev.yml"
    PROJECT_NAME="bot-dev"
    echo "Running migrations for DEV environment..."
fi

echo "=========================================="
echo "Database: $DB_NAME"
echo "Compose File: $COMPOSE_FILE"
echo "=========================================="
echo ""

# Phase 1: User Security
echo "Phase 1: User Security Features..."
cat backend/sql/add_password_reset_fields.sql | docker-compose -f $COMPOSE_FILE $([ -n "$PROJECT_NAME" ] && echo "-p $PROJECT_NAME") exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/add_password_history.sql | docker-compose -f $COMPOSE_FILE $([ -n "$PROJECT_NAME" ] && echo "-p $PROJECT_NAME") exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/add_account_lockout_fields.sql | docker-compose -f $COMPOSE_FILE $([ -n "$PROJECT_NAME" ] && echo "-p $PROJECT_NAME") exec -T postgres psql -U postgres -d $DB_NAME
echo "✓ Phase 1 complete"
echo ""

# Phase 2: Change Management
echo "Phase 2: Change Management..."
cat backend/sql/create_change_tickets_table.sql | docker-compose -f $COMPOSE_FILE $([ -n "$PROJECT_NAME" ] && echo "-p $PROJECT_NAME") exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/add_ticket_suppression_fields.sql | docker-compose -f $COMPOSE_FILE $([ -n "$PROJECT_NAME" ] && echo "-p $PROJECT_NAME") exec -T postgres psql -U postgres -d $DB_NAME
echo "✓ Phase 2 complete"
echo ""

# Phase 3: Self-Healing
echo "Phase 3: Self-Healing..."
cat backend/sql/add_parent_session_id_to_execution_sessions.sql | docker-compose -f $COMPOSE_FILE $([ -n "$PROJECT_NAME" ] && echo "-p $PROJECT_NAME") exec -T postgres psql -U postgres -d $DB_NAME
echo "✓ Phase 3 complete"
echo ""

# Phase 4: User Enhancements
echo "Phase 4: User Enhancements..."
cat backend/sql/add_user_profile_fields.sql | docker-compose -f $COMPOSE_FILE $([ -n "$PROJECT_NAME" ] && echo "-p $PROJECT_NAME") exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/add_user_preferences.sql | docker-compose -f $COMPOSE_FILE $([ -n "$PROJECT_NAME" ] && echo "-p $PROJECT_NAME") exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/create_user_login_history.sql | docker-compose -f $COMPOSE_FILE $([ -n "$PROJECT_NAME" ] && echo "-p $PROJECT_NAME") exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/create_user_activity_log.sql | docker-compose -f $COMPOSE_FILE $([ -n "$PROJECT_NAME" ] && echo "-p $PROJECT_NAME") exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/create_user_sessions.sql | docker-compose -f $COMPOSE_FILE $([ -n "$PROJECT_NAME" ] && echo "-p $PROJECT_NAME") exec -T postgres psql -U postgres -d $DB_NAME
echo "✓ Phase 4 complete"
echo ""

echo "=========================================="
echo "All migrations completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Restart backend service:"
if [ "$ENV" = "prod" ]; then
    echo "   docker-compose -f $COMPOSE_FILE restart backend"
else
    echo "   docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME restart backend"
fi
echo "2. Check backend logs to verify startup"
echo "3. Test key endpoints"

