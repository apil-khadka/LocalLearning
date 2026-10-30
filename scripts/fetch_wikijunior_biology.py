#!/usr/bin/env python3
"""Fetch the Wikibooks Wikijunior Biology text as one private prototype fixture."""

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://en.wikibooks.org/w/api.php"
BOOK_CATEGORY = "Category:Book:Wikijunior:Biology"
BOOK_TITLE = "Wikijunior:Biology"
PRINTABLE_TITLE = "Wikijunior:Biology/Printable version"
BOOK_URL = "https://en.wikibooks.org/wiki/Wikijunior:Biology"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
MAX_PAGES = 50
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "content/private/wikibooks"


def fetch_book() -> tuple[str, list[dict]]:
    headers = {
        "User-Agent": "DigitalHimalayaPrototype/0.1 (open educational resource pilot)"
    }

    def api(params: dict) -> dict:
        query = urlencode(params)
        request = Request(f"{API_URL}?{query}", headers=headers)
        with urlopen(request, timeout=20) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise RuntimeError(
                "The Wikibooks API response exceeded the prototype size limit."
            )
        payload = json.loads(body)
        if payload.get("error"):
            raise RuntimeError("The Wikibooks API rejected the catalog request.")
        return payload

    catalog = api(
        {
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "generator": "categorymembers",
            "gcmtitle": BOOK_CATEGORY,
            "gcmtype": "page",
            "gcmlimit": MAX_PAGES,
            "prop": "info",
            "inprop": "url",
        }
    )
    pages = catalog.get("query", {}).get("pages", [])
    if not isinstance(pages, list) or not pages or len(pages) > MAX_PAGES:
        raise RuntimeError(
            "The Wikibooks API returned an empty or unexpectedly large book."
        )
    if "continue" in catalog:
        raise RuntimeError("The Wikibooks book exceeded the prototype page limit.")

    sources = []
    for page in sorted(pages, key=lambda item: item.get("title", "")):
        title = page.get("title")
        full_url = page.get("fullurl", "")
        if (
            not isinstance(title, str)
            or not title.startswith(BOOK_TITLE)
            or not full_url.startswith("https://en.wikibooks.org/wiki/")
            or not isinstance(page.get("lastrevid"), int)
        ):
            raise RuntimeError("The Wikibooks API returned unexpected page metadata.")
        sources.append(
            {
                "title": title,
                "url": f"{full_url}?oldid={page['lastrevid']}",
                "revision_id": page["lastrevid"],
            }
        )

    printable = api(
        {
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "titles": PRINTABLE_TITLE,
            "prop": "extracts|info",
            "explaintext": 1,
            "inprop": "url",
        }
    )
    printable_pages = printable.get("query", {}).get("pages", [])
    if len(printable_pages) != 1 or printable_pages[0].get("title") != PRINTABLE_TITLE:
        raise RuntimeError("The Wikibooks API returned no printable biology text.")
    page = printable_pages[0]
    extract = page.get("extract", "")
    if (
        not isinstance(extract, str)
        or len(extract) < 1000
        or not isinstance(page.get("lastrevid"), int)
    ):
        raise RuntimeError(
            "The Wikibooks printable version did not contain readable text."
        )

    attribution = (
        "Wikijunior:Biology, Wikibooks contributors, licensed under CC BY-SA 4.0. "
        f"Source: {BOOK_URL}. The adjacent attribution.json lists source page revisions. "
        "Changes: extracted text from the printable version as UTF-8. Images and other media "
        "are not included."
    )
    text = f"{BOOK_TITLE}\n\n{attribution}\n\n{extract.strip()}\n"
    sources.append(
        {
            "title": page["title"],
            "url": f"{page['fullurl']}?oldid={page['lastrevid']}",
            "revision_id": page["lastrevid"],
            "role": "printable text source",
        }
    )
    return text, sources


def main() -> None:
    text, sources = fetch_book()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    text_path = OUTPUT_DIR / "wikijunior-biology.txt"
    manifest_path = OUTPUT_DIR / "attribution.json"
    text_path.write_text(text, encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "title": "Wikijunior: Biology",
                "source": BOOK_URL,
                "license": "CC BY-SA 4.0",
                "license_url": LICENSE_URL,
                "retrieved_at_utc": datetime.now(UTC).isoformat(),
                "scope": "Text only; images and other media are excluded.",
                "page_count": len(sources) - 1,
                "sources": sources,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Saved text sourced from {len(sources) - 1} Wikibooks pages "
        f"({text_path.stat().st_size:,} bytes) to {text_path}"
    )
    print(f"Attribution and revision IDs: {manifest_path}")


if __name__ == "__main__":
    main()
