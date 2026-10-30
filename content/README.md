# Learning content

`sample/force-and-motion.txt` is an original demonstration note, not an official textbook.
Use it to exercise staff import and retrieval before adding approved curriculum material.
Text uploads use a single logical page; PDF citations use the original PDF page number, not printed textbook numbering.

Use `make books-pilot` to fetch Wikijunior Biology and `make books-more` to fetch selected chapters from three additional Wikibooks titles.
The scripts write text and revision-level attribution manifests only under ignored `content/private/wikibooks/`.
`books-more` downloads a bounded set of chapters rather than mirroring complete books.
To fetch one title after an interrupted request, run `make books-more BOOKS=solar-system` or `make books-more BOOKS=elementary-geometry`.
The fetched books are not reviewed for Nepal curriculum alignment and must be teacher-reviewed before classroom use.

Keep school files in `content/private/` or the application's data volume, both excluded from Git.
Require license or permission and source attribution on every import.
See [content licensing](../docs/CONTENT_LICENSES.md) before distributing third-party material.
