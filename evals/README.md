# Teacher-scored tutor evaluation

This directory holds the tooling inputs for repeatable evaluation of the tutor.
The tool records answers and summarizes teacher scores.
It does not judge answers itself, and it does not measure hallucination.

The fixed Phi-4 model probes are a separate automated check, summarized in the [matched model comparison](../docs/PHI4_MODEL_COMPARISON.md).
They use heuristic checks and do not replace the teacher-scored procedure in this guide.

## Rules

- Use only questions written by teachers. Never put learner conversations, names or school records in a question set, run record or score sheet.
- `sample-questions.json` only shows the format. It is not teacher-approved.
- `runs/` and `scores/` are ignored by Git. Review a run before deliberately committing it as a baseline.

## Question set format

A JSON file with an `items` list. Each item has a unique `id`, `grade`, `subject`, and `question`.
Optional fields: `chapter`, `language` (`en` or `ne`), `mode` (`explain`, `hint` or `debug`), `hint_level` (0-4), `attempt` (required for `debug`).
A teacher may add `expected_sources`: `[{"document_id": "<book id>", "pages": [12, 13]}]`, copied from the Books API.
Retrieval hit rate counts an item as a hit when a returned source is on one of those pages. It measures retrieval only.

## Procedure

Start the API with AI enabled and the services under test configured, then from the repository root:

```sh
make eval QUESTIONS=evals/my-questions.json RUN=2026-11-baseline
make eval-template RUN=2026-11-baseline
```

Give `evals/scores/2026-11-baseline-blank.csv` to each teacher.
Each teacher copies it, fills in `scorer`, the five score columns, and `comments`, and saves it as a separate file.
Scores are integers from 0 to 3, or blank when a dimension does not apply:

| Score | Meaning |
| --- | --- |
| 0 | Wrong, unsafe or unusable |
| 1 | Significant problems |
| 2 | Acceptable with minor problems |
| 3 | Correct and appropriate |

Dimensions: `factual_correctness`, `source_support` (claims match the cited page or note), `grade_level`, `language_quality`, and `mode_behavior` (a hint withholds the answer; a debug reply names the error without rewriting the solution).

```sh
make eval-report RUN=2026-11-baseline SCORES="evals/scores/rai.csv evals/scores/thapa.csv"
```

Each run also records the configured chat and embedding model identifiers, retrieval settings, and a SHA-256 fingerprint of the embedding identity.
It excludes service URLs and credentials.
The report lists per-dimension means, items with any zero, disagreements of two or more points between teachers, unscored items, and the retrieval hit rate.
To compare two runs, call `python -m app.evaluation report --help` for the baseline options.

## What a good result does not show

A small authored set shows how the tutor handled those questions on that day with that model and index.
It does not establish that answers are correct in general.
A `textbook` or `note` label means material was supplied to the model, not that the answer was checked against it.
The local Phi-4 probe report is additional model-specific evidence, not a teacher-approved baseline or school deployment acceptance.
