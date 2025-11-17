#!/bin/bash
# Quick memory check script

echo "=== System Memory Status ==="
echo ""
echo "Total RAM: $(sysctl -n hw.memsize | awk '{printf "%.1f GB", $1/1024/1024/1024}')"
echo ""

# Get memory stats
vm_stat | while IFS= read -r line; do
    if [[ $line =~ "Pages free" ]]; then
        free_pages=$(echo $line | awk '{print $3}' | sed 's/\.//')
        free_mb=$((free_pages * 16384 / 1024 / 1024))
        echo "Free RAM: ${free_mb} MB (~$((free_mb * 100 / 8192))%)"
    fi
    if [[ $line =~ "Pages active" ]]; then
        active_pages=$(echo $line | awk '{print $3}' | sed 's/\.//')
        active_mb=$((active_pages * 16384 / 1024 / 1024))
        echo "Active RAM: ${active_mb} MB"
    fi
    if [[ $line =~ "Pages inactive" ]]; then
        inactive_pages=$(echo $line | awk '{print $3}' | sed 's/\.//')
        inactive_mb=$((inactive_pages * 16384 / 1024 / 1024))
        echo "Inactive RAM: ${inactive_mb} MB"
    fi
    if [[ $line =~ "Pages speculative" ]]; then
        spec_pages=$(echo $line | awk '{print $3}' | sed 's/\.//')
        spec_mb=$((spec_pages * 16384 / 1024 / 1024))
        echo "Speculative RAM: ${spec_mb} MB"
    fi
    if [[ $line =~ "Pages wired down" ]]; then
        wired_pages=$(echo $line | awk '{print $4}' | sed 's/\.//')
        wired_mb=$((wired_pages * 16384 / 1024 / 1024))
        echo "Wired RAM: ${wired_mb} MB"
    fi
    if [[ $line =~ "Pages purgeable" ]]; then
        purgeable_pages=$(echo $line | awk '{print $3}' | sed 's/\.//')
        purgeable_mb=$((purgeable_pages * 16384 / 1024 / 1024))
        echo "Purgeable RAM: ${purgeable_mb} MB"
    fi
done

echo ""
echo "=== Top Memory Consumers ==="
ps aux | sort -rk 4 | head -10 | awk '{printf "%-10s %8s MB %5s%% CPU\n", $11, int($6/1024), $3}'

echo ""
echo "=== Docker Status ==="
if docker info >/dev/null 2>&1; then
    docker stats --no-stream --format "{{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null || echo "No running containers"
else
    echo "Docker not running"
fi

echo ""
echo "=== LLM Server Status ==="
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    ps aux | grep "llama-server" | grep -v grep | awk '{printf "Running: %8s MB RAM\n", int($6/1024)}'
else
    echo "Not running on port 8080"
fi







