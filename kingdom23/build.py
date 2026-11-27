import html
import shutil
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from config import SITE_URL, STAGE, SITEMAP_SHARD_LIMIT
from validate_data import validate_all


def validate_build_config():
    parsed = urlparse(SITE_URL)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit("STOP: SITE_URL must be a valid HTTPS base URL")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise SystemExit("STOP: SITE_URL must not contain a path, query or fragment")
    if not isinstance(SITEMAP_SHARD_LIMIT, int) or isinstance(SITEMAP_SHARD_LIMIT, bool) or SITEMAP_SHARD_LIMIT < 1:
        raise SystemExit("STOP: SITEMAP_SHARD_LIMIT must be a positive integer")
    stage = STAGE.resolve()
    output = __import__("config").OUTPUT.resolve()
    if stage == output or stage in output.parents or output in stage.parents:
        raise SystemExit("STOP: STAGE and OUTPUT paths must be separate")



def esc(value):
    return html.escape(str(value or ""), quote=True)


def page(title, description, body, canonical):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<meta name="robots" content="index,follow">
<style>
:root{{--ink:#29251f;--cream:#fffaf0;--amber:#d78b25;--muted:#71695e}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--cream);color:var(--ink);font:16px/1.65 system-ui,sans-serif}}
header,main,footer{{max-width:960px;margin:auto;padding:22px}}
header{{border-bottom:1px solid #e8dcc7}}
a{{color:#80500e}}
.hero{{padding:42px 24px;background:#f4e5c9;border-radius:18px}}
h1,h2{{line-height:1.2}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}}
.card{{background:white;border:1px solid #eadfcf;border-radius:14px;padding:20px}}
label{{display:block;font-weight:650;margin:12px 0 5px}}
input{{width:100%;padding:12px;border:1px solid #b9ad9b;border-radius:8px;font:inherit}}
button{{margin-top:14px;background:var(--amber);color:#21180c;border:0;border-radius:8px;padding:12px 18px;font-weight:700}}
.result{{font-weight:700;margin-top:12px}}
small,.muted{{color:var(--muted)}}
footer{{border-top:1px solid #e8dcc7;margin-top:40px}}
</style>
</head>
<body>
<header><a href="/">Global Travel eSIM Atlas</a></header>
<main>{body}</main>
<footer><p>Independent travel data tools. Plan details and availability can change. Verify all plan terms with the provider before purchase.</p><small>Copyright <span id="year"></span> Global Travel eSIM Atlas</small></footer>
<script>document.getElementById("year").textContent=new Date().getFullYear();</script>
</body></html>"""


def calculator_pages():
    data_calc = """
<section class="hero">
<h1>Travel Data Usage Calculator</h1>
<p>Estimate how much mobile data you may need while travelling. This is a planning estimate, not a provider quote.</p>
</section>
<section class="card">
<label for="days">Trip length (days)</label><input id="days" type="number" min="1" max="365" value="7">
<label for="daily">Estimated data use per day (GB)</label><input id="daily" type="number" min="0" step="0.1" value="1">
<button onclick="calc()">Estimate data</button>
<p class="result" id="result" aria-live="polite">Enter your estimates to calculate.</p>
</section>
<section class="card">
<h2>What uses mobile data while travelling?</h2>
<p>Your daily data estimate depends on how you use your phone. Messaging and email containing mostly text may use relatively little data, while photo and video sharing can use considerably more. Video streaming, video calls, cloud backups and large downloads can consume data quickly. Navigation may also use data when maps or location information need to load online.</p>
<h2>How to estimate daily travel data</h2>
<p>Think through a typical travel day. Consider browsing, social networks, photo uploads, entertainment, video calls and hotspot use. Include other connected devices if they will share your mobile connection. Your travel habits may differ from your usual home routine, so base the estimate on the activities you actually expect to do.</p>
<h2>Allow for changing usage</h2>
<p>Trip length multiplied by estimated daily usage gives a baseline, not a guaranteed requirement. Consider adding a personal allowance for unexpected usage or unusually busy days. Offline maps and downloaded entertainment can reduce mobile data consumption. Background app refresh, automatic updates and photo synchronisation can increase it.</p>
<p><strong>Important:</strong> This calculator uses only the trip duration and daily usage you enter. It does not measure your device, predict app consumption or check provider packages. Actual usage varies with device settings, content quality and network conditions. Check your phone's data-usage settings during the trip and adjust your estimate when needed.</p>
</section>
<script>
function calc(){
 const d=Number(document.getElementById('days').value);
 const g=Number(document.getElementById('daily').value);
 const r=document.getElementById('result');
 if(!Number.isFinite(d)||!Number.isFinite(g)||d<1||d>365||g<0){r.textContent='Enter valid positive trip days and non-negative daily usage.';return;}
 r.textContent='Estimated trip data: '+(d*g).toFixed(2)+' GB. Consider a buffer for unexpected usage.';
}
</script>"""
    cost_calc = """
<section class="hero">
<h1>eSIM Cost per GB Calculator</h1>
<p>Compare plan values using prices and data allowances that you enter yourself. This tool does not fetch live prices.</p>
</section>
<section class="card">
<label for="price">Plan price (your currency)</label><input id="price" type="number" min="0" step="0.01" placeholder="e.g. 15">
<label for="gb">Included data (GB)</label><input id="gb" type="number" min="0.01" step="0.01" placeholder="e.g. 5">
<button onclick="calc()">Calculate cost per GB</button>
<p class="result" id="result" aria-live="polite">Enter a plan price and data allowance.</p>
</section>
<section class="card">
<h2>How cost per GB is calculated</h2>
<p>Divide the plan price by its included data allowance in gigabytes. For example, a plan costing 15 currency units with 5 GB of data has an arithmetic cost of 3 currency units per GB. The result stays in the same currency as the price you enter. This calculator does not convert currencies or retrieve current market prices.</p>
<h2>Compare more than the headline rate</h2>
<p>A lower cost per GB does not automatically mean a better travel plan. Check how long the allowance remains valid and whether it covers your entire trip. Review destination coverage, full-speed data limits and any fair-use policy. Confirm hotspot or tethering rules if you plan to connect a laptop or another device.</p>
<h2>Check total cost and plan conditions</h2>
<p>Look for activation deadlines, top-up requirements, taxes, fees and device restrictions. An advertised allowance may be shared across destinations or subject to local network limitations. Compare plans in the same currency and on equivalent terms. If currencies differ, convert prices using a current exchange rate and account for possible conversion fees.</p>
<p><strong>Important:</strong> This tool compares only the price and data allowance you enter. It does not verify coverage, network speed, validity, taxes, availability or plan conditions. Confirm all details on the provider's official offer before purchasing.</p>
</section>
<script>
function calc(){
 const p=Number(document.getElementById('price').value);
 const g=Number(document.getElementById('gb').value);
 const r=document.getElementById('result');
 if(!Number.isFinite(p)||!Number.isFinite(g)||p<0||g<=0){r.textContent='Enter a non-negative price and data allowance greater than zero.';return;}
 r.textContent='Cost per GB: '+(p/g).toFixed(2)+' in the same currency as your entered price.';
}
</script>"""
    return [
        ("tools/data-usage-calculator.html", "Travel Data Usage Calculator", "Estimate mobile data needs for a trip using your own assumptions.", data_calc),
        ("tools/esim-cost-per-gb-calculator.html", "eSIM Cost per GB Calculator", "Compare eSIM plan value using user-entered prices and data allowances.", cost_calc),
    ]


def main():
    validate_build_config()
    data = validate_all()

    if data["page_topics.csv"]:
        raise SystemExit(
            "STOP: page_topics.csv contains rows, but evidence-backed guide "
            "templates are not implemented yet. No placeholder guide pages "
            "will be published. Keep topics empty until the matching page "
            "templates and evidence checks are ready."
        )
    if STAGE.exists():
        raise SystemExit(f"STOP: staging directory already exists; inspect before replacing: {STAGE}")

    STAGE.mkdir(parents=True)
    urls = []
    today = datetime.now(timezone.utc).date().isoformat()

    def write_page(relative, title, description, body):
        target = STAGE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        canonical = (
            SITE_URL.rstrip("/") + "/"
            if relative == "index.html"
            else urljoin(SITE_URL.rstrip("/") + "/", relative)
        )
        target.write_text(page(title, description, body, canonical), encoding="utf-8")
        urls.append(canonical)

    home_body = """
<section class="hero">
<h1>Global Travel eSIM Atlas</h1>
<p>Independent tools and evidence-led guides for understanding international eSIM data plans and travel connectivity.</p>
<p>Plan your data needs and compare costs using your own inputs. Provider prices, availability, coverage and plan conditions can change; always confirm details with the provider.</p>
</section>
<h2>Travel planning tools</h2>
<div class="grid">
<article class="card"><h3><a href="/tools/data-usage-calculator.html">Travel Data Usage Calculator</a></h3><p>Estimate data needs from trip length and daily usage.</p></article>
<article class="card"><h3><a href="/tools/esim-cost-per-gb-calculator.html">eSIM Cost per GB Calculator</a></h3><p>Compare user-entered plan prices and data allowances.</p></article>
</div>
<h2>Destination and provider research</h2>
<p class="muted">Destination and plan guides will appear as source-backed observations are added and validated. No unverified coverage or pricing claims are published.</p>
"""
    write_page("index.html", "Global Travel eSIM Atlas | Travel Data Tools", "Plan travel data needs and compare eSIM costs with independent calculators.", home_body)

    for relative, title, description, body in calculator_pages():
        write_page(relative, title, description, body)


    shards = [
        urls[i:i + SITEMAP_SHARD_LIMIT]
        for i in range(0, len(urls), SITEMAP_SHARD_LIMIT)
    ]
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    for number, shard in enumerate(shards, 1):
        entries = "".join(
            f"<url><loc>{esc(url)}</loc><lastmod>{today}</lastmod></url>"
            for url in shard
        )
        xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="{namespace}">{entries}</urlset>'
        (STAGE / f"sitemap-{number}.xml").write_text(xml, encoding="utf-8")

    sitemap_entries = "".join(
        f"<sitemap><loc>{esc(urljoin(SITE_URL.rstrip('/') + '/', f'sitemap-{n}.xml'))}</loc><lastmod>{today}</lastmod></sitemap>"
        for n in range(1, len(shards) + 1)
    )
    index_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="{namespace}">{sitemap_entries}</sitemapindex>'
    (STAGE / "sitemap.xml").write_text(index_xml, encoding="utf-8")
    (STAGE / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL.rstrip('/')}/sitemap.xml\n",
        encoding="utf-8",
    )

    print("BUILD_COMPLETE")
    print(f"Output: {STAGE}")
    print(f"HTML pages: {len(urls)}")
    print(f"Sitemap shards: {len(shards)}")
    print(f"Build lastmod: {today}")


if __name__ == "__main__":
    main()
