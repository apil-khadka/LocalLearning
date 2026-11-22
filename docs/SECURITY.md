# Security and privacy

The application supports named local accounts, but a school deployment still requires review of privacy, HTTPS, network controls, and retention before students use it.
Keep management services away from student networks and the public internet.
The [network policy](NETWORK.md) is part of deployment, not something the React UI can enforce.

The production student listener blocks `/staff` and `/api/admin`.
The staff listener defaults to host loopback; direct staff-VLAN access requires an explicit `STAFF_BIND` plus firewall enforcement, or staff can use SSH forwarding.
Students, teachers, and administrators have separate local accounts, roles, and password hashes.
The one-time `ADMIN_TOKEN` authorizes the first administrator setup only; after any account exists, it no longer authorizes staff APIs.
Administrators create teacher accounts and assign classes; teachers create learner accounts and manage class activity.
New accounts must change their initial password before using the application.
Administrators can reset an account to a temporary password and disable or restore it; teacher password resets are limited to learners in the teacher's assigned class.
Resetting a password revokes the account's sessions and requires a password change at next sign-in; disabling an account also revokes its sessions.
Passwords are stored as scrypt hashes, sessions use random opaque tokens stored as hashes, cookies are HttpOnly and SameSite=Strict, and state-changing cookie requests require a CSRF token.
Login attempts are limited to five per username in a 15-minute window, and sessions expire after seven days.
Set `AUTH_COOKIE_SECURE=true` behind HTTPS; the supplied Compose listener is plain HTTP, so it is not a production TLS terminator.
The browser keeps the CSRF token in memory; it does not store session or CSRF tokens in localStorage or sessionStorage.
The development server exposes the staff page for development and must not be used as the school deployment boundary.

Student tutor sessions and transcripts are stored in the local SQLite data volume until the learner deletes a session.
Learners can read and permanently delete their own sessions.
Teachers can read transcripts only for currently assigned classes, and each class-session listing and full transcript view is recorded in `transcript_audit` without storing viewed message text in that audit row.
Learners can be assigned to one active class at a time; a teacher cannot add a learner already assigned to another class.
Deactivated learners disappear from teacher rosters and transcript lists, while administrators retain access for school records.
Restoring a deactivated account requires a password change before the user can continue.
Administrators can review access events through the staff-only `/api/admin/transcript-audit` endpoint.
Administrators can review transcripts across the school.
Transcript contents are not encrypted by the application at rest; protect the host, SQLite volume, and backups with operating-system and storage controls.

Kolibri uses its own coach and learner accounts, independently of Digital Himalaya accounts.
Its web and packaged-content ports are separate from the protected portal listeners, so keep them loopback-bound until the facility is configured and firewall rules are reviewed.
Kolibri account data, roles, course content and progress are not synchronized with the tutor or this application's staff workspace.

Upload authorization runs before request-body parsing.
Request/file/page/text limits bound normal ingestion, and imports allow only PDF/UTF-8 text with plain filenames.
File delivery resolves a validated document ID through the local catalog and never accepts a caller-controlled filesystem path.
PDFs are untrusted active documents even after text extraction; curate them and keep browser/PDF software patched.
The extractor has bounded pages/text but is not a hardened process sandbox against all malicious PDF resource-exhaustion cases.
Add isolated worker execution, CPU/memory/time budgets and malware review before accepting untrusted contributors' documents.

Teaching notes are written by teachers and administrators through the protected `/api/admin/notes` routes, which the student listener blocks.
Teachers cannot approve their own notes; a different teacher or an administrator must complete review.
Authenticated note creation and approval records the signed-in account; the legacy free-text reviewer value is accepted only before the first account is created.
Note text, the learner's attempt in check-my-work mode, retrieved text and conversation history are untrusted model inputs.
The model has no execution tools and browser output is escaped text.
Prompt injection and wrong educational answers still require evaluation; prompt wording and a score threshold are not safety proofs.
AI is off by default, and supervised use/age policies must be approved before enabling it.
The tutor uses the signed-in student's configured grade when one is assigned; a student account is not age verification.
Kolibri accounts are not shared with the tutor.

Application logs contain request IDs, method, status and duration without bodies, query strings, credentials or exception messages.
Nginx access logging and Uvicorn access logging are disabled in the supplied container configuration.
When reporting a failure, provide the request ID, action, time and observed status; omit student questions and tokens.
Inspect upstream service logging/retention settings separately.

The browser does not call model/vector services or external assets directly.
The API can use local Ollama, local LM Studio, or a configured OpenAI-compatible chat provider.
With a hosted provider selected, prompts, prior conversation turns, learner attempts, and retrieved textbook excerpts are sent from the API to that provider.
Review its privacy, retention, and data-processing terms before sending student data; use non-identifying test prompts during initial integration.
Network egress policy remains the operator's responsibility.
`/api/services` reachability checks do not verify content completeness, safety, model quality or actual client routing.
Public service URLs should point only to approved learner destinations.

For a suspected vulnerability, avoid posting credentials, school data or exploit details in public issues.
Use the repository's private vulnerability-reporting feature when enabled; otherwise contact the maintainer through an already verified private channel.
