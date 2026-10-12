FROM python:3.12-slim

WORKDIR /app

# Disable FastMCP's startup update check; the container has no need to
# reach PyPI at runtime
ENV FASTMCP_CHECK_FOR_UPDATES=off

# Install git for cloning the strimzi.github.io repository
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/
COPY data/ data/

# Install dependencies from the committed lockfile, baking them into the
# image at build time
RUN uv sync --locked --no-dev

# Build the index at container build time
RUN uv run --no-sync strimzi-docs-index index

# Run the MCP server directly from the baked venv so no dependency
# resolution happens on container start
EXPOSE 8000

CMD ["/app/.venv/bin/mcp-strimzi-docs"]
