# Content and dependency licensing

The project's software uses Apache License 2.0.
That license does not grant permission to distribute third-party models, textbooks, videos or encyclopedias.

The original demonstration text in `content/sample/force-and-motion.txt` is dedicated under CC0 1.0.
It is a software demonstration, not an officially approved Nepal curriculum textbook.
Its separate dedication is in `content/sample/LICENSE`.

Every school import requires a source and license/permission field.
Recording those fields documents an operator's statement; it is not independent legal verification.
Keep evidence of permission and any restrictions with the private school content register.
Do not put an E-Pustakalaya bundle, published textbook, model weight, ZIM or video collection in this Git repository.

Review the actual [Qwen model license](https://ollama.com/library/qwen3:4b-instruct), [EmbeddingGemma model terms](https://huggingface.co/google/embeddinggemma-300m), and licenses/attributions for each installed Kiwix or Kolibri collection.
Confirm offline package availability and redistribution rights directly with content providers before promising integration.
The official Kolibri 0.19.5 container is MIT-licensed, but that software license does not grant rights to its separately distributed learning channels.
Review and retain the license and attribution for every Kolibri channel and resource selected for a school.

The initial book-source review is in [book-sources.md](research/book-sources.md).
That review found different terms at E-Pustakalaya per item, no reuse terms on the CDC catalog entries reviewed, and a CC BY 4.0 Open Textbook Library candidate.
For the local CDC prototype collection, the project owner confirmed permission to use the copied materials.
Those PDFs stay under the ignored `content/private/` directory and must not enter this public repository.
The private manifest retains the official CDC source page, direct file URL, retrieval time, and SHA-256 for each downloaded item.
Locally fetched text-only Wikibooks prototypes include Wikijunior:Biology and selected chapters from Wikijunior:Human Body, Wikijunior:Solar System, and Geometry for Elementary School under CC BY-SA 4.0; revision-level attribution manifests are kept beside the content in ignored storage.
They are prototype fixtures, not curriculum approvals or public content bundles.
The Solar System text comes from current Wikibooks pages, not the historical PDF copy.

Frontend dependencies include Nunito Sans and Noto Sans Devanagari font packages, Phosphor icons, Radix UI, React and React Router.
Their license files remain in installed packages and must be retained with redistributed bundles; the image build copies notices into its served distribution.
Use the lockfiles to identify exact packages when preparing release notices and a software bill of materials.
