.PHONY: setup check test build
setup:
	uv sync --project backend --locked
	npm ci --prefix frontend
check:
	uv run --project backend ruff check backend
	uv run --project backend ruff format --check backend
	npm run check --prefix frontend
test:
	cd backend && uv run pytest -q
	npm run test:e2e --prefix frontend
build:
	npm run build --prefix frontend
	docker compose build
