# Digital Himalaya

An offline-first learning portal for school networks in Nepal, with local books, Wikipedia, Kolibri courses, and an optional textbook-grounded AI tutor.

**Status: working software foundation, not a field-validated school deployment.**
AI starts disabled.
Model inference, curriculum quality, Nepali language quality, school Wi-Fi capacity, and power recovery must pass the [deployment acceptance checks](docs/DEMO_SCRIPT.md) on the actual hardware.

[Project website](https://apil-khadka.github.io/LocalLearning/) · [Product brief](PRODUCT.md) · [Build plan](docs/BUILD_PLAN.md) · [Architecture](docs/ARCHITECTURE.md) · [Network design](docs/NETWORK.md) · [Kolibri operations guide](docs/KOLIBRI_GUIDE.md) · [Verification](docs/VERIFICATION.md)

## What is here

- A responsive React/TypeScript portal with English and Nepali interface text.
- A FastAPI API with switchable chat and separate Ollama or OpenAI-compatible embedding providers.
- Protected PDF/text ingestion, page-aware chunks, real retrieval metadata, and safe no-match responses.
- A searchable, paginated textbook catalog with filters, multi-select, inline PDF preview, and staff diagnostics.
- Staff-triggered vector indexing for saved books, processed one title at a time with small embedding batches.
- Separate student and staff reverse-proxy listeners, container packaging, and automated checks.
- An optional Kolibri 0.19.5 classroom service with persistent storage and a student portal link.
- A static project website for GitHub Pages, independent of the school application.

There are no scripted AI answers in the application.
Unconfigured or unavailable services are reported honestly.
The Digital Himalaya portal does not require student accounts or store chat history or analytics.
When enabled, Kolibri manages separate classroom accounts and learning progress in its own data volume.
The default AI chat endpoint is disabled until an operator adds a key and sets `AI_ENABLED=true`.
When the OpenAI-compatible provider is selected, learner questions, conversation history and retrieved excerpts are sent to that configured provider.
Keep `CHAT_PROVIDER=ollama` to process chat on a reachable local Ollama service instead.
The source planning attachments are private local material and are excluded from both Git and Docker builds.
Prototype book samples can be fetched locally with `make books-pilot` and `make books-more`.
They are text-only Wikibooks books or selected chapters with revision-level attribution, saved under ignored `content/private/` and excluded from public builds.
They are integration-test fixtures, not Nepal-approved curriculum sources.
The current private local environment also contains 216 CDC PDFs covering Kindergarten through Grade 12 and one cross-grade reference.
Run `make books-cdc-k12` to refresh them and `COMPOSE_FILE=docker-compose.yml:internal/compose-network.yml make books-import-k12` to put them in the local Books library without AI indexing.
The PDF files and generated manifest are ignored by Git; see [content setup](content/README.md) and the [CDC source inventory](docs/research/additional-book-sources.md).
The My Textbooks page searches titles, subjects, chapters, and sources through the API, and provides grade/subject filters, pagination, selection, and an in-page PDF preview.
The CDC books remain visible in the catalog but are not vector-indexed automatically.

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
EMBED_PROVIDER=ollama
EMBED_MODEL=embeddinggemma
```

Replace the host placeholders.
For containers, `localhost` means that container, not the Ubuntu host.
Use a verified container network address or `host.docker.internal` with a properly restricted host service.
Do not duplicate or modify existing NOMAD services.
Provision models and content while online, then disconnect WAN for acceptance.
To use a different OpenAI-compatible embedding service, configure `EMBED_PROVIDER=openai-compatible`, `EMBED_API_BASE_URL`, `EMBED_API_KEY`, and that provider's embedding model in `EMBED_MODEL`.
Chat and embedding configuration are independent; the configured chat model is not assumed to provide embeddings.

To test the requested hosted model, fill in these local-only values in `.env` and then enable AI:

```dotenv
AI_ENABLED=true
CHAT_PROVIDER=openai-compatible
CHAT_API_BASE_URL=https://inference.baseten.co/v1
CHAT_API_KEY=your-private-key
CHAT_MODEL=meta-models/muse-spark-open-1026
CHAT_REASONING_EFFORT=low
```

The key is never committed.
To switch chat to local Ollama, use `CHAT_PROVIDER=ollama` and set `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.
To switch to another OpenAI-compatible service, change `CHAT_API_BASE_URL`, `CHAT_API_KEY`, and `CHAT_MODEL`.
Clear `CHAT_REASONING_EFFORT` if the new service does not support Muse-style reasoning controls.
Textbook retrieval uses the separately configured embedding provider and Qdrant collection.
With either one unavailable, chat can still return a clearly labeled general explanation without textbook citations.

Set a random staff token of at least 32 characters in `.env` using a password manager or a local generator.
For example, `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'` generates a value to copy into `ADMIN_TOKEN`.
Keep it out of Git, logs and frontend build variables.
In development, open `/staff`, sign in, and import `content/sample/force-and-motion.txt` with grade `8`, subject `Science`, chapter `Force and Motion`, license `CC0-1.0`, and source `Original demonstration note`.
For books already in the catalog, use **Prepare books for tutor search** in Staff and index one searchable title at a time.
Each action embeds up to four passages per provider call and can be retried safely using stable vector IDs.
Scanned books without selectable text need OCR before they can be indexed.
Vector indexing requires an embedding provider and Qdrant, while tutor chat remains separately gated by `AI_ENABLED`.
General chat can be tested without either retrieval service.
After teacher review, enable AI and restart the API to test real questions.

The OLE Nepal and Nepal CDC catalog links are documented in [the book-source review](docs/research/book-sources.md).
The current E-Pustakalaya terms do not allow copying content to a separate host without written permission, and the CDC catalog entries reviewed did not state reuse terms.
The additional prototype fetcher and title-level source review are documented in [additional book sources](docs/research/additional-book-sources.md).

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
Kolibri is an optional Compose profile so the base application does not pull or start the education service unless requested.
Set `KOLIBRI_PUBLIC_URL=http://127.0.0.1:8092` and `KOLIBRI_PROBE_URL=http://kolibri:8080` in `.env`, then run `make education-up` to start and connect it alongside the portal.
Kolibri keeps its database, user records, and imported content in a separate persistent `kolibri-data` volume.
On a fresh local volume, `make education-up` provisions a formal `Digital Himalaya Dev School` facility and a `devadmin` super-admin account from the password in the ignored `private-local/kolibri-admin-password` file.
The bootstrap skips any volume that already contains a facility, so it does not reset existing Kolibri accounts or content.
Import approved channels in Kolibri's own interface; this project does not download course content or provision learner accounts.
The local dev password and access note belong only in the ignored `private-local/` directory and must not be committed or reused for a school deployment.
Use the [Kolibri operations guide](docs/KOLIBRI_GUIDE.md) for role setup, rights review, offline channel imports, update review, verification, and backup steps.
For a school LAN, set `KOLIBRI_BIND` to the server's reserved LAN IP and `KOLIBRI_PUBLIC_URL` to the student-reachable address after reviewing firewall rules.
Keep the education profile off when an existing NOMAD or Kolibri deployment already provides the service, and configure its verified URLs instead.
Run `make education-down` to stop only the Kolibri container without deleting its stored data.
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
