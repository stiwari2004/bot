#!/bin/bash
# Quick script to identify high CPU processes

echo "=========================================="
echo "High CPU Usage Investigation"
echo "=========================================="
echo ""

echo "[1] Top 15 CPU-consuming processes:"
ps aux --sort=-%cpu | head -16
echo ""

echo "[2] Checking for known malicious processes:"
MALICIOUS_PATTERNS=("xmrig" "miner" "crypto" "\.system" "4thepool" "watcher" "\.b4nd1d0" "\.est1" "ksoftirq.*tmp" "install")
for pattern in "${MALICIOUS_PATTERNS[@]}"; do
    FOUND=$(ps aux | grep -i "$pattern" | grep -v grep || true)
    if [ ! -z "$FOUND" ]; then
        echo "⚠️  FOUND: $pattern"
        echo "$FOUND"
        echo ""
    fi
done

echo "[3] Processes with deleted executables:"
ps aux | while read line; do
    pid=$(echo "$line" | awk '{print $2}')
    if [ -n "$pid" ] && [ "$pid" != "PID" ]; then
        exe=$(readlink -f /proc/$pid/exe 2>/dev/null)
        if echo "$exe" | grep -q "(deleted)"; then
            echo "⚠️  PID $pid: $exe"
            echo "$line"
        fi
    fi
done
echo ""

echo "[4] Processes running from /tmp:"
ps aux | awk '{print $2, $11}' | while read pid cmd; do
    if [ -L /proc/$pid/exe ] 2>/dev/null; then
        realpath=$(readlink -f /proc/$pid/exe 2>/dev/null)
        if echo "$realpath" | grep -q "/tmp"; then
            echo "⚠️  PID $pid running from /tmp: $realpath"
            ps -fp $pid
        fi
    fi
done
echo ""

echo "[5] System load average:"
uptime
echo ""

echo "[6] Network connections (suspicious):"
netstat -anp 2>/dev/null | grep ESTABLISHED | grep -vE "127.0.0.1|::1|docker|postgres|redis|nginx|ssh" | head -20 || true
echo ""

echo "=========================================="
echo "Investigation Complete"
echo "=========================================="



