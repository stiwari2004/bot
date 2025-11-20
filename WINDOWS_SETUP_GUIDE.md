# Windows Setup Guide - Docker Desktop & Llama.cpp LLM

This guide will help you set up Docker Desktop and llama.cpp with a full model for your 32GB RAM system.

## System Requirements
- ✅ 32GB RAM (sufficient for 7B-13B models)
- ✅ NVIDIA GPU with 2GB VRAM (can use GPU acceleration)
- ✅ Windows 10/11

---

## Step 1: Install Docker Desktop

1. **Download Docker Desktop:**
   - Visit: https://www.docker.com/products/docker-desktop/
   - Download "Docker Desktop for Windows"
   - File: `Docker Desktop Installer.exe`

2. **Install Docker Desktop:**
   - Run the installer
   - Follow the installation wizard
   - **Important:** Enable WSL 2 backend (recommended) or Hyper-V
   - Restart your computer if prompted

3. **Verify Installation:**
   ```powershell
   docker --version
   docker-compose --version
   ```

4. **Configure Docker Resources:**
   - Open Docker Desktop
   - Go to Settings > Resources
   - Set Memory: **16GB** (you have 32GB, so this is safe)
   - Set CPUs: Use 50-75% of available cores
   - Click "Apply & Restart"

---

## Step 2: Install llama.cpp Server

### Option A: Download Pre-built Binary (Recommended)

1. **Download llama.cpp server:**
   - Visit: https://github.com/ggerganov/llama.cpp/releases
   - Download the latest `llama-bXXXX-w64-avx2.zip` (Windows x64 with AVX2)
   - Extract to: `C:\llama.cpp\`

2. **Add to PATH (Optional):**
   - Add `C:\llama.cpp\` to your system PATH
   - Or use full path in scripts

### Option B: Build from Source

```powershell
# Install prerequisites
# - Visual Studio 2022 with C++ build tools
# - CMake: https://cmake.org/download/

git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
```

---

## Step 3: Download Llama Model

With 32GB RAM, you can run:
- **Llama 2 7B** (recommended) - ~4GB model file, ~8GB RAM usage
- **Llama 2 13B** - ~7GB model file, ~14GB RAM usage
- **Mistral 7B** - ~4GB model file, excellent quality

### Recommended: Llama 2 7B Q4_K_M (Best balance)

1. **Download from Hugging Face:**
   - Visit: https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF
   - Download: `llama-2-7b-chat.Q4_K_M.gguf` (~4.1GB)
   - Save to: `C:\Users\Admin\Documents\bot\models\`

2. **Alternative: Mistral 7B (Higher Quality)**
   - Visit: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF
   - Download: `mistral-7b-instruct-v0.2.Q4_K_M.gguf` (~4.1GB)
   - Save to: `C:\Users\Admin\Documents\bot\models\`

### Create Models Directory:
```powershell
mkdir C:\Users\Admin\Documents\bot\models
```

---

## Step 4: Start LLM Server

Use the provided PowerShell script: `start-llm-windows.ps1`

```powershell
cd C:\Users\Admin\Documents\bot
.\start-llm-windows.ps1
```

This will:
- Start llama-server on port 8080
- Use your downloaded model
- Configure for 32GB RAM system
- Enable GPU acceleration if available

---

## Step 5: Start Docker Containers

Once the LLM server is running:

```powershell
cd C:\Users\Admin\Documents\bot
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Backend API (port 8000)
- Frontend (port 3000)
- Worker

---

## Step 6: Verify Setup

1. **Check LLM Server:**
   ```powershell
   curl http://localhost:8080/health
   ```

2. **Check Backend:**
   ```powershell
   curl http://localhost:8000/health
   ```

3. **Check Frontend:**
   - Open browser: http://localhost:3000

4. **Test LLM Connection:**
   ```powershell
   python test_llm_connection.py
   ```

---

## Troubleshooting

### LLM Server Won't Start
- Check if port 8080 is in use: `netstat -ano | findstr :8080`
- Verify model path in script
- Check llama-server binary exists

### Docker Containers Can't Connect to LLM
- Ensure LLM server is running on `localhost:8080`
- Docker uses `host.docker.internal:8080` to access host
- Check Windows Firewall isn't blocking port 8080

### Out of Memory
- Reduce Docker memory allocation
- Use Q4_K_S instead of Q4_K_M (smaller, faster)
- Close other applications

### GPU Not Working
- Install NVIDIA Container Toolkit (for Docker GPU support)
- Or run LLM server on CPU (still fast with 32GB RAM)

---

## Model Recommendations for 32GB RAM

| Model | Size | RAM Usage | Quality | Speed |
|-------|------|-----------|---------|-------|
| Llama 2 7B Q4_K_M | 4.1GB | ~8GB | ⭐⭐⭐⭐ | Fast |
| Llama 2 13B Q4_K_M | 7.2GB | ~14GB | ⭐⭐⭐⭐⭐ | Medium |
| Mistral 7B Q4_K_M | 4.1GB | ~8GB | ⭐⭐⭐⭐⭐ | Fast |
| Llama 2 7B Q5_K_M | 4.8GB | ~9GB | ⭐⭐⭐⭐ | Fast |

**Recommendation:** Start with **Mistral 7B Q4_K_M** for best quality/speed balance.

---

## Next Steps

1. ✅ Install Docker Desktop
2. ✅ Install llama.cpp server
3. ✅ Download model
4. ✅ Start LLM server
5. ✅ Start Docker containers
6. ✅ Test the system

Enjoy your containerized AI troubleshooting system! 🚀






