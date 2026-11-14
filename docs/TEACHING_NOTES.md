# Teaching notes, tutor modes and evaluation

This page describes the teacher-curated layer added on top of the book library and the tutor.
It lists what the software does today and the gates that only people and real hardware can pass.

## Teaching notes

A teaching note is a short structured summary a teacher writes for one topic, linked to pages of a book already in the library.
Fields: title, grade, subject, chapter, language, linked book, source page ranges, key ideas, a worked example, common mistakes with corrections, ordered hints, a check question, and an optional Kolibri channel ID.
Notes contain no answer key.

Lifecycle, enforced by the API (`/api/admin/notes`, teacher or administrator account required, blocked on the student listener):

1. **Draft.** Created or edited by staff. Saving any edit returns an approved note to draft, increments its revision, and clears the reviewer.
2. **In review.** Submitted from draft.
3. **Approved.** Allowed only from in review by a different teacher or an administrator, and only while the linked book is `ready`, the grade matches the book, and every page range lies inside the book.

Students see approved notes only (`GET /api/notes`), and only while their book stays ready.
Student responses omit status, reviewer, and review dates.
With named accounts, creation, editing, and approval record the signed-in user ID and display name.
Teachers cannot approve their own notes; schools still need a second staff member to review the pedagogical content before learners see it.

Notes live in the same SQLite file as the catalog (`catalog.sqlite3` in the `content-data` volume), so the existing [backup procedure](INSTALL.md#backup-and-restore) covers them.

### Study page

`/study` lists approved notes with filters, key ideas, a worked example, common mistakes, a check question, and hints that students reveal one at a time.
It works without AI, Qdrant, or any model service.
Each note links to the book reader at the cited page.
The reader opens PDFs at that page with a standard `#page=` fragment.
Text files have no page structure and open at the top.

### Kolibri reference

A note may store a Kolibri channel ID.
The API validates it as 32 hexadecimal characters and builds a Learn deep link from the configured public URL.
That is the entire integration: no Kolibri accounts, classes, credentials, or progress are read or written, and no Kolibri content is copied into the portal.
A stored ID is not checked against the live catalog, so a link can point to a channel a school has not imported.

## Tutor modes

`POST /api/tutor/chat` accepts `mode`: `explain` (default, so older clients are unchanged), `hint`, or `debug`.

| Mode | Extra input | Behavior |
| --- | --- | --- |
| `explain` | none | Explain one concept, give an example if useful, and end with a check question. |
| `hint` | `hint_level` 0-4, held by the browser | Instructs the model to give one hint step and not the answer. Teacher hints above the current level are withheld from the prompt. |
| `debug` | `attempt`, required | Instructs the model to name the likely error in the learner's attempt and ask a question that leads to the fix. |

Approved notes for the learner's grade, subject and chapter are ranked by word overlap with the question and attempt.
Up to two are added to the prompt, followed by any retrieved book passages.
Notes are cited as sources (`kind: "note"`) with the first page range, and the browser links them to the reader.
Note selection needs no embedding or vector service.
Response `grounding` is `textbook` when retrieved passages were supplied, `note` when only notes were, and `general` otherwise.

What this does not guarantee:

- Supplying notes or passages does not make an answer correct. The model can ignore, misread, or add to them.
- "Hint mode withholds the answer" is an instruction to the model. The prompt omits stronger hints, but the model can still reveal an answer. Measure this with the evaluation tool.
- Word-overlap note ranking is a simple heuristic and misses paraphrases and Nepali inflections.
- The learner's attempt, notes, passages and history are marked untrusted in the prompt. That reduces injection risk and does not remove it.

## Visuals

The portal links answers and notes to the exact book page in the reader.
It does not extract, crop, or render page images, and it does not generate diagrams.
Page images from the CDC collection stay off until reuse terms are confirmed in writing (see [content licenses](CONTENT_LICENSES.md)).
If page images are added later, show them only for books whose license field permits it.

## Teacher-scored evaluation

`backend/app/evaluation.py` runs an authored question set against a running API, writes a run record, produces a blank score CSV, and reports on completed sheets.
Run records include safe model identifiers, retrieval settings, and a hash of the embedding identity without service URLs or credentials.
Teachers score five dimensions from 0 to 3.
The report shows per-dimension means, scorer disagreements of two or more points, items with a zero, unscored items, retrieval hit rate against teacher-marked pages, and the change from a baseline run.
Procedure and CSV format: [evals/README.md](../evals/README.md).

The tool never judges answers and never reads learner conversations.
The sample question set only shows the format.

## Gates that remain open

The full release checklist is in [production readiness](PRODUCTION_READINESS.md).

None of these has been passed.

| Gate | Needed |
| --- | --- |
| Teacher-authored notes | Teachers write and approve real notes from reviewed book pages. No such notes exist in this repository. |
| Teacher-authored question set | Teachers write in-scope, no-match, Nepali, misleading-premise and injection items, including expected pages. |
| Scored baseline | At least two teachers score a real run. The pilot gate in the [acceptance script](DEMO_SCRIPT.md) is at least 80% acceptable replies with zero severe unsafe outputs. |
| Nepali review | A fluent reviewer checks interface strings, notes and answers. The Nepali strings added with this feature are unreviewed machine-assisted drafts. |
| Live services | A real embedding service, Qdrant, and chat model on the target hardware. |
| Page images | Written confirmation of reuse terms before any CDC page image is shown. |
| Approval separation | A school procedure for independent note approval; individual staff accounts now provide reviewer identity. |
