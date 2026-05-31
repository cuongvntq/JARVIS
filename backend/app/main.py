"""FastAPI application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.errors import (
    JarvisError,
    RequestIDMiddleware,
    jarvis_exception_handler,
    validation_exception_handler,
)
from app.routers import auth, chat, health, memories, notes, todos

settings = get_settings()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("jarvis.startup", env=settings.app_env, version="0.1.0")
    yield
    log.info("jarvis.shutdown")


app = FastAPI(
    title="J.A.R.V.I.S Backend API",
    version="0.1.0",
    description="Personal AI Assistant — MVP 1",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware (order matters — RequestID first so handlers can read it)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(JarvisError, jarvis_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Routers
app.include_router(health.router, prefix="", tags=["health"])
app.include_router(auth.router, prefix="", tags=["auth"])
app.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
app.include_router(todos.router, prefix="/v1/todos", tags=["todos"])
app.include_router(notes.router, prefix="/v1/notes", tags=["notes"])
app.include_router(memories.router, prefix="/v1/memories", tags=["memories"])


@app.get("/")
async def root():
    return {
        "name": "jarvis-backend",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
