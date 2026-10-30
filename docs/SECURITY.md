# Security and privacy

This foundation is for a controlled local prototype and requires site review before student deployment.
Keep management services away from student networks and the public internet.
The [network policy](NETWORK.md) is part of deployment, not something the React UI can enforce.

The production student listener blocks `/staff` and `/api/admin`.
The staff listener is bound to host loopback; staff use the local console or SSH forwarding.
Every staff API request additionally requires a random configured Bearer token of at least 32 characters.
An empty token disables staff access.
The browser keeps the token only in memory; no build-time secret, cookie, localStorage or sessionStorage is used.
Use authenticated individual staff accounts, rotation and shared rate limiting before broad deployment.
The development server exposes the staff page for development and must not be used as the school deployment boundary.

Upload authorization runs before request-body parsing.
Request/file/page/text limits bound normal ingestion, and imports allow only PDF/UTF-8 text with plain filenames.
File delivery resolves a validated document ID through the local catalog and never accepts a caller-controlled filesystem path.
PDFs are untrusted active documents even after text extraction; curate them and keep browser/PDF software patched.
The extractor has bounded pages/text but is not a hardened process sandbox against all malicious PDF resource-exhaustion cases.
Add isolated worker execution, CPU/memory/time budgets and malware review before accepting untrusted contributors' documents.

Retrieved text and conversation history are untrusted model inputs.
The model has no execution tools and browser output is escaped text.
Prompt injection and wrong educational answers still require evaluation; prompt wording and a score threshold are not safety proofs.
AI is off by default, and supervised use/age policies must be approved before enabling it.
The current grade selector is not identity or age verification.

Student conversations remain in page memory; the server does not persist prompts, answers, student names or analytics.
Application logs contain request IDs, method, status and duration without bodies, query strings, credentials or exception messages.
Nginx access logging and Uvicorn access logging are disabled in the supplied container configuration.
When reporting a failure, provide the request ID, action, time and observed status; omit student questions and tokens.
Inspect upstream service logging/retention settings separately.

No browser calls to model/vector services or external assets are needed.
Network egress policy remains the operator's responsibility; only configure local service endpoints.
`/api/services` reachability checks do not verify content completeness, safety, model quality or actual client routing.
Public service URLs should point only to approved learner destinations.

For a suspected vulnerability, avoid posting credentials, school data or exploit details in public issues.
Use the repository's private vulnerability-reporting feature when enabled; otherwise contact the maintainer through an already verified private channel.
