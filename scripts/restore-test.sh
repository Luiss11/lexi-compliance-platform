#!/usr/bin/env bash
# Prueba que un respaldo SE PUEDE restaurar, sin tocar producción.
#
#   scripts/restore-test.sh --latest
#   scripts/restore-test.sh /var/backups/lexi/20261106-030000
#
# Qué hace:
#   1. Verifica las sumas SHA-256 del respaldo.
#   2. Restaura db.dump en un Postgres temporal y desechable (no expone puertos).
#   3. Descomprime storage.tar.gz en una carpeta temporal y comprueba que CADA evidencia y
#      CADA PDF registrados en la base existen y que su SHA-256 coincide con el sellado.
#   4. Comprueba que el índice de Qdrant se puede leer.
# Sale con código 1 si algo falla. Programa una corrida semanal en cron (ver la guía):
#
#   30 4 * * 0  /opt/lexi/scripts/restore-test.sh --latest >> /var/log/lexi-backup.log 2>&1

# shellcheck source=prod-env.sh
source "$(dirname "$0")/prod-env.sh"

src=""
for arg in "$@"; do
  case "$arg" in
    --latest) src="$(latest_backup)" ;;
    *) src="$arg" ;;
  esac
done
[[ -n "$src" && -d "$src" ]] || die "Uso: $0 <carpeta-de-respaldo> | --latest"
src="$(cd "$src" && pwd)"

pg="lexi-restore-test-$$"
work="$(mktemp -d)"
cleanup() { docker rm -f "$pg" >/dev/null 2>&1 || true; rm -rf "$work"; }
trap cleanup EXIT

log "Probando $src"
verify_checksums "$src"
log "OK  sumas SHA-256"

docker run -d --rm --name "$pg" -e POSTGRES_USER=lexi -e POSTGRES_PASSWORD=prueba \
  -e POSTGRES_DB=lexi pgvector/pgvector:pg16 >/dev/null
# -h 127.0.0.1: durante la inicialización solo escucha por socket; esperamos al arranque final
for _ in $(seq 60); do
  docker exec "$pg" pg_isready -h 127.0.0.1 -U lexi -q 2>/dev/null && break
  sleep 1
done
docker exec "$pg" pg_isready -h 127.0.0.1 -U lexi -q || die "El Postgres temporal no arrancó."

docker exec -i "$pg" pg_restore -U lexi -d lexi --no-owner --exit-on-error < "$src/db.dump" \
  || die "pg_restore falló: la base del respaldo no se puede restaurar."
sql() { docker exec "$pg" psql -U lexi -d lexi -At -F '|' -c "$1"; }
counts="$(sql "select (select count(*) from tenants), (select count(*) from users),
  (select count(*) from tasks), (select count(*) from evidence_files),
  (select count(*) from documents)")"
IFS='|' read -r n_tenants n_users n_tasks n_evidence n_docs <<< "$counts"
log "OK  base restaurada: $n_tenants organización(es), $n_users usuario(s), $n_tasks tarea(s), $n_evidence evidencia(s), $n_docs documento(s)"
[[ "$n_tenants" -gt 0 ]] || die "La base restaurada no tiene organizaciones: respaldo vacío."

mkdir -p "$work/storage"
tar -C "$work/storage" -xzf "$src/storage.tar.gz" || die "storage.tar.gz no se puede descomprimir."

bad=0
# Cada archivo se ubica igual que en la API: <tenant>/evidence/<id>.<ext> y <tenant>/documents/<id>.pdf
check_file() {  # tipo, patrón, sha esperado
  local kind="$1" pattern="$2" expected="$3" file actual
  file="$(compgen -G "$work/storage/$pattern" | head -n 1 || true)"
  if [[ -z "$file" ]]; then
    log "FALTA  $kind $pattern"; bad=$((bad + 1)); return
  fi
  actual="$(sha256sum "$file" | cut -d' ' -f1)"
  if [[ "$actual" != "$expected" ]]; then
    log "ALTERADO  $kind $pattern"; bad=$((bad + 1))
  fi
}
while IFS='|' read -r tenant id sha; do
  [[ -n "$id" ]] && check_file evidencia "$tenant/evidence/$id.*" "$sha"
done < <(sql 'select t."tenantId", e.id, e.sha256 from evidence_files e join tasks t on t.id = e."taskId"')
while IFS='|' read -r tenant id sha; do
  [[ -n "$id" ]] && check_file documento "$tenant/documents/$id.pdf" "$sha"
done < <(sql 'select "tenantId", id, sha256 from documents')

[[ "$bad" -eq 0 ]] || die "$bad archivo(s) faltan o no coinciden con su SHA-256 sellado."
log "OK  $n_evidence evidencia(s) y $n_docs documento(s) presentes y con SHA-256 íntegro"

tar -tzf "$src/qdrant.tar.gz" | grep -q '^\./collections' \
  || die "qdrant.tar.gz no contiene colecciones."
log "OK  índice de Qdrant legible"

log "RESTAURACIÓN PROBADA: el respaldo $(basename "$src") es utilizable."
