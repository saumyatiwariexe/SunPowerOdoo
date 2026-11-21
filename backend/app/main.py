from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from app.core.config import get_settings
from app.core.errors import AppError, handle_app_error, handle_http_error, handle_validation_error
from app.modules.users.router import router as auth_router
from app.modules.users.service import LoginRateLimiter


def create_app() -> FastAPI:
    app = FastAPI(title="SunPower Solar Installation Management System")
    app.state.login_rate_limiter = LoginRateLimiter()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[get_settings().frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(HTTPException, handle_http_error)

    api = APIRouter(prefix="/api/v1")

    @api.get("/public/health", tags=["public"])
    def health() -> dict[str, dict[str, str]]:
        return {"data": {"status": "ok"}}

    api.include_router(auth_router)

    # Person D routers
    from app.modules.leads.router import router as leads_router
    from app.modules.public.router import router as public_router
    from app.modules.reports.router import router as reports_router
    from app.modules.subsidy.router import router as subsidy_router

    api.include_router(leads_router)
    api.include_router(public_router)
    api.include_router(reports_router)
    api.include_router(subsidy_router)

    app.include_router(api)
    return app


app = create_app()
