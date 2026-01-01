#!/bin/bash
# Create Docker network for bot application

docker network create bot_app-network 2>/dev/null || echo "Network already exists or created"
