import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "research_output"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

CLUSTERS = [
    ("destination_intent", "Destination-specific travel eSIM research: country, city, arrival, local networks, practical pre-purchase questions."),
    ("provider_comparison", "eSIM provider comparisons, provider selection intent, plan differences, transparent comparison criteria."),
    ("regional_travel", "Multi-country, regional, and cross-border travel eSIM planning."),
    ("device_compatibility", "eSIM-compatible phones, tablets, device checks, dual SIM, locked devices, and setup troubleshooting."),
    ("activation_setup", "Installation, QR code, activation timing, roaming settings, troubleshooting, and travel-day setup."),
    ("data_usage", "Travel data usage, trip duration, maps, messaging, video calls, hotspot, and data planning calculators."),
    ("policy_questions", "Hotspot/tethering, fair-use, speed limits, validity, top-ups, refunds, and policy questions requiring official evidence."),
    ("traveler_scenarios", "Practical eSIM planning for tourists, business travelers, families, long stays, cruises, and frequent travelers."),
]

FIELDS = [
    "keyword", "cluster", "search_intent", "page_type", "destination_slug",
    "provider_slug", "rationale", "evidence_needed", "suggested_title",
    "suggested_h1", "faq_ideas", "followup_search_queries",
    "search_volume", "organic_competition", "metrics_status", "research_status"
]

def load_slugs(filename, field):
    path = DATA / filename
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {str(row.get(field, "")).strip().lower() for row in csv.DictReader(f) if row.get(field)}

def parse_keys(raw):
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            parts = value
        elif isinstance(value, dict):
            parts = value.get("keys", [])
        else:
            parts = re.split(r"[\s,;]+", raw)
    except json.JSONDecodeError:
        parts = re.split(r"[\s,;]+", raw)
    result = []
    for item in parts:
        if isinstance(item, str):
            item = item.strip()
            if item and item not in result:
                result.append(item)
    return result

def prompt_for(cluster, description, destinations, providers):
    return f"""
You are an SEO research analyst for an independent global travel eSIM information website.
Research cluster: {cluster}
Scope: {description}

Generate 12 distinct, useful keyword/page-intent candidates. Prioritize specific long-tail questions and
clear user intent over broad head terms. Avoid near-duplicate phrasing and doorway-page ideas.
Use only these destination slugs when naming a destination: {", ".join(sorted(destinations))}
Use only these provider slugs when naming a provider: {", ".join(sorted(providers))}

Return ONLY a JSON array. Every item must have these string fields:
keyword, search_intent, page_type, destination_slug, provider_slug, rationale,
evidence_needed, suggested_title, suggested_h1, faq_ideas, followup_search_queries.

Allowed page_type values: destination_guide, provider_guide, comparison, calculator,
setup_help, compatibility_guide, policy_explainer, travel_planning_guide.
For destination_slug/provider_slug use an exact allowed slug or an empty string.
Separate multiple FAQ ideas and followup queries with " | ".

Critical accuracy rules:
- Do NOT invent search volume, keyword difficulty, organic competition, CPC, traffic, rankings, prices,
  plan allowances, provider coverage, supported networks, speeds, or policies.
- Do NOT claim a provider serves a destination unless independently verified from an official source.
- Do NOT invent source URLs or claim that research was verified.
- Candidates are hypotheses only and require independent evidence and real keyword metrics.
- Avoid making one thin page per minor keyword variation or city when the underlying answer is identical.
- Suggest a page only when it could answer a distinct user need with substantial original value.
""".strip()

def request_gemini(key, cluster, description, destinations, providers):
    body = {
        "contents": [{"parts": [{"text": prompt_for(cluster, description, destinations, providers)}]}],
        "generationConfig": {
            "temperature": 0.35,
            "responseMimeType": "application/json"
        }
    }
    request = urllib.request.Request(
        API_URL.format(model=MODEL),
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key,
        },
        method="POST"
    )
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=100) as response:
                payload = json.loads(response.read().decode("utf-8"))
            parts = payload["candidates"][0]["content"]["parts"]
            raw_text = "".join(part.get("text", "") for part in parts)
            parsed = json.loads(raw_text)
            if not isinstance(parsed, list):
                raise ValueError("Model response was not a JSON array.")
            return cluster, parsed
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                detail = ""
            detail = detail.replace(key, "[REDACTED]")
            try:
                error_data = json.loads(detail)
                message = error_data.get("error", {}).get("message", detail)
            except (ValueError, AttributeError):
                message = detail
            last_error = f"HTTP {exc.code} {exc.reason}: {str(message)[:500]}"
            if attempt < 2:
                time.sleep(2 ** attempt)
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
            last_error = f"{type(exc).__name__}: {str(exc)[:300]}"
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Cluster {cluster} failed after retries ({last_error}).")

def main():
    keys = parse_keys(os.environ.get("GEMINI_KEYS_8"))
    if len(keys) != 8:
        raise SystemExit(f"STOP: GEMINI_KEYS_8 must contain exactly 8 unique keys; detected {len(keys)}. Secret values were not displayed.")
    destinations = load_slugs("destinations.csv", "slug")
    providers = load_slugs("providers.csv", "provider_slug")
    OUT.mkdir(parents=True, exist_ok=True)

    results = []
    errors = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(request_gemini, keys[i], cluster, description, destinations, providers): cluster
            for i, (cluster, description) in enumerate(CLUSTERS)
        }
        for future in as_completed(futures):
            cluster = futures[future]
            try:
                name, items = future.result()
                for item in items:
                    if isinstance(item, dict):
                        item["_cluster"] = name
                        results.append(item)
                print(f"Completed cluster: {cluster} ({len(items)} candidates)")
            except Exception as exc:
                errors.append(f"{cluster}: {exc}")
                print(f"FAILED cluster: {cluster} ({type(exc).__name__})")

    seen = set()
    rows = []
    for item in results:
        keyword = re.sub(r"\s+", " ", str(item.get("keyword", "")).strip())
        normalized = keyword.casefold()
        if not keyword or normalized in seen:
            continue
        seen.add(normalized)
        destination = str(item.get("destination_slug", "")).strip().lower()
        provider = str(item.get("provider_slug", "")).strip().lower()
        if destination not in destinations:
            destination = ""
        if provider not in providers:
            provider = ""
        row = {field: str(item.get(field, "")).strip() for field in FIELDS}
        row["keyword"] = keyword
        row["cluster"] = item.get("_cluster", "")
        row["destination_slug"] = destination
        row["provider_slug"] = provider
        row["search_volume"] = ""
        row["organic_competition"] = ""
        row["metrics_status"] = "not_measured"
        row["research_status"] = "unverified_hypothesis"
        rows.append(row)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = OUT / f"keyword_candidates_{timestamp}.csv"
    temp_file = OUT / f"keyword_candidates_{timestamp}.csv.tmp"
    with temp_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    temp_file.replace(output_file)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "workers": 8,
        "clusters_requested": len(CLUSTERS),
        "unique_candidates": len(rows),
        "csv_file": output_file.name,
        "metrics_status": "not_measured",
        "publication_status": "not_published",
        "errors": errors,
    }
    (OUT / f"research_report_{timestamp}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(f"RESEARCH_COMPLETE: {len(rows)} unique candidates")
    print("Metrics: NOT MEASURED; publication: NOT PUBLISHED")
    print(f"Output: {output_file}")
    if errors:
        raise SystemExit(f"{len(errors)} cluster(s) failed; inspect report before relying on this batch.")

if __name__ == "__main__":
    main()
