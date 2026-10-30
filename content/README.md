# Learning content

`sample/force-and-motion.txt` is an original demonstration note, not an official textbook.
Use it to exercise staff import and retrieval before adding approved curriculum material.
Text uploads use a single logical page; PDF citations use the original PDF page number, not printed textbook numbering.

Use `make books-pilot` to fetch Wikijunior Biology and `make books-more` to fetch selected chapters from three additional Wikibooks titles.
The scripts write text and revision-level attribution manifests only under ignored `content/private/wikibooks/`.
`books-more` downloads a bounded set of chapters rather than mirroring complete books.
To fetch one title after an interrupted request, run `make books-more BOOKS=solar-system` or `make books-more BOOKS=elementary-geometry`.
The fetched books are not reviewed for Nepal curriculum alignment and must be teacher-reviewed before classroom use.

Use `make books-cdc-k12` to fetch official CDC Nepal Kindergarten–Grade 12 PDFs into ignored `content/private/cdc/k12/`.
It scans the G, B, M, S, T, and E textbook feeds and adds CDC's current early-childhood curriculum page.
The script records the feed, catalog page, source page, download URL, file size, and SHA-256 checksum.
It throttles requests, bounds file and corpus sizes, and resumes verified files after an interrupted run.
To expose the private folder to the local API container, start it with `COMPOSE_FILE=docker-compose.yml:internal/compose-network.yml docker compose up -d --wait --force-recreate api`.
Then run `COMPOSE_FILE=docker-compose.yml:internal/compose-network.yml make books-import-k12` to add those PDFs to the local student library.
Kindergarten materials appear under K; CDC resources that do not declare one grade appear under All grades.
This library import stores books for reading and does not require embeddings, Qdrant, or the AI tutor.
The imported copies remain in the ignored Compose data volume and are not part of the public repository.

Keep school files in `content/private/` or the application's data volume, both excluded from Git.
The owner confirmed permission for the local prototype copies; the fetcher records official CDC source pages and checksums for refresh and review.
See [content licensing](../docs/CONTENT_LICENSES.md) before distributing third-party material.
