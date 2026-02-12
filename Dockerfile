FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock ./
COPY core/pyproject.toml ./core/
COPY tools/pyproject.toml ./tools/

# Copy source code
COPY . .
RUN dos2unix hive

# Install dependencies
RUN uv sync --frozen

# Install Playwright browsers
RUN uv run python -m playwright install chromium --with-deps

# Set environment variables
ENV PYTHONPATH="/app/core:/app/exports:/app"
ENV PATH="/app/.venv/bin:/app:$PATH"

# Create entrypoint script to handle line endings
RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'if [ -f /app/hive ]; then dos2unix -q /app/hive; fi' >> /entrypoint.sh && \
    echo 'exec "$@"' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Default command to run the TUI
ENTRYPOINT ["/entrypoint.sh", "uv", "run", "hive"]
CMD ["tui"]
