"""Reproducible, teacher-scored evaluation of the tutor.

Workflow (see evals/README.md):

1. ``run``      send an authored question set to a running API and save a run record.
2. ``template`` write a score CSV that teachers fill in.
3. ``report``   summarize one run with its score sheets, optionally against a baseline.

Only authored questions are used. The tool never reads or stores learner
conversations. Scores come from teachers; the tool does not judge answers.
Retrieval hit rate compares returned sources with pages a teacher marked in
advance. It measures retrieval, not whether an answer is correct.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from uuid import uuid4

import httpx

DIMENSIONS = (
    "factual_correctness",
    "source_support",
    "grade_level",
    "language_quality",
    "mode_behavior",
)
SCALE = (0, 1, 2, 3)
SCORE_COLUMNS = ["run_id", "item_id", "scorer", *DIMENSIONS, "comments"]
CONTEXT_COLUMNS = [
    "mode",
    "grade",
    "subject",
    "question",
    "attempt",
    "grounding",
    "sources",
    "answer",
]
FORMAT_VERSION = 1
MODES = {"explain", "hint", "debug"}


class EvalError(Exception):
    """A problem the operator can fix; reported without a traceback."""


def load_questions(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EvalError(f"{path} is not valid JSON: {exc}") from exc
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise EvalError("The question set needs a non-empty 'items' list.")
    seen = set()
    for item in items:
        ident = item.get("id") if isinstance(item, dict) else None
        if not isinstance(ident, str) or not ident or ident in seen:
            raise EvalError("Every item needs a unique string 'id'.")
        seen.add(ident)
        if not isinstance(item.get("question"), str) or not item["question"].strip():
            raise EvalError(f"Item {ident} needs a question.")
        if item.get("mode", "explain") not in MODES:
            raise EvalError(f"Item {ident} has an unknown mode.")
        if item.get("mode") == "debug" and not str(item.get("attempt", "")).strip():
            raise EvalError(f"Debug item {ident} needs an attempt.")
        for key in ("grade", "subject"):
            if key not in item:
                raise EvalError(f"Item {ident} needs '{key}'.")
    return data, hashlib.sha256(raw).hexdigest()


def request_body(item: dict) -> dict:
    body = {
        "message": item["question"],
        "grade": item["grade"],
        "subject": item["subject"],
        "chapter": item.get("chapter", ""),
        "language": item.get("language", "en"),
        "mode": item.get("mode", "explain"),
        "hint_level": item.get("hint_level", 0),
    }
    if item.get("attempt"):
        body["attempt"] = item["attempt"]
    return body


def ask(client: httpx.Client, base: str, item: dict, retries: int = 5) -> dict:
    """Ask one question, waiting out the tutor's concurrency limit (HTTP 429)."""
    result: dict = {"id": item["id"]}
    for attempt in range(retries + 1):
        try:
            response = client.post(f"{base}/api/tutor/chat", json=request_body(item))
        except httpx.HTTPError as exc:
            return {**result, "error": f"request failed: {type(exc).__name__}"}
        if response.status_code == 429 and attempt < retries:
            time.sleep(min(float(response.headers.get("Retry-After", "5")), 30))
            continue
        break
    if response.status_code != 200:
        try:
            detail = response.json().get("detail", "")
        except ValueError:
            detail = ""
        return {**result, "error": f"HTTP {response.status_code}: {str(detail)[:200]}"}
    reply = response.json()
    return {
        **result,
        "answer": reply["answer"],
        "grounding": reply["grounding"],
        "model": reply["model"],
        "sources": reply["sources"],
    }


def run_questions(questions_path: Path, base: str, timeout: float = 180) -> dict:
    questions, digest = load_questions(questions_path)
    base = base.rstrip("/")
    with httpx.Client(timeout=timeout, trust_env=False) as client:
        try:
            services = client.get(f"{base}/api/services").json()
        except (httpx.HTTPError, ValueError) as exc:
            raise EvalError(f"Could not reach the API at {base}.") from exc
        results = [ask(client, base, item) for item in questions["items"]]
    return {
        "format": FORMAT_VERSION,
        "run_id": uuid4().hex[:12],
        "started_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "api": base,
        # Sanitized model/retrieval settings from /api/services. The API exposes
        # model identifiers and a hash of embedding identity, never service URLs
        # or credentials, so runs can be compared without recording secrets.
        "configuration": services.get("evaluation_config", {}),
        "question_set": {"name": questions.get("name", ""), "sha256": digest},
        "tutor_status": services.get("tutor", {}).get("status"),
        "models": sorted({r["model"] for r in results if "model" in r}),
        "items": questions["items"],
        "results": results,
    }


def read_run(path: Path) -> dict:
    try:
        run = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalError(f"Could not read run record {path}.") from exc
    if run.get("format") != FORMAT_VERSION or "results" not in run:
        raise EvalError(f"{path} is not a run record this tool understands.")
    return run


def source_text(result: dict) -> str:
    return "; ".join(
        f"{s['title']} p.{s['page_start']}-{s['page_end']} ({s.get('kind', 'passage')})"
        for s in result.get("sources", [])
    )


def write_template(run: dict, out: Path):
    items = {item["id"]: item for item in run["items"]}
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(SCORE_COLUMNS + CONTEXT_COLUMNS)
        for result in run["results"]:
            item = items[result["id"]]
            writer.writerow(
                [run["run_id"], result["id"], "", *([""] * len(DIMENSIONS)), ""]
                + [
                    item.get("mode", "explain"),
                    item["grade"],
                    item["subject"],
                    item["question"],
                    item.get("attempt", ""),
                    result.get("grounding", ""),
                    source_text(result),
                    result.get("answer", result.get("error", "")),
                ]
            )


def read_scores(path: Path, run: dict) -> list[dict]:
    """Parse and validate one teacher's score sheet against a run."""
    known = {result["id"] for result in run["results"]}
    rows, seen = [], set()
    try:
        handle = path.open(newline="", encoding="utf-8")
    except OSError as exc:
        raise EvalError(f"Could not read {path}.") from exc
    with handle:
        reader = csv.DictReader(handle)
        missing = [c for c in SCORE_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise EvalError(f"{path} is missing columns: {', '.join(missing)}")
        for number, row in enumerate(reader, start=2):
            scores = {d: (row.get(d) or "").strip() for d in DIMENSIONS}
            if not any(scores.values()):
                continue  # An unscored row is allowed; it is reported as unscored.
            where = f"{path} line {number}"
            if row["run_id"] != run["run_id"]:
                raise EvalError(f"{where}: run_id does not match this run.")
            if row["item_id"] not in known:
                raise EvalError(f"{where}: unknown item_id {row['item_id']!r}.")
            scorer = (row.get("scorer") or "").strip()
            if not scorer:
                raise EvalError(f"{where}: fill in the scorer name.")
            if (scorer, row["item_id"]) in seen:
                raise EvalError(f"{where}: duplicate score for {row['item_id']} by {scorer}.")
            seen.add((scorer, row["item_id"]))
            parsed = {}
            for dimension, text in scores.items():
                if text == "":
                    parsed[dimension] = None
                    continue
                try:
                    value = int(text)
                except ValueError:
                    value = -1
                if value not in SCALE:
                    raise EvalError(f"{where}: {dimension} must be one of 0-3 or blank.")
                parsed[dimension] = value
            rows.append(
                {
                    "item_id": row["item_id"],
                    "scorer": scorer,
                    "scores": parsed,
                    "comments": row.get("comments", ""),
                }
            )
    return rows


def _overlaps(source: dict, expected: dict) -> bool:
    if source["document_id"] != expected["document_id"]:
        return False
    pages = expected.get("pages") or []
    return not pages or any(source["page_start"] <= p <= source["page_end"] for p in pages)


def retrieval_hits(run: dict) -> tuple[int, int]:
    """(hits, items with a teacher-marked expected source), counting answered items only."""
    results = {r["id"]: r for r in run["results"]}
    marked = hits = 0
    for item in run["items"]:
        expected = item.get("expected_sources")
        if not expected:
            continue
        marked += 1
        result = results.get(item["id"], {})
        if any(_overlaps(s, e) for s in result.get("sources", []) for e in expected):
            hits += 1
    return hits, marked


def dimension_means(rows: list[dict]) -> dict[str, tuple[float, int] | None]:
    summary = {}
    for dimension in DIMENSIONS:
        values = [r["scores"][dimension] for r in rows if r["scores"][dimension] is not None]
        summary[dimension] = (mean(values), len(values)) if values else None
    return summary


def disagreements(rows: list[dict]) -> list[str]:
    by_item: dict[str, list[dict]] = {}
    for row in rows:
        by_item.setdefault(row["item_id"], []).append(row)
    found = []
    for item_id, group in sorted(by_item.items()):
        for dimension in DIMENSIONS:
            values = [r["scores"][dimension] for r in group if r["scores"][dimension] is not None]
            if len(values) > 1 and max(values) - min(values) >= 2:
                found.append(f"{item_id} {dimension}: {sorted(values)}")
    return found


def build_report(run: dict, rows: list[dict], baseline: tuple[dict, list[dict]] | None) -> str:
    results = run["results"]
    answered = [r for r in results if "answer" in r]
    errors = [r for r in results if "error" in r]
    grounding: dict[str, int] = {}
    for result in answered:
        grounding[result["grounding"]] = grounding.get(result["grounding"], 0) + 1
    scored_items = {r["item_id"] for r in rows}
    lines = [
        f"# Evaluation report: run {run['run_id']}",
        "",
        f"- Question set: {run['question_set']['name'] or 'unnamed'} "
        f"(sha256 {run['question_set']['sha256'][:12]})",
        f"- Started: {run['started_at']}; API {run['api']}; tutor status {run['tutor_status']}",
        f"- Models reported: {', '.join(run['models']) or 'none'}",
        f"- Items: {len(results)}; answered {len(answered)}; errors {len(errors)}",
        "- Grounding labels: "
        + (", ".join(f"{k} {v}" for k, v in sorted(grounding.items())) or "none"),
    ]
    hits, marked = retrieval_hits(run)
    lines.append(
        f"- Retrieval hit rate against teacher-marked pages: {hits}/{marked}"
        if marked
        else "- Retrieval hit rate: no items have teacher-marked expected sources"
    )
    lines += ["", "## Teacher scores (0-3; 3 is best)", ""]
    scorers = sorted({r["scorer"] for r in rows})
    lines.append(
        f"Scorers: {', '.join(scorers)}. Items scored: {len(scored_items)}/{len(results)}."
        if rows
        else "No scores supplied. Run `template`, have teachers fill in the CSV, then report again."
    )
    if rows:
        previous = dimension_means(baseline[1]) if baseline else {}
        lines += [
            "",
            "| Dimension | Mean | Scores | Change vs baseline |",
            "| --- | --- | --- | --- |",
        ]
        for dimension, value in dimension_means(rows).items():
            if value is None:
                lines.append(f"| {dimension} | not scored | 0 | |")
                continue
            before = previous.get(dimension)
            delta = f"{value[0] - before[0]:+.2f}" if before else ""
            lines.append(f"| {dimension} | {value[0]:.2f} | {value[1]} | {delta} |")
        low = sorted({r["item_id"] for r in rows if any(v == 0 for v in r["scores"].values())})
        lines += ["", f"Items with a zero on any dimension: {', '.join(low) or 'none'}"]
        found = disagreements(rows)
        lines += ["", "Scorer disagreements of 2 or more points:"]
        lines += [f"- {entry}" for entry in found] or ["- none (or only one scorer per item)"]
        if baseline:
            lines += ["", f"Baseline run: {baseline[0]['run_id']} ({baseline[0]['started_at']})"]
    lines += [
        "",
        "Items not yet scored: "
        + (", ".join(r["id"] for r in results if r["id"] not in scored_items) or "none"),
    ]
    if errors:
        lines += ["", "Items that returned errors:"]
        lines += [f"- {r['id']}: {r['error']}" for r in errors]
    lines += [
        "",
        "Limits: scores are the teachers' judgments on a small authored set. "
        "A 'textbook' or 'note' grounding label means material was supplied to the model, "
        "not that the answer was verified against it.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.evaluation", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Ask every authored question and save a run record.")
    run.add_argument("--questions", type=Path, required=True)
    run.add_argument("--api", default="http://127.0.0.1:8000")
    run.add_argument("--out", type=Path, required=True)
    template = sub.add_parser("template", help="Write a blank teacher score CSV for a run.")
    template.add_argument("--run", type=Path, required=True)
    template.add_argument("--out", type=Path, required=True)
    report = sub.add_parser("report", help="Summarize a run and its score sheets.")
    report.add_argument("--run", type=Path, required=True)
    report.add_argument("--scores", type=Path, nargs="*", default=[])
    report.add_argument("--baseline-run", type=Path)
    report.add_argument("--baseline-scores", type=Path, nargs="*", default=[])
    report.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            record = run_questions(args.questions, args.api)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            failed = sum(1 for r in record["results"] if "error" in r)
            print(f"Run {record['run_id']}: {len(record['results'])} items, {failed} errors")
            return 1 if failed == len(record["results"]) else 0
        if args.command == "template":
            write_template(read_run(args.run), args.out)
            print(f"Wrote {args.out}")
            return 0
        current = read_run(args.run)
        rows = [row for path in args.scores for row in read_scores(path, current)]
        baseline = None
        if args.baseline_run:
            base_run = read_run(args.baseline_run)
            baseline = (
                base_run,
                [r for p in args.baseline_scores for r in read_scores(p, base_run)],
            )
        text = build_report(current, rows, baseline)
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        print(text)
        return 0
    except EvalError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
