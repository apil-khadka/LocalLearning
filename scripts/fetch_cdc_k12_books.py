#!/usr/bin/env python3
"""Fetch CDC Nepal K–12 PDF catalogs into ignored prototype storage."""

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen


CATALOG_URL = "https://moecdc.gov.np/category/textbook--g-/"
CATALOG_HOST = "moecdc.gov.np"
FEEDS = {
    "G": "https://moecdc.gov.np/category/textbook--g-/",
    "B": "https://moecdc.gov.np/category/textbook--b-/",
    "M": "https://moecdc.gov.np/category/textbook--m-/",
    "S": "https://moecdc.gov.np/category/textbook--s-/",
    "T": "https://moecdc.gov.np/category/textbook--t-/",
    "E": "https://moecdc.gov.np/category/textbook--e-/",
}
EARLY_CHILDHOOD_CURRICULUM = (
    "https://moecdc.gov.np/content/671/"
    "curriculum-of-early-childhood-development-and-education-/"
)
DOWNLOAD_HOSTS = {
    "giwmscdnone.gov.np",
    "giwmscd.gov.np",
    CATALOG_HOST,
    "lib.moecdc.gov.np",
}
USER_AGENT = "DigitalHimalayaPrototype/0.1 (offline classroom library)"
MAX_CATALOG_PAGES = 40
MAX_CATALOG_BYTES = 5 * 1024 * 1024
MAX_FILE_BYTES = 150 * 1024 * 1024
REQUEST_INTERVAL_SECONDS = 1.0
CHUNK_BYTES = 64 * 1024
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "content/private/cdc/k12"
MANIFEST_NAME = "catalog.json"

NEPALI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
GRADE_PATTERN = re.compile(r"(?:कक्षा|class|grade)\s*[-–:]?\s*(\d{1,2})", re.IGNORECASE)
PDF_VARIABLE_PATTERN = re.compile(r"\bvar\s+pdf\s*=\s*(['\"])(.*?)\1", re.IGNORECASE)


@dataclass(frozen=True)
class CatalogBook:
    grade: int | None
    title: str
    subject: str
    feed: str
    catalog_page: str
    source_page: str
    download_url: str | None
    filename: str | None


class CatalogParser(HTMLParser):
    """Extract table rows and their links without depending on a web framework."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[dict] = []
        self.row: dict | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "tr":
            self.row = {"cells": [], "links": []}
        elif self.row is not None and tag in {"td", "th"}:
            self.cell = []
        elif self.row is not None and tag == "a":
            href = attributes.get("href")
            if href:
                self.row["links"].append(href.strip())

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None and self.row is not None:
            self.row["cells"].append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
            self.cell = None


class CatalogCardParser(HTMLParser):
    """Read CDC category cards, used by the early-childhood feed."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cards: list[dict[str, str]] = []
        self.listing_depth = 0
        self.card: dict[str, str] | None = None
        self.card_depth = 0
        self.in_title = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "div" and "category-1-grid" in classes:
            self.listing_depth = 1
        elif self.listing_depth and tag == "div":
            self.listing_depth += 1
        if (
            self.listing_depth
            and tag == "div"
            and "grid__card" in classes
            and self.card is None
        ):
            self.card = {"title": "", "source_page": ""}
            self.card_depth = 1
        elif self.card is not None:
            if tag == "div":
                self.card_depth += 1
            elif tag == "h3" and "card__title" in classes:
                self.in_title = True
                self.title_parts = []
            elif tag == "a" and not self.card["source_page"]:
                href = attributes.get("href", "").strip()
                if urlsplit(href).path.startswith("/content/"):
                    self.card["source_page"] = href

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "h3" and self.in_title and self.card is not None:
            self.card["title"] = " ".join("".join(self.title_parts).split())
            self.in_title = False
        elif tag == "div" and self.card is not None:
            self.card_depth -= 1
            if self.card_depth == 0:
                if self.card["title"] and self.card["source_page"]:
                    self.cards.append(self.card)
                self.card = None
        if tag == "div" and self.listing_depth:
            self.listing_depth -= 1


def grade_from_title(title: str) -> int | None:
    normalized = title.casefold()
    if any(
        token in normalized
        for token in (
            "kindergarten",
            "early childhood",
            "child development centre",
            "child development center",
            "preschool",
            "प्रारम्भिक बालविकास",
            "शिशु विकास केन्द्र",
        )
    ):
        return 0
    match = GRADE_PATTERN.search(title.translate(NEPALI_DIGITS))
    if not match:
        return None
    grade = int(match.group(1))
    return grade if 1 <= grade <= 12 else None


def subject_from_title(title: str) -> str:
    normalized = title.casefold()
    labels = (
        (
            (
                "प्रारम्भिक बालविकास",
                "शिशु विकास केन्द्र",
                "early childhood",
                "child development centre",
                "child development center",
                "eced",
            ),
            "Early Childhood Education",
        ),
        (("भोट भाषा", "भोटे भाषा", "bhote", "bhot language"), "Bhote Language"),
        (("उर्दु", "اردو", "urdu"), "Urdu"),
        (("अरबी", "अरेबिक", "arabic", "عربي"), "Arabic"),
        (("दीनियत", "दिनियात", "दीनियात", "deeniyat", "diniyat"), "Diniyat"),
        (("संस्कृत", "sanskrit"), "Sanskrit"),
        (("ऐच्छिक गणित", "optional mathematics"), "Optional Mathematics"),
        (("गणित", "mathematics", "maths"), "Mathematics"),
        (("नेपाली", "nepali"), "Nepali"),
        (("अङ्ग्रेजी", "अंग्रेजी", "english"), "English"),
        (("विज्ञान", "science"), "Science and Technology"),
        (("सामाजिक अध्ययन", "social studies"), "Social Studies"),
        (("कम्प्युटर", "computer"), "Computer Science"),
        (("स्वास्थ्य", "health"), "Health and Physical Education"),
        (("जनसङ्ख्या", "population"), "Population Education"),
        (("अर्थशास्त्र", "economics"), "Economics"),
        (("इतिहास", "history"), "History"),
        (("अवधी", "awadhi"), "Awadhi"),
        (("लिम्बु", "limbu"), "Limbu"),
        (("नेपालभाषा", "nepal bhasa"), "Nepal Bhasa"),
    )
    for needles, label in labels:
        if any(needle in normalized for needle in needles):
            return label
    return "Other"


def safe_filename(source_page: str, title: str) -> str:
    parts = [part for part in urlsplit(source_page).path.split("/") if part]
    item_id = parts[1] if len(parts) >= 3 and parts[0] == "content" else "book"
    slug = parts[2] if len(parts) >= 3 and parts[0] == "content" else title
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower()[:80] or "book"
    suffix = hashlib.sha256(source_page.encode()).hexdigest()[:8]
    return f"{item_id}-{slug}-{suffix}.pdf"


def _source_page_pdf(html: str, source_page: str) -> str | None:
    match = PDF_VARIABLE_PATTERN.search(html)
    if not match:
        return None
    download_url = urljoin(source_page, match.group(2).strip())
    _assert_source_url(download_url, DOWNLOAD_HOSTS)
    if not urlsplit(download_url).path.lower().endswith(".pdf"):
        raise ValueError("The CDC item page returned an unexpected file link.")
    return download_url


def _assert_source_url(url: str, hosts: set[str]):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in hosts or parsed.username:
        raise ValueError(
            "The CDC catalog returned a link outside its official HTTPS sources."
        )


def parse_catalog_page(html: str, page_url: str, feed: str = "G") -> list[CatalogBook]:
    _assert_source_url(page_url, {CATALOG_HOST, "www." + CATALOG_HOST})
    parser = CatalogParser()
    parser.feed(html)
    books = []
    for row in parser.rows:
        cells = row["cells"]
        if len(cells) < 2:
            continue
        title = cells[1]
        grade = grade_from_title(title)
        if grade is None:
            continue
        source_page = next(
            (
                urljoin(page_url, link)
                for link in row["links"]
                if urlsplit(urljoin(page_url, link)).path.startswith("/content/")
            ),
            "",
        )
        download_url = next(
            (
                urljoin(page_url, link)
                for link in row["links"]
                if urlsplit(urljoin(page_url, link)).path.lower().endswith(".pdf")
            ),
            None,
        )
        if source_page:
            _assert_source_url(source_page, {CATALOG_HOST, "www." + CATALOG_HOST})
        if download_url:
            _assert_source_url(download_url, DOWNLOAD_HOSTS)
        books.append(
            CatalogBook(
                grade=grade,
                title=title,
                subject=subject_from_title(title),
                feed=feed,
                catalog_page=page_url,
                source_page=source_page,
                download_url=download_url,
                filename=safe_filename(source_page, title) if source_page else None,
            )
        )
    return books


def parse_category_cards(
    html: str, page_url: str, feed: str = "E"
) -> list[CatalogBook]:
    _assert_source_url(page_url, {CATALOG_HOST, "www." + CATALOG_HOST})
    parser = CatalogCardParser()
    parser.feed(html)
    books = []
    for card in parser.cards:
        source_page = urljoin(page_url, card["source_page"])
        _assert_source_url(source_page, {CATALOG_HOST, "www." + CATALOG_HOST})
        title = card["title"]
        books.append(
            CatalogBook(
                grade=grade_from_title(title),
                title=title,
                subject=subject_from_title(title),
                feed=feed,
                catalog_page=page_url,
                source_page=source_page,
                download_url=None,
                filename=safe_filename(source_page, title),
            )
        )
    return books


class CatalogPageNotFound(Exception):
    pass


def request_bytes(
    url: str, *, max_bytes: int, method: str = "GET"
) -> tuple[bytes, object]:
    _assert_source_url(url, {CATALOG_HOST, "www." + CATALOG_HOST} | DOWNLOAD_HOSTS)
    request = Request(url, headers={"User-Agent": USER_AGENT}, method=method)
    for attempt in range(4):
        try:
            with urlopen(request, timeout=90) as response:
                length = int(response.headers.get("Content-Length", "0") or 0)
                if length and length > max_bytes:
                    raise RuntimeError(
                        "A source response exceeds the configured size limit."
                    )
                if method == "HEAD":
                    return b"", response.headers
                body = response.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise RuntimeError(
                        "A source response exceeds the configured size limit."
                    )
                return body, response.headers
        except HTTPError as error:
            if error.code == 404:
                raise CatalogPageNotFound from error
            if error.code not in {408, 425, 429, 500, 502, 503, 504} or attempt == 3:
                raise RuntimeError(
                    f"The CDC source returned HTTP {error.code}."
                ) from error
            retry_after = error.headers.get("Retry-After", "")
            delay = int(retry_after) if retry_after.isdigit() else 2**attempt
        except (TimeoutError, URLError, ConnectionError, OSError) as error:
            if attempt == 3:
                raise RuntimeError(
                    "The CDC source could not be reached after retries."
                ) from error
            delay = 2**attempt
        sleep(delay)
    raise RuntimeError("The CDC source request did not complete.")


def crawl_catalog(*, pause=sleep) -> tuple[list[CatalogBook], dict[str, int]]:
    books: dict[str, CatalogBook] = {}
    scanned_pages: dict[str, int] = {}
    for feed, feed_url in FEEDS.items():
        empty_pages = 0
        feed_scanned = 0
        for page in range(1, MAX_CATALOG_PAGES + 1):
            url = feed_url + "?" + urlencode({"page": page})
            try:
                html, _ = request_bytes(url, max_bytes=MAX_CATALOG_BYTES)
            except CatalogPageNotFound:
                empty_pages += 1
                if empty_pages >= 2 and feed_scanned:
                    break
                pause(REQUEST_INTERVAL_SECONDS)
                continue
            feed_scanned += 1
            page_html = html.decode("utf-8", "replace")
            page_books = parse_catalog_page(page_html, url, feed)
            if feed == "E":
                page_books.extend(parse_category_cards(page_html, url, feed))
                resolved = []
                for book in page_books:
                    detail_html, _ = request_bytes(
                        book.source_page, max_bytes=MAX_CATALOG_BYTES
                    )
                    download_url = _source_page_pdf(
                        detail_html.decode("utf-8", "replace"), book.source_page
                    )
                    if download_url:
                        resolved.append(
                            CatalogBook(
                                **{**asdict(book), "download_url": download_url}
                            )
                        )
                    pause(REQUEST_INTERVAL_SECONDS)
                page_books = resolved
            if not page_books:
                empty_pages += 1
                if empty_pages >= 2:
                    break
            else:
                empty_pages = 0
            for book in page_books:
                key = (
                    book.download_url
                    or book.source_page
                    or f"{book.grade}:{book.title}"
                )
                books.setdefault(key, book)
            pause(REQUEST_INTERVAL_SECONDS)
        else:
            raise RuntimeError(f"CDC feed {feed} exceeded the configured page limit.")
        scanned_pages[feed] = feed_scanned

    # CDC currently places the ECED curriculum under a syllabus feed, not the E textbook feed.
    curriculum_html, _ = request_bytes(
        EARLY_CHILDHOOD_CURRICULUM, max_bytes=MAX_CATALOG_BYTES
    )
    curriculum_pdf = _source_page_pdf(
        curriculum_html.decode("utf-8", "replace"), EARLY_CHILDHOOD_CURRICULUM
    )
    if curriculum_pdf:
        item = CatalogBook(
            grade=0,
            title="प्रारम्भिक बालविकास र शिक्षाको पाठ्यक्रम, २०७७ (परिमार्जन, २०८२)",
            subject="Early Childhood Education",
            feed="Syllabus E",
            catalog_page=EARLY_CHILDHOOD_CURRICULUM,
            source_page=EARLY_CHILDHOOD_CURRICULUM,
            download_url=curriculum_pdf,
            filename=safe_filename(EARLY_CHILDHOOD_CURRICULUM, "ECED curriculum"),
        )
        books.setdefault(curriculum_pdf, item)
    if not books:
        raise RuntimeError("No K–12 books were found in the CDC catalog feeds.")
    return list(books.values()), scanned_pages


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(path: Path, payload: dict):
    temporary = path.with_suffix(".pending")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    temporary.replace(path)


def download_pdf(book: CatalogBook, directory: Path, remaining_bytes: int) -> dict:
    if not book.download_url or not book.filename:
        raise RuntimeError(f"The catalog has no PDF download for {book.title}.")
    target = directory / book.filename
    if target.exists():
        with target.open("rb") as existing:
            magic = existing.read(5)
        if target.stat().st_size > MAX_FILE_BYTES or magic != b"%PDF-":
            raise RuntimeError(
                f"An existing local PDF failed validation: {target.name}."
            )
        return {
            **asdict(book),
            "bytes": target.stat().st_size,
            "sha256": sha256_file(target),
        }

    request = Request(book.download_url, headers={"User-Agent": USER_AGENT})
    temporary = target.with_suffix(target.suffix + ".part")
    for attempt in range(4):
        digest = hashlib.sha256()
        byte_count = 0
        try:
            with (
                urlopen(request, timeout=120) as response,
                temporary.open("wb") as output,
            ):
                content_type = response.headers.get_content_type()
                length = int(response.headers.get("Content-Length", "0") or 0)
                if length and (length > MAX_FILE_BYTES or length > remaining_bytes):
                    raise RuntimeError(
                        "The download set exceeds its configured size limit."
                    )
                first_chunk = b""
                while chunk := response.read(CHUNK_BYTES):
                    if not first_chunk:
                        first_chunk = chunk[:5]
                    byte_count += len(chunk)
                    if byte_count > MAX_FILE_BYTES or byte_count > remaining_bytes:
                        raise RuntimeError(
                            "The download set exceeds its configured size limit."
                        )
                    output.write(chunk)
                    digest.update(chunk)
                if first_chunk != b"%PDF-" or byte_count < 64:
                    raise RuntimeError("The CDC source did not return a readable PDF.")
                if content_type not in {"application/pdf", "application/octet-stream"}:
                    raise RuntimeError(
                        "The CDC source returned an unexpected file type."
                    )
            temporary.replace(target)
            return {
                **asdict(book),
                "bytes": byte_count,
                "sha256": digest.hexdigest(),
                "content_type": content_type,
            }
        except (TimeoutError, URLError, ConnectionError, OSError) as error:
            temporary.unlink(missing_ok=True)
            if attempt == 3:
                raise RuntimeError(
                    f"The PDF download failed for {book.title}."
                ) from error
            sleep(2**attempt)
    raise RuntimeError(f"The PDF download failed for {book.title}.")


def summarize(books: list[CatalogBook]) -> dict:
    counts = {
        "K": sum(book.grade == 0 for book in books),
        **{
            str(grade): sum(book.grade == grade for book in books)
            for grade in range(1, 13)
        },
    }
    ungraded = sum(book.grade is None for book in books)
    if ungraded:
        counts["Cross-grade"] = ungraded
    return {label: count for label, count in counts.items() if count}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="List books without downloading PDFs."
    )
    parser.add_argument(
        "--max-total-gib",
        type=float,
        default=8.0,
        help="Stop if the local corpus would exceed this bound (default: 8 GiB).",
    )
    args = parser.parse_args(argv)
    if args.max_total_gib <= 0:
        parser.error("--max-total-gib must be positive")
    books, pages = crawl_catalog()
    downloadable = [book for book in books if book.download_url and book.filename]
    print("CDC category pages scanned:", json.dumps(pages, ensure_ascii=False))
    print(f"K–12 and cross-grade titles found: {len(books)}")
    print(f"Titles with downloadable PDFs: {len(downloadable)}")
    print("Titles by grade:", json.dumps(summarize(books), ensure_ascii=False))
    if args.dry_run:
        for book in books:
            suffix = "PDF" if book.download_url else "no PDF link"
            print(f"Grade {book.grade} | {book.subject} | {book.title} | {suffix}")
        return 0

    directory = OUTPUT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    total_limit = int(args.max_total_gib * 1024**3)
    old_manifest_path = directory / MANIFEST_NAME
    old_manifest = (
        json.loads(old_manifest_path.read_text("utf-8"))
        if old_manifest_path.exists()
        else {}
    )
    previous = {
        item.get("download_url"): item
        for item in old_manifest.get("books", [])
        if isinstance(item, dict) and item.get("download_url")
    }
    results = []
    total_bytes = 0
    payload = {
        "provider": "Curriculum Development Centre, Nepal",
        "catalog_urls": FEEDS,
        "grade_range": {"from": 0, "to": 12},
        "retrieved_at": datetime.now(UTC).isoformat(),
        "catalog_pages_scanned": pages,
        "complete": False,
        "books": results,
    }
    write_manifest(old_manifest_path, payload)
    for index, book in enumerate(downloadable, start=1):
        old = previous.get(book.download_url)
        path = directory / book.filename
        if old and path.is_file() and path.stat().st_size == old.get("bytes"):
            result = {
                **asdict(book),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        else:
            result = download_pdf(book, directory, total_limit - total_bytes)
        total_bytes += result["bytes"]
        results.append(result)
        payload["books"] = results
        payload["total_bytes"] = total_bytes
        write_manifest(old_manifest_path, payload)
        if index % 10 == 0 or index == len(downloadable):
            print(
                f"Downloaded {index}/{len(downloadable)} PDFs ({total_bytes / 1024**2:.1f} MiB).",
                flush=True,
            )
        sleep(REQUEST_INTERVAL_SECONDS)
    payload["complete"] = len(results) == len(downloadable)
    payload["missing_pdf_titles"] = [
        asdict(book) for book in books if not book.download_url
    ]
    write_manifest(old_manifest_path, payload)
    print(f"Private PDF folder: {directory}")
    print(f"Private manifest: {old_manifest_path}")
    print(
        f"Downloaded {len(results)} PDFs, {total_bytes} bytes, sha256 verified per file."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
