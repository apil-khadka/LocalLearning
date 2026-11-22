# Foundation verification

## Local Phi-4 model evaluation (2026-11-22)

A matched 39-probe run compared Phi-4 Reasoning Plus and Phi-4 Mini Instruct through the Digital Himalaya tutor harness and LM Studio.

Reasoning Plus passed 30/39 primary probes and Mini Instruct passed 25/39; Mini Instruct's mean response time was 2.74 seconds versus 75.74 seconds for Reasoning Plus.

On the fixed Grade 5–12 math set the raw scores were 12/13 and 6/13 respectively; one Reasoning Plus answer was correct but missed by the automated matcher.

Both models scored 1/3 on the Nepali probes, so neither is validated for Nepali-medium tutoring.

See the [full report and limitations](PHI4_MODEL_COMPARISON.md).

This model evaluation is separate from software tests and does not satisfy teacher review or the school deployment gates below.

## Software verification snapshot (2026-11-14)

This historical record describes software checks, not acceptance of a school deployment.

- `make check`, `make test`, and `make build` completed successfully.
- Backend tests passed: 182 passed, 2 skipped.
- The full frontend Playwright suite passed; Docker deployment cases are skipped by default unless deployment URLs and credentials are provided.
- Docker images built successfully, then the isolated QA stack ran with `--no-build` on alternate loopback ports `18190` and `18191`.
- Twelve built-container Playwright checks passed across desktop and Android-sized viewports, covering the student/staff listener boundary, Kolibri link, account recovery, staff redirect, and student history with assigned-teacher transcript review.
- The opt-in `DEPLOYMENT_LIVE_AI=1` browser check passed against the live AI provider configured in the ignored `.env`; the real student tutor UI saved a session that the assigned teacher could open.
- A separate Docker API smoke passed live AI chat, transcript audit and access isolation, staff document import, note review and approval, student note visibility, and note-grounded AI chat.
- An API-container restart preserved QA accounts, class assignments, tutor history, approved notes, transcript audit rows, and Kolibri catalog reachability.
- The Docker Kolibri integration returned version 0.19.5 with one of two listed channels available; the unavailable channel has no dead deep link.
- The QA environment had a configured and reachable hosted chat provider, but no embedding provider or Qdrant vector service; textbook vector indexing returned HTTP 503 without breaking saved books or approved teaching notes.
- HTTP QA used `AUTH_COOKIE_SECURE=false` on loopback only; the Compose stack still needs a TLS terminator and school-device HTTPS validation before LAN release.
- The frontend production build emits a 502.53 kB JavaScript chunk warning; the build still succeeds.

The results above are local evidence for the tested Docker configuration, not school-site release approval.
There is no CI run URL for these uncommitted changes.
Physical WAN-off testing, TLS and school VLAN checks, content redistribution rights, bilingual teacher scoring, backup restoration, phone and network capacity, and UPS recovery remain open gates in [`PRODUCTION_READINESS.md`](PRODUCTION_READINESS.md).
The current application also lacks class withdrawal/transfer and teacher reassignment controls, and learner initial passwords are entered by teachers; resolve those roster and credential handoff gaps before broad school use.

## Historical teaching notes, tutor modes and evaluation snapshot (2026-11-14)

Software checks run locally on the uncommitted working tree:

- `make check` (Ruff, format check, TypeScript, ESLint) passed.
- `uv run pytest -q` in `backend/` passed 176 tests, with 2 opt-in live-service tests skipped. The new tests cover the note lifecycle and approval rules, student visibility, staff-token enforcement, restart persistence, request validation, the three tutor modes, hint withholding, evaluation round trips, safe runtime configuration fingerprints and score-sheet validation.
- `npm run test:e2e` passed 30 browser cases at desktop and Android-sized viewports, with 6 skipped because they need `DEPLOYMENT_URL`. The new case covers staff-created notes, approval, the Study page, hint reveal, reader page links, and tutor check-my-work mode against the contract doubles.
- `npm run build` for the frontend passed. Docker images were not rebuilt, and the production browser checks were not run.

Not verified:

- No real model, embedding service or Qdrant answered any of these checks. They use the HTTP contract doubles, so they show that the application builds the intended prompts and parses replies, not that a model follows the hint or debug instructions.
- No teacher has written, approved or scored anything. `evals/sample-questions.json` is a format example, and no scored baseline exists.
- The Kolibri catalog code is covered by contract tests. The local Kolibri service was not running during this pass, so the earlier research note's statement that PhET was imported was not re-checked here, and the Kolibri row below still stands.
- Nepali strings for the new screens are unreviewed drafts.
- The 5-link navbar was checked at 1280, 663 and 390 px in an emulated browser, not on a physical phone.

## Historical software and service state snapshot

The record below predates the current verification section and is retained for context only.

`make check`, the frontend Prettier check, and `make build` passed.
`make test` passed with 58 backend tests and 26 browser cases; 2 opt-in live-service backend tests and 6 production browser cases were skipped because they require `DEPLOYMENT_URL`.
A full Playwright run with `DEPLOYMENT_URL` passed 27 tests against the rebuilt local containers, with 1 expected desktop-only mobile-navigation skip.
A production-container run passed the portal boundary, tutor Markdown, app-shell cache, and PDF preview policy checks at desktop and Android-sized viewports.
Browser coverage checks the full-width sticky navbar at desktop, tablet, and phone sizes, keeps its three learner links in the navbar, and places the brand, connection state, and language toggle in the shared footer.
The GitHub Actions backend, frontend, and container jobs passed for commit `da29f812ccbd1289427c5a60bfbd643f01789296` in [run 41062097349](https://github.com/apil-khadka/LocalLearning/actions/runs/41062097349).

The OpenAI-compatible provider has mocked contract coverage, and one live non-identifying request to the requested `meta-models/muse-spark-open-1026` model returned HTTP 200.
That live answer had general grounding and no textbook sources because Qdrant was not configured.
AI is disabled by default and remained disabled after the live request.
The local `.env` is ignored by Git, and credentials are not included in the public repository.

The 2026-10-30 baseline recorded the optional Kolibri 0.19.5 Compose service running locally with persistent storage and reachable from the API and student portal.
That baseline recorded a formal `Digital Himalaya Dev School` facility and a `devadmin` super-admin account in the local volume.
The generated password and access note are stored only under ignored `private-local/` files, and the bootstrap preserves the provisioned data when rerun.
The baseline reported no learner accounts or course channels.
A 2026-11-04 research note later reported that PhET content had been imported, but this was not rechecked on 2026-11-14, so the current local imported-content state is unknown.
The staff workspace includes an English/Nepali import and update checklist, and the [Kolibri operations guide](KOLIBRI_GUIDE.md) covers rights review, offline imports, channel updates, and post-update checks.

No `QDRANT_URL` or embedding service is configured in the current local stack, so private books are stored in the library but are not indexed for tutor retrieval.
The API reports the Kolibri service reachable, the tutor disabled, and the embedding and vector services unconfigured.
The student `/staff` route returns 404, and the loopback staff `/staff` route returns 200.
The private prototype content includes a 62 KB Wikijunior Biology text fixture plus selected chapters from Wikijunior:Human Body, Wikijunior:Solar System, and Geometry for Elementary School, with revision manifests and checksums under ignored `content/private/`.
The local CDC snapshot contains 216 PDFs totaling 1,848,082,014 bytes, with titles assigned to Kindergarten and Grades 1–12 plus one cross-grade reference.
The crawl covers the current G, B, M, T, and E feeds and the early-childhood curriculum page; the separate OPAC technical shelves were unreachable during this pass.
All 216 documents are ready in the local Books API with `index_status=not_indexed`, `chunks=0`, and AI disabled.
The API returned all 216 titles, every K–12 grade filter returned its expected assigned books plus the cross-grade item, and a Grade 9 PDF returned HTTP 200 with a valid PDF signature.
The PDFs and generated manifest remain in ignored local storage and are not committed.
Project NOMAD is not installed or integrated in the current test environment.

| Check | Result | Boundary |
| --- | --- | --- |
| Backend tests and lint | 58 tests passed, 2 opt-in tests skipped | Live Ollama and Qdrant checks require explicit service configuration. |
| Browser suite | 26 passed, 6 skipped | Tests use isolated APIs and test doubles; six production checks require `DEPLOYMENT_URL`. |
| Website accessibility | No axe violations on the overview, learner-flow, and project-status pages | Automated WCAG A/AA checks run at desktop and Android-sized browser viewports; manual review is still required. |
| Production portal checks | 6 desktop and Android-sized checks passed | Built containers render the student portal, formatted tutor answers, same-origin PDF preview policy, and no-cache app-shell responses. |
| Static checks and build | `make check`, Prettier, and `make build` passed | Ruff, Python formatting, TypeScript, ESLint, frontend production build, and both Docker image builds. |
| Live hosted chat request | One request to the requested model returned HTTP 200 | The result was general, without textbook grounding; AI was disabled immediately afterward. |
| Qdrant retrieval | Earlier protocol test passed against a disposable Qdrant v1.15.5 container | Deterministic embedding fixtures validate storage and filter isolation, not semantic relevance; current local Qdrant is unconfigured. |
| Kolibri | Formal local facility and `devadmin` account provisioned; API reports the service reachable | No learner accounts or course channels have been imported; target Ubuntu hardware still needs verification. |
| Student and staff boundary | Student `/staff` returns 404; staff route returns 200 on loopback | Tests verify application listeners, not school router or firewall configuration. |
| Private material exclusion | Source attachments, `.env`, dependencies, generated output, and all 216 downloaded CDC PDFs are ignored | Review staged files before each commit. |

Browser mobile emulation is not a physical-phone or school Wi-Fi load test.
The local Compose network override is ignored and is not part of the school deployment configuration.

See the [acceptance script](DEMO_SCRIPT.md) for real inference, curriculum and Nepali review, downloaded content, WAN-off clients, capacity, router ACLs, UPS recovery, and restore evidence still required.
