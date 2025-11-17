# Ultra-Low Memory Configuration Guide (6GB RAM)

## System Memory Breakdown

With **6GB total RAM** and **4GB allocated to Docker**, you have approximately **2GB** for:
- macOS system: ~1-1.5GB
- LLM model (Mistral 7B Q4_K_S): ~2-3GB
- Other applications (Cursor, etc.): ~0.5GB

**This is extremely tight!** The optimizations below minimize memory usage to the absolute minimum.

## Optimizations Applied

### 1. LLM Server (Ultra-Low Memory Mode)
- **Context size: 2048 tokens** (reduced from 4096)
  - This may cause some prompts to exceed context, but it's necessary
  - If you see "exceed_context_size_error", the prompt is too large
- **Threads: 2** (reduced from 3)
- **Memory mapping: enabled** (`--mmap`)
  - Uses file-backed memory instead of pure RAM
- **Model: Mistral 7B Q4_K_S** (already the smallest quantized version)

**Expected RAM usage: ~2-2.5GB**

### 2. Docker Containers (Total: ~1.85GB)
- **PostgreSQL: 350MB** (reduced from 400MB)
- **Redis: 150MB** (unchanged - already minimal)
- **Backend: 400MB** (reduced from 600MB)
- **Worker: 300MB** (reduced from 400MB) - *optional, can disable*
- **Frontend: 400MB** (reduced from 512MB)
- **Total: ~1.6GB reserved + overhead ≈ 1.85GB**

### 3. Docker Desktop Settings
- **Allocated: 4GB** (you've already set this)
- Consider reducing to **3.5GB** if the model still has issues

## Memory Usage Estimates

| Component | RAM Usage | Priority |
|-----------|-----------|----------|
| macOS | 1-1.5GB | Required |
| LLM Model | 2-2.5GB | Required |
| Docker (4GB alloc) | ~1.85GB | Required |
| Docker overhead | ~0.5GB | Required |
| **Total** | **~5.35-6.35GB** | **TIGHT!** |

## Startup Order (Critical!)

1. **First**: Start LLM server (takes ~10-15 seconds to load model)
   ```bash
   ./start-llm-optimized.sh
   ```

2. **Wait** for LLM server to be fully loaded (check: `curl http://localhost:8080/health`)

3. **Then**: Start Docker containers
   ```bash
   docker-compose -f docker-compose.optimized.yml up -d
   ```

## If System Still Freezes

### Option 1: Disable Worker (Saves ~300MB)
Edit `docker-compose.optimized.yml` and comment out the worker service:
```yaml
# worker:
#   ...
```

### Option 2: Reduce Docker to 3.5GB
- Docker Desktop → Settings → Resources → Memory → 3.5GB

### Option 3: Further Reduce Context Size
Edit `start-llm-optimized.sh`:
- Change `--ctx-size 2048` to `--ctx-size 1536` or `--ctx-size 1024`
- **Warning**: This may cause more context size errors

### Option 4: Use an Even Smaller Model
Consider switching to:
- **Phi-2** (2.7B parameters) - much smaller but less capable
- **TinyLlama** (1.1B parameters) - very small but very limited

### Option 5: Close Other Applications
- Close unnecessary browser tabs
- Close other memory-intensive apps (IDEs, etc.)
- Use Activity Monitor to find memory hogs

## Monitoring Memory

```bash
# Check system memory
vm_stat

# Check Docker memory usage (when Docker is running)
docker stats --no-stream

# Check process memory
ps aux | grep -E "llama-server|docker" | sort -rn -k4 | head -10
```

## Context Size Errors

If you see `"exceed_context_size_error"` with `n_prompt_tokens > 2048`:
- The prompt is too large for the reduced context window
- You may need to increase context size slightly (try 2560 or 3072)
- Or reduce the system prompt size in `runbook_generator.py`

## Expected Performance

- **Startup time**: ~30-60 seconds (model loading)
- **Response time**: Slower due to reduced threads (2 instead of 3-4)
- **Context errors**: More likely with large prompts
- **Quality**: Should remain acceptable with 2048 context

## Troubleshooting

1. **System freezes immediately**: 
   - Reduce Docker memory to 3.5GB
   - Or disable worker service

2. **Out of memory errors**:
   - Check actual Docker memory usage: `docker stats`
   - Reduce context size further
   - Close other applications

3. **Model won't load**:
   - Check available RAM: `vm_stat`
   - Ensure Docker isn't using all 4GB
   - Try starting LLM before Docker

4. **Slow responses**:
   - Normal with reduced threads - be patient
   - Consider increasing threads to 3 if you have spare CPU





