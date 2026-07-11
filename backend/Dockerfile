FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

RUN uv run python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
