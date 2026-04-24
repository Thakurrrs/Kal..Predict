"""FastAPI application exposing read-only UI endpoints."""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from kal_predict.api.routes import router as ui_router
from kal_predict.api.routes import trial_router


def _error(error_code: str, message: str, details: object = None) -> dict:
    payload = {
        "ok": False,
        "error_code": error_code,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": "api-validation",
    }
    if details is not None:
        payload["details"] = details
    return payload


def create_app() -> FastAPI:
    app = FastAPI(title="Kal..Predict UI API", version="0.1.0")
    app.include_router(ui_router)
    app.include_router(trial_router)

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(_request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error(
                "validation_error",
                "Request payload failed validation.",
                details=exc.errors(),
            ),
        )

    @app.api_route("/api/ui/{path:path}", methods=["POST", "PUT", "PATCH", "DELETE"])
    async def reject_mutation(path: str) -> JSONResponse:  # pragma: no cover - route guard
        return JSONResponse(
            status_code=405,
            content=_error("method_not_allowed", "UI API is read-only. Use GET endpoints only."),
        )

    return app


app = create_app()
