import time
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class GlobalExceptionHandlerMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        try:
            return await call_next(request)
        except Exception as error:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": str(error),
                    "detail": "Internal server error"
                }
            )