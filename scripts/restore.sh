#!/usr/bin/env bash
# Restaura un respaldo de scripts/backup.sh sobre la pila de producción.
# REEMPLAZA la base de datos, los archivos y el índice actuales.
#
#   scripts/restore.sh /var/backups/lexi/20261106-030000
#   scripts/restore.sh --latest            # el respaldo completo más reciente
#   scripts/restore.sh --latest --yes      # sin pedir confirmación
#
# Antes de restaurar en el servidor real, prueba el respaldo con scripts/restore-test.sh.

# shellcheck source=prod-env.sh
source "$(dirname "$0")/prod-env.sh"

src="" yes=0
for arg in "$@"; do
  case "$arg" in
    --latest) src="$(latest_backup)" ;;
    --yes) yes=1 ;;
    *) src="$arg" ;;
  esac
done
[[ -n "$src" && -d "$src" ]] || die "Uso: $0 <carpeta-de-respaldo> | --latest [--yes]"
src="$(cd "$src" && pwd)"

log "Verificando $src"
verify_checksums "$src"

if [[ "$yes" -ne 1 ]]; then
  echo "Esto BORRA los datos actuales de producción y los reemplaza por $src."
  read -r -p "Escribe RESTAURAR para continuar: " answer
  [[ "$answer" == "RESTAURAR" ]] || die "Cancelado."
fi

log "Deteniendo web y API (el sitio mostrará un error mientras tanto)"
"${COMPOSE[@]}" stop web api

log "1/3 Base de datos"
"${COMPOSE[@]}" exec -T postgres sh -c \
  'dropdb -U "$POSTGRES_USER" --if-exists --force "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
"${COMPOSE[@]}" exec -T postgres \
  sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --exit-on-error' < "$src/db.dump"

log "2/3 Evidencias y documentos"
"${COMPOSE[@]}" run --rm --no-deps -T --entrypoint sh api \
  -c 'find /data/storage -mindepth 1 -delete && tar -C /data/storage -xzf -' < "$src/storage.tar.gz"

log "3/3 Índice del asistente"
"${COMPOSE[@]}" stop qdrant
"${COMPOSE[@]}" run --rm --no-deps -T --entrypoint sh qdrant \
  -c 'find /qdrant/storage -mindepth 1 -delete && tar -C /qdrant/storage -xzf -' < "$src/qdrant.tar.gz"

log "Levantando la pila"
"${COMPOSE[@]}" up -d
log "Restauración terminada. Entra al sitio y revisa el panel y una evidencia."
