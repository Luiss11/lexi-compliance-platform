.PHONY: up down logs migrate seed dev-web dev-api test lint fmt \n	prod-up prod-down prod-logs prod-ps backup restore-test

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api web

migrate:
	docker compose exec web npx prisma migrate deploy

seed:
	docker compose exec web npx prisma db seed

dev-web:
	cd apps/web && npm install && npm run dev

dev-api:
	cd services/api && python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt && uvicorn app.main:app --reload --port 8000

test:
	cd services/api && pytest -q
	cd apps/web && npm run lint

lint:
	cd services/api && ruff check app tests
	cd apps/web && npm run lint

fmt:
	cd services/api && ruff format app tests

# ---------- Producción (ver docs/INSTALACION_PRODUCCION.md) ----------
PROD = docker compose -f docker-compose.prod.yml --env-file .env.prod

prod-up:
	$(PROD) up -d --build

prod-down:
	$(PROD) down

prod-logs:
	$(PROD) logs -f --tail=100 caddy web api

prod-ps:
	$(PROD) ps

backup:
	scripts/backup.sh

restore-test:
	scripts/restore-test.sh --latest
