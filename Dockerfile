FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY mcp-server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt boto3

COPY mcp-server/ ./mcp-server/
COPY scripts/entrypoint.sh scripts/download-db-from-spaces.py ./scripts/

RUN chmod +x scripts/entrypoint.sh

EXPOSE 8080

# Health check uses the /health route added to the MCP server
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -sf http://localhost:8080/health || exit 1

ENTRYPOINT ["./scripts/entrypoint.sh"]
