from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.routers import countries, visa_map
from app.exceptions import register_exception_handlers
from app.middleware import logging_middleware
from app.logging_config import setup_logging

setup_logging()

app = FastAPI(
    title="Visa Map API",
    description="API для сервиса визовых режимов стран мира",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(BaseHTTPMiddleware, dispatch=logging_middleware)

register_exception_handlers(app)

app.include_router(countries.router)
app.include_router(visa_map.router)


@app.get("/health", tags=["system"])
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "version": "0.1.0",
        "database": db_status,
    }