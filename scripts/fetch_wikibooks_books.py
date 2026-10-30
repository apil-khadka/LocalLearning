#!/usr/bin/env python3
"""Fetch selected, text-only Wikibooks books into ignored prototype storage."""

import argparse
import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://en.wikibooks.org/w/api.php"
LICENSE = "CC BY-SA 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
USER_AGENT = "DigitalHimalayaPrototype/0.1 (open educational resource pilot)"
MAX_PAGES = 100
MAX_RESPONSE_BYTES = 3 * 1024 * 1024
MAX_BOOK_CHARS = 1_000_000
REQUEST_INTERVAL_SECONDS = 1.1
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "content/private/wikibooks"


@dataclass(frozen=True)
class Book:
    slug: str
    title: str
    subject: str
    level_notes: str
    pages: tuple[str, ...]

    @property
    def source_url(self) -> str:
        return "https://en.wikibooks.org/wiki/" + self.title.replace(" ", "_")

    @property
    def category(self) -> str:
        return "Category:Book:" + self.title


BOOKS = {
    "human-body": Book(
        slug="human-body",
        title="Wikijunior:Human Body",
        subject="Science",
        level_notes=(
            "Wikijunior targets ages 8-12; these selected sections need teacher review."
        ),
        pages=(
            "Wikijunior:Human Body",
            "Wikijunior:Human Body/Heart",
            "Wikijunior:Human Body/Blood",
            "Wikijunior:Human Body/Lungs",
            "Wikijunior:Human Body/Skeleton",
            "Wikijunior:Human Body/Brain",
        ),
    ),
    "solar-system": Book(
        slug="solar-system",
        title="Wikijunior:Solar System",
        subject="Science",
        level_notes="Not mapped to Nepal grades; teacher review required.",
        pages=(
            "Wikijunior:Solar System",
            "Wikijunior:Solar System/The Sun",
            "Wikijunior:Solar System/Earth",
            "Wikijunior:Solar System/Moon",
            "Wikijunior:Solar System/Mars",
            "Wikijunior:Solar System/Jupiter",
        ),
    ),
    "elementary-geometry": Book(
        slug="elementary-geometry",
        title="Geometry for Elementary School",
        subject="Mathematics",
        level_notes="Elementary-school title; Nepal grade alignment needs teacher review.",
        pages=(
            "Geometry for Elementary School",
            "Geometry for Elementary School/Concepts",
            "Geometry for Elementary School/Angles",
            "Geometry for Elementary School/Plane shapes",
            "Geometry for Elementary School/Measurements",
            "Geometry for Elementary School/Symmetry",
        ),
    ),
}


def request_api(params: dict) -> dict:
    request = Request(
        f"{API_URL}?{urlencode(params)}", headers={"User-Agent": USER_AGENT}
    )
    try:
        with urlopen(request, timeout=25) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        if error.code == 429:
            retry_after = error.headers.get("Retry-After", "later")
            raise RuntimeError(
                f"Wikibooks rate-limited this fetch; retry after {retry_after}."
            ) from error
        raise
    if len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeError(
            "A Wikibooks API response exceeded the prototype size limit."
        )
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("The Wikibooks API returned invalid JSON.") from error
    if payload.get("error"):
        raise RuntimeError("The Wikibooks API rejected the catalog request.")
    return payload


def markdown_extract(text: str) -> str:
    """Convert MediaWiki section markers to Markdown while preserving other text."""
    converted = []
    for line in text.splitlines():
        match = re.fullmatch(r"(={2,6})\s*(.*?)\s*\1", line.strip())
        if match:
            level = min(len(match.group(1)) + 1, 6)
            converted.append(f"{'#' * level} {match.group(2)}")
        else:
            converted.append(line)
    return "\n".join(converted).strip()


def fetch_book(
    book: Book,
    api: Callable[[dict], dict] = request_api,
    pause: Callable[[float], None] = sleep,
) -> tuple[str, dict]:
    catalog = api(
        {
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "generator": "categorymembers",
            "gcmtitle": book.category,
            "gcmtype": "page",
            "gcmlimit": MAX_PAGES,
            "prop": "info",
            "inprop": "url",
        }
    )
    listed_pages = catalog.get("query", {}).get("pages", [])
    if (
        not isinstance(listed_pages, list)
        or not listed_pages
        or len(listed_pages) > MAX_PAGES
        or "continue" in catalog
    ):
        raise RuntimeError(
            f"Wikibooks returned an empty or oversized book: {book.title}."
        )

    catalog_titles = set()
    for page in listed_pages:
        title = page.get("title")
        if not isinstance(title, str) or (
            title != book.title and not title.startswith(book.title + "/")
        ):
            raise RuntimeError(
                "The Wikibooks API returned a page outside the selected book."
            )
        catalog_titles.add(title)

    page_titles = list(book.pages)
    if len(page_titles) > MAX_PAGES or len(set(page_titles)) != len(page_titles):
        raise RuntimeError(
            f"The selected Wikibooks sections are invalid: {book.title}."
        )
    if any(title not in catalog_titles for title in page_titles):
        raise RuntimeError(
            f"A selected section is not in the Wikibooks book: {book.title}."
        )

    extracts = {}
    for index, title in enumerate(page_titles):
        if index:
            pause(REQUEST_INTERVAL_SECONDS)
        response = api(
            {
                "action": "query",
                "format": "json",
                "formatversion": 2,
                "titles": title,
                "prop": "extracts|info",
                "explaintext": 1,
                "inprop": "url",
            }
        )
        pages = response.get("query", {}).get("pages", [])
        if not isinstance(pages, list) or len(pages) != 1:
            raise RuntimeError("The Wikibooks API returned invalid page content.")
        page = pages[0]
        response_title = page.get("title")
        url = page.get("fullurl", "")
        extract = page.get("extract", "")
        revision = page.get("lastrevid")
        if (
            response_title != title
            or (title != book.title and not title.startswith(book.title + "/"))
            or not url.startswith("https://en.wikibooks.org/wiki/")
            or page.get("missing")
            or not isinstance(revision, int)
            or not isinstance(extract, str)
        ):
            raise RuntimeError("The Wikibooks API returned unexpected page metadata.")
        extracts[title] = {
            "url": f"{url}?oldid={revision}",
            "revision_id": revision,
            "extract": extract.strip(),
        }

    if set(extracts) != set(page_titles):
        raise RuntimeError(
            "The Wikibooks API returned an incomplete set of book pages."
        )

    included_pages = []
    source_pages = []
    for title in sorted(page_titles, key=str.casefold):
        page = extracts[title]
        is_template = title.rsplit("/", 1)[-1].casefold().endswith(" template")
        include = bool(page["extract"]) and not is_template
        source_pages.append(
            {
                "title": title,
                "url": page["url"],
                "revision_id": page["revision_id"],
                "characters": len(page["extract"]),
                "included": include,
            }
        )
        if include:
            included_pages.append(f"## {title}\n\n{markdown_extract(page['extract'])}")

    attribution = (
        f"{book.title}, Wikibooks contributors, licensed under {LICENSE}. "
        f"Source: {book.source_url}. Exact source revisions are listed in the adjacent "
        "attribution JSON. Changes: page text was extracted as UTF-8, section heading markers "
        "were converted to Markdown, and selected pages were combined into one text file; "
        "images and other media are excluded."
    )
    text = f"{book.title}\n\n{attribution}\n\n" + "\n\n".join(included_pages) + "\n"
    if len(text) < 1000 or len(text) > MAX_BOOK_CHARS:
        raise RuntimeError(f"The extracted book had an unexpected size: {book.title}.")
    manifest = {
        "title": book.title,
        "subject": book.subject,
        "level_notes": book.level_notes,
        "source": book.source_url,
        "license": LICENSE,
        "license_url": LICENSE_URL,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "scope": (
            "Selected chapter text only; images and other media are excluded. "
            "This is a partial source extraction, not a complete copy of the book."
        ),
        "page_count": len(included_pages),
        "character_count": len(text),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "pages": source_pages,
    }
    return text, manifest


def write_book(book: Book, output_dir: Path = OUTPUT_DIR) -> tuple[Path, Path]:
    text, manifest = fetch_book(book)
    output_dir.mkdir(parents=True, exist_ok=True)
    text_path = output_dir / f"{book.slug}.txt"
    manifest_path = output_dir / f"{book.slug}.json"
    text_temp = text_path.with_suffix(".txt.tmp")
    manifest_temp = manifest_path.with_suffix(".json.tmp")
    text_temp.write_text(text, encoding="utf-8")
    manifest_temp.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    text_temp.replace(text_path)
    manifest_temp.replace(manifest_path)
    return text_path, manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "books",
        nargs="*",
        choices=sorted(BOOKS),
        default=sorted(BOOKS),
        help="Book slugs to fetch (default: all configured books).",
    )
    args = parser.parse_args()
    try:
        for slug in args.books:
            text_path, manifest_path = write_book(BOOKS[slug])
            print(f"Saved {text_path.stat().st_size:,} bytes to {text_path}")
            print(f"Revision-level attribution: {manifest_path}")
    except (RuntimeError, HTTPError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
