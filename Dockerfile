FROM node:22-alpine AS frontend-builder

WORKDIR /frontend/react-app

COPY frontend/react-app/package.json frontend/react-app/package-lock.json ./
RUN npm install --no-audit --no-fund

COPY frontend/react-app/ ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src
COPY frontend/react-app/package.json ./frontend/react-app/package.json
COPY --from=frontend-builder /frontend/react-app/build ./frontend/react-app/build

EXPOSE 8000

CMD ["python", "-m", "src.main"]
