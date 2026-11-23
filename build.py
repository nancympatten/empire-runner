import os, re, csv, json, html
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "").strip())
site_url = os.environ["SITE_URL"].rstrip("/")
topic = os.environ["KINGDOM_TOPIC"]
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

p0 = f"List 25 distinct sub-topics or regions for: {topic}. One per line, plain text."
res_p = client.models.generate_content(model="gemini-3.5-flash-lite", contents=p0)
clusters = [l.strip("- *0123456789.") for l in res_p.text.splitlines() if l.strip()][:25]
while len(clusters) < 25:
    clusters.append(f"{topic} Hub {len(clusters)+1}")

def fetch(ic):
    i, c = ic
    p = (
        f"Generate 400 unique SEO entries for '{topic}' focused on '{c}'. "
        "Output strictly pipe-separated lines (NO header, NO markdown), 8 fields: "
        "Title | Category | Summary | OptionA | OptionB | OptionC | ProTip | FAQ"
    )
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash"]:
        try:
            cfg = types.GenerateContentConfig(temperature=0.4, max_output_tokens=65536)
            r = client.models.generate_content(model=m, contents=p, config=cfg)
            rows = []
            for l in r.text.splitlines():
                parts = [x.strip() for x in l.split("|")]
                if len(parts) >= 8 and not parts[0].lower().startswith("title"):
                    rows.append(parts[:8])
            print(f"Batch {i+1}/25: {len(rows)} rows")
            return rows
        except Exception as e:
            print(f"Retry {i+1}: {e}")
    return []

all_rows, seen = [], set()
with ThreadPoolExecutor(max_workers=12) as ex:
    for f in as_completed([ex.submit(fetch, x) for x in enumerate(clusters)]):
        for r in f.result():
            bs = re.sub(r"[^a-z0-9]+", "-", r[0].lower()).strip("-")[:80] or "guide"
            s, k = bs, 2
            while s in seen:
                s, k = f"{bs}-{k}", k + 1
            seen.add(s)
            all_rows.append((s, r))

if all_rows:
    pool, idx = list(all_rows), 0
    while len(all_rows) < 10000:
        oslug, orow = pool[idx % len(pool)]
        v = (idx // len(pool)) + 2
        ns = f"{oslug}-v{v}"
        if ns not in seen:
            seen.add(ns)
            all_rows.append((ns, [f"{orow[0]} (2026 Edition #{v})"] + orow[1:]))
        idx += 1

all_rows = all_rows[:10000]
print("Total SEO Pages Built:", len(all_rows))
with open("data.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Slug","Title","Category","Summary","OptionA","OptionB","OptionC","ProTip","FAQ"])
    for s, r in all_rows:
        w.writerow([s] + r)

os.makedirs("dist/guide", exist_ok=True)
cats = sorted(list({r for _, r in all_rows}))
cmap = {}
for idx, (s, r) in enumerate(all_rows):
    cmap.setdefault(r, []).append(idx)

dslug = site_url.split("//")[-1].split(".")
sname = " ".join(w.capitalize() for w in dslug.split("-"))

def render(idx):
    s, r = all_rows[idx]
    t, c, sm, oa, ob, oc, tip, faq = [html.escape(x) for x in r]
    can = f"{site_url}/guide/{s}.html"
    rels = "".join(
        f"<li><a href='/guide/{all_rows[p]}.html'>{html.escape(all_rows[p])}</a></li>"
        for p in cmap.get(r, [])[:6] if p != idx
    )
    sch = json.dumps({
        "@context": "https://schema.org", "@type": "Article",
        "headline": r, "description": r,
        "mainEntityOfPage": can, "dateModified": today
    })
    h = (
        f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{t} | {html.escape(sname)}</title>"
        f"<meta name='description' content='{sm}'><link rel='canonical' href='{can}'>"
        f"<script type='application/ld+json'>{sch}</script>"
        "<style>body{font-family:system-ui,sans-serif;background:#f8fafc;color:#0f172a;margin:0;line-height:1.6}"
        "nav{background:#fff;border-bottom:1px solid #e2e8f0;padding:1rem 1.5rem;display:flex;justify-content:space-between}"
        "nav a{color:#0f172a;text-decoration:none;font-weight:700}"
        ".box{max-width:860px;margin:2rem auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:2rem}"
        ".badge{background:#eff6ff;color:#2563eb;padding:.2rem .75rem;border-radius:999px;font-size:.8rem;font-weight:600}"
        "table{width:100%;border-collapse:collapse;margin:1.5rem 0}th,td{border:1px solid #e2e8f0;padding:.75rem;text-align:left}"
        "th{background:#f1f5f9}.tip{background:#f0fdf4;border-left:4px solid #16a34a;padding:1rem;border-radius:8px;margin:1.5rem 0}"
        ".faq{background:#f8fafc;border:1px solid #e2e8f0;padding:1.2rem;border-radius:8px}</style></head><body>"
        f"<nav><a href='/'>{html.escape(sname)}</a><a href='/sitemap.xml' style='color:#2563eb'>10,000 Guides</a></nav>"
        f"<div class='box'><span class='badge'>{c}</span><h1>{t}</h1><p>{sm}</p>"
        f"<table><tr><th>Tier / Option</th><th>Verified Details &amp; Protocol</th></tr>"
        f"<tr><td><b>Primary</b></td><td>{oa}</td></tr>"
        f"<tr><td><b>Alternative</b></td><td>{ob}</td></tr>"
        f"<tr><td><b>Express / Budget</b></td><td>{oc}</td></tr></table>"
        f"<div class='tip'><b>Insider Tip:</b> {tip}</div>"
        f"<div class='faq'><b>FAQ:</b><p>{faq}</p></div>"
        f"<h3>Related {c} Guides</h3><ul>{rels}</ul></div></body></html>"
    )
    with open(f"dist/guide/{s}.html", "w", encoding="utf-8") as pf:
        pf.write(h)

with ThreadPoolExecutor(max_workers=32) as ex:
    list(ex.map(render, range(len(all_rows))))

sidx = [{"s": s, "t": r, "c": r, "d": r[:110]} for s, r in all_rows]
with open("dist/search-index.json", "w", encoding="utf-8") as jf:
    json.dump(sidx, jf, separators=(",", ":"))

pills = "".join(f"<button class='pill' onclick=\"setCat('{html.escape(c)}',this)\">{html.escape(c)}</button>" for c in cats)
ih = (
    f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
    f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
    f"<title>{html.escape(sname)} | 10,000 Verified Guides</title>"
    f"<meta name='description' content='10,000 verified guides for {html.escape(topic)}'>"
    f"<link rel='canonical' href='{site_url}/'>"
    "<style>body{font-family:system-ui,sans-serif;margin:0;color:#0f172a}"
    "header{background:#f8fafc;border-bottom:1px solid #e2e8f0;padding:2.5rem 1rem;text-align:center}"
    "h1{font-size:2.2rem;margin:.5rem 0}#q{width:100%;max-width:540px;padding:.85rem 1rem;border:1px solid #cbd5e1;border-radius:10px;font-size:1rem}"
    ".pills{display:flex;flex-wrap:wrap;justify-content:center;gap:.4rem;max-width:960px;margin:1rem auto 0}"
    ".pill{background:#fff;border:1px solid #e2e8f0;padding:.4rem .85rem;border-radius:999px;cursor:pointer}.pill.active{background:#2563eb;color:#fff}"
    ".main{max-width:1180px;margin:2rem auto;padding:0 1rem}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1rem}"
    ".card{display:block;text-decoration:none;color:inherit;border:1px solid #e2e8f0;border-radius:10px;padding:1.2rem}.card:hover{border-color:#2563eb}"
    ".badge{background:#eff6ff;color:#2563eb;font-size:.75rem;padding:.2rem .5rem;border-radius:6px;font-weight:600}.pager{text-align:center;margin:2rem 0}</style></head><body>"
    f"<header><span class='badge'>Directory Refreshed • 10,000 Guides</span><h1>{html.escape(sname)}</h1>"
    "<input id='q' type='search' placeholder='Search 10,000 guides...' oninput='Q=this.value.toLowerCase();P=1;apply()'>"
    f"<div class='pills'><button class='pill active' onclick=\"setCat('ALL',this)\">All (10,000)</button>{pills}</div></header>"
    "<div class='main'><p id='cnt'></p><div class='grid' id='g'></div>"
    "<div class='pager'><button onclick='if(P>1){P--;render()}'>← Prev</button> <span id='pi'></span> <button onclick='if(P*60<F.length){P++;render()}'>Next →</button></div></div>"
    "<script>let D=[],F=[],C='ALL',Q='',P=1;fetch('/search-index.json').then(r=>r.json()).then(d=>{D=d;F=d;render()});"
    "function setCat(c,b){C=c;P=1;document.querySelectorAll('.pill').forEach(x=>x.classList.remove('active'));b.classList.add('active');apply()}"
    "function apply(){F=D.filter(x=>(C==='ALL'||x.c===C)&&(!Q||x.t.toLowerCase().includes(Q)||x.d.toLowerCase().includes(Q)));render()}"
    "function render(){document.getElementById('cnt').textContent='Showing '+F.length+' guides';document.getElementById('pi').textContent='Page '+P;"
    "document.getElementById('g').innerHTML=F.slice((P-1)*60,P*60).map(x=>`<a class='card' href='/guide/${x.s}.html'><span class='badge'>${x.c}</span><h3>${x.t}</h3><p>${x.d}...</p></a>`).join('')}</script></body></html>"
)
with open("dist/index.html", "w", encoding="utf-8") as f:
    f.write(ih)

urls = [f"{site_url}/"] + [f"{site_url}/guide/{s}.html" for s, _ in all_rows]
subs = []
for i in range(0, len(urls), 2000):
    fn = f"sitemap-{(i//2000)+1}.xml"
    subs.append(f"{site_url}/{fn}")
    items = "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>" for u in urls[i:i+2000])
    with open(f"dist/{fn}", "w", encoding="utf-8") as sf:
        sf.write(f"<?xml version='1.0' encoding='UTF-8'?><urlset xmlns='http://sitemaps.org'>{items}</urlset>")

sitems = "".join(f"<sitemap><loc>{s}</loc><lastmod>{today}</lastmod></sitemap>" for s in subs)
with open("dist/sitemap.xml", "w", encoding="utf-8") as f:
    f.write(f"<?xml version='1.0' encoding='UTF-8'?><sitemapindex xmlns='http://sitemaps.org'>{sitems}</sitemapindex>")

with open("dist/robots.txt", "w", encoding="utf-8") as f:
    f.write(f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n")
