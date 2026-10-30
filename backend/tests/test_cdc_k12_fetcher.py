import importlib.util
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FETCHER_PATH = REPOSITORY_ROOT / "scripts/fetch_cdc_k12_books.py"
FETCHER_SPEC = importlib.util.spec_from_file_location("fetch_cdc_k12_books", FETCHER_PATH)
FETCHER = importlib.util.module_from_spec(FETCHER_SPEC)
sys.modules[FETCHER_SPEC.name] = FETCHER
FETCHER_SPEC.loader.exec_module(FETCHER)


def test_catalog_parser_keeps_grade_subject_source_and_download_metadata():
    page_url = "https://moecdc.gov.np/category/textbook--g-/?page=13"
    html = """
    <table>
      <tr><th>no</th><th>title</th></tr>
      <tr><td>1</td><td>अङ्ग्रेजी कक्षा ९ (२०२५)</td>
        <td><a href="https://giwmscdnone.gov.np/media/class9.pdf"></a></td>
        <td><a href="/content/64/english-class-9-2025/"></a></td></tr>
      <tr><td>2</td><td>ऐच्छिक गणित कक्षा ९ (२०८१)</td>
        <td><a href="https://giwmscdnone.gov.np/media/optional-math.pdf"></a></td>
        <td><a href="/content/58/elective-mathematics-class-9/"></a></td></tr>
      <tr><td>3</td><td>नेपाली कक्षा १३ (sample)</td>
        <td><a href="https://giwmscdnone.gov.np/media/out-of-range.pdf"></a></td>
        <td><a href="/content/999/grade-13/"></a></td></tr>
    </table>
    """

    books = FETCHER.parse_catalog_page(html, page_url)

    assert [(book.grade, book.subject) for book in books] == [
        (9, "English"),
        (9, "Optional Mathematics"),
    ]
    assert books[0].title == "अङ्ग्रेजी कक्षा ९ (२०२५)"
    assert books[0].feed == "G"
    assert books[0].download_url == "https://giwmscdnone.gov.np/media/class9.pdf"
    assert books[0].source_page == "https://moecdc.gov.np/content/64/english-class-9-2025/"
    assert books[0].filename.startswith("64-english-class-9-2025-")
    assert books[0].filename.endswith(".pdf")


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("नेपाली कक्षा १", 1),
        ("गणित कक्षा - १२ (२०८२)", 12),
        ("Natural Sciences Grade-9", 9),
        ("Kindergarten ECED booklet", 0),
        ("शिशु विकास केन्द्रका सहजकर्ता पुस्तिका", 0),
        ("Grade 13", None),
        ("कक्षा आठ", None),
    ],
)
def test_grade_parser_accepts_nepali_and_english_numerals(title, expected):
    assert FETCHER.grade_from_title(title) == expected


def test_catalog_parser_rejects_a_non_cdc_pdf_host():
    html = """
    <table><tr><td>1</td><td>नेपाली कक्षा १</td>
      <td><a href="https://example.com/book.pdf"></a></td>
      <td><a href="/content/1/nepali-grade-1/"></a></td></tr></table>
    """

    with pytest.raises(ValueError, match="outside its official"):
        FETCHER.parse_catalog_page(html, "https://moecdc.gov.np/category/textbook--g-/")


def test_catalog_parser_rejects_non_https_catalog_pages():
    with pytest.raises(ValueError, match="outside its official"):
        FETCHER.parse_catalog_page("<table></table>", "http://moecdc.gov.np/catalog")


def test_special_language_feed_keeps_bhote_grade_and_feed_code():
    html = """
    <table><tr><td>1</td><td>भोट भाषा कक्षा ७</td>
      <td><a href="https://giwmscdnone.gov.np/media/bhote7.pdf"></a></td>
      <td><a href="/content/654/bhote-language-class-7/"></a></td></tr></table>
    """

    book = FETCHER.parse_catalog_page(
        html, "https://moecdc.gov.np/category/textbook--b-/", feed="B"
    )[0]

    assert (book.grade, book.subject, book.feed) == (7, "Bhote Language", "B")


def test_early_childhood_cards_resolve_to_official_item_pages():
    html = """
    <div class="category-1-grid">
      <div class="grid__card"><div><h3 class="card__title">
        <a href="/content/470/early-childhood-guide/">Child development centre facilitator guide</a>
      </h3></div></div>
    </div>
    """

    book = FETCHER.parse_category_cards(html, "https://moecdc.gov.np/category/textbook--e-/")[0]

    assert book.grade == 0
    assert book.subject == "Early Childhood Education"
    assert book.source_page == "https://moecdc.gov.np/content/470/early-childhood-guide/"


def test_early_childhood_item_pdf_must_be_on_official_host():
    source = "https://moecdc.gov.np/content/470/early-childhood-guide/"

    assert FETCHER._source_page_pdf(
        "var pdf = 'https://giwmscdnone.gov.np/media/guide.pdf';", source
    )
    with pytest.raises(ValueError, match="outside its official"):
        FETCHER._source_page_pdf("var pdf = 'https://example.com/guide.pdf';", source)
