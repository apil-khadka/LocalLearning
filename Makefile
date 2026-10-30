.PHONY: setup check test build books-pilot books-more education-up education-down
setup:
	uv sync --project backend --locked
	npm ci --prefix frontend
check:
	uv run --project backend ruff check backend scripts
	uv run --project backend ruff format --check backend scripts
	npm run check --prefix frontend
test:
	cd backend && uv run pytest -q
	npm run test:e2e --prefix frontend
build:
	npm run build --prefix frontend
	docker compose build
books-pilot:
	python scripts/fetch_wikijunior_biology.py
books-more:
	python scripts/fetch_wikibooks_books.py $(BOOKS)
education-up:
	docker compose --profile education up -d --wait
education-down:
	docker compose --profile education stop kolibri
