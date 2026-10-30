# Foundation verification

Verified locally on 2026-10-30.
This record describes software checks, not acceptance of a school deployment.

## Current software and service state

`make check`, the frontend Prettier check, and `make build` passed.
`make test` passed with 31 backend tests and 17 browser tests; 2 opt-in live-service backend tests and 7 deployment-specific browser cases were skipped.
A separate production-container run passed all 4 desktop and Android-sized tutor Markdown and app-shell cache regression checks.
The full Playwright suite with `DEPLOYMENT_URL` also passed earlier against the rebuilt local containers, with 21 passed and 1 expected desktop-only mobile-navigation skip.
The GitHub Actions backend, frontend, and container jobs passed for commit `da29f812ccbd1289427c5a60bfbd643f01789296` in [run 41062097349](https://github.com/apil-khadka/LocalLearning/actions/runs/41062097349).

The OpenAI-compatible provider has mocked contract coverage, and one live non-identifying request to the requested `meta-models/muse-spark-open-1026` model returned HTTP 200.
That live answer had general grounding and no textbook sources because Qdrant was not configured.
AI is disabled by default and remained disabled after the live request.
The API key and service credentials remain only in the ignored local `.env` file.

The optional Kolibri 0.19.5 Compose service was started locally with persistent storage and reported reachable from the API and student portal.
Kolibri first-run setup remains incomplete, and no facility accounts, learners, or course channels have been created or downloaded.
The staff workspace includes an English/Nepali import and update checklist, and the [Kolibri operations guide](KOLIBRI_GUIDE.md) covers rights review, offline imports, channel updates, and post-update checks.

No `QDRANT_URL` or embedding service is configured in the current local stack, so the private Wikibooks files are downloaded but are not indexed for tutor retrieval.
The API reports the Kolibri service reachable, the tutor disabled, and the embedding and vector services unconfigured.
The student `/staff` route returns 404, and the loopback staff `/staff` route returns 200.
The private prototype content includes a 62 KB Wikijunior Biology text fixture plus selected chapters from Wikijunior:Human Body, Wikijunior:Solar System, and Geometry for Elementary School, with revision manifests and checksums under ignored `content/private/`.
No E-Pustakalaya or Nepal CDC book files were copied because the reviewed sources did not authorize separate hosting or state redistribution terms.
Project NOMAD is not installed or integrated in the current test environment.

| Check | Result | Boundary |
| --- | --- | --- |
| Backend tests and lint | 31 tests passed, 2 opt-in tests skipped | Live Ollama and Qdrant checks require explicit service configuration. |
| Browser suite | 17 passed, 7 skipped | Tests use isolated APIs and test doubles; deployment-only checks require `DEPLOYMENT_URL`. |
| Website accessibility | No axe violations on the overview, learner-flow, and project-status pages | Automated WCAG A/AA checks run at desktop and Android-sized browser viewports; manual review is still required. |
| Production tutor regressions | 4 desktop and Android-sized checks passed | Built containers render Markdown headings, bold text, lists, and no-cache app-shell responses. |
| Static checks and build | `make check`, Prettier, and `make build` passed | Ruff, Python formatting, TypeScript, ESLint, frontend production build, and both Docker image builds. |
| Live hosted chat request | One request to the requested model returned HTTP 200 | The result was general, without textbook grounding; AI was disabled immediately afterward. |
| Qdrant retrieval | Earlier protocol test passed against a disposable Qdrant v1.15.5 container | Deterministic embedding fixtures validate storage and filter isolation, not semantic relevance; current local Qdrant is unconfigured. |
| Kolibri | Optional service reached during local verification | First-run setup and course channels remain incomplete; target Ubuntu hardware still needs verification. |
| Student and staff boundary | Student `/staff` returns 404; staff route returns 200 on loopback | Tests verify application listeners, not school router or firewall configuration. |
| Private material exclusion | Source attachments, `.env`, dependencies, generated output, and downloaded book text are ignored | Review staged files before each commit. |

Browser mobile emulation is not a physical-phone or school Wi-Fi load test.
The local Compose network override is ignored and is not part of the school deployment configuration.

See the [acceptance script](DEMO_SCRIPT.md) for real inference, curriculum and Nepali review, downloaded content, WAN-off clients, capacity, router ACLs, UPS recovery, and restore evidence still required.
