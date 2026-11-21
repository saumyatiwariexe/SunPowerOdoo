from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def error_response(status: int, code: str, message: str, details=None, headers=None):
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or []}},
        headers=headers,
    )


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status, exc.code, exc.message)


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"loc": list(error["loc"]), "message": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    route_name = getattr(request.scope.get("route"), "name", None)
    if route_name == "complete_installation" and any(
        item["type"] == "missing" and item["loc"][-1] in
        {"signature", "started_at", "finished_at", "system_kw", "signed_by_name"} for item in details
    ):
        return error_response(409, "INSTALL_PROOF_REQUIRED", "Complete the installation proof before submitting.", details)
    unprocessable = any(
        item["type"] == "extra_forbidden" or
        (route_name == "submit_enquiry" and item["loc"] in (["body", "phone"], ["body", "pincode"]))
        for item in details
    )
    return error_response(422 if unprocessable else 400, "VALIDATION_ERROR", "Check the submitted fields.", details)


async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
    codes = {401: "UNAUTHENTICATED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
    return error_response(
        exc.status_code, codes.get(exc.status_code, "HTTP_ERROR"), str(exc.detail), headers=exc.headers
    )
