#!/bin/sh
# Konteyner root sifatida boshlanadi, faqat ma'lumotlar papkasi egaligini
# tuzatadi va darhol appuser (UID 1000) ga tushadi.
#
# Sabab: Docker faqat YANGI va bo'sh named volume ga image dagi egalikni
# ko'chiradi. Eskidan qolgan volume (masalan ilgari boshqa yo'lga ulangan
# bo'lsa) root ga tegishli bo'lib qoladi va konteyner unga yozolmaydi.
# Buni har safar qo'lda `docker run ... chown` bilan tuzatish o'rniga
# shu yerda avtomatik qilamiz.
set -e

APP_UID=1000
APP_GID=1000
DATA_DIR="$(dirname "${DB_PATH:-/app/data/exercise_bot.db}")"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$DATA_DIR"
    if [ "$(stat -c %u "$DATA_DIR")" != "$APP_UID" ]; then
        echo "🔧 $DATA_DIR egasi tuzatilmoqda -> ${APP_UID}:${APP_GID}"
        chown -R "${APP_UID}:${APP_GID}" "$DATA_DIR"
    fi
    exec gosu "${APP_UID}:${APP_GID}" "$@"
fi

# Allaqachon root emas (masalan compose da `user:` ko'rsatilgan) — shundoq ishlaymiz.
exec "$@"
