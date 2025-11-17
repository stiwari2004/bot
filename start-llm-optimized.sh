#!/bin/bash
# Optimized LLM Server Startup Script for Low-RAM Systems (<8GB)
# This script starts llama-server with minimal memory footprint

set -e

echo "🚀 Starting OPTIMIZED LLM Server (Mistral 7B Q4_K_S)"
echo "💾 Memory optimizations for 6GB RAM systems:"
echo "   - Context size: 4096 tokens (balanced: enough for runbook generation)"
echo "   - Threads: 2 (balanced for performance)"
echo "   - Batch size: 1 (process one request at a time)"
echo "   - Parallel: 1 (prevents memory spikes)"

MODEL_PATH="$HOME/Library/Caches/llama.cpp/TheBloke_Mistral-7B-Instruct-v0.2-GGUF_mistral-7b-instruct-v0.2.Q4_K_S.gguf"
PORT=8080

# Check if model exists
if [ ! -f "$MODEL_PATH" ]; then
    echo "❌ Error: Model not found at $MODEL_PATH"
    echo "   Please ensure the model is downloaded."
    exit 1
fi

# Find llama-server binary
LLAMA_SERVER=""
if command -v llama-server >/dev/null 2>&1; then
    LLAMA_SERVER="llama-server"
elif [ -f "/usr/local/bin/llama-server" ]; then
    LLAMA_SERVER="/usr/local/bin/llama-server"
elif [ -f "$HOME/llama.cpp/server" ]; then
    LLAMA_SERVER="$HOME/llama.cpp/server"
elif [ -f "$HOME/llama.cpp/build/bin/llama-server" ]; then
    LLAMA_SERVER="$HOME/llama.cpp/build/bin/llama-server"
elif command -v llama-cpp-server >/dev/null 2>&1; then
    LLAMA_SERVER="llama-cpp-server"
else
    echo "❌ Error: llama-server not found!"
    echo ""
    echo "Please install llama.cpp server:"
    echo "  Option 1: Homebrew: brew install llama-cpp"
    echo "  Option 2: Build from source: https://github.com/ggerganov/llama.cpp"
    echo ""
    echo "Or update this script with the correct path to llama-server"
    exit 1
fi

echo "✅ Found llama-server at: $LLAMA_SERVER"

# Check if llama-server is already running
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port $PORT is already in use. Stopping existing process..."
    lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start llama-server with optimized settings
echo ""
echo "📡 Starting server on port $PORT..."
echo "   Model: Mistral-7B-Instruct-v0.2 Q4_K_S"
echo "   Context: 4096 tokens (balanced for runbook generation)"
echo "   Threads: 2 (balanced for performance)"
echo "   Batch size: 1 (process one request at a time)"
echo ""

# Balanced Memory-optimized settings for 6GB RAM systems:
# - --ctx-size 4096: Sufficient context for runbook generation (YAML needs ~2000-4000 tokens)
# - --threads 2: Balanced threads for better performance while staying within memory limits
# - --batch-size 1: Process one request at a time (reduces peak memory)
# - --parallel 1: Single parallel request (prevents memory spikes)
# - --host 0.0.0.0: Allow Docker to connect
# - --log-disable: Disable logging to save memory
"$LLAMA_SERVER" \
    --model "$MODEL_PATH" \
    --port $PORT \
    --ctx-size 4096 \
    --threads 2 \
    --batch-size 1 \
    --parallel 1 \
    --host 0.0.0.0 \
    --log-disable

echo "✅ LLM Server started successfully!"
echo "   Access at: http://localhost:$PORT"
echo ""
echo "Press Ctrl+C to stop the server"

