#!/usr/bin/env bash
# Respaldo completo de producción: base de datos, archivos (evidencias y PDFs) e índice del
# asistente (Qdrant). Pensado para correr cada noche con cron:
#
#   0 3 * * *  /opt/lexi/scripts/backup.sh >> /var/log/lexi-backup.log 2>&1
#
# Deja una carpeta por respaldo en $BACKUP_DIR (por defecto /var/backups/lexi):
#   20261106-030000/
#     db.dump          pg_dump en formato custom (se restaura con pg_restore)
#     storage.tar.gz   STORAGE_DIR completo: evidencias selladas y PDFs normativos
#     qdrant.tar.gz    índice vectorial (si se pierde, el asistente no encuentra la normativa)
#     SHA256SUMS       para detectar un respaldo dañado antes de restaurarlo
#
# Borra los respaldos de más de $BACKUP_KEEP_DAYS días. Si BACKUP_REMOTE está definido,
# copia además el respaldo fuera del servidor con rclone (ver la guía de instalación).

# shellcheck source=prod-env.sh
source "$(dirname "$0")/prod-env.sh"

stamp="$(date +%Y%m%d-%H%M%S)"
dest="$BACKUP_DIR/$stamp"
tmp="$dest.parcial"
mkdir -p "$tmp"
chmod 700 "$BACKUP_DIR" "$tmp"

log "Respaldo $stamp → $dest"

log "1/3 Base de datos"
"${COMPOSE[@]}" exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$tmp/db.dump"
[[ -s "$tmp/db.dump" ]] || die "pg_dump no produjo datos."

log "2/3 Evidencias y documentos"
"${COMPOSE[@]}" exec -T api tar -C /data/storage -czf - . > "$tmp/storage.tar.gz"

log "3/3 Índice del asistente (Qdrant se detiene unos segundos para copiarlo consistente)"
restart_qdrant() { "${COMPOSE[@]}" start qdrant >/dev/null 2>&1 || true; }
trap restart_qdrant EXIT
"${COMPOSE[@]}" stop qdrant >/dev/null 2>&1
"${COMPOSE[@]}" run --rm --no-deps -T --entrypoint tar qdrant \
  -C /qdrant/storage -czf - . > "$tmp/qdrant.tar.gz"
restart_qdrant
trap - EXIT

(cd "$tmp" && sha256sum db.dump storage.tar.gz qdrant.tar.gz > SHA256SUMS)
mv "$tmp" "$dest"
log "Listo: $(du -sh "$dest" | cut -f1)"

if [[ -n "$BACKUP_REMOTE" ]]; then
  log "Copiando fuera del servidor a $BACKUP_REMOTE/$stamp"
  rclone copy "$dest" "$BACKUP_REMOTE/$stamp"
fi

# Retención: respaldos viejos y copias que quedaron a medias
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name '20*' ! -name '*.parcial' \
  -mtime +"$BACKUP_KEEP_DAYS" -exec rm -rf {} +
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name '*.parcial' -mtime +1 -exec rm -rf {} +
log "Respaldos conservados: $(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name '20*' ! -name '*.parcial' | wc -l)"
