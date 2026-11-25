#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "data" / "source_registry.json"

REQUIRED = (
    "id", "publisher", "dataset", "url",
    "data_family", "limitations", "initial_status"
)

OFFICIAL_DOMAINS = {
    "census.gov", "api.census.gov",
    "ons.gov.uk",
    "cmhc-schl.gc.ca",
    "ura.gov.sg", "eservice.ura.gov.sg",
    "mospi.gov.in",
    "oecd.org", "www.oecd.org", "sdmx.oecd.org"
}

def fail(message):
    print("ERROR:", message)
    return False

def is_official_host(host):
    return any(host == domain or host.endswith("." + domain)
               for domain in OFFICIAL_DOMAINS)

def check_url(url, timeout):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Kingdom21-SourceValidator/1.0"},
        method="HEAD"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.geturl()
    except urllib.error.HTTPError as exc:
        if exc.code not in (403, 405, 501):
            return exc.code, url
    except Exception:
        pass

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Kingdom21-SourceValidator/1.0",
            "Range": "bytes=0-0"
        }
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.geturl()
    except urllib.error.HTTPError as exc:
        return exc.code, url
    except Exception as exc:
        return None, str(exc).__class__.__name__

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-urls",
        action="store_true",
        help="Check source URLs over HTTPS"
    )
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()

    if not REGISTRY.is_file():
        raise SystemExit("Source registry not found: " + str(REGISTRY))

    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit("Invalid registry JSON: " + str(exc))

    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise SystemExit("Registry must contain a non-empty sources list.")

    ids = set()
    errors = 0
    warnings = 0

    print("SOURCE REGISTRY VALIDATION")
    print("Sources:", len(sources))

    for index, source in enumerate(sources, 1):
        label = source.get("id", "source-" + str(index))
        problems = []

        if not isinstance(source, dict):
            errors += int(fail(f"{label}: source entry must be an object"))
            continue

        for field in REQUIRED:
            if not source.get(field):
                problems.append("missing " + field)

        source_id = source.get("id")
        if source_id in ids:
            problems.append("duplicate source id")
        ids.add(source_id)

        url = source.get("url", "")
        parsed = urlparse(url)

        if parsed.scheme != "https" or not parsed.hostname:
            problems.append("source URL must use HTTPS")

        elif not is_official_host(parsed.hostname):
            problems.append("domain is not in the approved official-domain list")

        if not isinstance(source.get("limitations"), list) or not source.get("limitations"):
            problems.append("limitations must be a non-empty list")

        metrics = source.get("metrics")
        if not metrics:
            problems.append("metrics must be documented")

        if source.get("initial_status") == "registered_not_ingested":
            warnings += 1

        if problems:
            errors += 1
            print("FAIL:", label, "|", "; ".join(problems))
        else:
            print("PASS:", label)

        if args.check_urls and not problems:
            status, detail = check_url(url, args.timeout)
            if status is not None and 200 <= status < 400:
                print("  URL_HTTP_OK:", status)
            else:
                warnings += 1
                print("  URL_UNVERIFIED:", status, detail)

    print()
    print("UNIQUE_SOURCE_IDS:", len(ids))
    print("ERRORS:", errors)
    print("WARNINGS:", warnings)

    if errors:
        raise SystemExit(1)

    print("SOURCE_REGISTRY_AUDIT_PASSED")
    if not args.check_urls:
        print("NOTE: URL reachability was not tested. Use --check-urls separately.")

if __name__ == "__main__":
    main()
