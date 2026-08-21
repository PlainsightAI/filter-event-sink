# syntax=docker/dockerfile:1.4
FROM python:3.14-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pip + filter-event-sink at version from VERSION file
RUN --mount=type=bind,source=VERSION,target=/tmp/VERSION,ro \
    set -eux; \
    RAW="$(head -n1 /tmp/VERSION)"; \
    PKG_VERSION="$(printf '%s' "$RAW" | tr -d ' \t\r\n' | sed 's/^[vV]//')"; \
    [ -n "$PKG_VERSION" ] || { echo "VERSION file is empty"; exit 1; }; \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "filter-event-sink==${PKG_VERSION}"

# openfilter-base = python:3.14-slim + all outstanding Debian security patches
# (rebuilt weekly): provides the PYTHONDONTWRITEBYTECODE/PYTHONUNBUFFERED env, the
# appuser account, and /app (WORKDIR) + /app/logs — so none of that is repeated here.
FROM plainsightai/openfilter-base:py3.14

USER appuser

COPY --from=builder /usr/local /usr/local

CMD ["python", "-m", "filter_event_sink.filter"]
