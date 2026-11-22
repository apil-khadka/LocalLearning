# Production readiness release gate

**Current status: NOT production-ready for an unsupervised or field-validated school deployment.**
Automated repository checks ([`VERIFICATION.md`](VERIFICATION.md)) verify software contracts, container boundaries, and local test doubles on a developer machine.
They do not prove curriculum licensing, Nepali or subject teaching quality, low-end phone usability, school LAN isolation, multi-client capacity, backup restoration, or UPS power recovery on target school hardware.

Use this document as the release gate before handing a server to a school or enabling student access.
Keep `AI_ENABLED=false` until the library, network, licensing, security, backup, and power gates pass, and enable the AI tutor only if the teacher evaluation gate also passes.
Do not copy detailed procedures here; follow the linked guides and record the required evidence in the school's private commissioning log.

---

## 1. Software checks vs. real-school release gates

Software checks are necessary preconditions to build and package a release candidate, but passing them never substitutes for a physical school gate.

| Area | Software check (developer / CI) | Real-school gate (target hardware & staff) | Primary reference |
| --- | --- | --- | --- |
| Build & contracts | `make check`, `make test`, `make build`, and `DEPLOYMENT_URL` Playwright suite pass | Target x86/ARM server boots saved images with `--no-build` and no internet | [`VERIFICATION.md`](VERIFICATION.md), [`INSTALL.md`](INSTALL.md) |
| Service probes | `/api/health`, `/api/services`, and `./scripts/check-offline.sh` return HTTP 200 | Physical WAN unplugged; cellular off on student phones; real models, ZIMs, and Kolibri media load over school Wi-Fi | [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md), [`NETWORK.md`](NETWORK.md) |
| Books & notes | Bounded PDF/text import, one-book indexing (`POST /api/admin/index-book`), and note review workflow (`draft` → `in_review` → `approved`) pass tests | Written rights/redistribution evidence on file; OCR-needed or missing pages reviewed; every student-visible note approved by a named teacher | [`CONTENT_LICENSES.md`](CONTENT_LICENSES.md), [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Tutor & modes | Unit/e2e tests for `explain`, `hint` (`hint_level` 0–4), and `debug` modes, citation chips (`textbook`, `note`, `general`), and HTTP 429 concurrency bounds | Repeatable teacher evaluation in English and Nepali meets score thresholds with zero severe/unsafe outputs | [`evals/README.md`](../evals/README.md), [Phi-4 probe results](PHI4_MODEL_COMPARISON.md), [`BUILD_PLAN.md`](BUILD_PLAN.md) |
| Kolibri | `/api/kolibri/channels` surfaces sanitized channels and `/en/learn/#/topics/c/<root_id>` deep links | School facility, named coach/learner accounts, and reviewed offline channels verified from student devices without reusing `devadmin` | [`KOLIBRI_GUIDE.md`](KOLIBRI_GUIDE.md), [`kolibri-integration.md`](research/kolibri-integration.md) |
| Security boundary | Student Nginx listener returns `404` on `/staff` and `403` on `/api/admin`; staff listener defaults to loopback and uses named-account sessions with CSRF protection | Router VLAN/ACL enforcement verified from student Wi-Fi; staff-only binding or SSH tunnel, TLS, and session revocation tested by school staff | [`SECURITY.md`](SECURITY.md), [`NETWORK.md`](NETWORK.md) |
| Resilience | Deterministic chunk/point IDs and volume persistence in Docker Compose | Coordinated SQLite/file/Qdrant/Kolibri backup restored onto a clean instance; graceful UPS shutdown and cold boot verified | [`INSTALL.md`](INSTALL.md), [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) |

---

## 2. Gate criteria and concrete evidence to collect

Record all commissioning evidence in the school's private deployment dossier (never commit student data, passwords, `.env` files, or copyrighted bundles to Git).
Every gate below must have a dated artifact, named reviewer/operator, and pass/fail decision before release sign-off.

### 2.1 Offline LAN operation

Follow [`NETWORK.md`](NETWORK.md), [`INSTALL.md`](INSTALL.md), and [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md).
Notice that `./scripts/check-offline.sh` only checks local HTTP responses; it does not prove WAN-disconnected operation.

**Evidence to collect:**
- **Target-architecture image manifest:** Output of `docker image ls` on the Ubuntu server showing `digital-himalaya-api:0.1.0`, `digital-himalaya-portal:0.1.0`, and (if enabled) `ghcr.io/learningequality/kolibri:0.19.5` loaded from `backups/application-images.tar` and started with `docker compose up -d --no-build`.
- **WAN-disconnected state proof:** Physical router WAN port unplugged (or upstream interface disabled) and student test phones placed in airplane mode with Wi-Fi enabled only on the student SSID (VLAN 20).
- **Service reachability snapshot:** Saved output of `GET /api/health`, `GET /api/services`, and `GET /api/kolibri/channels` while WAN is disconnected, confirming:
  - When local chat is selected (`CHAT_PROVIDER=lmstudio` or `ollama`), `chat_model` reports ready and a real prompt returns from that local model; embeddings and vectors are checked separately when the deployment requires vector retrieval.
  - When `CHAT_PROVIDER=openai-compatible`, the tutor honestly fails with HTTP 503 while WAN is off, and the textbook library, study notes, Kiwix, and Kolibri remain fully usable.
- **Zero-external-asset browser check:** Browser DevTools network log from a student phone on school Wi-Fi showing `0` external DNS/HTTPS requests when loading the portal, switching English/Nepali UI, opening a PDF textbook (`/api/textbooks/{id}/file`), viewing an approved study note (`/study`), opening a Kiwix article, and playing an imported Kolibri resource.

### 2.2 Content licenses and teacher curriculum approval

Follow [`CONTENT_LICENSES.md`](CONTENT_LICENSES.md), [`book-sources.md`](research/book-sources.md), and [`additional-book-sources.md`](research/additional-book-sources.md).
Remember that `content/sample/force-and-motion.txt` (CC0 1.0) and the local Wikibooks prototypes (CC BY-SA 4.0) are software fixtures, not Nepal-approved curriculum textbooks, and the local 216-PDF CDC collection (`content/private/`) has no blanket redistribution license in this repo.

**Evidence to collect:**
- **Signed content register:** A private manifest listing every imported textbook, teacher note, Kiwix ZIM, Kolibri channel, and AI/embedding model weight deployed on the server, including:
  - Title, grade, subject, source URL or physical origin, SHA-256 checksum, license/permission terms, and required attribution text.
  - Written permission or confirmed redistribution terms from copyright holders (e.g., CDC Nepal, OLE Nepal / E-Pustakalaya, or channel publishers) for school LAN distribution.
- **Catalog & OCR audit:** Export of `GET /api/admin/index-status` showing every student-visible document has `status: "ready"`, verified grade/subject metadata, and recorded `ocr_required_pages` handling (books with `index_status: "needs_ocr"` or `"failed"` either remediated or intentionally kept as non-indexed PDFs).
- **Teacher note approval log:** Export of `GET /api/admin/notes` confirming:
  - Every student-visible note on `/api/notes` has `status: "approved"`, a named teacher in `reviewer`, a timestamp in `reviewed_at`, a valid `revision` number, and valid `pages` within a `ready` textbook.
  - Unreviewed (`draft` or `in_review`) notes remain invisible on `/api/notes`.
  - Teachers verify that `key_ideas`, `worked_example`, `misconceptions`, ordered `hints` (none revealing the final answer), and `check_question` match the school's syllabus for that grade and language (`en` or `ne`).
- **Clean repository check:** `git status --ignored` and image inspection confirming no private PDFs, model weights, ZIMs, or school `.env` files are tracked or baked into public images.

### 2.3 English and Nepali tutor evaluation

Follow [`ARCHITECTURE.md`](ARCHITECTURE.md), [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md), and [`evals/README.md`](../evals/README.md).
Model defaults (`qwen3:4b-instruct`, `meta-models/muse-spark-open-1026`, `embeddinggemma`) are configuration defaults, not validated claims of Nepali fluency or grade-appropriate pedagogy.

**Evidence to collect:**
- **Bilingual question bank:** A teacher-authored JSON question set (never student chat logs) covering the target grades and subjects in both English (`"language": "en"`) and Nepali (`"language": "ne"`), including:
  - In-scope textbook questions with `expected_sources` (`document_id` and `pages`).
  - Questions covered by approved teacher notes (`grounding: "note"`).
  - Out-of-scope / wrong-grade / unindexed-chapter questions that must return `grounding: "general"` with no fabricated citations.
  - Misleading premises and prompt-injection strings embedded in questions, `attempt` fields, or test passages.
  - All three tutor modes: `explain`, `hint` across `hint_level` `0` through `4` (verifying later hints in teacher notes are withheld above `request.hint_level`), and `debug` with realistic learner `attempt` inputs.
- **Citation and grounding verification:** Manual spot-check log confirming that clicking source chips in the Tutor UI opens the cited textbook PDF page or study note, and that `grounding` labels (`textbook`, `note`, `general`) match what was supplied.
- **Native Nepali & subject sign-off:** Written sign-off from a fluent Nepali-speaking subject teacher confirming mathematical/scientific terminology, Devanagari rendering, grade appropriateness, and mode adherence (e.g., `hint` never leaks the final answer; `debug` identifies the learner's misconception without rewriting the full solution).

### 2.4 Repeatable teacher scoring

Follow [`evals/README.md`](../evals/README.md) and the CLI in `backend/app/evaluation.py`.
 Note that the evaluation tool records model outputs and summarizes human teacher scores; it does not auto-grade answers or prove absence of hallucinations.

**Evidence to collect:**
- **Frozen question set & run artifact:**
  - Command executed: `make eval QUESTIONS=evals/<school-set>.json RUN=<run-name>`
  - Saved run JSON (`evals/runs/<run-name>.json`) recording `run_id`, `started_at`, `question_set.sha256`, `models`, `tutor_status`, and per-item responses/sources, plus the exact `embedding_identity` (model, provider, query/document prefixes, Qdrant collection) and embedding model digest.
- **Independent teacher score sheets:**
  - Blank template generated via `make eval-template RUN=<run-name>`.
  - Completed CSV files (`evals/scores/<teacher>.csv`) from at least two independent teachers scoring all five dimensions (`factual_correctness`, `source_support`, `grade_level`, `language_quality`, `mode_behavior`) on the `0–3` scale.
- **Evaluation summary report:**
  - Output of `make eval-report RUN=<run-name> SCORES="evals/scores/t1.csv evals/scores/t2.csv"` (and `--baseline-run` / `--baseline-scores` when comparing model, prompt, or index changes).
  - **Release gate threshold (from [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md)):**
    - Zero items scored `0` ("Wrong, unsafe or unusable") on safety/factual correctness.
    - At least 80% of scored replies rated acceptable (`>= 2` across applicable dimensions).
    - All inter-rater disagreements of `>= 2` points reviewed and adjudicated by the teaching lead.
    - Zero unscored items or unexplained HTTP errors.
    - Retrieval hit rate (`hits/marked` against `expected_sources`) recorded and reviewed before calibrating `RETRIEVAL_THRESHOLD`.
  - If the run fails these thresholds, keep `AI_ENABLED=false` and ship the portal in library/study-notes/Kolibri mode only.

### 2.5 Kolibri operations and content separation

Follow [`KOLIBRI_GUIDE.md`](KOLIBRI_GUIDE.md), [`INSTALL.md`](INSTALL.md), and [`kolibri-integration.md`](research/kolibri-integration.md).

**Evidence to collect:**
- **Production facility & credential separation:** Verification that the school deployment does **not** use the local development facility (`Digital Himalaya Dev School`) or `devadmin` bootstrap password from `private-local/kolibri-admin-password`. Record that a school-specific facility, super-admin credential (stored in the school's private credential vault), coach accounts, and learner accounts/groups were created directly in Kolibri.
- **Channel import & offline media check:**
  - List of imported Kolibri channels with version numbers, resource counts, and license/attribution records.
  - Confirmation from `/api/services` and `/api/kolibri/channels` that `available_count` and `resource_count` match the imported channels (not metadata-only records with `available: false` and `0` resources).
  - Verification on a student device (with WAN off) that `/courses` lists the channels, each **Open in Kolibri** link (`/en/learn/#/topics/c/<root_id>`) and any study-note `kolibri_url` link opens the channel in Kolibri, and sample videos, HTML5 simulations (e.g., PhET), and exercises play to completion.
- **Role and data separation check:**
  - Coach assigns a lesson/quiz to a test class; learner completes it; coach views progress inside Kolibri.
  - Verification that Digital Himalaya's SQLite catalog (`data/catalog.sqlite3`), Qdrant collection, and logs contain zero Kolibri user accounts, passwords, or learner progress records, and that importing a PDF/note in Digital Himalaya does not modify `kolibri-data`.

### 2.6 Backup and restore

Follow [`INSTALL.md`](INSTALL.md) and [`KOLIBRI_GUIDE.md`](KOLIBRI_GUIDE.md).
Restoring only SQLite or only Qdrant vectors breaks retrieval consistency.

**Evidence to collect:**
- **Coordinated backup manifest:** Dated backup bundle stored on encrypted external/off-server media containing:
  - `content-data` snapshot (`catalog.sqlite3` including documents and `notes` tables, plus all `<id>.pdf` / `<id>.txt` files) taken while `api` is stopped.
  - Matching Qdrant collection snapshot (`dh_curriculum_v1` or configured `dh_` collection).
  - Recorded `embedding_identity` JSON tuple (`embed_model`, `embed_provider`, `embed_api_base_url`, `embed_query_prefix`, `embed_document_prefix`, `qdrant_collection`) and model weight digest.
  - Separate `kolibri-data` stopped-volume backup or Kolibri channel/facility export.
  - Encrypted copy of `.env`, router/switch/AP configuration backup, and the school content register.
- **Disposable restore drill log:** Executed on a clean target environment before school handover, recording:
  1. Stopping `api`, copying `backups/content-data/.` into `/data`, repairing ownership (`chown -R 10001:10001 /data`), and restoring the Qdrant snapshot.
  2. Restoring `kolibri-data` and starting services with `docker compose up -d --no-build`.
  3. Verifying book count, approved study notes, PDF file delivery, an identical cited tutor query returning the same `document_id` and page range, and intact Kolibri learner/coach records.
  4. Measured time-to-restore (RTO) and verification that no `down -v` command appears in operator runbooks.

### 2.7 Low-end phone and network capacity

Follow [`NETWORK.md`](NETWORK.md), [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md), and [`BUILD_PLAN.md`](BUILD_PLAN.md).
Playwright mobile viewport emulation on a desktop is not a physical phone or Wi-Fi airtime test.

**Evidence to collect:**
- **Physical low-end Android device test:** Test report from representative budget Android phones used at the school (cellular data off, connected to student Wi-Fi) covering:
  - Initial page load time, font rendering (Nunito Sans and Noto Sans Devanagari), sticky navbar and footer language toggle (`EN` / `नेपाली`).
  - Searching and filtering the 200+ book catalog (`/api/textbooks/catalog`), opening inline PDFs (`/api/textbooks/{id}/file`) without browser crashes, reading study notes and stepping through progressive hints, and opening Kolibri resources.
- **12-client concurrent library load test:** Measured results with 12 simultaneous client devices browsing textbooks, loading PDFs, reading study notes, and streaming Kiwix/Kolibri content over the actual school AP:
  - p50 and p95 HTTP response latency, error count (must be `0` unhandled 5xx errors), Wi-Fi packet loss, and AP signal coverage in the classroom.
- **Concurrent AI admission test (when AI is enabled):**
  - Because `MAX_CHAT_CONCURRENCY` defaults to `1` (configurable `1–8`) with a `0.1s` slot acquire timeout, send 3 simultaneous tutor requests and record:
    - Accepted-request end-to-end latency on the actual CPU/GPU or hosted link.
    - Immediate, honest HTTP `429` (`Retry-After: 5`) busy responses for excess concurrent requests rather than unbounded queuing or server OOM.
    - Server CPU, RAM, swap, and thermal behavior during sustained inference and during a staff one-book indexing run (`POST /api/admin/index-book`, 4 chunks/batch).

### 2.8 Security and privacy

Follow [`SECURITY.md`](SECURITY.md) and [`NETWORK.md`](NETWORK.md).

**Evidence to collect:**
- **Network segmentation & port scan from student Wi-Fi:** Output of `nmap` / `curl` from a client on the student VLAN (VLAN 20) proving:
  - Permitted: `PORTAL_PORT` (`8090`), approved Kiwix port, and (when enabled) Kolibri ports (`8092`, `8093`).
  - Blocked/unreachable: `STAFF_PORT` (`8091`), raw `api` (`8000`), Ollama (`11434`), Qdrant (`6333`/`6334`), SSH (`22`), router/AP admin interfaces, NOMAD management ports, and peer student devices (client isolation).
  - Verify both host firewall rules and Docker port bindings (`PORTAL_BIND`, `KOLIBRI_BIND`, and `127.0.0.1:8091`), as Docker bridge rules can bypass `ufw`/`iptables` input chains.
  - Confirm IPv6 mirrors the IPv4 policy or routed IPv6 is disabled.
- **Application boundary & auth checks:**
  - From the student listener (`:8090`): `GET /staff` returns `404` and `GET /api/admin/index-status` returns `403` even if a valid Bearer token is supplied.
  - Verify HTTPS termination and `Secure` session cookies with the school's actual host and phones; the supplied Compose listener is plain HTTP.
  - Verify one-time administrator bootstrap, removal of `ADMIN_TOKEN` afterward, session logout/expiry, CSRF rejection, and initial-password change.
  - Verify account creation, teacher-scoped learner password reset, administrator reset, forced password change, account disable session revocation, and restore.
  - Verify a student can access only their own dashboard and sessions, delete a session, and cannot open teacher routes.
  - Verify a teacher can access assigned class rosters and transcripts only, a teacher from another class receives `404`, and every transcript view creates a `transcript_audit` record.
  - Verify oversized staff uploads return `413` before unauthenticated parsing and individual teacher accounts can reach the staff workspace through the management listener.
- **Roster lifecycle and learner credentials:**
  - This build prevents a learner from being assigned to a second class, but it does not yet provide a class withdrawal/transfer or teacher reassignment workflow; add an authorized, audited roster-change path before operating with changing school rosters.
  - Teacher-created learner accounts currently use an initial password entered by the teacher; confirm a safe one-time handoff and first-login change procedure, or replace it with a learner activation flow before production.
  - Login throttling is keyed by username and can lock a staff account after repeated failed attempts; validate the documented operator recovery process or add source-aware throttling before exposing the sign-in page to a broad student network.
- **Operational limitation acknowledgment:** Written school sign-off acknowledging current software boundaries in [`SECURITY.md`](SECURITY.md):
  - Local SQLite stores account records and tutor transcripts; the application does not encrypt these data at rest, and students can permanently delete their own sessions.
  - Assigned-class teachers and administrators can read transcripts; access is logged, but the application does not verify student age or replace school safeguarding policies.
  - PDF extraction is bounded by size (`MAX_UPLOAD_BYTES`) and page count (`MAX_PDF_PAGES` / `MAX_INDEX_PDF_PAGES`), not an OS sandbox; only staff-curated PDFs from trusted sources may be imported.
  - If `CHAT_PROVIDER=openai-compatible` or `EMBED_PROVIDER=openai-compatible` is enabled, prompts, learner attempts, conversation turns, and retrieved textbook passages leave the school network to that provider, requiring explicit school privacy/retention approval.
- **Zero-PII log inspection:** Inspection of `docker compose logs api portal` after student chat and staff sign-in confirming logs contain only timestamp, level, `request_id`, HTTP method, status code, and `duration_ms`—with no student questions, conversation history, query strings, or tokens.

### 2.9 Power recovery and hardware resilience

Follow [`INSTALL.md`](INSTALL.md), [`NETWORK.md`](NETWORK.md), and [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md).

**Evidence to collect:**
- **Measured site power & thermal profile:** Idle and peak wattage measured at the wall for the server, router, switch, and AP during a 12-client + AI session, paired with ambient and server CPU/SSD temperatures over an extended classroom period.
- **UPS runtime & graceful shutdown test:**
  - Cut mains power to the UPS while the system is serving requests.
  - Record battery runtime and verify automated or operator-triggered graceful shutdown (`docker compose down` / clean OS halt—never `docker compose down -v`) completes before battery exhaustion.
- **Cold-boot & ungraceful power-loss recovery:**
  - Restore power with WAN still disconnected; verify the server, router/DHCP/DNS, Docker daemon, `api`, `portal`, `kolibri`, and local model/vector services start automatically (`restart: unless-stopped`).
  - Check system clock behavior after power loss (NTP/RTC) and confirm TLS/token/log timestamps behave as expected.
  - Run `./scripts/check-offline.sh`, verify SQLite (`catalog.sqlite3`), uploaded PDFs, approved study notes, Qdrant vectors, and Kolibri channels are intact, and re-import any book left in `status: "indexing"` or `index_status: "indexing"` if power failed mid-ingestion.

---

## 3. Release sign-off checklist

Do not mark a deployment ready until every row below is completed with linked private evidence.

| Gate | Required evidence artifact | Verified on school hardware? | Reviewer / role | Date | Status |
| --- | --- | --- | --- | --- | --- |
| 1. Software baseline | CI run URL + local `make check`, `make test`, `make build` output ([`VERIFICATION.md`](VERIFICATION.md)) | N/A (software) | Engineering | | Pending |
| 2. Offline LAN operation | WAN-unplugged `/api/services` output + phone DevTools zero-external-request capture ([`NETWORK.md`](NETWORK.md)) | Required | Network operator | | Pending |
| 3. Content & note approvals | Signed content register + `GET /api/admin/notes` & `index-status` exports ([`CONTENT_LICENSES.md`](CONTENT_LICENSES.md)) | Required | School lead / curriculum reviewer | | Pending |
| 4. Bilingual tutor & scoring | `evals/runs/<run>.json`, teacher CSVs, and `make eval-report` passing thresholds ([`evals/README.md`](../evals/README.md)) | Required (if `AI_ENABLED=true`) | English & Nepali subject teachers | | Pending |
| 5. Kolibri separation | Non-dev facility proof, `/api/kolibri/channels` output, offline learner/coach test ([`KOLIBRI_GUIDE.md`](KOLIBRI_GUIDE.md)) | Required (if Kolibri enabled) | School coach / admin | | Pending |
| 6. Backup & restore drill | Coordinated backup manifest + clean-instance restore log and cited query check ([`INSTALL.md`](INSTALL.md)) | Required | System operator | | Pending |
| 7. Phone & LAN capacity | Low-end Android test sheet + 12-client library and 3-client AI load logs ([`DEMO_SCRIPT.md`](DEMO_SCRIPT.md)) | Required | Field engineer | | Pending |
| 8. Security & privacy | Student-VLAN `nmap`/`curl` scan, SSH staff tunnel check, log inspection, privacy sign-off ([`SECURITY.md`](SECURITY.md)) | Required | Security reviewer / school head | | Pending |
| 9. Power & UPS recovery | Wattage/thermal log, UPS graceful shutdown test, cold-boot WAN-off check ([`INSTALL.md`](INSTALL.md)) | Required | Site technician | | Pending |
