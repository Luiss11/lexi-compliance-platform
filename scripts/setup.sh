#!/usr/bin/env bash
# Prepara el entorno local por primera vez.
set -euo pipefail
command -v docker >/dev/null || { echo "Instala Docker 24+"; exit 1; }
command -v node >/dev/null || { echo "Instala Node 20 LTS"; exit 1; }
command -v python3 >/dev/null || { echo "Instala Python 3.11"; exit 1; }

[ -f .env ] || cp .env.example .env && echo ".env creado: completa OPENAI_API_KEY y JWT_SECRET"

(cd apps/web && npm install)
(cd services/api && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt)

docker compose up -d postgres qdrant
echo "Listo. Ejecuta: make up && make migrate && make seed"
