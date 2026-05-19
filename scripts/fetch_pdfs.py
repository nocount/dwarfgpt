"""Download the Neo-Khuzdul support-document PDFs from The Dwarrow Scholar's
public library page into corpus/pdfs/.

Usage:
    uv run python scripts/fetch_pdfs.py                # default listing URL
    uv run python scripts/fetch_pdfs.py --dry-run      # list links, download nothing
    uv run python scripts/fetch_pdfs.py --include-zip  # also fetch the .zip plugins
    uv run python scripts/fetch_pdfs.py --url <other>  # different listing page

Behavior:
- scrapes <a href="...pdf"> links from the listing page
- the PDFs themselves live on Dropbox; rewrites URLs to add ?dl=1 so we get a
  raw download instead of the Dropbox preview HTML
- writes to corpus/pdfs/<sanitized-filename>.pdf
- skips files that already exist on disk
- prints a per-file summary at the end
- rate-limits to ~1 request/sec on the listing host and on Dropbox
- writes a corpus/pdfs/_index.json with {filename, source_url, sha256, bytes}
  per downloaded file so we can diff against future runs
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

LISTING_URL = "https://www.dwarrowscholar.com/library.html"
USER_AGENT = "dwarfgpt-research/0.1 (+https://github.com/wilsonburchenal/dwarfgpt; contact: wilsonburchenal@gmail.com)"
SLEEP_BETWEEN_REQUESTS = 1.0
TIMEOUT_SECONDS = 60.0

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_ROOT / "corpus" / "pdfs"
INDEX_PATH = PDF_DIR / "_index.json"


@dataclass(frozen=True, slots=True)
class PdfLink:
    source_url: str          # original href as it appeared on the listing page
    download_url: str        # rewritten for direct download (e.g. Dropbox ?dl=1)
    filename: str            # sanitized local filename


def sanitize_filename(name: str) -> str:
    name = unquote(name)
    name = unicodedata.normalize("NFKC", name)
    name = name.replace("/", "_").replace("\\", "_")
    # collapse runs of whitespace, strip control chars
    name = re.sub(r"[\x00-\x1f]+", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    # Windows-illegal characters
    name = re.sub(r'[<>:"|?*]', "-", name)
    return name


def rewrite_for_download(url: str) -> str:
    """Dropbox preview pages serve HTML by default. Add ?dl=1 to force a direct
    download. Non-Dropbox URLs are returned unchanged."""
    parts = urlsplit(url)
    if "dropbox.com" not in parts.netloc:
        return url
    query = parts.query
    if "dl=1" in query:
        return url
    if "dl=0" in query:
        query = query.replace("dl=0", "dl=1")
    else:
        query = (query + "&dl=1") if query else "dl=1"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def extract_pdf_links(listing_html: str, listing_url: str, *, include_zip: bool) -> list[PdfLink]:
    soup = BeautifulSoup(listing_html, "html.parser")
    seen_urls: set[str] = set()
    links: list[PdfLink] = []

    valid_suffixes = (".pdf",) if not include_zip else (".pdf", ".zip")

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
            continue
        absolute = urljoin(listing_url, href)
        # Strip fragments for matching; some Dropbox URLs end with `?...&dl=0`
        path = urlparse(absolute).path.lower()
        if not path.endswith(valid_suffixes):
            continue
        if absolute in seen_urls:
            continue
        seen_urls.add(absolute)

        basename = sanitize_filename(Path(urlparse(absolute).path).name)
        links.append(
            PdfLink(
                source_url=absolute,
                download_url=rewrite_for_download(absolute),
                filename=basename,
            )
        )

    return links


def fetch_listing(client: httpx.Client, listing_url: str) -> str:
    resp = client.get(listing_url, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def download_pdf(client: httpx.Client, link: PdfLink, dest: Path) -> tuple[int, str]:
    """Stream-download one PDF. Returns (bytes_written, sha256_hex)."""
    h = hashlib.sha256()
    total = 0
    tmp = dest.with_suffix(dest.suffix + ".part")
    with client.stream("GET", link.download_url, follow_redirects=True) as resp:
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        if "html" in ctype.lower():
            raise RuntimeError(
                f"server returned HTML, not a PDF (content-type={ctype!r}). "
                "Probably hit a Dropbox preview / login wall."
            )
        with tmp.open("wb") as f:
            for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                if not chunk:
                    continue
                f.write(chunk)
                h.update(chunk)
                total += len(chunk)
    tmp.replace(dest)
    return total, h.hexdigest()


def load_existing_index(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_index(path: Path, index: dict[str, dict]) -> None:
    path.write_text(
        json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default=LISTING_URL, help="listing page URL")
    ap.add_argument("--dest", default=str(PDF_DIR), help="destination directory")
    ap.add_argument("--dry-run", action="store_true", help="list links, don't download")
    ap.add_argument("--include-zip", action="store_true", help="also fetch .zip files")
    ap.add_argument("--limit", type=int, default=0, help="only download first N (debug)")
    args = ap.parse_args(argv)

    dest_dir = Path(args.dest).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    index_path = dest_dir / "_index.json"
    index = load_existing_index(index_path)

    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    with httpx.Client(headers=headers, timeout=TIMEOUT_SECONDS) as client:
        print(f"Fetching listing: {args.url}")
        html = fetch_listing(client, args.url)
        links = extract_pdf_links(html, args.url, include_zip=args.include_zip)
        print(f"Found {len(links)} link(s).")

        if args.limit:
            links = links[: args.limit]

        if args.dry_run:
            for L in links:
                print(f"  {L.filename}\n    src={L.source_url}\n    dl ={L.download_url}")
            return 0

        downloaded, skipped, failed = 0, 0, 0
        time.sleep(SLEEP_BETWEEN_REQUESTS)
        for i, link in enumerate(links, 1):
            dest = dest_dir / link.filename
            if dest.exists() and dest.stat().st_size > 0:
                print(f"  [{i:3d}/{len(links)}] SKIP (exists) {link.filename}")
                skipped += 1
                continue
            print(f"  [{i:3d}/{len(links)}] GET  {link.filename}")
            try:
                nbytes, sha = download_pdf(client, link, dest)
            except (httpx.HTTPError, RuntimeError) as exc:
                print(f"        FAILED: {exc}", file=sys.stderr)
                failed += 1
                time.sleep(SLEEP_BETWEEN_REQUESTS)
                continue
            index[link.filename] = {
                "source_url": link.source_url,
                "download_url": link.download_url,
                "bytes": nbytes,
                "sha256": sha,
            }
            save_index(index_path, index)
            print(f"        OK   {nbytes:,} bytes  sha256={sha[:16]}...")
            downloaded += 1
            time.sleep(SLEEP_BETWEEN_REQUESTS)

        print(
            f"\nDone. downloaded={downloaded} skipped={skipped} failed={failed} "
            f"-> {dest_dir}"
        )
        return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
