# Additional learning-book candidates

Reviewed on 2026-10-30 for the Digital Himalaya local prototype.
This note identifies additional titles and verifies source and reuse information from the publishers or hosting projects themselves.
It does not constitute Nepal curriculum approval or a substitute for a teacher's content review.

## Recommended prototype candidates

### Wikijunior: How Things Work

The book is explicitly written for ages 8-12 and explains everyday machines and technology in child-friendly language.
The current book page lists publishable, developing, and stub articles and says its text is available under the Creative Commons Attribution-ShareAlike license.
Its book category currently contains 53 pages, so the fetcher should cap page counts and select only complete or publishable chapters rather than importing every stub.
The official printable-version page or the Wikibooks MediaWiki API can supply current text; record each source page's revision ID and the item-level license with the extracted corpus.
This is a good small engineering pilot, with teacher review needed because the book is partly developed.
Sources: [book and age range](https://en.wikibooks.org/wiki/Wikijunior:How_Things_Work), [book page category](https://en.wikibooks.org/wiki/Category:Book:Wikijunior:How_Things_Work), [Wikijunior license statement](https://en.wikibooks.org/wiki/Wikijunior).

### Wikijunior: The Elements

This is a child-focused chemistry and periodic-table book with a printable version hosted by Wikibooks.
The printable version includes an explicit CC BY-SA 3.0 license notice, so retain that exact license version in the attribution manifest for this copy.
It is a practical text-extraction candidate, but the page has older sections and should receive a teacher's science review before student use.
Use the current printable page or MediaWiki API and store revision-linked attribution; do not treat the Wikijunior collection's general license notice as changing the printable copy's stated version.
Sources: [book page](https://en.wikibooks.org/wiki/Wikijunior:The_Elements), [printable text and explicit license notice](https://en.wikibooks.org/wiki/Wikijunior:The_Elements/Printable_version), [Wikijunior collection rights statement](https://en.wikibooks.org/wiki/Wikijunior).

### Siyavula: Natural Sciences Grade 9

Siyavula's official Grade 9 page provides a broad learner's textbook covering life science, matter, Earth systems, and space science, with a chapter outline and downloadable formats.
The same page says the textbook content is under a Creative Commons Attribution license, and Siyavula's download catalog distinguishes branded CC BY-ND editions from unbranded CC BY editions.
The unbranded CC BY EPUB is the suitable variant for text extraction and adaptation; preserve Siyavula attribution and note that the book follows South Africa's curriculum, including locally specific examples.
A catalog link labeled for the Grade 9 Natural Sciences CC BY EPUB resolved during this review to a file named `Gr9_PhysicalSciences_Learner_Eng_CC-BY.epub`, so verify the downloaded file's title and embedded license before importing it.
The browser could not inspect the EPUB payload itself, so the binary identity and size remain unverified.
Sources: [Grade 9 book and chapter/download page](https://www.siyavula.com/read/za/natural-sciences/grade-9), [download catalog and per-variant licenses](https://www.siyavula.com/read), [CC BY 3.0 license](https://creativecommons.org/licenses/by/3.0/).

## Candidate requiring content freshness review

### Wikijunior: Solar System

The current Wikijunior page marks this as a featured book and provides a substantial set of planet, moon, glossary, and activity sections under Wikibooks' Creative Commons Attribution-ShareAlike terms.
A downloadable 105-page PDF is available from Wikimedia Commons, but its own front matter identifies the snapshot as August 2005, licenses that PDF under GFDL 1.2, and describes Pluto as a planet.
Do not use that old PDF as a student-facing source; if selected for a prototype, fetch the current Wikibooks pages through the API, retain the current page revision and license data, and teacher-review scientific currency first.
Sources: [current book page](https://en.wikibooks.org/wiki/Wikijunior:Solar_System), [historical 105-page PDF and its own license/date notice](https://upload.wikimedia.org/wikipedia/commons/9/96/Wikijunior-Solar_System.pdf).

## Retrieval and attribution workflow

Use Wikibooks' official MediaWiki API with a bounded page request and plain-text extracts, following the existing `scripts/fetch_wikijunior_biology.py` pattern.
For each source, store the exact book URL, page URLs with revision IDs, retrieval timestamp, license URL/version, and a checksum in the private `content/private/` manifest.
Keep downloaded full text and book binaries outside Git, as configured by `.gitignore`.
Filter incomplete/stub chapters, preserve headings and page/chapter boundaries for citations, and review source-page notices for third-party content before ingestion.
A public catalog may contain title, source link, and license metadata, but should not mirror book content unless the chosen license and attribution are followed.

## Prototype fetch selection

The local fetch command selects text-only chapters from *Wikijunior:Human Body*, *Wikijunior:Solar System*, and *Geometry for Elementary School*.
It requests current Wikibooks page revisions through the official API, records each selected page revision and a checksum, and writes content only to ignored `content/private/wikibooks/`.
The Human Body selection includes its overview, heart, blood, lungs, skeleton, and brain pages.
The title page targets ages 8-12 but classifies most sections as developing or stubs, so this selection is incomplete and needs teacher review.
The Solar System selection includes the book overview, Sun, Earth, Moon, Mars, and Jupiter pages.
The Geometry selection includes the book overview, Concepts, Angles, Plane shapes, Measurements, and Symmetry pages.
The Solar System extraction uses current Wikibooks pages rather than the stale 2005 Commons PDF snapshot noted above.
These partial extracts are for integration testing and still require teacher review before classroom use.

The fetched private text is about 19.0 KB for Human Body, 20.9 KB for Geometry, and 43.6 KB for Solar System, with a separate JSON manifest for each title.
The original private Biology fixture remains about 62.3 KB with its own attribution manifest.
Together, the four private text files contain about 145.8 KB of content.
The download scripts and source notes are public, but no book text or manifest is tracked in Git.

The official [Wikijunior Human Body page](https://en.wikibooks.org/wiki/Wikijunior:Human_Body) documents its audience and section status.
The [Geometry for Elementary School page](https://en.wikibooks.org/wiki/Geometry_for_Elementary_School) and its [book category](https://en.wikibooks.org/wiki/Category:Book:Geometry_for_Elementary_School) expose the geometry chapter pages.
Wikibooks' project-wide license statement covers content under [CC BY-SA 4.0](https://meta.wikimedia.org/wiki/Wikibooks/en).

## Sources not added to the fetch list

OpenStax books can be downloaded from their official book pages, but titles such as *Biology 2e* use CC BY-NC-SA 4.0 and require derivatives to remain under that license, so they are not a default fit for this Apache-licensed prototype corpus.
E-Pustakalaya and CDC terms remain item-specific or unclear in the existing [book-source review](book-sources.md), so do not copy their PDFs into the local corpus without item-level permission or explicit reuse terms.
Sources: [OpenStax Biology 2e license and format](https://openstax.org/books/biology-2e/pages/preface), [OpenStax license guidance](https://help.openstax.org/s/article/Openstax-textbook-licensing-and-customization).
