#!/bin/bash
# Disable IPv6 on the system

set -e

echo "🔧 Checking IPv6 status..."

# Check if IPv6 is enabled
if [ -f /proc/sys/net/ipv6/conf/all/disable_ipv6 ]; then
    CURRENT_STATUS=$(cat /proc/sys/net/ipv6/conf/all/disable_ipv6)
    if [ "$CURRENT_STATUS" = "1" ]; then
        echo "✅ IPv6 is already disabled"
    else
        echo "⚠️  IPv6 is currently enabled (value: $CURRENT_STATUS)"
        echo ""
        echo "To disable IPv6 temporarily (until reboot):"
        echo "  sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1"
        echo "  sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1"
        echo ""
        echo "To disable IPv6 permanently, add to /etc/sysctl.conf:"
        echo "  net.ipv6.conf.all.disable_ipv6 = 1"
        echo "  net.ipv6.conf.default.disable_ipv6 = 1"
    fi
else
    echo "❌ Cannot check IPv6 status (file not found)"
fi

echo ""
echo "📋 Current IPv6 configuration:"
sysctl net.ipv6.conf.all.disable_ipv6 2>/dev/null || echo "Cannot read IPv6 config"
sysctl net.ipv6.conf.default.disable_ipv6 2>/dev/null || echo "Cannot read IPv6 default config"

echo ""
echo "📋 Testing connection to backend:"
echo "  IPv4 only: curl -4 http://localhost:8001/health"
echo "  IPv6 only: curl -6 http://localhost:8001/health"
