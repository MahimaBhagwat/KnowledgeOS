from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_422_UNPROCESSABLE_ENTITY

from app.api.router import api_router
from app.core.logging import configure_logging, get_logger

load_dotenv()

configure_logging()
logger = get_logger(__name__)

app = FastAPI(title="KnowledgeOS Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    configure_logging()
    logger.info("Starting KnowledgeOS backend application")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning(
        "HTTP exception occurred: %s %s",
        exc.status_code,
        exc.detail,
        extra={"path": request.url.path},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(
        "Validation error on request: %s",
        request.url.path,
        extra={"errors": exc.errors()},
    )
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unexpected error while processing request: %s",
        request.url.path,
    )
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."},
    )


@app.get("/health", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
