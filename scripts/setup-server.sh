#!/bin/bash
# Initial server setup script
# Run this once on a fresh Ubuntu server
# Usage: ./scripts/setup-server.sh

set -e

echo "🛠️  Setting up Ubuntu server for Troubleshooting AI deployment..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "❌ Please do not run as root. Use sudo when needed."
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✅ Docker installed. Please log out and back in for group changes to take effect."
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "🐳 Installing Docker Compose..."
    sudo apt-get install -y docker-compose-plugin
else
    echo "✅ Docker Compose already installed"
fi

# Install Nginx
if ! command -v nginx &> /dev/null; then
    echo "🌐 Installing Nginx..."
    sudo apt-get install -y nginx
    sudo systemctl enable nginx
    sudo systemctl start nginx
else
    echo "✅ Nginx already installed"
fi

# Install Certbot for SSL
if ! command -v certbot &> /dev/null; then
    echo "🔒 Installing Certbot for SSL certificates..."
    sudo apt-get install -y certbot python3-certbot-nginx
else
    echo "✅ Certbot already installed"
fi

# Create application directories
echo "📁 Creating application directories..."
sudo mkdir -p /opt/troubleshooting-ai-demo
sudo mkdir -p /opt/troubleshooting-ai-dev
sudo chown $USER:$USER /opt/troubleshooting-ai-demo
sudo chown $USER:$USER /opt/troubleshooting-ai-dev

# Create backups directory
mkdir -p /opt/troubleshooting-ai-demo/backups

# Configure firewall (if ufw is installed)
if command -v ufw &> /dev/null; then
    echo "🔥 Configuring firewall..."
    sudo ufw allow 22/tcp   # SSH
    sudo ufw allow 80/tcp   # HTTP
    sudo ufw allow 443/tcp  # HTTPS
    echo "⚠️  Firewall configured. Internal ports (3000, 8000, 5432, 6379) are not exposed."
fi

echo ""
echo "✅ Server setup completed!"
echo ""
echo "📋 Next steps:"
echo "   1. Log out and back in (for Docker group)"
echo "   2. Clone repository to /opt/troubleshooting-ai-demo"
echo "   3. Configure .env files"
echo "   4. Copy nginx configs to /etc/nginx/sites-available/"
echo "   5. Set up SSL certificates with certbot"
echo "   6. Deploy application"

