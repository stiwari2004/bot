"""
Entry point for the agent worker service.
"""
from __future__ import annotations

import asyncio
import os

from app.core.config import settings
from worker.service import WorkerService


async def main() -> None:
    worker_id = os.getenv("WORKER_ID", "worker-local")
    backend_base_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
    redis_url = os.getenv("REDIS_URL", settings.REDIS_URL)

    service = WorkerService(
        worker_id=worker_id,
        backend_base_url=backend_base_url,
        redis_url=redis_url,
    )
    await service.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass



