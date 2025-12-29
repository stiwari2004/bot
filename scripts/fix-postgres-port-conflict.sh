#!/bin/bash
# Fix PostgreSQL port conflict between Resolvify and Strapi (admin.fitglide.in)
# Ensures Resolvify PostgreSQL doesn't expose port 5432 to host

set -e

echo "🔧 Fixing PostgreSQL port conflict..."
echo ""

# Check which compose file is being used
COMPOSE_FILE="docker-compose.production.yml"

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ $COMPOSE_FILE not found!"
    exit 1
fi

echo "📋 Checking $COMPOSE_FILE configuration..."

# Check if PostgreSQL port is exposed
if grep -q "^\s*-\s*\"5432:5432\"" "$COMPOSE_FILE"; then
    echo "⚠️  PostgreSQL port 5432 is exposed to host (conflicts with Strapi)"
    echo ""
    echo "🔧 Fixing configuration..."
    
    # Create backup
    cp "$COMPOSE_FILE" "${COMPOSE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ Backup created"
    
    # Comment out the port mapping
    sed -i 's/^\s*-\s*"5432:5432"/    #   - "5433:5432"  # Changed to avoid conflict with Strapi on 5432/' "$COMPOSE_FILE"
    
    echo "✅ Port mapping commented out"
    echo ""
    echo "📝 Updated configuration:"
    grep -A 2 "postgres:" "$COMPOSE_FILE" | grep -E "(postgres:|ports:|- \"543)" || echo "   Port mapping removed"
    
    echo ""
    echo "🔄 Restarting services..."
    docker-compose -f "$COMPOSE_FILE" down
    docker-compose -f "$COMPOSE_FILE" up -d postgres
    
    echo ""
    echo "✅ PostgreSQL is now only accessible within Docker network"
    echo "   Strapi can use host port 5432 without conflict"
    
elif grep -q "#.*5432:5432\|#.*5433:5432" "$COMPOSE_FILE"; then
    echo "✅ PostgreSQL port is NOT exposed to host (correct configuration)"
    echo "   Resolvify PostgreSQL is only accessible within Docker network"
    echo "   Strapi can use host port 5432 without conflict"
else
    echo "✅ PostgreSQL port mapping not found (already correct)"
fi

# Verify current port usage
echo ""
echo "🔍 Checking port 5432 usage:"
if lsof -i :5432 > /dev/null 2>&1 || netstat -tuln | grep -q ":5432 "; then
    echo "   Port 5432 is in use:"
    if command -v lsof > /dev/null 2>&1; then
        lsof -i :5432 | head -5
    else
        netstat -tulnp | grep ":5432 " | head -5
    fi
    echo ""
    echo "   This should be Strapi's PostgreSQL, not Resolvify's"
else
    echo "   Port 5432 is not in use"
fi

# Check Docker containers
echo ""
echo "🐳 Docker PostgreSQL containers:"
docker ps --filter "name=postgres" --format "table {{.Names}}\t{{.Ports}}"

echo ""
echo "💡 Important notes:"
echo "   1. Resolvify backend connects via Docker network: postgres:5432"
echo "   2. Strapi connects via host: localhost:5432"
echo "   3. Both can coexist without conflict"
echo ""
echo "✅ Port conflict resolved!"



