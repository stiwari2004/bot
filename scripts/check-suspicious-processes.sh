#!/bin/bash
# Script to investigate suspicious processes

echo "=========================================="
echo "Suspicious Process Investigation"
echo "=========================================="
echo ""

# Check the install+ process
echo "[1] Checking install+ process (PID 51372)..."
if ps -p 51372 > /dev/null 2>&1; then
    echo "Process details:"
    ps -fp 51372
    echo ""
    echo "Process tree:"
    pstree -p 51372
    echo ""
    echo "Command line:"
    cat /proc/51372/cmdline 2>/dev/null | tr '\0' ' ' || echo "Cannot read cmdline"
    echo ""
    echo "Working directory:"
    ls -la /proc/51372/cwd 2>/dev/null || echo "Cannot read cwd"
    echo ""
    echo "Open files:"
    lsof -p 51372 2>/dev/null | head -20 || echo "Cannot read open files"
    echo ""
    echo "Network connections:"
    netstat -anp 2>/dev/null | grep 51372 || ss -anp 2>/dev/null | grep 51372 || echo "No network connections"
else
    echo "Process 51372 no longer exists"
fi
echo ""

# Check all node processes
echo "[2] Checking all node processes..."
ps aux | grep node | grep -v grep
echo ""

# Check all processes using high CPU
echo "[3] Top 10 CPU-consuming processes:"
ps aux --sort=-%cpu | head -11
echo ""

# Check for processes with suspicious names
echo "[4] Checking for processes with suspicious patterns..."
ps aux | grep -iE "install|download|wget|curl|bash.*-c|sh.*-c|python.*-c|perl.*-e" | grep -v grep
echo ""

# Check for processes running from /tmp
echo "[5] Processes running from /tmp:"
ps aux | awk '{print $2, $11}' | while read pid cmd; do
    if [ -L /proc/$pid/exe ] 2>/dev/null; then
        realpath=$(readlink -f /proc/$pid/exe 2>/dev/null)
        if echo "$realpath" | grep -q "/tmp"; then
            echo "PID $pid: $realpath"
            ps -fp $pid
        fi
    fi
done
echo ""

# Check for processes with no controlling terminal (daemons)
echo "[6] Processes with no controlling terminal (potential daemons):"
ps aux | awk '$7 == "?" {print}'
echo ""

# Check for processes with unusual parent PIDs
echo "[7] Processes with unusual parent PIDs (not 1 or systemd):"
ps aux | awk '$3 != 1 && $3 != 0 && $3 != 2 && $3 != 3 && $3 != 4 && $3 != 5 && $3 != 6 && $3 != 7 && $3 != 8 && $3 != 9 && $3 != 10 && $3 != 11 && $3 != 12 && $3 != 13 && $3 != 14 && $3 != 15 && $3 != 16 {print $2, $3, $11}' | head -20
echo ""

echo "=========================================="
echo "Investigation Complete"
echo "=========================================="

