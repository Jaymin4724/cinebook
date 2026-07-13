import logging
import time
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class GlobalExceptionHandlerMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        try:
            return await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled exception for %s %s", request.method, request.url.path
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "detail": "Internal server error"
                }
            )