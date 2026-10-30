# Foundation verification

Verified locally on 2026-10-30.
This record describes software checks, not acceptance of a school deployment.

## Current provider and content pilot

The current backend suite passes with 28 passed and 2 opt-in live-service tests skipped.
The OpenAI-compatible provider contract is exercised with mocked responses; no live Baseten request was made because the local API key is blank and AI is disabled.
The browser suite passes with 13 passed and 3 viewport/deployment cases skipped.
The staff workspace now includes a Kolibri entry point and an English/Nepali channel import and update checklist.
A production-browser run passed on desktop and Android-sized viewports against the refreshed local containers with the live Kolibri link configured.
`make check` and `make build` pass, including Python lint/format checks, TypeScript/ESLint, frontend production build and both Docker image builds.
The official Kolibri 0.19.5 image starts in the optional Compose profile with its own persistent volume and is reachable from the API and student portal.
The current local app is left running on loopback at ports 8090-8093 with AI disabled; no Kolibri accounts or course channels have been created or downloaded.
The staff checklist and [Kolibri operations guide](KOLIBRI_GUIDE.md) cover content-rights review, supported offline imports, channel update review, and post-update verification.
No `QDRANT_URL` is set, so Qdrant correctly reports unconfigured and no live vector-store request was made.
The student `/staff` route returns 404 and the loopback staff `/staff` page returns 200.
The prototype book fetcher saved a text-only Wikijunior Biology sample with revision-level attribution under ignored `content/private/`.
No E-Pustakalaya or Nepal CDC book files were copied into the prototype because their reviewed pages did not authorize separate hosting or state redistribution terms.
Project NOMAD is not installed or integrated in the current test environment.

| Check                                   | Result                                                                                          | Boundary                                                                                                              |
| --------------------------------------- | ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Backend workflow/security suite         | 28 passed, 2 skipped                                                                            | Ollama and Qdrant live-service tests are opt-in; current provider tests use mocked HTTP responses                     |
| Desktop and Android-sized browser suite | 13 passed, 3 skipped; production deployment E2E 2 passed                                        | App workflows and public website; deployment run used the rebuilt local app and live Kolibri container                |
| Accessibility                           | No axe violations in tested WCAG A/AA rules                                                     | Public website at both tested browser sizes; not a complete manual accessibility certification                        |
| Static checks and build                 | `make check` and `make build` passed                                                            | Ruff, Python formatting, TypeScript, ESLint, frontend production build and Docker image builds                        |
| Frontend dependency audit               | No known vulnerabilities reported                                                               | `npm audit` at verification time                                                                                      |
| Containers and Kolibri                  | App images built; Kolibri 0.19.5 running with persistent storage; API reports Kolibri reachable | OrbStack on this development Mac; no course channels or users loaded; target Ubuntu hardware still needs verification |
| Student/staff boundary                  | Student `/staff` route 404; loopback staff page 200; Kolibri ports bound to loopback            | Production E2E verified the student/staff route boundary; school router/firewall is not configured by these tests     |
| Local browser assets                    | Browser flows passed with external origins blocked                                              | Portal fonts/scripts/styles bundled locally; no inference services were configured for this check                     |
| Private material exclusion              | Original attachments, `.env`, dependencies, generated output and the book sample are ignored    | Git ignore rules plus Docker build-context exclusion; final staged-file review required for every future commit       |

The real Qdrant integration test passed in the earlier foundation run against a disposable Qdrant v1.15.5 container.
That test validates storage/retrieval protocol and filter isolation using deterministic embedding fixtures; it does not measure semantic relevance or model quality.
Browser mobile emulation is not a physical phone or Wi-Fi load test.

The first Compose startup encountered this host's exhausted default Docker address pool.
Verification used an isolated explicit test subnet without pruning or changing other projects' networks.
That local override is not part of the school deployment configuration.

See [the acceptance script](DEMO_SCRIPT.md) for real inference, curriculum/Nepali review, downloaded content, WAN-off clients, capacity, router ACLs, UPS recovery and restore evidence still required.
