# Foundation verification

Verified locally on 2026-10-30.
This record describes software checks, not acceptance of a school deployment.

## Current software and service state

`make check`, the frontend Prettier check, and `make build` passed.
`make test` passed with 58 backend tests and 21 browser cases; 2 opt-in live-service backend tests and 7 browser cases were skipped, including 6 production checks that require `DEPLOYMENT_URL` and 1 desktop-only mobile-navigation case.
A full Playwright run with `DEPLOYMENT_URL` passed 27 tests against the rebuilt local containers, with 1 expected desktop-only mobile-navigation skip.
A production-container run passed the portal boundary, tutor Markdown, app-shell cache, and PDF preview policy checks at desktop and Android-sized viewports.
Browser coverage also checks that the desktop sidebar uses the one-word label, mobile navigation has exactly three links, and the full logo appears in the shared footer.
The GitHub Actions backend, frontend, and container jobs passed for commit `da29f812ccbd1289427c5a60bfbd643f01789296` in [run 41062097349](https://github.com/apil-khadka/LocalLearning/actions/runs/41062097349).

The OpenAI-compatible provider has mocked contract coverage, and one live non-identifying request to the requested `meta-models/muse-spark-open-1026` model returned HTTP 200.
That live answer had general grounding and no textbook sources because Qdrant was not configured.
AI is disabled by default and remained disabled after the live request.
The local `.env` is ignored by Git, and credentials are not included in the public repository.

The optional Kolibri 0.19.5 Compose service was started locally with persistent storage and reported reachable from the API and student portal.
The bootstrap now creates a formal `Digital Himalaya Dev School` facility and `devadmin` super-admin on a fresh volume after a local password is provided.
The service is currently reachable, but first-run provisioning is pending because no password has been entered; no facility account, learner account, or course channel has been created yet.
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
| Browser suite | 21 passed, 7 skipped | Tests use isolated APIs and test doubles; 6 production checks require `DEPLOYMENT_URL`, and 1 mobile-navigation test is desktop-only. |
| Website accessibility | No axe violations on the overview, learner-flow, and project-status pages | Automated WCAG A/AA checks run at desktop and Android-sized browser viewports; manual review is still required. |
| Production portal checks | 6 desktop and Android-sized checks passed | Built containers render the student portal, formatted tutor answers, same-origin PDF preview policy, and no-cache app-shell responses. |
| Static checks and build | `make check`, Prettier, and `make build` passed | Ruff, Python formatting, TypeScript, ESLint, frontend production build, and both Docker image builds. |
| Live hosted chat request | One request to the requested model returned HTTP 200 | The result was general, without textbook grounding; AI was disabled immediately afterward. |
| Qdrant retrieval | Earlier protocol test passed against a disposable Qdrant v1.15.5 container | Deterministic embedding fixtures validate storage and filter isolation, not semantic relevance; current local Qdrant is unconfigured. |
| Kolibri | API reports the optional service reachable; first-run provisioning waits for a local password | No facility, learner accounts, or course channels have been created; target Ubuntu hardware still needs verification. |
| Student and staff boundary | Student `/staff` returns 404; staff route returns 200 on loopback | Tests verify application listeners, not school router or firewall configuration. |
| Private material exclusion | Source attachments, `.env`, dependencies, generated output, and all 216 downloaded CDC PDFs are ignored | Review staged files before each commit. |

Browser mobile emulation is not a physical-phone or school Wi-Fi load test.
The local Compose network override is ignored and is not part of the school deployment configuration.

See the [acceptance script](DEMO_SCRIPT.md) for real inference, curriculum and Nepali review, downloaded content, WAN-off clients, capacity, router ACLs, UPS recovery, and restore evidence still required.
