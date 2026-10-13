"""Errores de dominio y envelope único de error (SDD §7.4).

Toda respuesta de error tiene la forma:
    {"error": {"code": "...", "message": "...", "details": {}}}
"""
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def unauthenticated(message: str = "Tu sesión expiró. Inicia sesión de nuevo.") -> AppError:
    return AppError(401, "UNAUTHENTICATED", message)


def forbidden(message: str = "No tienes permiso para esta acción.") -> AppError:
    return AppError(403, "FORBIDDEN", message)


def _envelope(status_code: int, code: str, message: str, details: dict | None = None):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError):
        return _envelope(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError):
        fields = [
            {"loc": [str(p) for p in e.get("loc", [])], "msg": e.get("msg", "")}
            for e in jsonable_encoder(exc.errors())
        ]
        return _envelope(400, "INVALID_INPUT", "Revisa los datos enviados.", {"fields": fields})

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException):
        codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 415: "UNSUPPORTED_FILE"}
        code = codes.get(exc.status_code, "HTTP_ERROR")
        return _envelope(exc.status_code, code, str(exc.detail))
