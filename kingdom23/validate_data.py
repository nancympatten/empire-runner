import csv
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from config import DATA_DIR

SCHEMAS = {
    "destinations.csv": ["slug","country_name","iso2","iso3","currency_code","region","travel_notes","source_slug","source_checked_date","evidence_status","currency_source_slug","capital_city","income_level","lending_type","capital_longitude","capital_latitude"],
    "providers.csv": ["provider_slug","provider_name","official_url","headquarters_country","support_url","source_slug","source_checked_date","evidence_status","notes"],
    "plan_observations.csv": ["observation_id","provider_slug","destination_slug","plan_name","data_gb","validity_days","price_amount","price_currency","network_type","hotspot_policy","activation_policy","fair_use_policy","observed_date","source_url","source_slug","evidence_status","limitations"],
    "source_registry.csv": ["source_slug","organization","source_type","source_url","geographic_coverage","verification_status","last_checked_date","methodology_notes","access_status","access_checked_date"],
    "page_topics.csv": ["slug","page_type","primary_keyword","destination_slug","provider_slug","title","meta_description","h1","intent","evidence_requirements","related_slugs"],
}

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EVIDENCE = {"verified", "partially_verified", "unverified", "needs_review"}
SOURCE_STATUS = {"verified", "partially_verified", "unverified", "needs_review"}
ACCESS_STATUS = {"http_200", "network_unreachable", "not_checked"}
ISO2_RE = re.compile(r"^[A-Z]{2}$")
ISO3_RE = re.compile(r"^[A-Z]{3}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def fail(message):
    raise ValueError(message)


def check_date(value, field, row_id):
    if not value:
        return
    try:
        date.fromisoformat(value)
    except ValueError:
        fail(f"Invalid ISO date in {field}, row {row_id}: {value!r}")


def check_url(value, field, row_id, required=False):
    if not value:
        if required:
            fail(f"Missing {field}, row {row_id}")
        return
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        fail(f"Expected HTTPS URL in {field}, row {row_id}: {value!r}")


def check_number(value, field, row_id, minimum=None, required=False):
    if not value:
        if required:
            fail(f"Missing {field}, row {row_id}")
        return
    try:
        number = Decimal(value)
    except InvalidOperation:
        fail(f"Invalid number in {field}, row {row_id}: {value!r}")
    if not number.is_finite() or (minimum is not None and number < minimum):
        fail(f"Out-of-range {field}, row {row_id}: {value!r}")


def load_csv(filename):
    path = DATA_DIR / filename
    if not path.is_file():
        fail(f"Missing required CSV: {path}")
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != SCHEMAS[filename]:
            fail(f"Header mismatch in {filename}: {reader.fieldnames}")
        rows = list(reader)
    for number, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            fail(f"Malformed row {number} in {filename}")
    return rows


def unique_values(rows, key, filename):
    seen = set()
    for number, row in enumerate(rows, 2):
        value = row[key].strip()
        if not value:
            fail(f"Empty {key} in {filename}, row {number}")
        if value in seen:
            fail(f"Duplicate {key}={value!r} in {filename}")
        seen.add(value)
    return seen


def validate_all():
    data = {name: load_csv(name) for name in SCHEMAS}

    destinations = unique_values(data["destinations.csv"], "slug", "destinations.csv")
    providers = unique_values(data["providers.csv"], "provider_slug", "providers.csv")
    provider_rows = {row["provider_slug"]: row for row in data["providers.csv"]}
    sources = unique_values(data["source_registry.csv"], "source_slug", "source_registry.csv")
    source_rows = {row["source_slug"]: row for row in data["source_registry.csv"]}
    iso2_seen = set()
    iso3_seen = set()
    unique_values(data["plan_observations.csv"], "observation_id", "plan_observations.csv")
    unique_values(data["page_topics.csv"], "slug", "page_topics.csv")

    for filename, key in (("destinations.csv", "slug"), ("providers.csv", "provider_slug")):
        for n, row in enumerate(data[filename], 2):
            if not SLUG_RE.fullmatch(row[key]):
                fail(f"Invalid slug in {filename}, row {n}: {row[key]!r}")
            if row["evidence_status"] not in EVIDENCE:
                fail(f"Invalid evidence_status in {filename}, row {n}")
            check_date(row["source_checked_date"], "source_checked_date", n)
            if row["source_slug"] and row["source_slug"] not in sources:
                fail(f"Unknown source_slug in {filename}, row {n}")
            if filename == "destinations.csv":
                primary_source = row["source_slug"]
                if not primary_source:
                    fail(f"Missing primary source in destinations.csv, row {n}")
                primary_record = source_rows[primary_source]
                if primary_record["source_type"] != "official_country_metadata_api":
                    fail(f"Invalid primary source type in destinations.csv, row {n}: {primary_record['source_type']!r}")
                if primary_record["verification_status"] != "verified":
                    fail(f"Unverified primary source registry entry in destinations.csv, row {n}")
                iso2 = row["iso2"]
                iso3 = row["iso3"]
                if not ISO2_RE.fullmatch(iso2):
                    fail(f"Invalid ISO2 code in destinations.csv, row {n}: {iso2!r}")
                if not ISO3_RE.fullmatch(iso3):
                    fail(f"Invalid ISO3 code in destinations.csv, row {n}: {iso3!r}")
                if iso2 in iso2_seen:
                    fail(f"Duplicate ISO2 code in destinations.csv: {iso2}")
                if iso3 in iso3_seen:
                    fail(f"Duplicate ISO3 code in destinations.csv: {iso3}")
                iso2_seen.add(iso2)
                iso3_seen.add(iso3)
                if not row["income_level"].strip() or not row["lending_type"].strip():
                    fail(f"Missing World Bank classification in destinations.csv, row {n}")
                longitude = row["capital_longitude"].strip()
                latitude = row["capital_latitude"].strip()
                if bool(longitude) != bool(latitude):
                    fail(f"Incomplete capital coordinates in destinations.csv, row {n}")
                if longitude and latitude:
                    try:
                        lon, lat = Decimal(longitude), Decimal(latitude)
                    except InvalidOperation:
                        fail(f"Invalid capital coordinates in destinations.csv, row {n}")
                    if not lon.is_finite() or not lat.is_finite() or not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                        fail(f"Out-of-range capital coordinates in destinations.csv, row {n}")

                currency = row["currency_code"]
                currency_source = row["currency_source_slug"]
                if currency and not CURRENCY_RE.fullmatch(currency):
                    fail(f"Invalid currency code in destinations.csv, row {n}: {currency!r}")
                if bool(currency) != bool(currency_source):
                    fail(f"Currency code/source mismatch in destinations.csv, row {n}")
                if currency_source:
                    if currency_source not in sources:
                        fail(f"Unknown currency_source_slug in destinations.csv, row {n}")
                    currency_record = source_rows[currency_source]
                    expected_type = "official_cldr_territory_currency_registry"
                    actual_type = currency_record["source_type"]
                    if actual_type != expected_type:
                        fail(f"Invalid currency source type in destinations.csv, row {n}: {actual_type!r}")
                    if currency_record["verification_status"] != "verified":
                        fail(f"Unverified currency source registry entry in destinations.csv, row {n}")
            if filename == "providers.csv":
                check_url(row["official_url"], "official_url", n, required=True)
                check_url(row["support_url"], "support_url", n)

    for n, row in enumerate(data["source_registry.csv"], 2):
        if row["verification_status"] not in SOURCE_STATUS:
            fail(f"Invalid verification_status in source_registry.csv, row {n}")
        if row["access_status"] not in ACCESS_STATUS:
            fail(f"Invalid access_status in source_registry.csv, row {n}")
        check_url(row["source_url"], "source_url", n, required=True)
        check_date(row["last_checked_date"], "last_checked_date", n)
        check_date(row["access_checked_date"], "access_checked_date", n)

    for n, row in enumerate(data["plan_observations.csv"], 2):
        if row["provider_slug"] not in providers:
            fail(f"Unknown provider_slug in plan_observations.csv, row {n}")
        if row["destination_slug"] not in destinations:
            fail(f"Unknown destination_slug in plan_observations.csv, row {n}")
        if row["evidence_status"] not in EVIDENCE:
            fail(f"Invalid evidence_status in plan_observations.csv, row {n}")
        source_slug = row["source_slug"].strip()
        if not source_slug or source_slug not in sources:
            fail(f"Missing or unknown source_slug in plan_observations.csv, row {n}")
        source_record = source_rows[source_slug]
        if source_record["source_type"] != "provider_plan_product_page":
            fail(f"Invalid plan source type in plan_observations.csv, row {n}")
        provider_name = provider_rows[row["provider_slug"]]["provider_name"].strip()
        if source_record["organization"].strip().casefold() != provider_name.casefold():
            fail(f"Plan source organization does not match provider in row {n}")
        check_url(row["source_url"], "source_url", n, required=True)
        if row["source_url"].strip() != source_record["source_url"].strip():
            fail(f"Plan source_url does not match registered source in row {n}")
        if row["evidence_status"] == "verified" and source_record["verification_status"] != "verified":
            fail(f"Verified plan observation uses an unverified source in row {n}")
        check_number(row["data_gb"], "data_gb", n, Decimal("0"), required=True)
        check_number(row["validity_days"], "validity_days", n, Decimal("1"), required=True)
        check_number(row["price_amount"], "price_amount", n, Decimal("0"), required=True)
        check_date(row["observed_date"], "observed_date", n)

    topic_slugs = {row["slug"] for row in data["page_topics.csv"]}
    for n, row in enumerate(data["page_topics.csv"], 2):
        if not SLUG_RE.fullmatch(row["slug"]):
            fail(f"Invalid topic slug, row {n}")
        if row["destination_slug"] and row["destination_slug"] not in destinations:
            fail(f"Unknown destination_slug in page_topics.csv, row {n}")
        if row["provider_slug"] and row["provider_slug"] not in providers:
            fail(f"Unknown provider_slug in page_topics.csv, row {n}")
        related = [x.strip() for x in row["related_slugs"].split(";") if x.strip()]
        unknown = set(related) - topic_slugs
        if unknown:
            fail(f"Unknown related topic slugs in row {n}: {sorted(unknown)}")
        if not row["evidence_requirements"].strip():
            fail(f"Missing evidence_requirements in page_topics.csv, row {n}")

    print("CSV_EVIDENCE_VALIDATION_OK")
    for name, rows in data.items():
        print(f"{name}: {len(rows)} rows")
    return data


if __name__ == "__main__":
    validate_all()
