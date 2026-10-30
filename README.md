# Digital Himalaya

An offline-first learning portal for school networks in Nepal, with local books, Wikipedia, video lessons, and an optional textbook-grounded AI tutor.

**Status: working software foundation, not a field-validated school deployment.**
AI starts disabled.
Model inference, curriculum quality, Nepali language quality, school Wi-Fi capacity, and power recovery must pass the [deployment acceptance checks](docs/DEMO_SCRIPT.md) on the actual hardware.

[Project website](https://apil-khadka.github.io/LocalLearning/) · [Build plan](docs/BUILD_PLAN.md) · [Architecture](docs/ARCHITECTURE.md) · [Network design](docs/NETWORK.md) · [Verification](docs/VERIFICATION.md)

## What is here

- A responsive React/TypeScript portal with English and Nepali interface text.
- A FastAPI API with Ollama chat/embedding adapters and a dedicated Qdrant curriculum collection.
- Protected PDF/text ingestion, page-aware chunks, real retrieval metadata, and safe no-match responses.
- A persistent local textbook catalog, file delivery, and staff diagnostics.
- Separate student and staff reverse-proxy listeners, container packaging, and automated checks.
- A static project website for GitHub Pages, independent of the school application.

There are no scripted AI answers in the application.
Unconfigured or unavailable services are reported honestly.
No student accounts, chat database, analytics, CDN assets, or cloud model API are required.
The source planning attachments are private local material and are excluded from both Git and Docker builds.

## Run locally

Install Node.js 22.13+ and [uv](https://docs.astral.sh/uv/), then run from the repository root:

```sh
cp .env.example .env
make setup
```

In one terminal:

```sh
cd backend
uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

In another:

```sh
npm run dev --prefix frontend
```

Open `http://127.0.0.1:5173`.
The development server proxies `/api` to port 8000.
If that port is occupied, choose another API port and set `API_PROXY_TARGET=http://127.0.0.1:YOUR_PORT` when starting Vite.
The portal works with empty configuration, showing an empty library and disabled/unconfigured services.

## Connect real local services

Edit the ignored `.env` file with **verified addresses reachable from the API process**:

```dotenv
OLLAMA_BASE_URL=http://LOCAL_MODEL_HOST:11434
QDRANT_URL=http://LOCAL_VECTOR_HOST:6333
OLLAMA_MODEL=qwen3:4b-instruct
EMBED_MODEL=embeddinggemma
```

Replace the host placeholders.
For containers, `localhost` means that container, not the Ubuntu host.
Use a verified container network address or `host.docker.internal` with a properly restricted host service.
Do not duplicate or modify existing NOMAD services.
Provision models and content while online, then disconnect WAN for acceptance.

Set a random staff token of at least 32 characters in `.env` using a password manager or a local generator.
For example, `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'` generates a value to copy into `ADMIN_TOKEN`.
Keep it out of Git, logs and frontend build variables.
In development, open `/staff`, sign in, and import `content/sample/force-and-motion.txt` with grade `8`, subject `Science`, chapter `Force and Motion`, license `CC0-1.0`, and source `Original demonstration note`.
Import requires a working local embedding model and Qdrant.
After teacher review, set `AI_ENABLED=true` and restart the API to test real questions.

Configure `KIWIX_PUBLIC_URL` and `KOLIBRI_PUBLIC_URL` only after opening downloaded content from a student device.
Optional `*_PROBE_URL` values provide a server-reachable equivalent when the public address differs.
A successful HTTP probe proves reachability, not that an article or video was downloaded.

## Run containers

```sh
docker compose build
docker compose up -d --wait
./scripts/check-offline.sh http://127.0.0.1:8090
```

The student portal is `http://127.0.0.1:8090` and staff sign-in is `http://127.0.0.1:8091/staff`.
After the [network policy](docs/NETWORK.md) is installed, set `PORTAL_BIND` to the school server's LAN address, recreate the portal container, and open `http://SERVER_LAN_IP:8090` on a phone connected to school Wi-Fi.
The staff port stays bound to loopback.
Stop with `docker compose down`; content remains in the named volume.
See [installation and backups](docs/INSTALL.md) for staff tunneling, offline provisioning and restoration.

## Test and build

```sh
make check
cd backend && uv run pytest -q
```

From the repository root:

```sh
cd frontend
npx playwright install chromium
npm run test:e2e
npm run build
```

Browser tests run against an isolated API with HTTP contract doubles for local AI services.
Those responses are test fixtures, never part of the deployed product.
For real Qdrant integration, point the test at a disposable local instance:

```sh
cd backend
QDRANT_TEST_URL=http://127.0.0.1:16333 uv run pytest -q
```

Only a unique `dh_test_` collection is created and deleted by that test.
For opt-in actual inference, set `LIVE_OLLAMA_URL`, `LIVE_QDRANT_URL`, and optionally `LIVE_OLLAMA_MODEL`, then run `uv run pytest tests/test_live_services.py -q` from `backend/`.
Ordinary tests skip live inference when those services are not supplied.

## Contributing and licensing

Read [CONTRIBUTING.md](CONTRIBUTING.md) and the [security notes](docs/SECURITY.md).
Software is licensed under [Apache 2.0](LICENSE).
The original sample note uses CC0 1.0; third-party books, models and lessons retain their own licenses.
Do not commit school records, identifiable student information, private planning documents, model weights or copyrighted collections.
