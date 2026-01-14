#!/bin/bash
# Script to check or reset user password
# Usage: ./check_user.sh <email> [new_password]

if [ -z "$1" ]; then
    echo "Usage: $0 <email> [new_password]"
    exit 1
fi

EMAIL="$1"
NEW_PASSWORD="${2:-}"

if [ -z "$NEW_PASSWORD" ]; then
    # Just check user status
    docker exec bot-dev-backend python /app/check_user.py "$EMAIL"
else
    # Reset password
    docker exec bot-dev-backend python /app/check_user.py "$EMAIL" "$NEW_PASSWORD"
fi

