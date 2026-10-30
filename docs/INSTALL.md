# Installation and operation

Provision on Ubuntu with Docker Engine and Compose v2, using supported official installation instructions.
Build/install while internet is available; runtime operation must be tested with WAN disconnected.
Use the [README](../README.md) for local development commands.

## Provisioning

1. Audit the site's power, hardware, storage, router/AP capabilities and approved content.
2. Configure the [network boundary](NETWORK.md) before exposing services to students.
3. If using NOMAD, follow its [official repository instructions](https://github.com/Crosstalk-Solutions/project-nomad) and inspect the installer before running it.
4. Verify the actual installed Ollama/Qdrant addresses and versions; do not install duplicates automatically.
5. Choose either local Ollama chat or an OpenAI-compatible chat endpoint, then verify the selected provider with a direct request.
6. Download the local embedding model only if textbook retrieval is needed, verify its license and run a direct local request.
7. Download one approved Kiwix article collection, import one reviewed Kolibri channel with its actual media, and select one permitted searchable chapter.
8. Copy `.env.example` to `.env`; set real service addresses, a random `ADMIN_TOKEN`, and verified student resource URLs.
9. Run `docker compose build` and `docker compose up -d --wait` from the repository root.

## Kolibri classroom service

The optional `education` Compose profile runs the official Kolibri 0.19.5 container with a persistent `kolibri-data` volume.
The image listens on ports 8080 and 8081 internally; this project publishes them as host ports 8092 and 8093 by default.
To use the embedded service locally, set `KOLIBRI_PUBLIC_URL=http://127.0.0.1:8092` and `KOLIBRI_PROBE_URL=http://kolibri:8080` in `.env`, create the ignored `private-local/kolibri-admin-password` file with a strong password of at least 16 characters, and run `make education-up`.
On a fresh volume, the target provisions a formal `Digital Himalaya Dev School` facility and `devadmin` super-admin account, then leaves Kolibri running for browser access at `http://127.0.0.1:8092`.
It skips provisioning when a facility already exists, preserving its accounts and content.
Create coach and learner accounts and import reviewed channels using Kolibri's interface.
The private local access note is `private-local/KOLIBRI_DEV_ACCESS.md`; both it and the password file are git-ignored.
Follow the [Kolibri operations guide](KOLIBRI_GUIDE.md) for a complete content-selection, import, update, verification, and backup procedure.
Kolibri channels must be imported from Kolibri Studio, another Kolibri device, or a prepared Kolibri storage drive; this application does not scrape or load course content into Kolibri.
For a school deployment, change `KOLIBRI_BIND` to the reserved server LAN address and set `KOLIBRI_PUBLIC_URL` to the address reachable by student devices only after firewall review.
Keep `KOLIBRI_PROBE_URL=http://kolibri:8080` when using the bundled service; for an existing NOMAD-managed Kolibri service, set both URLs to verified addresses and leave the `education` profile stopped.
Run `make education-down` to stop the bundled Kolibri container while retaining its data volume.

## Project NOMAD compatibility

The current application is not installed, managed or updated by Project NOMAD.
The two Docker Compose projects can run side by side, but integration requires an operator to verify and enter service URLs manually.
No NOMAD service discovery, management API or installer integration is implemented.
Do not duplicate or change existing NOMAD-managed Ollama, Qdrant, Kiwix or Kolibri services as part of this application's setup.

Model defaults are candidates, not a promise of acceptable Nepali or classroom performance.
The repository does not download models or third-party learning collections automatically.
Keep `AI_ENABLED=false` until the teacher and safety gate passes.

The API container can reach `host.docker.internal` through the Compose host-gateway entry.
Host services bound only to `127.0.0.1` are generally not reachable through that address on Linux.
Prefer an explicitly restricted shared/container network or a host binding reachable only by the backend, and test it.
Do not solve this by exposing model/database ports unrestricted on student Wi-Fi.

## Staff import and AI activation

Open the staff portal locally at `http://127.0.0.1:8091/staff` or through the SSH tunnel described in the network guide.
Enter the staff token; it remains in page memory and is lost on reload/sign-out.
Import the sample note or approved curriculum PDF with explicit attribution and permission.
Keep each file under 10 MiB and each PDF under 100 pages by default; import chapters rather than whole large collections.
The staff interface reports import failures, while scanned/missing text pages are flagged for OCR.
Text files have one logical page.

For local chat, set `CHAT_PROVIDER=ollama` and configure `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.
For an OpenAI-compatible chat API, set `CHAT_PROVIDER=openai-compatible`, `CHAT_API_BASE_URL`, `CHAT_API_KEY`, and `CHAT_MODEL` in the ignored `.env` file.
For Baseten's selected model, the defaults are `https://inference.baseten.co/v1` and `meta-models/muse-spark-open-1026`.
After successful provider checks and teacher review, set `AI_ENABLED=true` and run `docker compose up -d --force-recreate api`.
With the hosted provider enabled, questions, conversation history, and retrieved textbook excerpts leave the school network for that provider.
Use only test prompts or approved data until provider retention and privacy settings have been reviewed.
The flag is an operational gate, not proof of safety or a substitute for age controls and supervision.
The Digital Himalaya API does not link to Kolibri identities or provide student age verification.
Kolibri's own roles and progress remain separate from the tutor and staff token.
Restrict use to the approved supervised cohort until those controls exist.

Set `PORTAL_BIND` to the actual server LAN address only after firewall checks pass, then recreate the portal container.
Keep `STAFF_PORT` bound to loopback through the supplied Compose mapping.
Confirm both paths from real client devices.

## Offline packaging

After building on a compatible CPU architecture, save the two application images for transfer:

```sh
mkdir -p backups
docker save digital-himalaya-api:0.1.0 digital-himalaya-portal:0.1.0 -o backups/application-images.tar
```

When using the optional Kolibri profile, also pull its pinned image while online and include it in the transfer archive:

```sh
docker compose --profile education pull kolibri
docker save digital-himalaya-api:0.1.0 digital-himalaya-portal:0.1.0 ghcr.io/learningequality/kolibri:0.19.5 -o backups/application-images.tar
```

Load on the target with `docker load -i backups/application-images.tar`.
Start the base application with `docker compose up -d --no-build` or include Kolibri with `docker compose --profile education up -d --no-build` after preparing its URLs in `.env`.
Model weights, Qdrant storage, Kiwix ZIMs and Kolibri channels are separate artifacts and must be transferred/provisioned using their service workflows.
Building an ARM image on a Mac does not create an x86 image for an Ubuntu mini PC.
Build for the target architecture before disconnecting internet and verify startup there.

## Backup and restore

Back up the application catalog/files and Qdrant index as a coordinated set while imports and chat are stopped.
When Kolibri is enabled, back up its `kolibri-data` volume separately using a stopped-volume or Kolibri-supported export procedure so learner records, facility configuration, and imported channels stay together.
Keep `.env` and school/network configuration in separate encrypted private backups.
Never put backups in the public repository.

```sh
mkdir -p backups
docker compose stop api
docker compose cp api:/data/. backups/content-data/
# Take a Qdrant snapshot using the installed service's documented workflow.
docker compose start api
```

Record the embedding model digest, collection, model/prefix settings and snapshot identity alongside the backup.
To restore, first start a fresh deployment once so its volume exists, stop its API, copy the saved files into `/data`, restore the matching vector snapshot, and set ownership to UID 10001 before restarting.
For example, `docker compose cp backups/content-data/. api:/data/` copies the files into the stopped container's volume.
Use `docker compose run --rm --no-deps --user 0 api chown -R 10001:10001 /data` to repair ownership when needed.
Test this on a disposable deployment before relying on a backup for a school.
Restoring only SQLite or only vectors can lose retrieval consistency.

## Shutdown and diagnostics

Use `docker compose down` to stop the application without deleting volumes.
Do not use `down -v` as a normal stop command.
Configure graceful shutdown with the actual UPS and test power loss/restart before handover.

Use `docker compose ps`, `docker compose logs --tail 100 api`, and `./scripts/check-offline.sh` for basic diagnostics.
`/api/health` is application liveness; `/api/services` reports dependency reachability.
The staff index page shows failed/incomplete imports that are hidden from students.
If indexing fails, repair the service and reimport the same file/metadata to retry stable point IDs.
If embeddings change, use an intentional new catalog/index rather than silently mixing incompatible vectors.
