import csv
import json

import pytest

from app import evaluation


class Shim:
    """Present the in-process test client where the CLI opens an HTTP client."""

    def __init__(self, client):
        self.client = client

    def __enter__(self):
        return self.client

    def __exit__(self, *exc):
        return False


def questions(document_id):
    return {
        "name": "test set",
        "items": [
            {
                "id": "force-explain",
                "grade": 8,
                "subject": "Science",
                "chapter": "Force and Motion",
                "mode": "explain",
                "question": "What happens to acceleration when mass doubles?",
                "expected_sources": [{"document_id": document_id, "pages": [1]}],
            },
            {
                "id": "force-debug",
                "grade": 8,
                "subject": "Science",
                "mode": "debug",
                "question": "Check my working.",
                "attempt": "a = F x m",
                "expected_sources": [{"document_id": document_id, "pages": [9]}],
            },
        ],
    }


@pytest.fixture
def recorded(client, upload, staff, tmp_path, monkeypatch):
    document = upload().json()
    indexed = client.post(
        "/api/admin/index-book", headers=staff, json={"document_id": document["id"]}
    )
    assert indexed.status_code == 200
    path = tmp_path / "q.json"
    path.write_text(json.dumps(questions(document["id"])))
    monkeypatch.setattr(evaluation.httpx, "Client", lambda **kw: Shim(client))
    run = evaluation.run_questions(path, "")
    return path, run, document


def test_run_record_is_reproducible_input(recorded):
    path, run, document = recorded
    assert [r["id"] for r in run["results"]] == ["force-explain", "force-debug"]
    assert all("answer" in r for r in run["results"])
    assert run["question_set"]["sha256"] == evaluation.load_questions(path)[1]
    assert run["results"][0]["sources"][0]["document_id"] == document["id"]
    config = run["configuration"]
    assert config["chat_provider"] == "ollama"
    assert config["embedding_provider"] == "ollama"
    assert len(config["embedding_identity_sha256"]) == 64
    assert "embed_api_base_url" not in config


def test_retrieval_hit_rate_uses_teacher_marked_pages(recorded):
    _, run, _ = recorded
    assert evaluation.retrieval_hits(run) == (1, 2)


def test_scoring_round_trip_and_report(recorded, tmp_path):
    _, run, _ = recorded
    template = tmp_path / "scores.csv"
    evaluation.write_template(run, template)
    rows = list(csv.DictReader(template.open(encoding="utf-8")))
    assert rows[0]["run_id"] == run["run_id"] and rows[0]["factual_correctness"] == ""
    # An untouched template scores nothing and says so.
    assert "No scores supplied" in evaluation.build_report(run, [], None)

    def sheet(name, values):
        path = tmp_path / f"{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            for row, score in zip(rows, values, strict=True):
                writer.writerow(
                    {**row, "scorer": name, **{d: score for d in evaluation.DIMENSIONS}}
                )
        return path

    a = evaluation.read_scores(sheet("rai", [3, 1]), run)
    b = evaluation.read_scores(sheet("thapa", [3, 3]), run)
    report = evaluation.build_report(run, a + b, None)
    assert "Scorers: rai, thapa" in report
    assert "force-debug factual_correctness: [1, 3]" in report
    assert "Retrieval hit rate against teacher-marked pages: 1/2" in report
    assert "not that the answer was verified" in report
    comparison = evaluation.build_report(run, a, (run, b))
    assert "-1.00" in comparison or "-0.50" in comparison


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("factual_correctness", "4", "0-3"),
        ("factual_correctness", "good", "0-3"),
        ("scorer", "", "scorer"),
        ("run_id", "other", "run_id"),
        ("item_id", "nope", "unknown"),
    ],
)
def test_invalid_score_sheets_are_rejected(recorded, tmp_path, column, value, message):
    _, run, _ = recorded
    template = tmp_path / "s.csv"
    evaluation.write_template(run, template)
    rows = list(csv.DictReader(template.open(encoding="utf-8")))
    rows[0].update(scorer="rai", factual_correctness="2")
    rows[0][column] = value
    with template.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(evaluation.EvalError, match=message):
        evaluation.read_scores(template, run)


def test_question_set_validation(tmp_path):
    path = tmp_path / "bad.json"
    for bad in (
        {"items": []},
        {"items": [{"id": "a", "grade": 8, "subject": "S", "question": "q", "mode": "debug"}]},
        {"items": [{"id": "a", "grade": 8, "subject": "S", "question": "q"}] * 2},
    ):
        path.write_text(json.dumps(bad))
        with pytest.raises(evaluation.EvalError):
            evaluation.load_questions(path)


def test_cli_exit_codes_and_unreachable_api(tmp_path, capsys):
    path = tmp_path / "q.json"
    path.write_text(json.dumps(questions("a" * 32)))
    code = evaluation.main(
        [
            "run",
            "--questions",
            str(path),
            "--api",
            "http://127.0.0.1:1",
            "--out",
            str(tmp_path / "run.json"),
        ]
    )
    assert code == 2 and "Could not reach" in capsys.readouterr().err
