#!/usr/bin/env python3
"""Kingdom 21: rental-yield atlas static-site generator. Python 3.11 stdlib only."""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SITE_URL = os.environ.get("SITE_URL", "").strip().rstrip("/")
TOPIC = os.environ.get("KINGDOM_TOPIC", "Global rental yield, property tax and cap rate calculator directory").strip()
KINGDOM_NAME = os.environ.get("KINGDOM_NAME", "").strip().lower()
TODAY = datetime.now(timezone.utc).date().isoformat()
YEAR = datetime.now(timezone.utc).year
OUT = Path("dist")

LOCATIONS = [
    "New York City, United States", "Austin and Dallas, United States",
    "Miami and Orlando, United States", "Los Angeles and San Diego, United States",
    "London, United Kingdom", "Manchester and Birmingham, United Kingdom",
    "Mumbai and Thane, India", "Bengaluru and Whitefield, India",
    "Delhi NCR and Gurugram, India", "Bhubaneswar and Odisha, India",
    "Hyderabad and Pune, India", "Dubai Marina and Downtown Dubai, UAE",
    "Toronto and Mississauga, Canada", "Vancouver, Canada",
    "Sydney and Parramatta, Australia", "Melbourne, Australia",
    "Singapore", "Berlin and Munich, Germany", "Lisbon and Porto, Portugal",
    "Madrid and Barcelona, Spain", "Tokyo, Japan", "Paris and Île-de-France, France",
    "Amsterdam, Netherlands", "Zurich, Switzerland", "Bangkok, Thailand",
]
PROPERTY_TYPES = [
    "Studio apartment", "One-bedroom apartment", "Two-bedroom apartment",
    "Three-bedroom family apartment", "Luxury penthouse or villa",
    "Single-family suburban home", "Duplex or small multifamily property",
    "Short-term vacation rental", "Co-living or student housing",
    "Grade-A commercial office", "High-street retail unit",
    "Industrial warehouse", "Off-plan property", "Ready-to-move resale unit",
    "REIT versus direct property investment", "Leveraged buy-to-let property",
]

def slugify(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^\w]+", "-", value, flags=re.UNICODE)
    return re.sub(r"-+", "-", value).strip("-")

def esc(value: str) -> str:
    return html.escape(str(value), quote=True)

def page(title: str, description: str, canonical: str, body: str, schema: dict | None = None) -> str:
    schema_html = ""
    if schema:
        schema_html = '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False).replace("</", "<\\/") + "</script>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}"><meta name="robots" content="index,follow">
<meta name="theme-color" content="#101827">{schema_html}
<style>
:root{{--bg:#f5f7fb;--panel:#fff;--ink:#172033;--muted:#536176;--line:#dce3ed;--accent:#087f69}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 system-ui,-apple-system,Segoe UI,sans-serif}}
header,main,footer{{max-width:1080px;margin:auto;padding:1.2rem}}header{{display:flex;gap:1rem;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line)}}
a{{color:#086b9b}}.brand{{font-weight:800;text-decoration:none;color:var(--ink)}}main{{padding-top:2rem}}
.panel{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:1.2rem;margin:1rem 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem}}
label{{display:block;font-weight:650;margin:.65rem 0 .2rem}}input{{width:100%;padding:.7rem;border:1px solid #aab7c8;border-radius:8px;font:inherit}}
button{{background:var(--accent);color:white;border:0;border-radius:8px;padding:.65rem 1rem;font:inherit;cursor:pointer}}
.metric{{background:#f0f7f5;padding:.8rem;border-radius:9px}}.metric strong{{display:block;font-size:1.35rem;overflow-wrap:anywhere}}
small,.muted{{color:var(--muted)}}ul{{padding-left:1.3rem}}footer{{border-top:1px solid var(--line);font-size:.9rem}}
nav{{display:flex;gap:1rem;flex-wrap:wrap}}.warning{{border-left:4px solid #c28a24;padding:.7rem 1rem;background:#fff8e8}}
@media(max-width:600px){{header{{align-items:flex-start;flex-direction:column}}}}
</style></head><body>
<header><a class="brand" href="/">{esc(SITE_NAME)}</a><nav><a href="/locations.html">Locations</a><a href="/property-types.html">Property types</a><a href="/methodology.html">Methodology</a></nav></header>
<main>{body}</main>
<footer><p>© {YEAR} {esc(SITE_NAME)} · <a href="/about.html">About</a> · <a href="/privacy.html">Privacy</a> · <a href="/terms.html">Terms</a> · <a href="/llms.txt">AI index</a></p>
<p class="muted">Independent educational tools. Not investment, legal, accounting or tax advice.</p></footer>
</body></html>"""

SITE_NAME = " ".join(part.capitalize() for part in (urlparse(SITE_URL).hostname or "rental-yield-atlas").split(".")[0].split("-"))

CALCULATOR = r"""
<section class="panel" id="calculator">
<h2>Rental yield and investment calculator</h2>
<p class="muted">Enter your own figures. Values are calculated in this browser; no market averages or tax rates are assumed.</p>
<div class="grid">
<div><label for="currency">Currency code (display only)</label><input id="currency" value="USD" maxlength="8"></div>
<div><label for="price">Purchase price</label><input id="price" type="number" min="0" step="any" value="250000"></div>
<div><label for="closing">One-time closing costs</label><input id="closing" type="number" min="0" step="any" value="10000"></div>
<div><label for="rent">Monthly rent</label><input id="rent" type="number" min="0" step="any" value="1800"></div>
<div><label for="vacancy">Vacancy allowance (%)</label><input id="vacancy" type="number" min="0" max="100" step="any" value="5"></div>
<div><label for="expenses">Monthly operating expenses (excluding debt)</label><input id="expenses" type="number" min="0" step="any" value="350"></div>
<div><label for="down">Down payment (%)</label><input id="down" type="number" min="0" max="100" step="any" value="25"></div>
<div><label for="rate">Annual mortgage interest rate (%)</label><input id="rate" type="number" min="0" max="100" step="any" value="6.5"></div>
<div><label for="term">Mortgage term (years)</label><input id="term" type="number" min="1" max="50" step="1" value="25"></div>
</div>
<p><button type="button" id="calculate">Calculate returns</button></p>
<div class="grid" aria-live="polite">
<div class="metric"><small>Gross rental yield</small><strong id="gross">—</strong></div>
<div class="metric"><small>Net operating income (NOI)</small><strong id="noi">—</strong></div>
<div class="metric"><small>Cap rate</small><strong id="cap">—</strong></div>
<div class="metric"><small>Annual debt service</small><strong id="debt">—</strong></div>
<div class="metric"><small>Annual cash flow after debt</small><strong id="cashflow">—</strong></div>
<div class="metric"><small>Cash-on-cash return</small><strong id="coc">—</strong></div>
<div class="metric"><small>Debt service coverage (DSCR)</small><strong id="dscr">—</strong></div>
<div class="metric"><small>Net yield on total acquisition cost</small><strong id="netyield">—</strong></div>
</div>
<p class="muted" id="calc-note">Calculations use the inputs above. Results are estimates before income tax and extraordinary capital expenses.</p>
</section>
<script>
(() => {
 const ids=['currency','price','closing','rent','vacancy','expenses','down','rate','term'];
 const el=id=>document.getElementById(id);
 const n=id=>{const v=Number(el(id).value);return Number.isFinite(v)?v:NaN};
 const pct=v=>Number.isFinite(v)?(v*100).toFixed(2)+'%':'Not available';
 const money=v=>Number.isFinite(v)?el('currency').value.trim().toUpperCase()+' '+v.toLocaleString(undefined,{maximumFractionDigits:2}):'Not available';
 function calc(){
  const price=n('price'),closing=n('closing'),rent=n('rent'),vac=n('vacancy')/100,exp=n('expenses'),
        down=n('down')/100,rate=n('rate')/100,years=n('term');
  const vals=[price,closing,rent,vac,exp,down,rate,years];
  if(vals.some(v=>!Number.isFinite(v)||v<0)||price<=0||vac>1||down>1||rate>1||years<1||years>50){
   el('calc-note').textContent='Please enter valid non-negative values. Vacancy and down payment must be 0–100%; interest rate must be 0–100%; term 1–50 years.';return;
  }
  const grossRent=rent*12, effective=grossRent*(1-vac), operating=exp*12, noi=effective-operating;
  const acquisition=price+closing, cap=noi/price, netyield=noi/acquisition;
  const loan=price*(1-down), monthlyRate=rate/12, months=years*12;
  const payment=loan===0?0:(monthlyRate===0?loan/months:loan*monthlyRate/(1-Math.pow(1+monthlyRate,-months)));
  const debt=payment*12, cashflow=noi-debt, invested=price*down+closing;
  const coc=invested>0?cashflow/invested:NaN, dscr=debt>0?noi/debt:NaN;
  el('gross').textContent=pct(grossRent/price);el('noi').textContent=money(noi);
  el('cap').textContent=pct(cap);el('debt').textContent=money(debt);
  el('cashflow').textContent=money(cashflow);el('coc').textContent=pct(coc);
  el('dscr').textContent=Number.isFinite(dscr)?dscr.toFixed(2)+'x':'Not available (no debt service)';
  el('netyield').textContent=pct(netyield);
  el('calc-note').textContent='NOI = rent after vacancy allowance minus operating expenses. Cap rate = NOI ÷ purchase price. Cash flow subtracts estimated mortgage payments. Taxes, selling costs, major renovations and currency conversion are excluded.';
 }
 el('calculate').addEventListener('click',calc);
 ids.forEach(id=>el(id).addEventListener('change',calc));
 calc();
})();
</script>
"""

def guide_body(heading: str, kind: str, intro: str, slug: str) -> str:
    schema = None
    return f"""
<p><a href="/">Home</a> / {esc(kind)}</p>
<h1>{esc(heading)}: rental yield and cap rate guide</h1>
<p>{esc(intro)}</p>
<div class="warning"><strong>Data note:</strong> This page does not publish unverified local rent, tax, occupancy or appreciation figures. Add current figures from primary local sources and your own property documents before making a decision.</div>
{CALCULATOR}
<section class="panel"><h2>How to assess this {esc(kind.lower())}</h2>
<ul>
<li>Use comparable achieved rents, not asking rents alone, and record the date and source.</li>
<li>Include recurring owner-paid costs such as maintenance, insurance, management, service charges and property taxes in operating expenses.</li>
<li>Model vacancy and repairs explicitly; do not assume full occupancy.</li>
<li>Check local rental licensing, lease rules, zoning, foreign ownership restrictions and tax treatment with official sources or qualified professionals.</li>
<li>Stress-test lower rent, higher expenses, financing changes and periods without a tenant.</li>
</ul></section>
<section class="panel"><h2>Calculation definitions</h2>
<p><strong>Gross yield</strong> = annual scheduled rent ÷ purchase price.</p>
<p><strong>Net operating income (NOI)</strong> = rent after vacancy allowance − operating expenses, before mortgage payments and income tax.</p>
<p><strong>Capitalization rate</strong> = annual NOI ÷ purchase price.</p>
<p><strong>Cash-on-cash return</strong> = annual cash flow after debt service ÷ cash invested (down payment plus closing costs in this simplified model).</p>
<p><strong>DSCR</strong> = NOI ÷ annual debt service. It is not meaningful when there is no debt service.</p></section>
<p><a href="/methodology.html">Read the complete methodology and limitations</a>.</p>
"""

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def main() -> None:
    parsed = urlparse(SITE_URL)
    if parsed.scheme != "https" or not parsed.hostname or parsed.path not in ("", "/"):
        raise SystemExit("SITE_URL must be an HTTPS origin, for example https://project.pages.dev")
    if KINGDOM_NAME and parsed.hostname != f"{KINGDOM_NAME}.pages.dev":
        raise SystemExit("SITE_URL hostname does not match KINGDOM_NAME")
    if not TOPIC:
        raise SystemExit("KINGDOM_TOPIC is required")

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "guide").mkdir(parents=True)
    urls = []
    guide_count = 0

    intro = ("A practical framework for estimating rental property returns. This directory provides calculation tools and due-diligence checklists, "
             "not live market quotations or jurisdiction-specific tax advice.")
    home_body = f"""
<h1>Global rental yield and property investment calculator atlas</h1>
<p>{esc(intro)}</p>
{CALCULATOR}
<section class="panel"><h2>Explore location guides</h2><ul>{''.join(f'<li><a href="/guide/location-{slugify(x)}.html">{esc(x)}</a></li>' for x in LOCATIONS)}</ul></section>
<section class="panel"><h2>Explore property types</h2><ul>{''.join(f'<li><a href="/guide/property-{slugify(x)}.html">{esc(x)}</a></li>' for x in PROPERTY_TYPES)}</ul></section>
<section class="panel"><h2>Before you invest</h2><p>Verify title, comparable rent, local operating costs, financing terms, permitted use, insurance and tax obligations. Do not compare markets using gross yield alone.</p></section>
"""
    write(OUT / "index.html", page(f"{SITE_NAME} | Rental Yield & Cap Rate Calculator", intro, SITE_URL + "/", home_body))
    urls.append(("/", "Home"))

    for location in LOCATIONS:
        slug = "location-" + slugify(location)
        title = f"Rental property analysis in {location}"
        body = guide_body(title, "Location guide", f"This guide organizes due diligence for evaluating rental property in {location}. It does not assert current local market prices, rental yields or tax rates.", slug)
        canonical = f"{SITE_URL}/guide/{slug}.html"
        schema = {"@context":"https://schema.org","@type":"Article","headline":title,"description":f"Rental yield calculation framework for {location}.","dateModified":TODAY,"mainEntityOfPage":canonical,"author":{"@type":"Organization","name":SITE_NAME}}
        write(OUT / "guide" / f"{slug}.html", page(title + " | " + SITE_NAME, f"Calculate rental yield, NOI and cap rate for properties in {location}.", canonical, body, schema))
        urls.append((f"/guide/{slug}.html", title)); guide_count += 1

    for property_type in PROPERTY_TYPES:
        slug = "property-" + slugify(property_type)
        title = f"Rental yield analysis for {property_type}"
        body = guide_body(title, "Property type guide", f"Use this checklist and calculator to evaluate a {property_type.lower()}. Actual performance depends on the property, lease, costs, financing and local rules.", slug)
        canonical = f"{SITE_URL}/guide/{slug}.html"
        schema = {"@context":"https://schema.org","@type":"Article","headline":title,"description":f"Rental yield and cash-flow framework for {property_type}.","dateModified":TODAY,"mainEntityOfPage":canonical,"author":{"@type":"Organization","name":SITE_NAME}}
        write(OUT / "guide" / f"{slug}.html", page(title + " | " + SITE_NAME, f"Estimate gross yield, NOI, cap rate and cash flow for {property_type}.", canonical, body, schema))
        urls.append((f"/guide/{slug}.html", title)); guide_count += 1

    static_pages = {
      "about": ("About", "This independent directory provides educational rental property calculation tools and due-diligence frameworks. It does not claim to verify market data or provide individualized investment advice.",),
      "methodology": ("Calculation methodology", "Gross yield = annual scheduled rent ÷ purchase price. Vacancy-adjusted rent = annual scheduled rent × (1 − vacancy rate). NOI = vacancy-adjusted rent − annual operating expenses. Cap rate = NOI ÷ purchase price. Net yield on acquisition cost = NOI ÷ (purchase price + closing costs). Mortgage payments use standard monthly amortization. Cash flow = NOI − annual debt service. Cash-on-cash return = cash flow ÷ (down payment + closing costs). DSCR = NOI ÷ annual debt service. The model excludes income tax, capital gains tax, selling costs, major capital expenditure, refinancing, changing rates, and currency conversion. Enter local costs and verify legal and tax treatment independently.",),
      "privacy": ("Privacy", "The calculator runs in the visitor’s browser. The site generator does not transmit calculator inputs to a server. Standard hosting providers may process ordinary request logs; consult the hosting provider’s privacy documentation for its retention practices.",),
      "terms": ("Terms and limitations", "The tools are educational estimates, not financial, investment, legal, accounting or tax advice. Outputs depend on user-entered assumptions and may omit important costs. Verify all figures and local requirements independently before acting.",),
      "contact": ("Contact", "For corrections, source suggestions or accessibility feedback, use the contact channel provided by the site owner. No response time or professional advisory service is promised.",),
    }
    for slug, (heading, description) in static_pages.items():
        body = f"<p><a href='/'>Home</a></p><h1>{esc(heading)}</h1><p>{esc(description)}</p>"
        write(OUT / f"{slug}.html", page(f"{heading} | {SITE_NAME}", description, f"{SITE_URL}/{slug}.html", body))
        urls.append((f"/{slug}.html", heading))

    loc_items = "".join(f"<li><a href='/guide/location-{slugify(x)}.html'>{esc(x)}</a></li>" for x in LOCATIONS)
    prop_items = "".join(f"<li><a href='/guide/property-{slugify(x)}.html'>{esc(x)}</a></li>" for x in PROPERTY_TYPES)
    for slug, heading, items, desc in [
        ("locations", "Location guides", loc_items, "Browse rental property due-diligence guides by location."),
        ("property-types", "Property type guides", prop_items, "Browse rental property calculation guides by asset type."),
    ]:
        body = f"<h1>{heading}</h1><p>{desc}</p><ul>{items}</ul>"
        write(OUT / f"{slug}.html", page(f"{heading} | {SITE_NAME}", desc, f"{SITE_URL}/{slug}.html", body))
        urls.append((f"/{slug}.html", heading))

    sitemap = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path, _ in urls:
        node = ET.SubElement(sitemap, "url")
        ET.SubElement(node, "loc").text = SITE_URL + (path if path != "/" else "/")
        ET.SubElement(node, "lastmod").text = TODAY
    ET.ElementTree(sitemap).write(OUT / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    write(OUT / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    llms = f"# {SITE_NAME}\n\n> Educational rental yield, cap rate and cash-flow calculators. Updated {TODAY}.\n\n## Tools\n- Homepage calculator: {SITE_URL}/\n- Methodology: {SITE_URL}/methodology.html\n- Location guides: {SITE_URL}/locations.html\n- Property type guides: {SITE_URL}/property-types.html\n\n## Scope and limitations\n- Calculations use visitor-entered assumptions; no live market database is claimed.\n- Tax, legal, financing and regulatory rules vary by jurisdiction and must be checked with primary sources.\n- Outputs are educational estimates, not investment advice.\n"
    write(OUT / "llms.txt", llms)

    # Deterministic build audit: sitemap parses, canonical links exist, no legacy salary/tax claims.
    html_files = list(OUT.rglob("*.html"))
    if len(html_files) != 49:
        raise RuntimeError(f"Expected 49 HTML pages (home, 41 guides, 5 static, 2 indexes); got {len(html_files)}")
    ET.parse(OUT / "sitemap.xml")
    forbidden = ("Remote Salary", "Take-Home Pay", "10,000", "Fact-Checked", "30-Year Verified")
    for file in html_files:
        content = file.read_text(encoding="utf-8")
        if 'rel="canonical"' not in content or "<h1>" not in content:
            raise RuntimeError(f"Missing canonical or H1: {file}")
        if any(term.lower() in content.lower() for term in forbidden):
            raise RuntimeError(f"Legacy/misleading content detected in {file}")
    print(f"BUILD_OK: {len(html_files)} HTML pages; {guide_count} unique guides; {len(urls)} sitemap URLs.")
    print("AUDIT_OK: canonical tags, H1s, sitemap XML and legacy-content checks passed.")
    print("DEPLOYMENT: build.py does not deploy. GitHub Actions controls Cloudflare deployment.")

if __name__ == "__main__":
    main()
