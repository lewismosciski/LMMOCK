FROM python:3.12-slim

LABEL org.opencontainers.image.title="LMMock" \
      org.opencontainers.image.description="Visual mock server for OpenAI and Anthropic APIs" \
      org.opencontainers.image.source="https://github.com/lewismosciski/LMMOCK" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LMMOCK_HOST=0.0.0.0 \
    LMMOCK_PORT=17321 \
    LMMOCK_DATA_DIR=/data \
    LMMOCK_NO_BROWSER=1

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 lmmock \
    && mkdir -p /data \
    && chown -R lmmock:lmmock /app /data

USER lmmock
EXPOSE 17321
VOLUME ["/data"]
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:17321/healthz')"

CMD ["lmmock"]
