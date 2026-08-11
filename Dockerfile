FROM node:22-alpine AS ui-build

WORKDIR /src
COPY package.json vite.config.js ./
RUN npm install --no-audit --no-fund
COPY app-ui ./app-ui
RUN npm run build

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

RUN groupadd --system app && useradd --system --gid app --uid 10001 app

COPY pyproject.toml README.md ./
COPY app ./app
COPY --from=ui-build /src/app/static ./app/static
RUN pip install --upgrade pip && pip install .

USER 10001
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
