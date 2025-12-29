#!/bin/bash
# Consolidated Docker troubleshooting script
# Replaces multiple fix-*.sh scripts with a single unified tool
#
# ⚠️  IMPORTANT: This script PRESERVES all database volumes and data.
#     Only containers and images are removed. Volumes are NEVER deleted.

set -e

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"

show_help() {
    cat << EOF
Docker Troubleshooting Tool

Usage: $0 <command> [options]

Commands:
  containerconfig    Fix ContainerConfig KeyError (removes corrupted containers/images)
  timeout           Fix Docker timeout issues (restart daemon, increase timeout)
  port-conflict     Fix port conflicts (identify and stop conflicting processes)
  build-lease       Fix "lease does not exist" build errors (restart daemon)
  daemon-restart    Quick Docker daemon restart
  rebuild-backend   Rebuild backend container (fixes missing files in image)
  rebuild-all       Rebuild all containers from scratch
  check-state       Check Docker state (containers, images, volumes, networks)
  cleanup           Clean up unused containers/images (preserves volumes)

Options:
  --compose-file FILE    Use specific compose file (default: docker-compose.production.yml)
  --volumes             Include volumes in cleanup (DANGEROUS - not recommended)

Examples:
  $0 containerconfig
  $0 rebuild-backend
  $0 check-state
  $0 cleanup

EOF
}

fix_containerconfig() {
    echo "🔧 Fixing Docker Compose ContainerConfig error..."
    echo "✅ Database volumes and data will be PRESERVED (NOT deleted)."
    
    # Stop all containers
    echo "📦 Stopping all containers..."
    docker-compose -f "$COMPOSE_FILE" down || true
    docker stop $(docker ps -aq) 2>/dev/null || true
    
    # Remove problematic containers
    echo "🗑️  Removing old containers (volumes preserved)..."
    docker ps -aq | xargs -r docker rm -f || true
    
    # Remove problematic images
    echo "🗑️  Removing potentially corrupted images (volumes preserved)..."
    docker rmi bot_frontend bot_backend bot_worker 2>/dev/null || true
    
    # Clean up Docker system (EXCLUDING volumes)
    echo "🧹 Pruning Docker system (volumes EXCLUDED - data safe)..."
    docker system prune -f --volumes=false
    
    echo "✅ Cleanup complete. Rebuild containers with: $0 rebuild-all"
}

fix_timeout() {
    echo "🔧 Fixing Docker timeout issues..."
    
    # Restart Docker daemon
    echo "🔄 Restarting Docker daemon..."
    sudo systemctl restart docker || service docker restart || true
    sleep 5
    
    # Set higher timeout
    export COMPOSE_HTTP_TIMEOUT=300
    echo "⏱️  Set COMPOSE_HTTP_TIMEOUT=300"
    
    echo "✅ Docker daemon restarted. Try your command again with:"
    echo "   COMPOSE_HTTP_TIMEOUT=300 docker-compose -f $COMPOSE_FILE up -d"
}

fix_port_conflict() {
    PORT=${1:-5432}
    echo "🔧 Fixing port $PORT conflict..."
    
    # Find process using the port
    if command -v lsof >/dev/null 2>&1; then
        PID=$(lsof -ti:$PORT)
    elif command -v netstat >/dev/null 2>&1; then
        PID=$(netstat -tlnp | grep ":$PORT " | awk '{print $7}' | cut -d'/' -f1 | head -1)
    elif command -v ss >/dev/null 2>&1; then
        PID=$(ss -tlnp | grep ":$PORT " | awk '{print $6}' | cut -d',' -f2 | cut -d'=' -f2 | head -1)
    fi
    
    if [ -n "$PID" ]; then
        echo "⚠️  Found process $PID using port $PORT"
        read -p "Stop this process? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill -9 $PID 2>/dev/null || true
            echo "✅ Process stopped"
        fi
    else
        echo "✅ No process found using port $PORT"
    fi
}

fix_build_lease() {
    echo "🔧 Fixing Docker build 'lease does not exist' error..."
    
    # Restart Docker daemon
    echo "🔄 Restarting Docker daemon..."
    sudo systemctl restart docker || service docker restart || true
    sleep 5
    
    # Clean build cache
    echo "🧹 Cleaning build cache..."
    docker builder prune -f
    
    echo "✅ Docker daemon restarted and cache cleaned. Try building again."
}

daemon_restart() {
    echo "🔄 Restarting Docker daemon..."
    sudo systemctl restart docker || service docker restart || true
    sleep 5
    echo "✅ Docker daemon restarted"
}

rebuild_backend() {
    echo "🔨 Rebuilding backend container..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache backend
    docker-compose -f "$COMPOSE_FILE" up -d backend
    echo "✅ Backend rebuilt and started"
}

rebuild_all() {
    echo "🔨 Rebuilding all containers..."
    echo "⚠️  This will rebuild all services from scratch"
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    docker-compose -f "$COMPOSE_FILE" up -d
    echo "✅ All containers rebuilt and started"
}

check_state() {
    echo "📊 Docker State Check"
    echo "===================="
    echo ""
    echo "Containers:"
    docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "NAMES|bot_" || echo "No bot containers found"
    echo ""
    echo "Images:"
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -E "REPOSITORY|bot_" || echo "No bot images found"
    echo ""
    echo "Volumes:"
    docker volume ls | grep bot || echo "No bot volumes found"
    echo ""
    echo "Networks:"
    docker network ls | grep bot || echo "No bot networks found"
}

cleanup() {
    INCLUDE_VOLUMES=${1:-false}
    
    if [ "$INCLUDE_VOLUMES" = "true" ]; then
        echo "⚠️  WARNING: This will delete volumes and data!"
        read -p "Are you sure? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            echo "Cancelled"
            exit 1
        fi
        docker system prune -af --volumes
    else
        echo "🧹 Cleaning up unused containers/images (volumes preserved)..."
        docker system prune -af --volumes=false
    fi
    echo "✅ Cleanup complete"
}

# Main command handler
case "${1:-help}" in
    containerconfig)
        fix_containerconfig
        ;;
    timeout)
        fix_timeout
        ;;
    port-conflict)
        fix_port_conflict "${2:-5432}"
        ;;
    build-lease)
        fix_build_lease
        ;;
    daemon-restart)
        daemon_restart
        ;;
    rebuild-backend)
        rebuild_backend
        ;;
    rebuild-all)
        rebuild_all
        ;;
    check-state)
        check_state
        ;;
    cleanup)
        INCLUDE_VOLUMES=false
        if [ "${2:-}" = "--volumes" ]; then
            INCLUDE_VOLUMES=true
        fi
        cleanup "$INCLUDE_VOLUMES"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac



