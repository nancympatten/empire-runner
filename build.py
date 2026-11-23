import os
import re
import csv
import json
from datetime import datetime, timezone
from google import genai
from google.genai import types
from pydantic import BaseModel

api_key = os.environ.get("GEMINI_API_KEY", "").strip()
if not api_key:
    raise RuntimeError("❌ GEMINI_API_KEY secret is empty or missing in GitHub Secrets!")

client = genai.Client(api_key=api_key)
site_url = os.environ["SITE_URL"].rstrip("/")
kingdom_topic = os.environ["KINGDOM_TOPIC"]
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

class GuideEntry(BaseModel):
    title: str
    slug: str
    category: str
    meta_description: str
    overview: str
    key_details: list[str]
    pro_tip: str

class EmpireBlueprint(BaseModel):
    site_title: str
    meta_description: str
    hero_heading: str
    hero_subheading: str
    entries: list[GuideEntry]

prompt = f"""
Build an authoritative, SEO-optimized directory dataset for: {kingdom_topic}
Generate 30 comprehensive, accurate, real-world entries.
Each entry must have a clean URL-friendly slug (lowercase letters and hyphens only), detailed overview, 4 actionable bullet points in key_details, and a practical pro_tip.
"""

response = None
last_err = None
for model_name in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]:
    try:
        print(f"Trying model: {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EmpireBlueprint,
                temperature=0.2,
            ),
        )
        print(f"✅ Success with {model_name}!")
        break
    except Exception as e:
        print(f"⚠️ Model {model_name} failed: {e}")
        last_err = e

if response is None:
    raise RuntimeError(f"All models failed. Last error: {last_err}")

data = json.loads(response.text)

os.makedirs("dist/guide", exist_ok=True)
sitemap_urls = [f"{site_url}/"]

with open("data.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Title", "Slug", "Category", "Meta Description", "Overview", "Pro Tip"])
    for e in data["entries"]:
        writer.writerow([e["title"], e["slug"], e["category"], e["meta_description"], e["overview"], e["pro_tip"]])

cards_html = []

for entry in data["entries"]:
    clean_slug = re.sub(r"[^a-z0-9-]+", "-", entry["slug"].lower()).strip("-")
    page_path = f"/guide/{clean_slug}.html"
    canonical_url = f"{site_url}{page_path}"
    sitemap_urls.append(canonical_url)

    bullets = "".join(f"<li>{d}</li>" for d in entry["key_details"])
    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{entry['title']} | {data['site_title']}</title>
<meta name="description" content="{entry['meta_description']}">
<link rel="canonical" href="{canonical_url}">
<meta property="og:title" content="{entry['title']}">
<meta property="og:description" content="{entry['meta_description']}">
<meta property="og:url" content="{canonical_url}">
<style>
body{{font-family:system-ui,-apple-system,sans-serif;background:#0b1120;color:#e2e8f0;margin:0;padding:2rem;line-height:1.6}}
.wrap{{max-width:820px;margin:0 auto;background:#1e293b;padding:2rem;border-radius:14px;border:1px solid #334155}}
a.back{{color:#38bdf8;text-decoration:none;font-weight:600}}
.badge{{display:inline-block;background:#0284c7;color:#fff;padding:.25rem .75rem;border-radius:999px;font-size:.8rem;margin:1rem 0}}
h1{{color:#f8fafc;margin:.2rem 0 1rem}}
.tip{{background:#0f172a;border-left:4px solid #38bdf8;padding:1rem;border-radius:8px;margin-top:1.5rem}}
</style>
</head>
<body>
<div class="wrap">
<a class="back" href="/">← Back to {data['site_title']}</a><br>
<span class="badge">{entry['category']}</span>
<h1>{entry['title']}</h1>
<p>{entry['overview']}</p>
<h2>Key Details & Transfer Options</h2>
<ul>{bullets}</ul>
<div class="tip"><strong>Pro Tip:</strong> {entry['pro_tip']}</div>
</div>
</body>
</html>"""

    with open(f"dist/guide/{clean_slug}.html", "w", encoding="utf-8") as pf:
        pf.write(page_html)

    cards_html.append(
        f"<a class='card' data-search='{entry['title'].lower()} {entry['category'].lower()}' href='{page_path}'>"
        f"<span class='badge'>{entry['category']}</span>"
        f"<h3>{entry['title']}</h3>"
        f"<p>{entry['meta_description']}</p>"
        f"<span class='read'>View Full Guide →</span></a>"
    )

index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{data['site_title']}</title>
<meta name="description" content="{data['meta_description']}">
<link rel="canonical" href="{site_url}/">
<style>
body{{font-family:system-ui,-apple-system,sans-serif;background:#0b1120;color:#f8fafc;margin:0;padding:2rem}}
header{{text-align:center;max-width:850px;margin:0 auto 2rem}}
h1{{font-size:2.3rem;color:#38bdf8;margin-bottom:.5rem}}
input#q{{width:100%;max-width:520px;padding:.85rem 1.1rem;border-radius:10px;border:1px solid #334155;background:#1e293b;color:#fff;font-size:1rem;margin-top:1rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:1.2rem;max-width:1200px;margin:0 auto}}
.card{{display:block;text-decoration:none;color:inherit;background:#1e293b;padding:1.4rem;border-radius:12px;border:1px solid #334155;transition:.2s}}
.card:hover{{border-color:#38bdf8;transform:translateY(-2px)}}
.badge{{background:#0284c7;color:#fff;padding:.2rem .65rem;border-radius:999px;font-size:.75rem}}
.read{{color:#38bdf8;font-size:.85rem;font-weight:600}}
footer{{text-align:center;margin-top:3rem;color:#94a3b8;font-size:.85rem}}
</style>
</head>
<body>
<header>
<h1>{data['hero_heading']}</h1>
<p>{data['hero_subheading']}</p>
<input id="q" type="search" placeholder="Search airports, cities, or transfer guides..." oninput="filterCards(this.value)">
</header>
<div class="grid" id="grid">{''.join(cards_html)}</div>
<footer><p>© 2026 {data['site_title']} • <a style="color:#38bdf8" href="/sitemap.xml">Sitemap</a></p></footer>
<script>
function filterCards(v){{v=v.toLowerCase();document.querySelectorAll('.card').forEach(c=>c.style.display=c.dataset.search.includes(v)?'block':'none')}}
</script>
</body>
</html>"""

with open("dist/index.html", "w", encoding="utf-8") as f:
    f.write(index_html)

xml_items = "\n".join(
    f"  <url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>{'1.0' if u == site_url + '/' else '0.8'}</priority></url>"
    for u in sitemap_urls
)
sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://sitemaps.org">
{xml_items}
</urlset>"""

with open("dist/sitemap.xml", "w", encoding="utf-8") as f:
    f.write(sitemap_xml)

with open("dist/robots.txt", "w", encoding="utf-8") as f:
    f.write(f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n")

print(f"✅ SEO Empire built with {len(sitemap_urls)} locked canonical URLs at {site_url}")
