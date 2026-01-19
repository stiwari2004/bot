"""
Entry point for the agent worker service.
"""
from __future__ import annotations

import asyncio
import os
import json
import traceback
from datetime import datetime

# #region agent log
try:
    import os
    log_path = os.getenv("DEBUG_LOG_PATH", "/app/worker_debug.log")
    with open(log_path, "a") as f:
        f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:14", "message": "Worker main.py starting", "data": {"hypothesisId": "A"}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
except: pass
# #endregion

try:
    from app.core.config import settings
    # #region agent log
    try:
        with open("/app/worker_debug.log", "a") as f:
            f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:20", "message": "Successfully imported app.core.config", "data": {"hypothesisId": "A"}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
    except: pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        with open("/app/worker_debug.log", "a") as f:
            f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:25", "message": "Failed to import app.core.config", "data": {"hypothesisId": "A", "error": str(e), "traceback": traceback.format_exc()}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
    except: pass
    # #endregion
    raise

try:
    from worker.service import WorkerService
    # #region agent log
    try:
        with open("/app/worker_debug.log", "a") as f:
            f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:33", "message": "Successfully imported WorkerService", "data": {"hypothesisId": "A"}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
    except: pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        with open("/app/worker_debug.log", "a") as f:
            f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:38", "message": "Failed to import WorkerService", "data": {"hypothesisId": "A", "error": str(e), "traceback": traceback.format_exc()}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
    except: pass
    # #endregion
    raise


async def main() -> None:
    # #region agent log
    try:
        with open("/app/worker_debug.log", "a") as f:
            f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:46", "message": "main() function entry", "data": {"hypothesisId": "B"}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
    except: pass
    # #endregion
    
    worker_id = os.getenv("WORKER_ID", "worker-local")
    backend_base_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
    redis_url = os.getenv("REDIS_URL", settings.REDIS_URL)
    
    # #region agent log
    try:
        with open("/app/worker_debug.log", "a") as f:
            f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:52", "message": "Environment variables loaded", "data": {"hypothesisId": "B", "worker_id": worker_id, "backend_base_url": backend_base_url, "has_redis_url": bool(redis_url)}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
    except: pass
    # #endregion

    try:
        service = WorkerService(
            worker_id=worker_id,
            backend_base_url=backend_base_url,
            redis_url=redis_url,
        )
        # #region agent log
        try:
            with open("/app/worker_debug.log", "a") as f:
                f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:63", "message": "WorkerService initialized", "data": {"hypothesisId": "B"}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
        except: pass
        # #endregion
    except Exception as e:
        # #region agent log
        try:
            with open("/app/worker_debug.log", "a") as f:
                f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:68", "message": "Failed to initialize WorkerService", "data": {"hypothesisId": "B", "error": str(e), "traceback": traceback.format_exc()}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
        except: pass
        # #endregion
        raise
    
    try:
        # #region agent log
        try:
            with open("/app/worker_debug.log", "a") as f:
                f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:75", "message": "Calling service.run()", "data": {"hypothesisId": "C", "hypothesisId2": "D"}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
        except: pass
        # #endregion
        await service.run()
        # #region agent log
        try:
            with open("/app/worker_debug.log", "a") as f:
                f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:80", "message": "service.run() completed", "data": {"hypothesisId": "C"}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
        except: pass
        # #endregion
    except Exception as e:
        # #region agent log
        try:
            with open("/app/worker_debug.log", "a") as f:
                f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:84", "message": "service.run() failed", "data": {"hypothesisId": "C", "hypothesisId2": "D", "error": str(e), "traceback": traceback.format_exc()}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
        except: pass
        # #endregion
        raise


if __name__ == "__main__":
    try:
        # #region agent log
        try:
            with open("/app/worker_debug.log", "a") as f:
                f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:92", "message": "__main__ entry point", "data": {"hypothesisId": "A"}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
        except: pass
        # #endregion
        asyncio.run(main())
        # #region agent log
        try:
            with open("/app/worker_debug.log", "a") as f:
                f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:95", "message": "asyncio.run() completed", "data": {"hypothesisId": "A"}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
        except: pass
        # #endregion
    except KeyboardInterrupt:
        # #region agent log
        try:
            with open("/app/worker_debug.log", "a") as f:
                f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:99", "message": "KeyboardInterrupt caught", "data": {"hypothesisId": "A"}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
        except: pass
        # #endregion
        pass
    except Exception as e:
        # #region agent log
        try:
            with open("/app/worker_debug.log", "a") as f:
                f.write(json.dumps({"timestamp": datetime.now().isoformat(), "location": "worker/main.py:103", "message": "Unhandled exception in __main__", "data": {"hypothesisId": "A", "error": str(e), "traceback": traceback.format_exc()}, "sessionId": "debug-session", "runId": "worker-startup"}) + "\n")
        except: pass
        # #endregion
        raise



