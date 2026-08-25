FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder

# Settings for faster container start
ENV UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=0 UV_LINK_MODE=copy

WORKDIR /app
COPY pyproject.toml LICENSE.txt *.md uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-alpine AS runtime

# ENV TEAMS_APP_ID="" TEAMS_APP_PASSWORD="" TEAMS_APP_TYPE="" TEAMS_APP_TENANT_ID="" TEAM_ID="" TEAMS_CHANNEL_ID=""

LABEL \
  org.opencontainers.image.vendor="Industria de Diseño Textil, S.A." \
  org.opencontainers.image.source="https://github.com/InditexTech/mcp-teams-server" \
  org.opencontainers.image.authors="Open Source Office Team" \
  org.opencontainers.image.title="MCP Teams Server" \
  org.opencontainers.image.description="MCP Teams Server container image" \
  org.opencontainers.image.licenses="Apache-2.0"

ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

RUN addgroup -S nonroot \
    && adduser -S nonroot -G nonroot

USER nonroot

ENTRYPOINT ["mcp-teams-server"]
