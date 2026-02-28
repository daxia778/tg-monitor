# ────────── Stage 1: Build ──────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src/ ./src/

# Install project into a target directory for copying
RUN pip install --no-cache-dir --prefix=/install .

# ────────── Stage 2: Runtime ──────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install minimal runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY src/ ./src/
COPY config.example.yaml ./config.example.yaml

# Create data directory
RUN mkdir -p /app/data

# Expose dashboard port
EXPOSE 8050

# Shell entrypoint: auto-copy example config if no config.yaml is mounted
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["start", "dashboard"]
