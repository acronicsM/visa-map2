import time
import logging
import uuid
from fastapi import Request

logger = logging.getLogger(__name__)


async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start_time = time.perf_counter()

    logger.info(
        f"[{request_id}] → {request.method} {request.url.path}"
    )

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        f"[{request_id}] ← {response.status_code} "
        f"{request.method} {request.url.path} "
        f"{duration_ms:.1f}ms"
    )

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{duration_ms:.1f}ms"

    return response