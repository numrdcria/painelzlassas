FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/instance

EXPOSE 8000

CMD ["sh", "-lc", "python scripts/init_db.py && gunicorn -b 0.0.0.0:${PORT:-8000} wsgi:app"]
