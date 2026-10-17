#!/usr/bin/env bash
# AV zaxirasi: PostgreSQL (pg_dump -Fc) + MEDIA_ROOT (tar.gz) -> /var/backups/av/YYYY-MM-DD.*
# Ma'lumotlar bazasi parol/manzili .env dagi DATABASE_URL dan olinadi (skriptda qattiq yozilmagan).
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/av/app}"
ENV_FAYL="${ENV_FAYL:-$APP_DIR/.env}"
ZAXIRA_DIR="${ZAXIRA_DIR:-/var/backups/av}"

[ -r "$ENV_FAYL" ] || { echo "backup: $ENV_FAYL o'qilmadi" >&2; exit 1; }

# DATABASE_URL va MEDIA_ROOT ni .env dan PG* o'zgaruvchilariga ajratish (parol buyruq qatorida ko'rinmasin).
ENV_KOD="$(python3 - "$ENV_FAYL" <<'PY'
import shlex, sys
from urllib.parse import unquote, urlparse

qiymat = {}
for qator in open(sys.argv[1], encoding="utf-8"):
    qator = qator.strip()
    if qator and not qator.startswith("#") and "=" in qator:
        k, v = qator.split("=", 1)
        qiymat[k.strip()] = v.strip().strip("'\"")
if not qiymat.get("DATABASE_URL"):
    sys.exit("backup: .env da DATABASE_URL yo'q")
u = urlparse(qiymat["DATABASE_URL"])
for nom, v in (
    ("PGHOST", u.hostname or "localhost"),
    ("PGPORT", str(u.port or 5432)),
    ("PGUSER", unquote(u.username or "")),
    ("PGPASSWORD", unquote(u.password or "")),
    ("PGDATABASE", u.path.lstrip("/")),
    ("MEDIA_ROOT", qiymat.get("MEDIA_ROOT", "/var/lib/av/media")),
):
    print(f"export {nom}={shlex.quote(v)}")
PY
)"
eval "$ENV_KOD"

mkdir -p "$ZAXIRA_DIR"
SANA="$(date +%F)"

# Yarim qolgan fayl zaxira bo'lib qolmasin: avval .tmp ga yozib, so'ng nomini almashtiramiz.
pg_dump -Fc -f "$ZAXIRA_DIR/$SANA.dump.tmp"
mv "$ZAXIRA_DIR/$SANA.dump.tmp" "$ZAXIRA_DIR/$SANA.dump"

if [ -d "$MEDIA_ROOT" ]; then
    tar -czf "$ZAXIRA_DIR/$SANA.media.tar.gz.tmp" -C "$MEDIA_ROOT" .
else
    tar -czf "$ZAXIRA_DIR/$SANA.media.tar.gz.tmp" -T /dev/null
fi
mv "$ZAXIRA_DIR/$SANA.media.tar.gz.tmp" "$ZAXIRA_DIR/$SANA.media.tar.gz"

# 14 kundan eskisini o'chirish
find "$ZAXIRA_DIR" -maxdepth 1 -type f \( -name '*.dump' -o -name '*.media.tar.gz' \) -mtime +14 -delete

echo "backup: tayyor -> $ZAXIRA_DIR/$SANA.*"
