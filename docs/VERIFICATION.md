# Foundation verification

Verified locally on 2026-10-30.
This record describes software checks, not acceptance of a school deployment.

| Check | Result | Boundary |
| --- | --- | --- |
| Backend workflow/security suite | 25 passed, 1 skipped with real-Qdrant test enabled | Ollama HTTP contract doubles; real filesystem/SQLite; real Qdrant v1.15.5 in a disposable container |
| Desktop and Android-sized browser suite | 14 passed | Portal/API flows, production bundle, public website; HTTP contract doubles for model output |
| Accessibility | No axe violations in tested WCAG A/AA rules | Homepage of production portal and public website at both tested viewport sizes; not a complete manual accessibility certification |
| Static checks | Ruff, Python formatting, TypeScript, ESLint, Prettier and diff whitespace checks passed | Source and build configuration |
| Frontend dependency audit | No known vulnerabilities reported | `npm audit` at verification time |
| Python runtime dependency audit | No known vulnerabilities reported | Exact exported runtime lock entries via `pip-audit`; not an image/OS audit |
| Containers | Both images built; API and portal started healthy | Docker Desktop on ARM, Python 3.12 API image; actual target architecture still needs verification |
| Student/staff boundary | Student admin API 403; staff path 404; loopback staff page 200; empty staff config 503 | Supplied Nginx/Compose behavior; school router/firewall not configured by these tests |
| Local browser assets | Production browser flow passed with external origins blocked | Portal fonts/scripts/styles bundled locally; no inference services were configured for this check |
| Private material exclusion | Original attachments, `.env`, dependencies and test output ignored | Git ignore rules plus Docker build-context exclusion; final staged-file review required for every future commit |

The live Ollama test was skipped because no actual model service was supplied on this machine.
The real Qdrant test validates storage/retrieval protocol and filter isolation using deterministic embedding fixtures; it does not measure semantic relevance or model quality.
Browser mobile emulation is not a physical phone or Wi-Fi load test.

The first Compose startup encountered this host's exhausted default Docker address pool.
Verification used an isolated explicit test subnet without pruning or changing other projects' networks.
That local override is not part of the school deployment configuration.

See [the acceptance script](DEMO_SCRIPT.md) for real inference, curriculum/Nepali review, downloaded content, WAN-off clients, capacity, router ACLs, UPS recovery and restore evidence still required.
