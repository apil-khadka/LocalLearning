# Contributing

Keep the student experience usable on low-end phones and entirely local after provisioning.
Build on the documented service contracts and avoid adding a cloud dependency for a core school workflow.

Run `make setup`, `make check`, backend tests, browser tests and the frontend build before proposing changes.
Changes to ingestion, authorization, retrieval or deployment should include meaningful workflow/security regression coverage.
Browser contract fixtures are not proof that a real model or school network works.

Never commit `.env`, `internal/`, school content, student information, private network configuration, model files or backups.
Check `git diff --cached --name-only` before committing.
Keep public documentation factual and separate verified results from future targets.

See [the build plan](docs/BUILD_PLAN.md) for next work and [security guidance](docs/SECURITY.md) for disclosure.
Contributions are submitted under the repository's Apache 2.0 license unless explicitly agreed otherwise.
