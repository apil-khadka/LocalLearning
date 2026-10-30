# Build plan

Deliver a useful local library first, then enable supervised AI only when its quality and operational gates pass.
The application runs independently of the software that manages the school's offline services.

## Architecture decision

Use React/TypeScript/Vite for static browser assets, FastAPI for the application API, SQLite/filesystem for the document catalog, a switchable Ollama/OpenAI-compatible chat provider, Ollama for local embeddings, and a dedicated Qdrant collection for retrieval.
Use Kiwix for offline reference articles and Kolibri for classroom courses, learner progress, and assessments.
The repository provides an optional pinned Kolibri Compose profile and otherwise connects to a verified existing Kolibri service.
Reuse NOMAD-managed services where available through documented service interfaces instead of installing duplicate services.
NOMAD is an optional provisioning dependency, not part of the student authentication boundary.

Do not run Open WebUI as a second student-facing chat application in the first release.
Do not add Jellyfin alongside Kolibri until a concrete content need justifies a second media service.
An E-Pustakalaya collection is a separate licensing/integration task; local PDF support is not a claim that E-Pustakalaya is installed or licensed.
Choose actual model and hardware combinations through measurement, not the names shown in a conceptual diagram.

## Milestones and exit conditions

| Milestone | Deliverable | Exit condition |
| --- | --- | --- |
| Foundation | Portal, typed API, local catalog, ingestion, service adapters, containers, CI | Automated checks pass; outages and empty configuration are truthful |
| Local curriculum integration | Approved chapter, real embedding model, dedicated persistent vector collection | Real model answer with a valid PDF page; out-of-scope questions have no false source chips |
| School network prototype | Router/AP configuration, protected management path, stable server address | Phone reaches approved resources with cellular and WAN off; student cannot reach admin or raw AI ports |
| Teaching and capacity review | English/Nepali task set, teacher scoring, measured library and AI load | Teacher-approved answers; no severe unsafe outputs; acceptable measured latency |
| Pilot readiness | Backups, restore drill, UPS shutdown/restart, operator training | School signs off on operation, safety and content permission |

## Initial implementation boundaries

The software foundation includes the integration code and test doubles needed to develop without a local model or API key.
It does not include a model, vector server, downloaded encyclopedia, video channel, official textbook, school account system, or management VLAN configuration.
Import is synchronous and bounded to one document at a time in one API process.
AI requests beyond the configured concurrency limit receive a retry response instead of an unbounded queue.
Changing API worker count requires shared admission control and ingestion coordination first.

Source chips identify retrieved passages; they do not prove every model-generated sentence is entailed by a source.
The relevance threshold is a starting configuration that requires curriculum-specific calibration.
Chunking is page-local with overlap; OCR, layout-aware extraction, multilingual evaluation and answer entailment checks are later quality work.
Current imports create a new immutable document ID for changed content or metadata; a withdrawal/version-management workflow is still needed before a school pilot.
Changing embedding model weights, prefixes or dimensions requires an intentional catalog/index migration, including when weights change under the same model tag.

## Next priorities

1. Run the OpenAI-compatible chat path against the configured endpoint with non-identifying test prompts, or switch to local Ollama.
2. Connect a real Ollama embedding service and Qdrant on target Ubuntu hardware; run the opt-in live-service test.
3. Import a permitted searchable Grade 8 chapter and prepare in-scope, no-match, Nepali and prompt-injection evaluation questions.
4. Review the proposed network on actual router/AP hardware and test the firewall from student devices.
5. Add content withdrawal, bounded background ingestion with recovery, and catalog/index migration before expanding collections.
6. Measure 12 simultaneous library clients separately from three AI requests; keep AI off if review fails.
7. Run the complete [offline acceptance script](DEMO_SCRIPT.md), restore drill and operator training before deployment.

## Public website

GitHub Pages serves the static project overview from `site/`.
It presents the architecture, implementation plan and current evidence without exposing planning attachments or school information.
It does not run the school API or proxy AI requests.
The school application is deployed separately on the LAN.
