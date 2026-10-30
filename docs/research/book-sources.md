# Book source and reuse review

Reviewed on 2026-10-30 for the Digital Himalaya local pilot.

## Decision

Use *Wikijunior:Biology* from Wikibooks for the first local retrieval test.
Wikijunior says its books are distributed under CC BY-SA, and the Wikibooks project states its content uses CC BY-SA 4.0.
The prototype fetcher stores a text-only printable version and revision-linked attribution manifest under ignored `content/private/`.
The fetch retrieved 33 source-page records plus the printable source page, producing a 62 KB local text file; no images or other media were fetched.
This is general beginner biology, not a Nepal curriculum-approved textbook.

The Open Textbook Library entry for *Environmental Biology* is a possible later test source because its record identifies CC BY and its publisher page identifies CC BY 4.0 except where otherwise noted.
The publisher PDF endpoint returned HTTP 403 to the normal metadata/download check, so it was not retried or bypassed.

The publisher identifies the book as introductory college science and says it was last updated in May 2021, so teachers should review its U.S.-specific examples and any third-party exclusions before using it with Nepalese students.

The book license is CC BY 4.0 except where otherwise noted, so preserve the title, author, source link, license link, attribution text, and any notices for excluded material when storing extracted passages or deriving a local index.

CC BY 4.0 permits sharing and adaptation, including commercially, when its attribution and other terms are followed; it does not guarantee that publicity, privacy, or other third-party rights are cleared.

Do not treat the catalog's CC0 metadata license as the book's license.

## Provider findings

### E-Pustakalaya / OLE Nepal

E-Pustakalaya's current homepage says its contents are free for learning but cannot be used commercially, separately hosted, or modified.
It also says website contents are under Creative Commons unless an item explicitly states otherwise.

A featured Nepali title, *बालबालिकामा पढ्ने बानीको विकास* (*Developing Reading Habits in Children*), has a 1.14 MB item page naming author Vinaya Kasajoo, publisher विवेक सिर्जनशील प्रकाशन, and 40 pages, but its visible “Read Book” action requires login.

That title's page links its applicable license as CC BY-NC-ND 3.0, which permits noncommercial sharing of the unchanged work but does not permit distributing an adaptation.
The E-Pustakalaya homepage separately prohibits separately hosting or modifying its contents, so do not copy its books into this application's corpus without written permission or an item-specific license that clearly allows that use.

The item-specific license and any explicit item notice take precedence over an overview page's general license statement.

Before using any other E-Pustakalaya item, inspect its own license and exclusions because OLE Nepal says it obtains permissions from authors, publishers, and organizations and its older advisory notes that rights can be item-specific.

### Nepal Curriculum Development Centre (CDC)

The official CDC catalog lists textbooks and provides e-copy links, including *English Grade 8*, but the catalog entry reviewed did not state a reuse license.

Public availability of those e-copy URLs is not evidence that the PDFs can be redistributed, transformed, or processed into a public corpus, so do not download or publish CDC textbook files until CDC provides an explicit license or written permission for the intended use.

A low-impact metadata-only catalog listing can be considered separately from downloading the underlying book files, subject to the site's current access rules.

### Open Textbook Library and Open Oregon

The Open Textbook Library discovery page states that its bibliographic records are CC0 and that textbook and subject records are available through a JSON API.

The *Environmental Biology* record identifies author Matthew R. Fisher, publisher Open Oregon Educational Resources, English language, a PDF format, and CC BY as the book's conditions of use.

The publisher's book page offers PDF, EPUB, XML, and other downloads and states that the book is CC BY 4.0 except where otherwise noted.

The publisher identifies a [PDF download page](https://openoregon.pressbooks.pub/envirobiology/open/download?type=pdf), and the item rights are documented on the [publisher book page](https://openoregon.pressbooks.pub/envirobiology/).
Automated access to the publisher page and download endpoint returned HTTP 403 during this review, so this title was not downloaded.

The Open Textbook Library is a referatory, so each record's Conditions of Use must be checked rather than assuming every listed title has the same license.

### OER Commons

OER Commons says each resource has its own conditions-of-use label and that the resource's own terms and copyright statement must be checked when its rights are unclear.

This makes OER Commons useful for finding additional candidates, but not a blanket authorization to bulk-download its catalog.

### Project Gutenberg

Project Gutenberg states that most of its ebooks are public domain in the United States, but users outside the United States must check local law before downloading, copying, or redistributing an individual work.

Do not bulk-import Project Gutenberg titles for a Nepal-targeted public service until the selected work's rights status in Nepal has been verified.

## Safe pilot rules

Start with one openly licensed title and a bounded number of files; do not mirror an entire provider library as the first test.

Before any book download, record the exact item page, author, title, license URL, file URL, retrieval date, file checksum, and any exclusions in the local rights manifest.

Keep downloaded books, extracted full text, embeddings, and provider credentials out of Git; the repository already ignores `content/private/` and `.env`.

Keep public project documentation to catalog metadata, provenance, license notices, and source links unless a book is explicitly selected for distribution with its complete attribution and license terms.

Use a rate-limited catalog-first workflow, obey provider access controls and site terms, and skip items with missing, ambiguous, or NoDerivatives rights for AI retrieval.

## Primary sources

- [OLE Nepal E-Pustakalaya overview and collection-level terms](https://olenepal.org/digital-learning-solutions/e-pustakalaya/).
- [E-Pustakalaya homepage with its learning-only, no-separate-hosting, and no-modification notice](https://pustakalaya.org/en/).
- [E-Pustakalaya item page for Developing Reading Habits in Children](https://pustakalaya.org/documents/detail/db8b2a80-5f00-4ec3-b04c-41e77703615d/).
- [CC BY-NC-ND 3.0 license linked from that E-Pustakalaya item](https://creativecommons.org/licenses/by-nc-nd/3.0/).
- [OLE Nepal's advisory note on item-specific author and publisher permissions](https://www.olenepal.org/our-stories/e-pustakalaya-advisory-panel/).
- [CDC online catalog entry linking to an English Grade 8 e-copy](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id_article=157&lvl=cmspage&pageid=4).
- [Open Textbook Library discovery and JSON API information](https://open.umn.edu/opentextbooks/discovery).
- [Open Textbook Library record for Environmental Biology](https://open.umn.edu/opentextbooks/textbooks/687).
- [Open Oregon publisher page for Environmental Biology](https://openoregon.pressbooks.pub/envirobiology/).
- [Creative Commons Attribution 4.0 deed](https://creativecommons.org/licenses/by/4.0/).
- [OER Commons usage-rights guidance](https://help.oercommons.org/support/solutions/articles/42000046845-usage-rights).
- [Project Gutenberg permission guidance for users outside the United States](https://www.gutenberg.org/policy/permission.html).
- [Wikijunior project overview and CC BY-SA distribution statement](https://en.wikibooks.org/wiki/Wikijunior).
- [Wikijunior Biology source book](https://en.wikibooks.org/wiki/Wikijunior:Biology).
- [Wikibooks project description and CC BY-SA 4.0 license statement](https://meta.wikimedia.org/wiki/Wikibooks/en).
