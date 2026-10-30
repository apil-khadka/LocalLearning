.PHONY: setup check test build books-pilot books-more books-cdc-k12 books-import-k12 education-up education-down
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
books-cdc-k12:
	python scripts/fetch_cdc_k12_books.py
books-import-k12:
	docker compose exec api .venv/bin/python -m app.library_import --manifest /private-cdc-books/catalog.json --data-dir /data
education-up:
	docker compose --profile education up -d kolibri
	python3 scripts/bootstrap_kolibri.py
education-down:
	docker compose --profile education stop kolibri
