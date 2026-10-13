.PHONY: up down logs migrate seed dev-web dev-api test lint fmt

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
