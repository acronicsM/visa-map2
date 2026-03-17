from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " → ".join(str(x) for x in error["loc"]),
                "message": error["msg"],
            })
        return JSONResponse(
            status_code=422,
            content={
                "error": "Ошибка валидации",
                "details": errors,
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request,
        exc: SQLAlchemyError,
    ):
        logger.error(f"Database error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Ошибка базы данных",
                "details": "Попробуйте позже",
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ):
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Внутренняя ошибка сервера",
                "details": "Попробуйте позже",
            },
        )