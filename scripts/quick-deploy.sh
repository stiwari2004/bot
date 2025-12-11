#!/bin/bash
# Quick deployment script for Hostinger - Automated setup
# Usage: ./scripts/quick-deploy.sh

set -e

echo "🚀 Quick Deployment Script for Hostinger"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "❌ Please do not run as root. Use sudo when needed."
    exit 1
fi

APP_DIR="/opt/troubleshooting-ai-demo"
COMPOSE_FILE="docker-compose.production.yml"

# Step 1: Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Installing..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✅ Docker installed. Please log out and back in, then run this script again."
    exit 0
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

if ! command -v nginx &> /dev/null; then
    echo "❌ Nginx not found. Installing..."
    sudo apt-get install -y nginx certbot python3-certbot-nginx
fi

echo "✅ Prerequisites check complete"
echo ""

# Step 2: Check if app directory exists
if [ ! -d "$APP_DIR" ]; then
    echo "❌ Application directory not found: $APP_DIR"
    echo "   Please clone the repository first:"
    echo "   git clone <your-repo-url> $APP_DIR"
    exit 1
fi

cd "$APP_DIR"

# Step 3: Check environment file
if [ ! -f "backend/.env" ]; then
    echo "⚠️  backend/.env not found. Creating from template..."
    cp backend/env.example backend/.env
    echo "⚠️  Please edit backend/.env and set:"
    echo "   - SECRET_KEY (generate with: python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
    echo "   - CREDENTIAL_ENCRYPTION_KEY (generate with: python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
    echo "   - GEMINI_API_KEY"
    echo "   - PERPLEXITY_API_KEY"
    echo "   - ALLOWED_HOSTS (with your domain)"
    echo ""
    read -p "Press Enter after you've configured backend/.env..."
fi

# Step 4: Build and start services
echo "🔨 Building Docker images..."
docker compose -f "$COMPOSE_FILE" build

echo "▶️  Starting services..."
docker compose -f "$COMPOSE_FILE" up -d

echo "⏳ Waiting for services to start..."
sleep 15

# Step 5: Check service health
echo "🏥 Checking service health..."
if docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
    echo "✅ Services are running"
else
    echo "⚠️  Some services may not be healthy. Check logs:"
    echo "   docker compose -f $COMPOSE_FILE logs"
fi

# Step 6: Initialize database
echo "🔄 Initializing database..."
docker compose -f "$COMPOSE_FILE" exec -T backend python -c "
from app.core.database import init_db
import asyncio
asyncio.run(init_db())
" 2>/dev/null || echo "⚠️  Database initialization may have failed. Check logs."

# Step 7: Verify
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Service Status:"
docker compose -f "$COMPOSE_FILE" ps
echo ""
echo "🌐 Next steps:"
echo "   1. Configure nginx (see QUICK_DEPLOY_20MIN.md)"
echo "   2. Set up SSL certificates: sudo certbot --nginx -d demo.YOUR_DOMAIN.com"
echo "   3. Test: curl http://localhost:8000/health"
echo ""
echo "📝 View logs: docker compose -f $COMPOSE_FILE logs -f"

