# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

# tzdata — zoneinfo (Asia/Tashkent) uchun zarur.
# PYTHONUNBUFFERED — loglar docker logs'ga darhol tushishi uchun.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DB_PATH=/app/data/exercise_bot.db \
    LOG_FILE=/app/data/bot.log

WORKDIR /app

# Avval faqat requirements — kod o'zgarganda ham layer cache saqlanadi.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ── Build vaqtidagi tekshiruv ────────────────────────────────────────────────
# Kontekst to'liq ko'chirilganiga ishonch hosil qilamiz. Ilgari `handlers/`
# papkasi bo'sh holda image'ga tushib, bot faqat ishga tushganda
# "ImportError: cannot import name 'admin' from 'handlers'" bilan yiqilgan edi.
# Endi bunday image umuman qurilmaydi — xato CI'da, deploy'gacha chiqadi.
RUN set -eux; \
    test -f handlers/__init__.py; \
    test -f handlers/admin.py; \
    test -f handlers/student.py; \
    test -f handlers/teacher.py; \
    BOT_TOKEN=build-check ADMIN_IDS=0 LOG_FILE=/tmp/build.log \
        python -c "import main; print('import tekshiruvi OK')"; \
    rm -f /tmp/build.log

# Root'dan ishlamaymiz. UID 1000 — serverdagi ./data papkasi egasi bilan mos.
RUN useradd --uid 1000 --create-home --shell /bin/bash appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

VOLUME ["/app/data"]

CMD ["python", "main.py"]
