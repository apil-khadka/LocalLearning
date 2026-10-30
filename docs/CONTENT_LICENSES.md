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

Frontend dependencies include Nunito Sans and Noto Sans Devanagari font packages, Phosphor icons, Radix UI, React and React Router.
Their license files remain in installed packages and must be retained with redistributed bundles; the image build copies notices into its served distribution.
Use the lockfiles to identify exact packages when preparing release notices and a software bill of materials.
