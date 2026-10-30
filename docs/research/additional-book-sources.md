# CDC Nepal textbook catalog inventory, Kindergarten–Grade 12

Reviewed on 2026-10-30 for the Digital Himalaya prototype.
Apil confirms that the project has rights to use the materials being gathered for this prototype.
This scan prioritizes official catalog provenance, Grades 1–12 coverage, language variants, and direct provider download links.
Keep provider title, grade, subject, language, edition, item page, direct file URL, retrieval date, and checksum in the local content manifest.

## Private prototype crawl snapshot

On 30 October 2026, the local crawler fetched 216 PDFs totaling 1,848,082,014 bytes from official CDC pages.
It traversed the [General Textbook G feed](https://moecdc.gov.np/category/textbook--g-/), [Bhote B feed](https://moecdc.gov.np/category/textbook--b-/), [Madrasa M feed](https://moecdc.gov.np/category/textbook--m-/), [Sanskrit S feed](https://moecdc.gov.np/category/textbook--s-/), [Technical T feed](https://moecdc.gov.np/category/textbook--t-/), and [Early childhood E feed](https://moecdc.gov.np/category/textbook--e-/).
It also fetched the current [Early Childhood Development and Education curriculum](https://moecdc.gov.np/content/671/curriculum-of-early-childhood-development-and-education-/), which CDC currently lists under an E syllabus category rather than its textbook E feed.

| CDC source stream | PDFs fetched |
| --- | ---: |
| General Textbook G | 137 |
| Bhote B | 17 |
| Madrasa M | 21 |
| Technical T | 38 |
| Early childhood E | 2 |
| Early childhood syllabus resource | 1 |
| Sanskrit S | 0 in the current feed crawl |
| **Total** | **216** |

The grade counts are K: 2; Grade 1: 7; Grade 2: 7; Grade 3: 7; Grade 4: 15; Grade 5: 16; Grade 6: 16; Grade 7: 17; Grade 8: 13; Grade 9: 48; Grade 10: 46; Grade 11: 12; Grade 12: 9; and one cross-grade reference.
The crawler verified the PDF signature and records the direct source URL, retrieval date, file size, and SHA-256 checksum in the ignored local manifest.
The prototype owner's permission statement covers local prototype use; all downloaded PDFs remain under ignored `content/private/` and are not part of the public repository.

The live feed crawl does not enumerate every item in CDC's separate library shelves.
In particular, the official Grade 9T–12T technical shelves can contain additional catalog-only material; the OPAC timed out from the local environment during this pass, so those shelves are not included in the 216-file count.
The [Grade 12T shelf](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=87&lvl=etagere_see) and [Grade 11T shelf](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=86&lvl=etagere_see) remain good sources to retry during a later catalog refresh.

## Official catalog coverage and enumeration

The Curriculum Development Centre (CDC), Nepal exposes twelve numbered academic-grade shelves in its online library catalog, from Grade One through Grade Twelve.
The direct shelf routes follow the observed `id=11` through `id=22` pattern with `lvl=etagere_see`; verify the displayed shelf heading before importing because CDC also uses numeric IDs for subject and other categories.
The [CDC library catalog](https://lib.moecdc.gov.np/catalog/opac_css/) and its [combined Textbooks shelf page](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id_rubrique=105&lvl=cmspage&pageid=6) link the numbered grade shelves and show item-level catalog fields.

| Grade | Official CDC catalog shelf |
| --- | --- |
| 1 | [Grade One](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=11&lvl=etagere_see) |
| 2 | [Grade Two](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=12&lvl=etagere_see) |
| 3 | [Grade Three](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=13&lvl=etagere_see) |
| 4 | [Grade Four](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=14&lvl=etagere_see) |
| 5 | [Grade Five](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=15&lvl=etagere_see) |
| 6 | [Grade Six](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=16&lvl=etagere_see) |
| 7 | [Grade Seven](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=17&lvl=etagere_see) |
| 8 | [Grade Eight](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=18&lvl=etagere_see) |
| 9 | [Grade Nine](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=19&lvl=etagere_see) |
| 10 | [Grade Ten](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=20&lvl=etagere_see) |
| 11 | [Grade Eleven](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=21&lvl=etagere_see) |
| 12 | [Grade Twelve](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=22&lvl=etagere_see) |

For completeness, Grades 9–12 also have separate official technical and vocational shelves: [Grade 9T](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=84&lvl=etagere_see), [Grade 10T](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=85&lvl=etagere_see), [Grade 11T](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=86&lvl=etagere_see), and [Grade 12T](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=87&lvl=etagere_see).
The [Grade 10T shelf](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=85&lvl=etagere_see) includes agriculture, animal science, computer engineering, civil engineering, and electrical learning resources, showing that the regular academic shelves alone do not cover every CDC book.

The live CDC website divides textbook posts among several category feeds rather than one complete grade-by-grade list.
The [General Textbook (G) feed](https://moecdc.gov.np/category/textbook--g-/) contains multiple pages, with pages 20 and 21 showing Grade 11 and Grade 12 titles and the page navigation reaching page 22.
The [Technical Textbook (T) feed](https://moecdc.gov.np/category/textbook--t-/) has separate pagination and includes Grades 9–10 vocational titles, while its catalog counterparts extend technical resources through Grade 12.
Other official feeds expose additional subject and language streams: [B](https://moecdc.gov.np/category/textbook--b-/) includes Bhote-language books, [M](https://moecdc.gov.np/category/textbook--m-/) includes Urdu, Arabic, and Diniyat titles, [S](https://moecdc.gov.np/category/textbook--s-/) includes Sanskrit and Gurukul subject titles, and [E](https://moecdc.gov.np/category/textbook--e-/) includes early-childhood and supplementary material.
These labels reflect the titles shown in the official feeds; they are not a CDC-published data dictionary for the letter codes.

### Initial sample count and confidence

The counts below are an earlier partial snapshot of CDC's General Textbook (G) feed, not the later local prototype crawl and not a claim that the full library catalog has been counted.
I fetched the HTML listing pages 1–12 and counted each title row once, retaining translations, self-study materials, and local-language examples as separate records; no PDF payload was fetched during that initial source-review pass.
Page 13 and later were rate-limited in the direct listing crawl, so later-page observations below use official CDC pages that remained searchable or readable.

| Grade | Distinct title rows observed in sampled G-feed pages | Coverage note |
| --- | ---: | --- |
| 1 | 6 | G-feed pages 1–12 |
| 2 | 6 | G-feed pages 1–12 |
| 3 | 6 | G-feed pages 1–12 |
| 4 | 9 | G-feed pages 1–12 |
| 5 | 10 | G-feed pages 1–12 |
| 6 | 11 | G-feed pages 1–12; one title spells “class” as `कलास` |
| 7 | 13 | G-feed pages 1–12 |
| 8 | 10 | G-feed pages 1–12 |
| 9 | At least 10 | Pages 1–12, 14, and 16 sampled |
| 10 | At least 3 | Page 16 sampled |
| 11 | At least 9 | Pages 20 and 21 sampled |
| 12 | At least 3 | Page 21 sampled |

Pages 14 and 16 list Grade 9 core, translated, and elective books; pages 20 and 21 list Grade 11 and Grade 12 books, respectively.
The page 20–21 snapshots show separate subjects and editions, including optional accountancy, business studies, optional English, biology, chemistry, physics, and Grade 12 Nepali, English, and Social Studies and Life Skills Education.
Sources: [CDC G-feed page 14](https://moecdc.gov.np/category/textbook--g-/?page=14), [page 16](https://moecdc.gov.np/category/textbook--g-/?page=16), [page 20](https://moecdc.gov.np/category/textbook--g-/?page=20), and [page 21](https://moecdc.gov.np/category/textbook--g-/?page=21).

The 72 rows from pages 1–12 carry 72 PDF links in the CDC listing, but the list does not provide normalized subject, edition, or language fields for every row.
Edition years and translation notes are often embedded in titles, while the official library's item records separately expose fields such as publication date, edition statement, language, keywords, material type, and an E-Library link.
The field-level tally from this partial snapshot is 72 title/file rows; subject, unique edition, and language totals remain unverified for the full 1–12 catalog.
This is a metadata limit rather than evidence that those fields are absent: the library item records expose them, but the full catalog records were not all retrievable in this pass.
For example, the CDC library's [English Grade Twelve record](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=12059&lvl=notice_display) records publication year, pagination, language, keywords, and its e-copy route.
The [Grade 10 catalog shelf page 2](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=20&lvl=etagere_see&nbr_lignes=28&page=2) and [Grade 9T shelf page 2](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=84&lvl=etagere_see&nbr_lignes=30&page=2) demonstrate that shelves paginate and that a single shelf may contain many older editions, translations, electives, or technical resources.
Subject, edition, and language totals for the complete Grade 1–12 inventory are therefore not safely established from the current listing snapshot.

Recommended enumeration procedure for the content manifest:

1. Traverse every grade shelf from 1–12 and, separately, every Grade 9T–12T shelf until its final page; follow page links and `nbr_lignes` values rather than assuming one page per grade.
2. Enumerate the CDC G, B, M, S, and T category feeds to their final pagination links, then deduplicate by stable CDC item ID and retain feed category as provenance.
3. For each candidate, open its CDC library `notice_display` record or CDC `/content/<id>/<slug>/` item page and capture exact title, grade, subject, edition/year, language, item URL, and direct official file URL.
4. Keep print records, electronic copies, translations, reprints, electives, local-language titles, and technical learning resources distinct unless the provider explicitly identifies them as the same edition.
5. Record retrieval status and checksum only after a permitted local download; this research pass did not download any book files.

CDC's catalog endpoints are unstable under repeated requests: the library listing returned gateway/timeout errors during direct opening, and direct CDC feed traversal began returning HTTP 403 after twelve pages.
Search-indexed CDC pages still exposed further official catalog pages and entries, but that partial visibility is not sufficient to certify a complete item count.
The CDC website itself states that it is still under construction, so plan for retries, cached page snapshots, and a refreshable source manifest rather than treating current page numbers or category taxonomy as a permanent API contract.
Source: [CDC site notice](https://moecdc.gov.np/).

## Primary source recommendation

The Curriculum Development Centre (CDC), Nepal is the strongest first source for the Grade 1–12 catalog because its official textbook pages and library records link to CDC-hosted e-copies or PDF files.
The CDC's Grade 9-10 compulsory curriculum identifies English, Nepali, Mathematics, Science and Technology, and Social Studies as the core subject set.
The official CDC catalog and current textbook feed also expose elective and language-variant titles, but those vary by school and by edition.
Sources: [CDC compulsory curriculum catalog record](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id_article=88&lvl=cmspage&pageid=4), [CDC textbook category](https://moecdc.gov.np/category/textbook--g-/), [CDC Grade Nine library shelf](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id_article=158&lvl=cmspage&pageid=4).

## Core Grade 9 textbooks

| Provider title | Grade / subject | Language | CDC item page | Direct official PDF |
| --- | --- | --- | --- | --- |
| English Class 9 | 9 / English | English | [CDC item](https://moecdc.gov.np/content/586/english-class---9/) | [PDF](https://giwmscdnone.gov.np/media/pdf_upload/5.%20Reduced-class%209%20English%20final_5hjggyv.pdf) |
| नेपाली कक्षा ९ (२०८२) | 9 / Nepali | Nepali | [CDC item](https://moecdc.gov.np/content/587/nepali-class---9/) | [PDF](https://giwmscdnone.gov.np/media/pdf_upload/6.Reduced-class%209%20Nepali_1tgrnzq.pdf) |
| गणित कक्षा ९ (२०८१) | 9 / Mathematics | Nepali | [CDC item](https://moecdc.gov.np/content/63/mathematics-class-9/) | [PDF](https://giwmscdnone.gov.np/media/pdf_upload/Maths%20Grade%20-9%20(Nepali)_ssdrrmo.pdf) |
| विज्ञान तथा प्रविधि कक्षा ९ (२०८२) | 9 / Science and Technology | Nepali | [CDC item](https://moecdc.gov.np/content/61/science-and-technology-class-9/) | [PDF](https://giwmscdnone.gov.np/media/pdf_upload/class%209%20Science%20final%202082_4echm3f.pdf) |
| सामाजिक अध्ययन कक्षा ९ (२०८२) | 9 / Social Studies | Nepali | [CDC item](https://moecdc.gov.np/content/649/social-studies-class-9/) | [PDF](https://giwmscdnone.gov.np/media/pdf_upload/%E0%A4%B8%E0%A4%BE%E0%A4%AE%E0%A4%BE%E0%A4%9C%E0%A4%BF%E0%A4%95%20%E0%A4%85%E0%A4%A7%E0%A5%8D%E0%A4%AF%E0%A4%AF%E0%A4%A8%20-%20%E0%A4%95%E0%A4%95%E0%A5%8D%E0%A4%B7%E0%A4%BE%209_gdt0ily.pdf) |

The English book page does not state an edition year in its title, so confirm its printed edition from the PDF cover when building the manifest.
The direct PDF links above were read from the official CDC item pages during the initial source-review pass; the current private download manifest records the files actually fetched in the later prototype crawl.

## Available English translations

| Provider title | Grade / subject | Language | CDC item page | Direct official PDF |
| --- | --- | --- | --- | --- |
| Mathematics Grade 9 (English Translation) | 9 / Mathematics | English | [CDC item](https://moecdc.gov.np/content/62/mathematics-/) | [PDF](https://giwmscdnone.gov.np/media/pdf_upload/Mathematics%20Grade%209%20(English%20Translation)%20Part%201_lnvm4wp.pdf) |
| Science and Technology Grade 9 (English Translation) | 9 / Science and Technology | English | [CDC item](https://moecdc.gov.np/content/60/science-and-technology-class-9--translated-version-/) | [PDF](https://giwmscdnone.gov.np/media/pdf_upload/Science%20and%20Technology%20Grade%20-9%20(English%20Translation)_v0nphvf.pdf) |

The CDC library separately catalogs English translations, including the Science and Technology translation as an electronic document.
The Mathematics translation PDF filename says `Part 1`, so check the CDC item page for any companion part before treating it as a complete book.
Sources: [CDC Mathematics translation page](https://moecdc.gov.np/content/62/mathematics-/), [CDC Science translation page](https://moecdc.gov.np/content/60/science-and-technology-class-9--translated-version-/), [CDC library record for Science and Technology Grade 9 English Translation](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id=13957&lvl=notice_display).

## Additional official Grade 9 electives with direct PDFs

| Provider title | Grade / subject | Language | CDC item page | Direct official PDF |
| --- | --- | --- | --- | --- |
| Computer Science Grade 9 (English Version, 2081) | 9 / Optional Computer Science | English | [CDC item](https://moecdc.gov.np/content/56/elective-computer-science-class-9--english-edition/) | [PDF](https://giwmscdnone.gov.np/media/pdf_upload/Computer%20Science%20Grade%209_r12pxcl.pdf) |
| ऐच्छिक गणित कक्षा ९ (अनुवादित संस्करण २०८२) | 9 / Optional Mathematics | English edition | [CDC item](https://moecdc.gov.np/content/570/optional-mathematics-grade-9/) | [PDF](https://giwmscdnone.gov.np/media/pdf_upload/Final%20opt%20math%20eng%20for%20press%209%20(2082-11-26)%201-12%20PM%20(1)_1iwtizb.pdf) |
| ऐच्छिक कार्यालय सञ्चालन तथा लेखा कक्षा ९ (२०८२) | 9 / Optional Office Operations and Accounting | Not stated on the item page; verify from the cover | [CDC item](https://moecdc.gov.np/content/585/elective-office-operations-and-accounting-class-9/) | [PDF](https://giwmscdnone.gov.np/media/pdf_upload/4.%20Reduced-class%209%20account%20final_9sk9qfx.pdf) |
| ऐच्छिक अर्थशास्त्र कक्षा ९ (२०८१) | 9 / Optional Economics | Likely Nepali from title and filename; verify from the cover | [CDC item](https://moecdc.gov.np/content/57/elective-economics-class-9--2081-/) | [PDF](https://giwmscdnone.gov.np/media/pdf_upload/%E0%A4%85%E0%A4%B0%E0%A5%8D%E0%A4%A5%E0%A4%B6%E0%A4%BE%E0%A4%B8%E0%A5%8D%E0%A4%A4%E0%A5%8D%E0%A4%B0%20%E0%A4%95%E0%A4%95%E0%A5%8D%E0%A4%B7%E0%A4%BE%20%E0%A5%AF_ddbtrjm.pdf) |
| ऐच्छिक इतिहास कक्षा ९ (२०८२) | 9 / Optional History | Not stated on the item page; verify from the cover | [CDC item](https://moecdc.gov.np/content/495/history--class-9-/) | [PDF](https://giwmscdnone.gov.np/media/pdf_upload/%E0%A4%87%E0%A4%A4%E0%A4%B9%E0%A4%BE%E0%A4%B8%20%E0%A4%95%E0%A4%95%E0%A5%8D%E0%A4%B7%E0%A4%BE-%E0%A5%AF_3kf761a.pdf) |

The Grade 9 optional catalog is not a single fixed set because schools select different subjects.
CDC's current textbook listing includes these elective titles and is the best source to refresh that set before each content import.
Source: [CDC textbook listing, including recent Grade 9 optional titles](https://moecdc.gov.np/category/textbook--g-/?page=14), [CDC textbook listing with additional Grade 9 titles](https://moecdc.gov.np/category/textbook--g-/?page=16).

## CDC E-Library additions and catalog-only records

CDC's E-Library lists an Optional Agriculture Education Grade 9 (2082) PDF resource with resource ID 11299.
Its official resource page is [here](https://lib.moecdc.gov.np/elibrary/?r=11299), and its title is listed in the [CDC Publications 2082 collection](https://lib.moecdc.gov.np/elibrary/pages/search.php?access=&archive=&display=list&foredit=&k=&modal=&noreload=true&offset=0&order_by=field8&per_page=240&recentdaylimit=&restypes=&search=%21collection18397&sort=DESC).
CDC also lists Optional Yoga Education Grade 9, first edition 2082, as an open PDF resource with resource ID 11166.
Its catalog route is [here](https://lib.moecdc.gov.np/elibrary/?r=11166).
The CDC library page reports the History Grade 9 (2082) resource as an open 9.9 MB PDF, which is an access-size example and not a downloaded file.
Source: [CDC E-Library record for Optional History Grade 9](https://lib.moecdc.gov.np/elibrary/?r=11298).

The E-Library also lists newer Grade 9 language resources, including Limbu (2082) and Nepal Bhasa (2082), and those can widen the language catalog after school-specific validation.
Sources: [CDC Publications 2082 collection](https://lib.moecdc.gov.np/elibrary/pages/search.php?access=&archive=&display=list&foredit=&k=&modal=&noreload=true&offset=0&order_by=field8&per_page=240&recentdaylimit=&restypes=&search=%21collection18397&sort=DESC), [CDC official textbook catalog](https://lib.moecdc.gov.np/catalog/opac_css/index.php?id_article=158&lvl=cmspage&pageid=4).

## Access and provenance notes

Confidence is high for the five-subject core catalog and the official CDC source pages.
Confidence is medium for elective completeness because local subject choices and new editions vary and CDC pages are actively updated.
The direct PDF paths are hosted on CDC's government delivery domain `giwmscdnone.gov.np`; file reachability, file size, embedded title, language, edition, and text extraction still need to be checked during the actual fetch.
Do not infer that an item's language from a Nepali title is definitive when the official page omits language metadata.
For each downloaded item, record the provider's exact displayed title, grade, subject, language from the cover, edition/year, CDC item page, direct file URL, retrieval time, byte size, and SHA-256.
Keep local full-text files under ignored `content/private/` and preserve that provenance with the document so staff can refresh the source later.

## Supplementary open textbook sources

For additional non-CDC science content, Wikijunior books have official child-focused titles and current Wikibooks text under Creative Commons Attribution-ShareAlike terms.
*How Things Work* targets ages 8-12, but its book page marks the work as partly developed, so limit extraction to completed chapters and review the science before student use.
*The Elements* has a printable version with an explicit CC BY-SA 3.0 notice.
Sources: [Wikijunior book collection](https://en.wikibooks.org/wiki/Wikijunior), [How Things Work](https://en.wikibooks.org/wiki/Wikijunior:How_Things_Work), [The Elements printable version](https://en.wikibooks.org/wiki/Wikijunior:The_Elements/Printable_version).

Siyavula's Grade 9 Natural Sciences page has a large chapter-based online book and downloadable EPUB entries, including a variant labeled CC BY.
An EPUB link labeled for Grade 9 Natural Sciences resolved during a prior review to a filename mentioning Physical Sciences, so verify the downloaded title and cover before adding it.
Sources: [Siyavula Grade 9 Natural Sciences](https://www.siyavula.com/read/za/natural-sciences/grade-9), [Siyavula download catalog and variant licenses](https://www.siyavula.com/read).
