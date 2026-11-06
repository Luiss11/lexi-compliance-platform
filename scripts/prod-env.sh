#!/usr/bin/env bash
# Configuración común de los scripts de producción (backup, restore, restore-test).
# Se carga con "source"; no se ejecuta solo.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env.prod ]]; then
  echo "No existe .env.prod en $ROOT. Cópialo de .env.prod.example (ver docs/INSTALACION_PRODUCCION.md)." >&2
  exit 1
fi

# Carga BACKUP_DIR, BACKUP_KEEP_DAYS, BACKUP_REMOTE, etc.
set -a
# shellcheck disable=SC1091
. ./.env.prod
set +a

BACKUP_DIR="${BACKUP_DIR:-/var/backups/lexi}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
BACKUP_REMOTE="${BACKUP_REMOTE:-}"

# Rutas relativas a $ROOT (ya hicimos cd ahí arriba)
COMPOSE=(docker compose -f docker-compose.prod.yml --env-file .env.prod)

# Solo afecta a Git Bash en Windows (pruebas locales): evita que convierta rutas como
# /data/storage en rutas de Windows al pasarlas a docker. En Linux no hace nada.
export MSYS_NO_PATHCONV=1

log() { echo "[$(date '+%F %T')] $*"; }
die() { log "ERROR: $*" >&2; exit 1; }

# Respaldo más reciente que esté completo (las carpetas *.parcial son copias interrumpidas)
latest_backup() {
  find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name '20*' ! -name '*.parcial' 2>/dev/null \
    | sort | tail -n 1
}

# Comprueba que los archivos del respaldo no se dañaron desde que se crearon
verify_checksums() {
  local dir="$1"
  [[ -f "$dir/SHA256SUMS" ]] || die "$dir no tiene SHA256SUMS; no parece un respaldo completo."
  (cd "$dir" && sha256sum --quiet -c SHA256SUMS) || die "Las sumas SHA-256 de $dir no coinciden: respaldo dañado."
}
