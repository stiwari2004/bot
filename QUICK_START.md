# Quick Start Guide

Follow these steps in order to get your system running:

## 1. Install Docker Desktop (5-10 minutes)

**Option A: Use the download script:**
```powershell
cd C:\Users\Admin\Documents\bot
.\download-docker.ps1
```

**Option B: Download manually:**
1. Visit: https://www.docker.com/products/docker-desktop/
2. Download "Docker Desktop for Windows"
3. Run the installer
4. Enable WSL 2 backend
5. Restart if prompted
6. Launch Docker Desktop

**Verify:**
```powershell
docker --version
```

---

## 2. Install llama.cpp Server (5 minutes)

**Download Pre-built Binary:**
1. Visit: https://github.com/ggerganov/llama.cpp/releases
2. Download: `llama-bXXXX-w64-avx2.zip` (latest Windows x64 AVX2)
3. Extract to: `C:\llama.cpp\`

**Or Build from Source:**
```powershell
# Requires: Visual Studio 2022 + CMake
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
# Binary will be in: build\bin\Release\llama-server.exe
```

---

## 3. Download LLM Model (10-30 minutes depending on internet)

**Recommended: Mistral 7B Q4_K_M** (Best quality/speed balance)

1. Visit: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF
2. Click "Files and versions"
3. Download: `mistral-7b-instruct-v0.2.Q4_K_M.gguf` (~4.1GB)
4. Save to: `C:\Users\Admin\Documents\bot\models\`

**Alternative: Llama 2 7B Q4_K_M**
1. Visit: https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF
2. Download: `llama-2-7b-chat.Q4_K_M.gguf` (~4.1GB)
3. Save to: `C:\Users\Admin\Documents\bot\models\`

---

## 4. Start LLM Server

```powershell
cd C:\Users\Admin\Documents\bot
.\start-llm-windows.ps1
```

**Keep this terminal open!** The LLM server must be running for the backend to work.

---

## 5. Start Docker Containers (in a new terminal)

```powershell
cd C:\Users\Admin\Documents\bot
docker-compose up -d
```

This starts all services:
- PostgreSQL (database)
- Redis (caching)
- Backend API (port 8000)
- Frontend (port 3000)
- Worker (background tasks)

---

## 6. Verify Everything Works

**Check LLM Server:**
```powershell
curl http://localhost:8080/health
```

**Check Backend:**
```powershell
curl http://localhost:8000/health
```

**Open Frontend:**
- Browser: http://localhost:3000

**Test LLM Connection:**
```powershell
python test_llm_connection.py
```

---

## Daily Usage

**To start the system:**

1. **Terminal 1 - Start LLM Server:**
   ```powershell
   cd C:\Users\Admin\Documents\bot
   .\start-llm-windows.ps1
   ```

2. **Terminal 2 - Start Docker:**
   ```powershell
   cd C:\Users\Admin\Documents\bot
   docker-compose up -d
   ```

**To stop the system:**

1. **Stop LLM Server:** Press `Ctrl+C` in Terminal 1
2. **Stop Docker:**
   ```powershell
   docker-compose down
   ```

---

## Troubleshooting

**Docker not found:**
- Make sure Docker Desktop is running
- Check PATH includes Docker

**LLM server not found:**
- Verify llama-server.exe exists at `C:\llama.cpp\llama-server.exe`
- Or update path in `start-llm-windows.ps1`

**Model not found:**
- Check file is in `C:\Users\Admin\Documents\bot\models\`
- Verify filename matches script expectations

**Port 8080 in use:**
- Stop other applications using port 8080
- Or change port in script and docker-compose.yml

**Docker can't connect to LLM:**
- Ensure LLM server is running on `localhost:8080`
- Check Windows Firewall settings
- Verify `host.docker.internal` resolves correctly

---

## Need Help?

See `WINDOWS_SETUP_GUIDE.md` for detailed instructions and troubleshooting.




