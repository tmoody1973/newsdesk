# The worker. A run is ~5 minutes of wall clock, so it cannot be a serverless
# function; this is the container the web app posts a story to.
#
# Two things in here are load-bearing and both fail SILENTLY if they are wrong,
# which is why /health checks them at boot rather than leaving them to be
# discovered by watching a finished video:
#
#   1. ffmpeg must be built with libass, or the `subtitles` filter does not
#      exist and captions do not burn. Debian's ffmpeg IS built with it — the
#      trap documented in HANDOFF.md is Homebrew's core bottle on macOS, which
#      is not. Nothing clever is needed here, but it must not be swapped for a
#      minimal static build without checking.
#   2. Anton must be installed and visible to fontconfig. libass falls back to
#      another face without a word, so a missing font is a style regression
#      nobody gets told about. `fc-list` is what assembly.anton_is_resolvable()
#      shells out to, so fontconfig has to be present too.

FROM python:3.12-slim-bookworm

# ffmpeg  — with libass, hence the `subtitles` filter
# fontconfig — provides fc-list and fc-cache
# fonts-liberation — a sane fallback so a miss is legible rather than tofu
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        fontconfig \
        fonts-liberation \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Anton, from Google Fonts. Tracks `main` rather than a pinned commit — stated
# plainly because it is a real, accepted risk: an upstream retouch would change
# the caption face between two runs whose receipts both name the same brand kit.
# Pin it to a SHA before this is anything but a hackathon build.
#
# The `fc-list | grep` is not decoration. It fails the BUILD if the font did not
# land, which is the only place this can be caught loudly — at runtime libass
# substitutes another face and says nothing.
RUN curl -fsSL -o /usr/share/fonts/truetype/Anton-Regular.ttf \
      "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf" \
    && fc-cache -f \
    && fc-list | grep -i anton

WORKDIR /app

# uv for the same resolution the project is developed against.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Dependencies before source, so a code change does not re-resolve the world.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY newsdesk ./newsdesk
COPY scripts ./scripts
RUN uv sync --frozen --no-dev

# The brand kit and stories are read from B2 at runtime, not baked in — a run
# styled by an unpublished kit is the failure brandkit.py refuses to allow.

ENV PORT=8080 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# Fails the deploy if this image cannot burn a caption.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8080/health | grep -q '"ok": true' || exit 1

CMD ["python", "-m", "newsdesk.server"]
