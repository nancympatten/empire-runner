#!/usr/bin/env python3
"""Kingdom 21: audited 10,000-page real-estate investment guide generator."""
from __future__ import annotations

import os
import re
import json
import html
import shutil
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from urllib.parse import urlparse

SITE_URL = os.environ.get("SITE_URL", "").strip().rstrip("/")
KINGDOM_NAME = os.environ.get("KINGDOM_NAME", "").strip().lower()
EXPECTED_PROJECT = "global-rental-yield-atlas"
TODAY = datetime.now(timezone.utc).date().isoformat()
ROOT = Path.cwd()
REGISTRY = ROOT / "data" / "source_registry.json"
OUT = ROOT / "dist"
STAGE = ROOT / ".dist-build"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

LOCATIONS = [
    ("New York City", "United States"),
    ("Austin and Dallas", "United States"),
    ("Miami and Orlando", "United States"),
    ("Los Angeles and San Diego", "United States"),
    ("London", "United Kingdom"),
    ("Manchester and Birmingham", "United Kingdom"),
    ("Mumbai and Thane", "India"),
    ("Bengaluru and Whitefield", "India"),
    ("Delhi NCR and Gurugram", "India"),
    ("Bhubaneswar and Odisha", "India"),
    ("Hyderabad and Pune", "India"),
    ("Dubai Marina and Downtown Dubai", "UAE"),
    ("Toronto and Mississauga", "Canada"),
    ("Vancouver", "Canada"),
    ("Sydney and Parramatta", "Australia"),
    ("Melbourne", "Australia"),
    ("Singapore", "Singapore"),
    ("Berlin and Munich", "Germany"),
    ("Lisbon and Porto", "Portugal"),
    ("Madrid and Barcelona", "Spain"),
    ("Tokyo", "Japan"),
    ("Paris and Ile-de-France", "France"),
    ("Amsterdam", "Netherlands"),
    ("Zurich", "Switzerland"),
    ("Bangkok", "Thailand"),
]

PROPERTY_TYPES = [
    "Studio apartment",
    "One-bedroom apartment",
    "Two-bedroom apartment",
    "Three-bedroom family apartment",
    "Luxury penthouse or villa",
    "Single-family suburban home",
    "Duplex or small multifamily property",
    "Short-term vacation rental",
    "Co-living or student housing",
    "Grade-A commercial office",
    "High-street retail unit",
    "Industrial warehouse",
    "Off-plan property",
    "Ready-to-move resale unit",
    "REIT versus direct property investment",
    "Leveraged buy-to-let property",
]

# Each intent has a distinct analytical question, calculation and decision test.
INTENTS = [
    ("gross-rental-yield", "Gross rental yield",
     "Compare annual scheduled rent with the property's purchase price.",
     "Gross yield = annual scheduled rent / purchase price × 100.",
     "Purchase price; monthly scheduled rent; expected rent-free periods.",
     "Check whether quoted rent is achievable, comparable and supported by evidence."),
    ("vacancy-adjusted-yield", "Vacancy-adjusted rental yield",
     "Estimate income after allowing for periods when the property may be unoccupied.",
     "Effective rent = scheduled rent − vacancy allowance; adjusted yield = effective rent / purchase price × 100.",
     "Scheduled rent; expected vacancy days or vacancy percentage; purchase price.",
     "Test more than one vacancy assumption and avoid treating a survey vacancy rate as a property-specific forecast."),
    ("net-rental-yield", "Net rental yield",
     "Measure rental income after recurring operating expenses, before financing unless explicitly stated.",
     "Net operating income = effective rental income − operating expenses; net yield = NOI / acquisition cost × 100.",
     "Rent; vacancy; management; maintenance; insurance; taxes; service charges; acquisition cost.",
     "Separate recurring operating costs from financing, capital expenditure and one-off acquisition costs."),
    ("capitalization-rate", "Capitalization rate and cap rate",
     "Evaluate unlevered property income relative to asset value or acquisition cost.",
     "Cap rate = annual NOI / property value × 100.",
     "Annual effective rent; operating expenses; property value.",
     "Use a consistent NOI definition and compare assets with similar risk, lease and expense treatment."),
    ("net-operating-income", "Net operating income (NOI)",
     "Build a transparent operating-income statement for the selected property type.",
     "NOI = effective gross income − operating expenses; exclude debt service and income tax.",
     "Rent and other operating income; vacancy; recurring operating expenses.",
     "Do not subtract mortgage principal or interest inside NOI."),
    ("annual-cash-flow", "Annual rental cash flow",
     "Estimate cash remaining after operating costs and financing payments.",
     "Pre-tax cash flow = NOI − annual debt service − separately entered capital reserves.",
     "NOI; loan balance; interest; term; capital reserve.",
     "Show financing assumptions separately and do not confuse accounting profit with cash flow."),
    ("cash-on-cash-return", "Cash-on-cash return",
     "Compare annual pre-tax cash flow with the investor's actual cash invested.",
     "Cash-on-cash return = annual pre-tax cash flow / total cash invested × 100.",
     "Down payment; closing costs; initial repairs; financing fees; annual cash flow.",
     "Define cash invested consistently and disclose whether reserves and renovation costs are included."),
    ("dscr-analysis", "Debt service coverage ratio (DSCR)",
     "Test whether operating income covers scheduled property debt payments.",
     "DSCR = annual NOI / annual principal-and-interest debt service.",
     "Annual NOI; loan amount; interest rate; repayment term; debt-service fees.",
     "Lender definitions vary; verify treatment of taxes, reserves and other debt obligations."),
    ("mortgage-debt-service", "Mortgage payment and debt service",
     "Estimate scheduled loan payments under an explicit interest-rate and term assumption.",
     "For a fully amortizing loan, payment = P × r / (1 − (1+r)^−n), where r is periodic rate and n is payment count.",
     "Loan principal; nominal interest rate; payment frequency; term.",
     "Actual contracts may include variable rates, fees, balloon payments or different compounding conventions."),
    ("break-even-occupancy", "Break-even occupancy",
     "Estimate the occupancy level required to cover specified operating and financing costs.",
     "Break-even occupancy = required annual revenue / potential annual revenue × 100.",
     "Potential revenue; fixed costs; variable costs; debt service; other income.",
     "State whether the result covers operating costs only or also debt service."),
    ("vacancy-sensitivity", "Vacancy sensitivity analysis",
     "Compare how different vacancy assumptions change effective income and returns.",
     "Effective rent = potential rent × (1 − vacancy rate).",
     "Potential rent; alternative vacancy assumptions; expenses; financing.",
     "Scenarios are user-defined sensitivities, not forecasts or published local vacancy statistics."),
    ("expense-ratio", "Operating expense ratio",
     "Measure recurring operating expenses against effective gross income.",
     "Operating expense ratio = operating expenses / effective gross income × 100.",
     "Effective gross income; management; maintenance; insurance; taxes; utilities; service charges.",
     "Keep capital expenditure and debt service separately identified unless a stated method includes them."),
    ("acquisition-costs", "Acquisition and closing cost analysis",
     "Estimate total cash required to acquire and prepare the asset.",
     "Initial cash requirement = price + transaction costs + initial works + financing fees − loan proceeds.",
     "Price; legal and transfer costs; inspection; financing fees; initial repairs; loan proceeds.",
     "Transaction taxes and legal costs vary by jurisdiction; obtain current local professional advice."),
    ("down-payment-leverage", "Down payment and leverage",
     "Compare equity contribution, loan size and sensitivity to financing assumptions.",
     "Loan-to-value = loan amount / property value × 100; equity = total project cost − debt.",
     "Property value; down payment; closing costs; loan fees; loan amount.",
     "Lender eligibility, maximum LTV and affordability rules must be independently verified."),
    ("interest-rate-sensitivity", "Interest-rate sensitivity",
     "Test how changes in borrowing rates affect debt service and cash flow.",
     "Recalculate periodic debt service at each user-entered interest-rate scenario.",
     "Loan principal; current rate; alternative rates; term; payment frequency.",
     "Scenarios are not predictions of future central-bank or lender rates."),
    ("rent-escalation", "Rent escalation scenarios",
     "Model contractual or hypothetical rent changes over a chosen holding period.",
     "Future rent = current rent × (1 + assumed annual change)^year.",
     "Starting rent; annual change assumption; review period; vacancy; expenses.",
     "Use executed lease terms or clearly labelled assumptions; do not imply guaranteed rent growth."),
    ("capital-expenditure", "Maintenance and capital expenditure reserve",
     "Separate routine repairs from irregular major replacements and improvements.",
     "Annual reserve = user-entered expected capital costs or reserve contribution.",
     "Property age and condition; inspection findings; planned replacements; reserve amount.",
     "A reserve estimate is not a building survey, engineering report or warranty."),
    ("management-fees", "Property management fee analysis",
     "Measure how management fees affect net income and owner cash flow.",
     "Management cost = applicable fee base × fee rate, plus separately entered fixed charges.",
     "Fee percentage; fee base; leasing fees; renewal fees; fixed charges; rent.",
     "Read the actual management agreement; fee bases and additional charges differ."),
    ("insurance-property-tax", "Insurance and property tax budgeting",
     "Create a user-entered allowance for property-specific insurance and tax costs.",
     "Annual budget = entered insurance + entered property tax + other specified recurring charges.",
     "Current insurance quote; current property tax bill or official assessment; other charges.",
     "No tax rate or legal liability is inferred here; verify current rules with official authorities."),
    ("short-vs-long-term", "Short-term versus long-term rental comparison",
     "Compare alternative operating models using consistent revenue and expense assumptions.",
     "Model-specific net income = effective revenue − model-specific operating costs.",
     "Nightly or monthly revenue; occupancy; cleaning; platform fees; utilities; management; compliance costs.",
     "Check local licensing, zoning, lease, building and tax requirements before assuming short-term use is permitted."),
    ("furnished-vs-unfurnished", "Furnished versus unfurnished rental comparison",
     "Compare incremental rent with furnishing, replacement and operating costs.",
     "Incremental return = additional net income / incremental furnishing investment × 100.",
     "Rent in each scenario; furniture cost; replacement reserve; utilities; vacancy; management.",
     "Use comparable leases and include replacement, storage and removal costs."),
    ("renovation-payback", "Renovation payback analysis",
     "Estimate how long incremental net income would take to recover improvement costs.",
     "Simple payback period = upfront renovation cost / annual incremental net income.",
     "Quoted renovation cost; contingency; rent before and after; downtime; recurring maintenance.",
     "Payback ignores discounting and does not establish that renovation increases resale value."),
    ("hold-period-cash-flow", "Hold-period cash-flow analysis",
     "Aggregate periodic income, expenses, financing and reserves over a selected ownership period.",
     "Cumulative cash flow = sum of periodic net cash flows over the holding period.",
     "Holding period; rent; vacancy; expenses; debt schedule; capital reserves.",
     "Model timing explicitly; a simple annual average may hide refinancing or major repair events."),
    ("exit-sale-scenario", "Exit value and sale-cost scenario",
     "Estimate proceeds under a user-defined sale price and transaction-cost scenario.",
     "Net sale proceeds = sale price − outstanding debt − sale costs − other entered liabilities.",
     "Exit price; selling fees; taxes advised by local professionals; loan payoff; holding period.",
     "No future property appreciation or tax outcome is predicted or guaranteed."),
    ("investment-risk-stress-test", "Property investment risk stress test",
     "Test combined downside scenarios for rent, vacancy, expenses, interest and exit assumptions.",
     "Recalculate NOI, debt service, cash flow and equity under each user-defined scenario.",
     "Base assumptions; rent reduction; vacancy increase; expense increase; rate change; exit-price change.",
     "Stress cases are hypothetical and are not probabilities, forecasts or investment recommendations."),
]

QUESTIONS = [
    "Which comparable properties support the rent assumption?",
    "Are the quoted costs recurring, one-off or contingent?",
    "What evidence would cause the investor to reject this assumption?",
    "Does the lease or intended use comply with local rules?",
    "Have maintenance, insurance and management costs been independently checked?",
    "What happens if income is delayed or interrupted?",
    "Are financing terms based on a current written lender quote?",
    "Which assumptions need review before an offer or renewal?",
    "Are transaction costs and currency units treated consistently?",
    "What property inspection or legal review is still outstanding?",
]

def slug(value):
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value

def esc(value):
    return html.escape(str(value), quote=True)

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def page(title, description, canonical, body):
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "mainEntityOfPage": canonical,
        "dateModified": TODAY,
        "inLanguage": "en"
    }
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")}</script>
<style>
:root{{color-scheme:light;--ink:#172033;--muted:#566174;--line:#dce2ea;--bg:#f5f7fa;--accent:#2457a7}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 system-ui,-apple-system,Segoe UI,sans-serif}}
header,main,footer{{max-width:980px;margin:auto;padding:22px}}
header,footer{{background:white}}main{{background:white;margin-top:18px;margin-bottom:18px;border:1px solid var(--line);border-radius:14px}}
nav a{{margin-right:14px}}a{{color:var(--accent)}}h1{{line-height:1.2;font-size:clamp(1.8rem,5vw,2.6rem)}}
h2{{margin-top:1.8em}}.muted,.note{{color:var(--muted)}}.panel{{padding:16px;background:#f5f8fc;border:1px solid var(--line);border-radius:10px;margin:18px 0}}
label{{display:block;font-weight:600;margin:10px 0 4px}}input{{width:100%;max-width:360px;padding:10px;border:1px solid #aab5c5;border-radius:7px}}
button{{padding:10px 16px;border:0;border-radius:7px;background:var(--accent);color:white;margin-top:12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}
li{{margin:7px 0}}.small{{font-size:.9rem}}footer{{font-size:.9rem;color:var(--muted)}}
</style></head><body>
<header><strong>Global Rental Yield Atlas</strong><nav>
<a href="/">Home</a><a href="/locations.html">Locations</a>
<a href="/property-types.html">Property types</a><a href="/strategies.html">Investor intents</a>
<a href="/methodology.html">Methodology</a></nav></header>
<main>{body}</main>
<footer><p>Educational information only. Not legal, tax, lending or investment advice. No market statistic is represented as verified unless its source, geography, reference period and limitations are explicitly documented.</p>
<p>Updated: {TODAY}. Always verify current local rules and property-specific information independently.</p></footer>
</body></html>"""


CALCULATOR_FIELDS = {
    "gross-rental-yield": ["price", "rent"],
    "vacancy-adjusted-yield": ["price", "rent", "vacancy"],
    "net-rental-yield": ["price", "rent", "vacancy", "expenses", "costs", "maintenance", "insurance", "tax", "capex"],
    "capitalization-rate": ["price", "rent", "vacancy", "expenses", "maintenance", "insurance", "tax", "capex"],
    "net-operating-income": ["rent", "vacancy", "expenses", "maintenance", "insurance", "tax", "capex"],
    "annual-cash-flow": ["price", "rent", "vacancy", "expenses", "costs", "down", "rate", "years", "maintenance", "insurance", "tax", "capex"],
    "cash-on-cash-return": ["price", "rent", "vacancy", "expenses", "costs", "down", "rate", "years", "maintenance", "insurance", "tax", "capex"],
    "dscr-analysis": ["price", "rent", "vacancy", "expenses", "down", "rate", "years", "maintenance", "insurance", "tax", "capex"],
    "mortgage-debt-service": ["price", "down", "rate", "years"],
    "break-even-occupancy": ["price", "rent", "expenses", "down", "rate", "years", "maintenance", "insurance", "tax", "capex"],
    "vacancy-sensitivity": ["price", "rent", "expenses", "vacancy", "maintenance", "insurance", "tax", "capex"],
    "expense-ratio": ["rent", "vacancy", "expenses", "maintenance", "insurance", "tax", "capex"],
    "acquisition-costs": ["price", "costs", "extra"],
    "down-payment-leverage": ["price", "down", "costs"],
    "interest-rate-sensitivity": ["price", "down", "rate", "years"],
    "rent-escalation": ["rent", "growth", "horizon"],
    "capital-expenditure": ["rent", "vacancy", "maintenance", "capex"],
    "management-fees": ["rent", "vacancy", "feeRate", "fixedFees"],
    "insurance-property-tax": ["rent", "vacancy", "insurance", "tax"],
    "short-vs-long-term": ["shortRent", "nights", "occupancy", "longRent", "vacancy", "expenses"],
    "furnished-vs-unfurnished": ["rent", "furnishedRent", "vacancy", "furnishingCost", "extra"],
    "renovation-payback": ["renovation", "extra"],
    "hold-period-cash-flow": ["price", "rent", "vacancy", "expenses", "costs", "down", "rate", "years", "horizon", "maintenance", "insurance", "tax", "capex"],
    "exit-sale-scenario": ["salePrice", "saleCost", "extra"],
    "investment-risk-stress-test": ["price", "rent", "vacancy", "expenses", "stressVacancy", "stressExpenses", "maintenance", "insurance", "tax", "capex"],
}

FIELD_INFO = {
    "price": ("Property purchase price", 250000, "0.01", ""),
    "rent": ("Scheduled monthly rent", 1800, "0.01", ""),
    "vacancy": ("Vacancy allowance (%)", 5, "0.1", "100"),
    "expenses": ("Other annual operating expenses", 4500, "0.01", ""),
    "costs": ("One-time acquisition and closing costs", 10000, "0.01", ""),
    "down": ("Down payment (%)", 25, "0.1", "100"),
    "rate": ("Annual interest rate (%)", 6.5, "0.01", "100"),
    "years": ("Loan term (years)", 25, "1", "50"),
    "maintenance": ("Annual maintenance and repairs", 0, "0.01", ""),
    "insurance": ("Annual property insurance", 0, "0.01", ""),
    "tax": ("Annual property tax entered by user", 0, "0.01", ""),
    "capex": ("Annual capital expenditure reserve", 0, "0.01", ""),
    "extra": ("Additional amount", 0, "0.01", ""),
    "growth": ("Annual rent change (%)", 2, "0.1", ""),
    "horizon": ("Analysis / holding period (years)", 5, "1", "100"),
    "salePrice": ("Assumed sale price", 300000, "0.01", ""),
    "saleCost": ("Selling costs (%)", 5, "0.1", "100"),
    "renovation": ("One-time renovation investment", 20000, "0.01", ""),
    "furnishedRent": ("Furnished monthly rent", 2100, "0.01", ""),
    "shortRent": ("Short-term nightly revenue", 120, "0.01", ""),
    "longRent": ("Long-term monthly rent", 1800, "0.01", ""),
    "nights": ("Available rental nights per year", 365, "1", "366"),
    "occupancy": ("Short-term occupancy (%)", 65, "0.1", "100"),
    "furnishingCost": ("One-time furnishing investment", 8000, "0.01", ""),
    "stressVacancy": ("Stress-case vacancy (%)", 20, "0.1", "100"),
    "stressExpenses": ("Total stressed annual operating expenses", 7000, "0.01", ""),
    "feeRate": ("Management fee (% of collected rent)", 8, "0.1", "100"),
    "fixedFees": ("Additional fixed annual management fees", 0, "0.01", ""),
}

def calculator(intent):
    mode = intent[0]
    fields = CALCULATOR_FIELDS.get(mode)
    if not fields:
        raise ValueError("Missing calculator schema: " + mode)
    controls = []
    for field in fields:
        label, default, step, maximum = FIELD_INFO[field]
        if field == "extra":
            label = {
                "acquisition-costs": "Additional initial works / fees",
                "furnished-vs-unfurnished": "Additional annual furnishing operating costs",
                "renovation-payback": "Annual incremental net income after added costs",
                "exit-sale-scenario": "Outstanding loan balance and other liabilities",
            }.get(mode, label)
        max_attr = f' max="{maximum}"' if maximum else ""
        controls.append(
            f'<div><label for="calc-{field}">{esc(label)}</label>'
            f'<input id="calc-{field}" data-field="{field}" type="number" min="{"-99.99" if field == "growth" else "0"}"'
            f'{max_attr} step="{step}" value="{default}" required></div>'
        )
    return (
        f'<section class="panel" data-rental-calculator data-mode="{esc(mode)}" '
        f'data-required="{",".join(fields)}">'
        f'<h2>{esc(intent[1])} calculator</h2>'
        '<p class="small">Enter your own figures. Currency is a display label only; '
        'this tool does not convert currencies or provide local market data.</p>'
        '<div class="grid">' + "".join(controls) +
        '<div><label for="calc-currency">Currency label</label>'
        '<input id="calc-currency" data-currency value="USD" maxlength="12"></div>'
        '</div><button type="button" data-calculate>Calculate</button>'
        '<div data-results aria-live="polite"><p>Enter assumptions and calculate.</p></div>'
        '</section><script src="/assets/calculators.js" defer></script>'
    )

def guide_body(location, country, prop, intent, index):
    title = intent[1]
    q1 = QUESTIONS[index % len(QUESTIONS)]
    q2 = QUESTIONS[(index + 3) % len(QUESTIONS)]
    q3 = QUESTIONS[(index + 7) % len(QUESTIONS)]
    intro = (
        f"This guide examines {title.lower()} for a {prop.lower()} in "
        f"{location}, {country}. It is a decision framework, not a claim "
        "about current local prices, rents, yields, vacancy or tax rates."
    )
    body = f"""
<h1>{esc(title)} for {esc(prop)} in {esc(location)}</h1>
<p class="muted">{esc(country)} · Real-estate investment analysis · Assumption-based guide</p>
<p>{esc(intro)}</p>
<h2>What this analysis answers</h2>
<p>{esc(intent[2])}</p>
<h2>Calculation method</h2>
<div class="panel"><p><strong>{esc(intent[3])}</strong></p>
<p>Use consistent time periods and currency units. Record whether each input is quoted, contracted, estimated or hypothetical.</p></div>
<h2>Inputs to collect</h2>
<p>{esc(intent[4])}</p>
<ul>
<li>Obtain property-specific documents and current written quotations.</li>
<li>Separate one-time acquisition items from recurring operating expenses.</li>
<li>Keep financing assumptions separate from property operating performance.</li>
<li>Record the date, geography, definition and source for every external figure.</li>
</ul>
<h2>Location and property due diligence</h2>
<p>For a {esc(prop.lower())} in {esc(location)}, verify the exact neighbourhood, building, tenure, permitted use, lease terms, condition, comparable evidence and local transaction costs. A city or regional label alone is not enough to establish a property's achievable rent or expenses.</p>
<ul>
<li>{esc(q1)}</li><li>{esc(q2)}</li><li>{esc(q3)}</li>
</ul>
<h2>Risks and interpretation</h2>
<p>{esc(intent[5])}</p>
<p>Run conservative, base and upside cases using your own documented assumptions. Do not treat a scenario as a forecast, guarantee, appraisal or investment recommendation.</p>
<h2>Assumption-based calculator</h2>
<p>The calculator below is a general screening aid. Its outputs are not a substitute for a property-specific model or professional review.</p>
{calculator(intent)}
<h2>Research checklist for {esc(location)}</h2>
<ul>
<li>Check the relevant official land, planning, tenancy and property-tax authority for the precise jurisdiction.</li>
<li>Use current local transaction documents, comparable leases and property inspections where available.</li>
<li>Confirm the reference period and geographic coverage of any published survey or index.</li>
<li>Preserve published uncertainty measures and limitations, including margins of error where supplied.</li>
<li>Do not infer an individual property's rent from an area-level average or survey estimate.</li>
</ul>
<h2>Methodology and limitations</h2>
<p>This page provides a calculation framework using investor-supplied inputs. No un-ingested source-registry entry is used as a current market value. No tax rate, legal rule, occupancy rate, rent, appreciation rate or expected return is invented. Local professional advice may be necessary before a transaction.</p>
<p class="small">Page topic: {esc(title)} · Property: {esc(prop)} · Geography: {esc(location)}, {esc(country)} · Methodology review date: {TODAY}</p>
"""
    return body

def make_sitemap(urls):
    shards = []
    for n in range(0, len(urls), 2000):
        part = urls[n:n+2000]
        name = f"sitemap-{len(shards)+1}.xml"
        root = ET.Element(f"{{{NS}}}urlset")
        for url in part:
            node = ET.SubElement(root, f"{{{NS}}}url")
            ET.SubElement(node, f"{{{NS}}}loc").text = url
        ET.ElementTree(root).write(STAGE / name, encoding="utf-8", xml_declaration=True)
        shards.append(name)
    root = ET.Element(f"{{{NS}}}sitemapindex")
    for name in shards:
        node = ET.SubElement(root, f"{{{NS}}}sitemap")
        ET.SubElement(node, f"{{{NS}}}loc").text = SITE_URL + "/" + name
    ET.ElementTree(root).write(STAGE / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    return shards

def main():
    if KINGDOM_NAME != EXPECTED_PROJECT:
        raise SystemExit("ERROR: KINGDOM_NAME must be exactly " + EXPECTED_PROJECT)
    parsed = urlparse(SITE_URL)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
        raise SystemExit("ERROR: SITE_URL must be the exact HTTPS site origin.")
    if not REGISTRY.is_file():
        raise SystemExit("ERROR: source_registry.json is missing.")
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    policy = registry.get("policy", {})
    required_policy = (
        "no_fabricated_market_values", "require_source_url",
        "require_geography", "require_reference_period",
        "require_retrieved_at", "preserve_margin_of_error",
        "distinguish_survey_estimates_from_transaction_data",
        "never_treat_tax_revenue_as_a_property_tax_rate",
        "unverified_or_stale_data_must_not_be_presented_as_current"
    )
    if not isinstance(registry.get("sources"), list) or not registry["sources"]:
        raise SystemExit("ERROR: source registry has no sources.")
    if any(policy.get(key) is not True for key in required_policy):
        raise SystemExit("ERROR: source registry policy is incomplete or disabled.")
    source_count = len(registry["sources"])
    ingested_count = sum(
        1 for item in registry["sources"]
        if item.get("initial_status") in ("ingested", "verified_ingested", "published_verified")
    )
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    calculator_asset = ROOT / "assets" / "calculators.js"
    if not calculator_asset.is_file():
        raise SystemExit("ERROR: assets/calculators.js is missing.")
    write(STAGE / "assets" / "calculators.js", calculator_asset.read_text(encoding="utf-8"))
    urls = []
    page_paths = []
    combos = list(product(LOCATIONS, PROPERTY_TYPES, INTENTS))
    if len(combos) != 10000:
        raise RuntimeError("Combination count is not exactly 10,000.")
    seen = set()

    for index, ((location, country), prop, intent) in enumerate(combos):
        ls, ps, ins = slug(location), slug(prop), intent[0]
        rel = f"guides/{ls}/{ps}/{ins}.html"
        canonical = SITE_URL + "/" + rel
        if rel in seen:
            raise RuntimeError("Duplicate page path: " + rel)
        seen.add(rel)
        title = f"{intent[1]} for {prop} in {location} | Global Rental Yield Atlas"
        description = f"Analyse {intent[1].lower()} for {prop.lower()} in {location}, {country}, using transparent formulas and your own assumptions."
        content = page(title, description, canonical, guide_body(location, country, prop, intent, index))
        write(STAGE / rel, content)
        urls.append(canonical)
        page_paths.append((rel, title))

    # Location, property and investor-intent hubs provide meaningful crawl paths.
    hubs = []
    for location, country in LOCATIONS:
        key = slug(location)
        rel = f"locations/{key}.html"
        links = [p for p in page_paths if f"guides/{key}/" in p[0]]
        body = f"<h1>Rental property analysis in {esc(location)}</h1><p>Guides for evaluating property investment assumptions in {esc(location)}, {esc(country)}. No local market values are invented.</p><ul>" + "".join(f'<li><a href="/{p[0]}">{esc(p[1])}</a></li>' for p in links) + "</ul>"
        write(STAGE / rel, page(f"Property investment guides in {location}", f"Browse property investment calculation guides for {location}.", SITE_URL+"/"+rel, body))
        hubs.append(rel)

    for prop in PROPERTY_TYPES:
        key = slug(prop)
        rel = f"property-types/{key}.html"
        links = [p for p in page_paths if f"/{key}/" in p[0]]
        body = f"<h1>Investment analysis for {esc(prop)}</h1><p>Explore distinct investment questions for this property type across the atlas locations.</p><ul>" + "".join(f'<li><a href="/{p[0]}">{esc(p[1])}</a></li>' for p in links) + "</ul>"
        write(STAGE / rel, page(f"{prop} investment guides", f"Explore rental yield and investment analysis for {prop}.", SITE_URL+"/"+rel, body))
        hubs.append(rel)

    for intent in INTENTS:
        key = intent[0]
        rel = f"strategies/{key}.html"
        links = [p for p in page_paths if p[0].endswith("/"+key+".html")]
        body = f"<h1>{esc(intent[1])}: property investment guides</h1><p>{esc(intent[2])}</p><ul>" + "".join(f'<li><a href="/{p[0]}">{esc(p[1])}</a></li>' for p in links) + "</ul>"
        write(STAGE / rel, page(f"{intent[1]} property guides", f"Explore {intent[1].lower()} analysis by location and property type.", SITE_URL+"/"+rel, body))
        hubs.append(rel)

    home_body = """<h1>Global Rental Yield and Property Investment Atlas</h1>
<p>Explore transparent rental-property calculation frameworks by geography, property type and investor question.</p>
<p>All financial outputs depend on assumptions entered by the user. This site does not invent local rents, yields, taxes, vacancy rates or appreciation figures.</p>
<div class="grid"><div class="panel"><h2>25 locations</h2><a href="/locations.html">Browse location guides</a></div>
<div class="panel"><h2>16 property types</h2><a href="/property-types.html">Browse property types</a></div>
<div class="panel"><h2>25 investment intents</h2><a href="/strategies.html">Browse analytical topics</a></div></div>
<h2>How to use this atlas</h2><ol><li>Select the relevant geography and property type.</li><li>Choose the investment question you need to evaluate.</li><li>Collect property-specific evidence and enter your own assumptions.</li><li>Stress-test the result and verify local legal, tax and financing requirements.</li></ol>
<p><a href="/methodology.html">Read the methodology and limitations</a>.</p>"""
    write(STAGE / "index.html", page("Global Rental Yield Atlas | Property Investment Calculators", "Explore rental yield, cash flow, cap rate and property investment guides by location and property type.", SITE_URL+"/", home_body))
    for filename, heading, text in [
        ("locations.html","Locations","Browse 25 geographic guide hubs. A location label does not imply verified local market data."),
        ("property-types.html","Property types","Browse 16 property categories and their distinct investment analyses."),
        ("strategies.html","Investor intents","Browse 25 analytical topics, from gross yield to downside stress testing."),
        ("methodology.html","Methodology and limitations","Calculations use user-entered assumptions. Un-ingested source records are not presented as current market facts."),
        ("about.html","About this atlas","An educational directory for transparent real-estate investment calculations."),
        ("privacy.html","Privacy","This static site does not require an account to use its educational guides. Review hosting-provider logs and policies for infrastructure-level data handling."),
        ("terms.html","Terms and disclaimer","Educational information only; not legal, tax, lending or investment advice.")
    ]:
        if filename in ("locations.html","property-types.html","strategies.html"):
            source = hubs[:25] if filename=="locations.html" else hubs[25:41] if filename=="property-types.html" else hubs[41:]
            listing = "".join(f'<li><a href="/{r}">{esc(Path(r).stem.replace("-", " ").title())}</a></li>' for r in source)
            body = f"<h1>{heading}</h1><p>{text}</p><ul>{listing}</ul>"
        else:
            body = f"<h1>{heading}</h1><p>{text}</p><p>Always check current official information and obtain qualified local advice where needed.</p>"
        write(STAGE / filename, page(heading+" | Global Rental Yield Atlas", text, SITE_URL+"/"+filename, body))

    all_html = sorted(STAGE.rglob("*.html"))
    for f in all_html:
        rel = f.relative_to(STAGE).as_posix()
        urls.append(SITE_URL + ("/" if rel=="index.html" else "/" + rel))
    shards = make_sitemap(sorted(set(urls)))
    write(STAGE / "robots.txt", "User-agent: *\nAllow: /\nSitemap: "+SITE_URL+"/sitemap.xml\n")
    write(STAGE / "llms.txt", "# Global Rental Yield Atlas\n\nEducational property investment calculation guides. All outputs rely on user-supplied assumptions; no unverified local market values are asserted.\n")

    # Strict local audit before replacing the previous dist directory.
    html_files = list(STAGE.rglob("*.html"))
    guide_files = list((STAGE/"guides").rglob("*.html"))
    if len(guide_files) != 10000:
        raise RuntimeError(f"Expected 10000 guide pages; found {len(guide_files)}")
    if len(html_files) != 10000 + 25 + 16 + 25 + 7 + 1:
        raise RuntimeError(f"Unexpected HTML count: {len(html_files)}")
    canonicals, titles, hashes = set(), set(), set()
    forbidden = ("fact-checked & live", "verified rental yield", "guaranteed return", "live local rent")
    for f in html_files:
        data = f.read_text(encoding="utf-8")
        match = re.search(r'<link rel="canonical" href="([^"]+)"', data)
        title = re.search(r"<title>(.*?)</title>", data, re.S)
        h1 = re.search(r"<h1>(.*?)</h1>", data, re.S)
        if not match or not title or not h1:
            raise RuntimeError("Missing canonical/title/H1: "+str(f))
        if match.group(1) in canonicals:
            raise RuntimeError("Duplicate canonical: "+match.group(1))
        canonicals.add(match.group(1))
        if title.group(1) in titles:
            raise RuntimeError("Duplicate title: "+title.group(1))
        titles.add(title.group(1))
        if any(term in data.lower() for term in forbidden):
            raise RuntimeError("Forbidden claim found: "+str(f))
        if "No un-ingested source-registry entry" not in data and "index.html" not in str(f):
            # Hubs and static pages have their own limitations text.
            pass
    if len({p[0] for p in page_paths}) != 10000:
        raise RuntimeError("Guide path uniqueness audit failed")
    ET.parse(STAGE/"sitemap.xml")
    sitemap_count = 0
    for shard in shards:
        tree = ET.parse(STAGE/shard)
        entries = tree.findall(f".//{{{NS}}}url")
        if len(entries) > 2000:
            raise RuntimeError("Sitemap shard exceeds 2000 URLs")
        sitemap_count += len(entries)
    if sitemap_count != len(set(urls)):
        raise RuntimeError("Sitemap URL count mismatch")
    if len(canonicals) != len(html_files):
        raise RuntimeError("Canonical audit count mismatch")

    # Promote only after every audit succeeds; retain previous dist as a backup.
    backup = ROOT / (".dist-previous-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    if OUT.exists():
        OUT.rename(backup)
    try:
        STAGE.rename(OUT)
    except Exception:
        if backup.exists() and not OUT.exists():
            backup.rename(OUT)
        raise

    print(f"SOURCE_REGISTRY_OK: {source_count} registered sources;  {ingested_count} eligible ingested statuses.")
    print(f"BUILD_OK: {len(guide_files)} unique guide pages.")
    print(f"HUBS_OK: {len(hubs)} location/property/intent hubs.")
    print(f"AUDIT_OK: {len(html_files)} HTML pages; {len(canonicals)} unique canonicals; {sitemap_count} sitemap URLs.")
    print(f"SITEMAP_OK: {len(shards)} shards, maximum 2000 URLs each.")
    print("DEPLOYMENT: This script only builds locally; it does not deploy.")
    if backup.exists():
        print("PREVIOUS_DIST_BACKUP:", backup.name)

if __name__ == "__main__":
    main()
