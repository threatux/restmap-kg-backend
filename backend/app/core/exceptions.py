"""
Custom exceptions + registered handlers.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Базовое исключение приложения."""
    
    status_code: int = 400
    code: str = "app_error"
    
    def __init__(self, message: str, code: str | None = None):
        self.message = message
        if code:
            self.code = code
        super().__init__(message)


class NotFoundError(AppException):
    status_code = 404
    code = "not_found"


class BusinessRuleError(AppException):
    status_code = 422
    code = "business_rule"


class InsufficientFundsError(AppException):
    status_code = 402
    code = "insufficient_funds"


class PermissionDenied(AppException):
    status_code = 403
    code = "permission_denied"


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрирует обработчики исключений."""
    
    @app.exception_handler(AppException)
    async def _handle(_req: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )