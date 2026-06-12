# S.S.O. Control Plane - Production Dockerfile
# Multi-stage build for optimal image size and security

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 rae && chown -R rae:rae /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/rae/.local

# Copy application code
COPY --chown=rae:rae backend/app /app/app
COPY --chown=rae:rae backend/migrations /app/migrations
COPY --chown=rae:rae backend/alembic.ini /app/

# Switch to non-root user
USER rae

# Add local Python packages to PATH
ENV PATH=/home/rae/.local/bin:$PATH

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
