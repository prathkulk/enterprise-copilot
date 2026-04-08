from contextlib import asynccontextmanager
import logging
from logging import getLogger
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.core.config import get_settings
from backend.app.core.observability import (
    REQUEST_ID_HEADER,
    bind_request_id,
    configure_logging,
    generate_request_id,
    log_event,
    reset_request_id,
)
from backend.app.db.session import initialize_database

settings = get_settings()
logger = getLogger("enterprise_copilot.http")

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get(REQUEST_ID_HEADER) or generate_request_id()
    request.state.request_id = request_id
    token = bind_request_id(request_id)
    started_at = perf_counter()

    log_event(
        logger,
        logging.INFO,
        "request.started",
        method=request.method,
        path=request.url.path,
        query=request.url.query or None,
    )

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = round((perf_counter() - started_at) * 1000, 3)
        log_event(
            logger,
            logging.ERROR,
            "request.failed",
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms,
            error=str(exc),
        )
        reset_request_id(token)
        raise

    duration_ms = round((perf_counter() - started_at) * 1000, 3)
    response.headers[REQUEST_ID_HEADER] = request_id
    log_event(
        logger,
        logging.INFO,
        "request.completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    reset_request_id(token)
    return response


app.include_router(api_router)
