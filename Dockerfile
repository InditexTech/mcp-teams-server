FROM ghcr.io/astral-sh/uv:python3.12-alpine

# ENV TEAMS_APP_ID="" TEAMS_APP_PASSWORD="" TEAMS_APP_TYPE="" TEAMS_APP_TENANT_ID="" TEAM_ID="" TEAMS_CHANNEL_ID=""

LABEL \
  org.opencontainers.image.vendor="Industria de Diseño Textil, S.A." \
  org.opencontainers.image.source="https://github.com/InditexTech/mcp-teams-server" \
  org.opencontainers.image.authors="Open Source Office Team" \
  org.opencontainers.image.title="MCP Teams Server" \
  org.opencontainers.image.description="MCP Teams Server container image" \
  org.opencontainers.image.licenses="Apache-2.0"

# Settings for faster container start
ENV UV_COMPILE_BYTECODE=0 UV_PYTHON_DOWNLOADS=0 UV_LINK_MODE=copy

COPY pyproject.toml LICENSE.txt *.md uv.lock src /app/
WORKDIR /app
RUN uv sync --frozen --no-dev

RUN addgroup -S nonroot \
    && adduser -S nonroot -G nonroot

USER nonroot

CMD ["uv", "run", "--no-build", "--frozen", "--no-dev", "mcp-teams-server"]
