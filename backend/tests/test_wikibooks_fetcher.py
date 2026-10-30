import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FETCHER_PATH = REPOSITORY_ROOT / "scripts/fetch_wikibooks_books.py"
FETCHER_SPEC = importlib.util.spec_from_file_location("fetch_wikibooks_books", FETCHER_PATH)
FETCHER = importlib.util.module_from_spec(FETCHER_SPEC)
sys.modules[FETCHER_SPEC.name] = FETCHER
FETCHER_SPEC.loader.exec_module(FETCHER)
BOOKS = FETCHER.BOOKS
MAX_PAGES = FETCHER.MAX_PAGES
fetch_book = FETCHER.fetch_book


def page(title, extract, revision=123):
    return {
        "title": title,
        "fullurl": "https://en.wikibooks.org/wiki/" + title.replace(" ", "_"),
        "lastrevid": revision,
        "extract": extract,
    }


def test_fetch_book_records_revision_attribution_and_skips_templates():
    book = replace(
        BOOKS["elementary-geometry"],
        pages=(
            "Geometry for Elementary School",
            "Geometry for Elementary School/Triangles",
            "Geometry for Elementary School/Stub Template",
        ),
    )
    chapter = "== Side lines ==\n\n" + ("Triangles and shapes " * 80)

    def api(params):
        if params.get("generator") == "categorymembers":
            assert params["gcmtitle"] == book.category
            assert params["gcmlimit"] == MAX_PAGES
            return {"query": {"pages": [{"title": title} for title in book.pages]}}
        title = params["titles"]
        extracts = {
            book.title: "Geometry for children " * 80,
            f"{book.title}/Triangles": chapter,
            f"{book.title}/Stub Template": "template helper",
        }
        return {
            "query": {
                "pages": [
                    page(
                        title,
                        extracts[title],
                        revision={
                            book.title: 456,
                            f"{book.title}/Triangles": 457,
                            f"{book.title}/Stub Template": 458,
                        }[title],
                    )
                ]
            }
        }

    text, manifest = fetch_book(book, api, pause=lambda _seconds: None)

    assert "Geometry for children" in text
    assert "Triangles and shapes" in text
    assert "### Side lines" in text
    assert "template helper" not in text
    assert manifest["license"] == "CC BY-SA 4.0"
    assert manifest["page_count"] == 2
    revisions = {item["title"]: item["revision_id"] for item in manifest["pages"]}
    assert revisions == dict(zip(book.pages, [456, 457, 458], strict=True))
    excluded = next(item for item in manifest["pages"] if item["title"].endswith("Stub Template"))
    assert excluded["included"] is False


def test_fetch_book_rejects_catalog_continuation():
    book = BOOKS["solar-system"]

    def api(_params):
        return {"query": {"pages": [{"title": book.title}]}, "continue": {"gcmcontinue": "x"}}

    with pytest.raises(RuntimeError, match="empty or oversized"):
        fetch_book(book, api, pause=lambda _seconds: None)


def test_fetch_book_rejects_pages_outside_the_selected_book():
    book = BOOKS["solar-system"]

    def api(params):
        if params.get("generator") == "categorymembers":
            return {"query": {"pages": [{"title": "Wikijunior:Biology"}]}}
        raise AssertionError("Unexpected page content request")

    with pytest.raises(RuntimeError, match="outside the selected book"):
        fetch_book(book, api, pause=lambda _seconds: None)
