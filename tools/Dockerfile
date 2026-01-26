# Aden Tools MCP Server
# Multi-stage build with uv for optimal performance and size

# Stage 1: Builder
# Use official uv image with Python 3.11 on Debian bookworm-slim
FROM ghcr.io/astral-sh/uv:0.5.11-python3.11-bookworm-slim AS builder

# Set uv environment variables for optimization
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Copy workspace configuration files for dependency resolution
# Order matters: copy dependency manifests first for better layer caching
COPY pyproject.toml uv.lock ./
COPY tools/pyproject.toml tools/README.md tools/
COPY core/pyproject.toml core/README.md core/

# Copy application source code early to satisfy build requirements
COPY tools/src ./tools/src
COPY tools/mcp_server.py ./tools/
COPY core/framework ./core/framework

# Install all dependencies and the project
# Using --frozen to ensure reproducible builds with lock file
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Stage 2: Runtime
# Use minimal Python runtime (no uv needed in final image)
FROM python:3.11-slim-bookworm

WORKDIR /app

# Create non-root user for security (must be done before COPY --chown)
RUN useradd -m -u 1001 appuser && \
    mkdir -p /app/workdir/workspaces

# Copy only the virtual environment and application from builder
# This excludes uv and build artifacts, keeping image small
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/tools /app/tools
COPY --from=builder --chown=appuser:appuser /app/core /app/core

# Set ownership of all app directories
RUN chown -R appuser:appuser /app

USER appuser

# Add venv to PATH so Python can find installed packages
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Declare volume for workspace persistence across container runs
VOLUME ["/app/workdir/workspaces"]

# Expose MCP server port
EXPOSE 4001

# Health check - verify server is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:4001/health').raise_for_status()" || exit 1

# Run MCP server
CMD ["python", "tools/mcp_server.py"]
