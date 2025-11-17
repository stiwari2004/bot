# Memory Optimization Guide for <8GB RAM Systems

This guide helps you run the troubleshooting RAG application with Docker and a local LLM model on systems with limited RAM (8GB or less).

## Current System Status

- **Total RAM**: 8GB
- **Free RAM**: ~684MB (8%)
- **Docker Allocated**: 3.8GB (needs reduction)
- **Model Size**: Mistral 7B Q4_K_S (~3.9GB on disk, ~2-3GB in RAM)

## Quick Start (Optimized)

### 1. Reduce Docker Desktop Memory

1. Open **Docker Desktop**
2. Go to **Settings** → **Resources** → **Advanced**
3. Reduce **Memory** from `3.8GB` to **`2GB`** (or `2.5GB` if you have 8GB total)
4. Reduce **CPUs** if needed (4-6 cores is usually enough)
5. Click **Apply & Restart**

**Why**: Docker VM currently uses ~900MB just for virtualization overhead. Reducing allocation frees up ~1.8GB for the LLM model.

### 2. Start the LLM Server (Optimized)

```bash
# Make the script executable
chmod +x start-llm-optimized.sh

# Start the optimized LLM server
./start-llm-optimized.sh
```

This script uses:
- **Context size**: 2048 tokens (reduces memory usage)
- **Threads**: 3 (prevents CPU thrashing)
- **Port**: 8080

### 3. Start Docker Containers (With Memory Limits)

```bash
# Use the optimized docker-compose file
docker-compose -f docker-compose.optimized.yml up -d
```

Total Docker memory usage with limits:
- PostgreSQL: 400MB
- Redis: 150MB
- Backend: 600MB
- Worker: 400MB (optional)
- Frontend: 512MB
- **Total**: ~2GB (with worker) or ~1.6GB (without worker)

### 4. Monitor Memory Usage

```bash
# Check Docker container memory
docker stats --no-stream

# Check system memory
vm_stat | head -10

# Check LLM server memory
ps aux | grep llama-server | grep -v grep
```

## Memory Breakdown

### With Optimizations:

| Component | Memory Usage |
|-----------|--------------|
| Docker VM Overhead | ~200MB |
| PostgreSQL | 200-400MB |
| Redis | 50-150MB |
| Backend | 300-600MB |
| Worker | 200-400MB (optional) |
| Frontend | 256-512MB |
| **Docker Total** | ~1.5-2GB |
| **LLM Model (Mistral 7B Q4_K_S)** | ~2-3GB |
| **System + Cursor** | ~1-1.5GB |
| **Total Used** | ~4.5-6.5GB |
| **Free** | ~1.5-3.5GB |

### Without Worker (Recommended for Development):

- Remove worker container: saves ~400MB
- **Docker Total**: ~1.1-1.6GB
- **Free**: ~2-3GB

## Advanced Optimizations

### Option 1: Use a Smaller Model (If Available)

If Mistral 7B is still too heavy, consider:
- **Mistral 7B Q2_K** (smaller quantization, ~2.5GB)
- **TinyLlama 1.1B** (much smaller, ~700MB, lower quality)
- **Phi-2 2.7B** (smaller alternative, ~1.5GB)

### Option 2: Disable Worker Container

If you don't need the worker for development:

```bash
# Edit docker-compose.optimized.yml and comment out the worker service
# Or start without worker:
docker-compose -f docker-compose.optimized.yml up -d postgres redis backend frontend
```

### Option 3: Run Frontend Locally (Not in Docker)

Saves ~512MB:

```bash
cd frontend-nextjs
npm install
npm run dev
```

Update `docker-compose.optimized.yml` to remove the frontend service.

### Option 4: Stop Unnecessary Services

```bash
# Stop Spotlight indexing (if not needed)
sudo mdutil -a -i off

# Stop Time Machine (if running)
sudo tmutil disablelocal

# Check and close unnecessary apps:
# - Chrome/other browsers (if not needed)
# - Mail app
# - Photos app (background indexing)
```

## Troubleshooting

### "Out of Memory" Errors

1. **Check Docker memory**: Ensure Docker Desktop is set to 2GB max
2. **Restart Docker**: `docker-compose -f docker-compose.optimized.yml restart`
3. **Kill unused containers**: `docker system prune -f`
4. **Restart LLM server**: Stop and restart `start-llm-optimized.sh`

### Containers Keep Crashing

1. Increase memory limits in `docker-compose.optimized.yml` slightly
2. Check logs: `docker-compose -f docker-compose.optimized.yml logs [service-name]`
3. Ensure Docker Desktop has at least 2GB allocated

### LLM Server Not Responding

1. Check if it's running: `lsof -i :8080`
2. Check memory: `ps aux | grep llama-server`
3. Restart: `./start-llm-optimized.sh`

### Still Running Out of Memory

1. Close Cursor and use a lighter editor temporarily
2. Close Chrome/other browsers
3. Reduce Docker memory to 1.5GB and remove worker
4. Consider using a cloud LLM (OpenAI API) instead of local model

## Recommended Startup Sequence

1. **Reduce Docker Desktop memory to 2GB** (one-time setup)
2. **Start LLM server**: `./start-llm-optimized.sh` (keep running in terminal)
3. **Start Docker**: `docker-compose -f docker-compose.optimized.yml up -d`
4. **Wait 30 seconds** for services to initialize
5. **Access**: http://localhost:3000

## Shutdown Sequence

1. Stop Docker: `docker-compose -f docker-compose.optimized.yml down`
2. Stop LLM server: Press `Ctrl+C` in the terminal running `start-llm-optimized.sh`

## Performance Tips

- **Context size**: Lower = less memory but shorter responses (2048 is a good balance)
- **Threads**: More threads = faster but more memory (3 is optimal for 8GB systems)
- **Docker limits**: Strict limits prevent one container from consuming all memory
- **Model quantization**: Q4_K_S is optimal balance (Q2_K is smaller but lower quality)







