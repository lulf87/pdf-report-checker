"""
FastAPI Application Entry Point
Provides REST API for report verification and comparison.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_config import setup_logging
from app.routers import ptr_compare, report_check

# Configure logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")


# Initialize FastAPI application
app = FastAPI(
    title="Report Checker Pro API",
    description="Backend service for report verification and comparison using OCR and LLM",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ptr_compare.router)
app.include_router(report_check.router)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "healthy", "service": "report-checker-pro-backend"}
