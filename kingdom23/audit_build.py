import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote
import xml.etree.ElementTree as ET

from config import SITE_URL, STAGE, SITEMAP_SHARD_LIMIT

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
BASE = SITE_URL.rstrip("/") + "/"
errors = []


def fail(message):
    errors.append(message)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = False
        self.title_text = ""
        self.h1_count = 0
        self.meta_description = ""
        self.canonical = None
        self.noindex = False
        self.links = []
        self.in_title = False
        self.in_h1 = False
        self.h1_text = ""
        self.visible_text = []
        self.html_seen = False
        self.head_seen = False
        self.body_seen = False
        self.in_body = False
        self.ignored_content = False

    def handle_starttag(self, tag, attrs):
        if tag == "html":
            self.html_seen = True
        elif tag == "head":
            self.head_seen = True
        elif tag == "body":
            self.body_seen = True
            self.in_body = True
        elif tag in ("script", "style"):
            self.ignored_content = True
        a = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.h1_count += 1
            self.in_h1 = True
        elif tag == "meta":
            if a.get("name", "").lower() == "description" and a.get("content", "").strip():
                self.meta_description = a.get("content", "").strip()
            if a.get("name", "").lower() == "robots" and "noindex" in a.get("content", "").lower():
                self.noindex = True
        elif tag == "link" and "canonical" in a.get("rel", "").lower().split():
            self.canonical = a.get("href")
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.ignored_content = False
        if tag == "body":
            self.in_body = False
        if tag == "title":
            self.in_title = False
        elif tag == "h1":
            self.in_h1 = False

    def handle_data(self, data):
        if self.in_title:
            self.title_text += data
        if self.in_h1:
            self.h1_text += data
        if self.in_body and not self.ignored_content:
            self.visible_text.append(data)


def valid_date(value, label):
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        fail(f"Invalid lastmod date in {label}: {value!r}")


def main():
    if not STAGE.is_dir():
        fail(f"Staging directory does not exist: {STAGE}")
        return

    index_path = STAGE / "sitemap.xml"
    robots_path = STAGE / "robots.txt"

    if not index_path.is_file():
        fail("Missing sitemap.xml")
        return
    if not robots_path.is_file():
        fail("Missing robots.txt")
    else:
        robots = robots_path.read_text(encoding="utf-8")
        if f"Sitemap: {BASE}sitemap.xml" not in robots:
            fail("robots.txt does not reference the canonical sitemap index")

    try:
        root = ET.parse(index_path).getroot()
    except ET.ParseError as exc:
        fail(f"Invalid sitemap index XML: {exc}")
        return

    if root.tag != f"{{{NS['sm']}}}sitemapindex":
        fail("sitemap.xml root is not a standard sitemapindex")

    shard_files = []
    for entry in root.findall("sm:sitemap", NS):
        loc = entry.findtext("sm:loc", default="", namespaces=NS)
        lastmod = entry.findtext("sm:lastmod", default="", namespaces=NS)
        valid_date(lastmod, "sitemap index")
        if not loc.startswith(BASE):
            fail(f"Non-canonical sitemap shard URL: {loc}")
            continue
        name = unquote(urlparse(loc).path.rsplit("/", 1)[-1])
        if not re.fullmatch(r"sitemap-[1-9][0-9]*\.xml", name):
            fail(f"Unexpected sitemap shard name: {name}")
            continue
        shard_files.append(name)

    if not shard_files:
        fail("Sitemap index contains no child shards")

    listed_urls = set()
    for name in shard_files:
        path = STAGE / name
        if not path.is_file():
            fail(f"Missing sitemap shard: {name}")
            continue
        try:
            shard = ET.parse(path).getroot()
        except ET.ParseError as exc:
            fail(f"Invalid XML in {name}: {exc}")
            continue

        if shard.tag != f"{{{NS['sm']}}}urlset":
            fail(f"{name} does not contain a standard urlset")

        entries = shard.findall("sm:url", NS)
        if len(entries) > SITEMAP_SHARD_LIMIT:
            fail(f"{name} exceeds the {SITEMAP_SHARD_LIMIT}-URL limit")

        for entry in entries:
            loc = entry.findtext("sm:loc", default="", namespaces=NS)
            lastmod = entry.findtext("sm:lastmod", default="", namespaces=NS)
            valid_date(lastmod, name)
            if not loc.startswith(BASE):
                fail(f"Non-canonical URL in {name}: {loc}")
            if loc in listed_urls:
                fail(f"Duplicate sitemap URL: {loc}")
            listed_urls.add(loc)

    html_files = sorted(STAGE.rglob("*.html"))
    html_urls = set()
    seen_titles = {}
    seen_descriptions = {}
    seen_h1 = {}
    seen_content = {}
    for path in html_files:
        relative = path.relative_to(STAGE).as_posix()
        url = BASE if relative == "index.html" else BASE + relative
        html_urls.add(url)

        try:
            source = path.read_text(encoding="utf-8")
            parser = PageParser()
            parser.feed(source)
        except Exception as exc:
            fail(f"Could not parse {relative}: {exc}")
            continue

        if not parser.html_seen or not parser.head_seen or not parser.body_seen:
            fail(f"Missing HTML, HEAD, or BODY structure: {relative}")

        title_value = " ".join(parser.title_text.split())
        description_value = " ".join(parser.meta_description.split())
        h1_value = " ".join(parser.h1_text.split())
        content_value = " ".join(" ".join(parser.visible_text).split())
        word_count = len(re.findall(r"\b[\w'-]+\b", content_value))

        if word_count < 100:
            fail(f"Thin body content: {relative} has {word_count} words; minimum is 100")

        for label, value, seen in (
            ("title", title_value, seen_titles),
            ("meta description", description_value, seen_descriptions),
            ("H1", h1_value, seen_h1),
            ("body content", content_value, seen_content),
        ):
            if value:
                key = value.casefold()
                if key in seen:
                    fail(f"Duplicate {label} in {relative}; also used by {seen[key]}")
                else:
                    seen[key] = relative

        if not title_value:
            fail(f"Missing title: {relative}")
        if not description_value:
            fail(f"Missing meta description: {relative}")
        if parser.h1_count != 1 or not h1_value:
            fail(f"Expected exactly one non-empty H1: {relative}")
        if parser.canonical != url:
            fail(f"Canonical mismatch in {relative}: {parser.canonical!r}")
        if parser.noindex:
            fail(f"noindex found in {relative}")

        for link in parser.links:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or link.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            target = unquote(parsed.path)
            if not target or target == "/":
                target = "index.html"
            elif target.startswith("/"):
                target = target.lstrip("/") or "index.html"
            else:
                target = (path.parent.relative_to(STAGE) / target).as_posix()
            resolved = (STAGE / target).resolve()
            if STAGE.resolve() not in resolved.parents and resolved != STAGE.resolve():
                fail(f"Link escapes staging directory in {relative}: {link}")
            elif not resolved.is_file():
                fail(f"Broken internal link in {relative}: {link}")

    if listed_urls != html_urls:
        missing = sorted(html_urls - listed_urls)
        extra = sorted(listed_urls - html_urls)
        if missing:
            fail(f"HTML pages missing from sitemap: {missing[:5]}")
        if extra:
            fail(f"Sitemap URLs without HTML pages: {extra[:5]}")

    if errors:
        print("BUILD_AUDIT_FAILED")
        for item in errors:
            print("ERROR:", item)
        sys.exit(1)

    print("BUILD_AUDIT_OK")
    print(f"HTML pages: {len(html_files)}")
    print(f"Sitemap shards: {len(shard_files)}")
    print(f"Sitemap URLs: {len(listed_urls)}")


if __name__ == "__main__":
    main()
