# ClosedPaw - Zero-Trust AI Assistant
# Production-ready Docker image with security hardening

# ============================================
# Stage 1: Backend Builder
# ============================================
FROM python:3.11-slim AS backend-builder

WORKDIR /app/backend

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================
# Stage 2: Frontend Builder
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps

# Build frontend
COPY frontend/ ./
RUN npm run build

# ============================================
# Stage 3: Production Image
# ============================================
FROM python:3.11-slim AS production

# Security: Create non-root user
RUN groupadd -r closedpaw && useradd -r -g closedpaw closedpaw

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=backend-builder /root/.local /home/closedpaw/.local
ENV PATH=/home/closedpaw/.local/bin:$PATH

# Copy backend
COPY --chown=closedpaw:closedpaw backend/ ./backend/

# Copy frontend build
COPY --from=frontend-builder --chown=closedpaw:closedpaw /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder --chown=closedpaw:closedpaw /app/frontend/public ./frontend/public
COPY --from=frontend-builder --chown=closedpaw:closedpaw /app/frontend/package*.json ./frontend/
COPY --from=frontend-builder --chown=closedpaw:closedpaw /app/frontend/node_modules ./frontend/node_modules

# Create config directory
RUN mkdir -p /home/closedpaw/.config/closedpaw && \
    chown -R closedpaw:closedpaw /home/closedpaw/.config

# Security: Set read-only filesystem for app
# RUN chmod -R 555 /app

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OLLAMA_HOST=host.docker.internal:11434 \
    FRONTEND_PORT=3000 \
    BACKEND_PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

# Expose ports
EXPOSE 3000 8000

# Switch to non-root user
USER closedpaw

# Start script
COPY docker/entrypoint.sh /entrypoint.sh
USER root
RUN chmod +x /entrypoint.sh
USER closedpaw

ENTRYPOINT ["/entrypoint.sh"]
