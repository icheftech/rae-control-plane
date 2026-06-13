"""R.A.E. Control Plane - FastAPI Application
Enterprise-Grade AI Governance Platform

Main application entry point for the R.A.E. (Runtime Authority Engine)
Control Plane. Provides REST API endpoints for managing AI agent workflows,
capabilities, connectors, control policies, kill switches, break glass access,
and production change governance.

NIST AI RMF Alignment:
- GOVERN: Organizational structures and accountability
- MAP: Context and risk identification
- MEASURE: Metrics and monitoring
- MANAGE: Risk response and incident handling
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn

from app.db.database import init_db, check_db_connection

# App metadata
VERSION = "0.1.0"
TITLE = "R.A.E. Control Plane API"
DESCRIPTION = """
Enterprise-Grade AI Governance Platform for PHI/PII-compliant AI agent systems.

## Features

### 🗂️ Registry Backbone (NIST MAP)
- **Workflows**: Multi-stage AI agent workflows with approval gates
- **Capabilities**: Reusable agent capabilities with risk classifications
- **Connectors**: External system integrations with credential management

### 🛡️ Controls Framework (NIST MANAGE)
- **Control Policies**: Rule-based governance with ALLOW/DENY/REVIEW outcomes
- **Kill Switches**: Emergency stop mechanisms with scope-based activation
- **Break Glass**: Time-bounded emergency access with mandatory review

### ⚖️ Enforcement Integration (NIST GOVERN)
- **Audit Events**: Cryptographically hash-chained immutable audit trail
- **Enforcement Gates**: Pre-execution policy evaluation checkpoints
- **Change Requests**: Multi-stage approval workflow for production changes

## Compliance

- **NIST AI RMF**: Full framework alignment (GOVERN/MAP/MEASURE/MANAGE)
- **SOC 2**: Type II controls for security and availability
- **HIPAA**: PHI/PII data handling and audit requirements
- **ISO 27001**: Information security management
"""

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize database connection, verify schema
    - Shutdown: Clean up resources
    """
    # Startup
    print("🚀 R.A.E. Control Plane starting up...")
    try:
        if check_db_connection():
            print("✅ Database connection successful")
        else:
            print("⚠️  Database connection failed - check DATABASE_URL")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
    
    yield
    
    # Shutdown
    print("🛑 R.A.E. Control Plane shutting down...")

# Create FastAPI application
app = FastAPI(
    title=TITLE,
    description=DESCRIPTION,
    version=VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS Middleware
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Register API routers
from app.api import workflows, capabilities, connectors, control_policies, kill_switches, change_requests, llm, tenants

app.include_router(workflows.router, prefix="/api")
app.include_router(capabilities.router, prefix="/api")
app.include_router(connectors.router, prefix="/api")
app.include_router(control_policies.router, prefix="/api")
app.include_router(kill_switches.router, prefix="/api")
app.include_router(change_requests.router, prefix="/api")
app.include_router(tenants.router, prefix="/api")
app.include_router(llm.router)  # LLM chat completions endpoint

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    db_healthy = check_db_connection()
    return {
        "status": "healthy" if db_healthy else "degraded",
        "version": VERSION,
        "database": "connected" if db_healthy else "disconnected",
    }

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """API root endpoint with service information."""
    return {
        "service": "R.A.E. Control Plane",
        "version": VERSION,
        "description": "Enterprise-Grade AI Governance Platform",
        "docs": "/api/docs",
        "health": "/health",
    }

# Version endpoint
@app.get("/version", tags=["Version"])
async def get_version():
    """Get API version information."""
    return {
        "version": VERSION,
        "service": "R.A.E. Control Plane",
    }

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url),
        },
    )

# Development server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
