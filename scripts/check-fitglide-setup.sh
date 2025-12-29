#!/bin/bash
# Check Fitglide/Strapi setup to determine if PostgreSQL proxying is needed

echo "🔍 Checking Fitglide/Strapi Setup..."
echo ""

# Check 1: Is Strapi running in Docker or on host?
echo "📦 Check 1: Strapi/Fitglide deployment method"
if docker ps --format "{{.Names}}" | grep -iE "strapi|fitglide"; then
    echo "   ✅ Strapi is running in Docker"
    STRAPI_IN_DOCKER=true
    docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -iE "strapi|fitglide"
else
    echo "   ℹ️  Strapi appears to be running on host (not in Docker)"
    STRAPI_IN_DOCKER=false
fi

echo ""

# Check 2: Where is Strapi's PostgreSQL?
echo "📊 Check 2: Strapi PostgreSQL location"
if [ "$STRAPI_IN_DOCKER" = true ]; then
    echo "   Checking Docker containers for Strapi PostgreSQL..."
    docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -iE "postgres|database" || echo "   No PostgreSQL container found for Strapi"
else
    echo "   Checking host PostgreSQL service..."
    if systemctl is-active --quiet postgresql; then
        echo "   ✅ Host PostgreSQL service is running"
        sudo systemctl status postgresql --no-pager | head -5
    else
        echo "   ⚠️  Host PostgreSQL service is not running"
    fi
fi

echo ""

# Check 3: Port usage
echo "🔌 Check 3: Port 5432 usage"
echo "   Processes using port 5432:"
if command -v lsof > /dev/null 2>&1; then
    sudo lsof -i :5432 | head -10 || echo "   No processes found (or need sudo)"
else
    sudo netstat -tulnp | grep ":5432 " || echo "   No processes found"
fi

echo ""

# Check 4: Nginx configuration for Fitglide
echo "🌐 Check 4: Nginx configuration for Fitglide"
if [ -d "/etc/nginx/sites-available" ] || [ -d "/etc/nginx/conf.d" ]; then
    echo "   Looking for Fitglide nginx configs..."
    find /etc/nginx -name "*fitglide*" -o -name "*strapi*" 2>/dev/null | head -5 || echo "   No Fitglide nginx configs found"
else
    echo "   Nginx config directory not found"
fi

echo ""

# Check 5: Strapi configuration files (if accessible)
echo "📁 Check 5: Strapi configuration"
if [ -d "/home/strapi" ] || [ -d "/opt/strapi" ] || [ -d "/var/www/strapi" ]; then
    echo "   Strapi directories found:"
    find /home /opt /var/www -maxdepth 2 -type d -iname "*strapi*" -o -iname "*fitglide*" 2>/dev/null | head -5
    echo ""
    echo "   Looking for database config..."
    find /home /opt /var/www -maxdepth 3 -name "database.js" -o -name "database.json" 2>/dev/null | head -3
else
    echo "   Strapi directories not found in common locations"
fi

echo ""
echo "📋 Summary:"
echo "   To determine if Fitglide needs PostgreSQL proxying, I need:"
echo "   1. Is Strapi in Docker or on host? → $(if [ "$STRAPI_IN_DOCKER" = true ]; then echo "Docker"; else echo "Host"; fi)"
echo "   2. Where is Strapi's PostgreSQL? → Check above"
echo "   3. How does Strapi connect to PostgreSQL? → Need to check Strapi config"
echo ""
echo "💡 Next steps:"
echo "   - If Strapi is in Docker: Check docker-compose.yml or container config"
echo "   - If Strapi is on host: Check /path/to/strapi/config/database.js"
echo "   - Check Strapi's DATABASE_URL or connection string"



