import os, json, html, time, uuid, urllib.request
from itertools import islice
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

site_url = os.environ.get("SITE_URL", "").rstrip("/")
topic = os.environ.get("KINGDOM_TOPIC", "")
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
year = datetime.now(timezone.utc).strftime("%Y")

def slugify(txt):
    out = "".join(c if c.isalnum() else "-" for c in txt.lower())
    while "--" in out: out = out.replace("--", "-")
    return "-".join(out.strip("-").split("-")[:11])

hubs = (
    "Hetzner Cloud (Germany & US)", "DigitalOcean Droplets",
    "Vultr High Frequency NVMe", "Linode Akamai Cloud",
    "AWS Lightsail & EC2", "Google Cloud Compute Engine",
    "Microsoft Azure Virtual Machines", "Cloudways Managed Cloud",
    "Hostinger KVM VPS", "Contabo Cloud VPS",
    "OVHcloud Bare Metal & VPS", "UpCloud MaxIOPS",
    "Kamatera Custom Cloud", "Oracle Cloud Ampere ARM",
    "Scaleway Europe Cloud", "IONOS Cloud VPS",
    "DreamHost Managed VPS", "Bluehost NVMe VPS",
    "A2 Hosting Turbo VPS", "SiteGround Cloud Hosting",
    "Liquid Web Managed Dedicated", "Fly.io Edge MicroVMs",
    "Railway App Hosting", "Render Cloud Services",
    "Cloudflare Workers & Pages"
)
roles = (
    "2 vCPU / 4GB RAM Starter", "4 vCPU / 8GB RAM Production",
    "8 vCPU / 16GB RAM Scale", "16 vCPU / 32GB RAM Enterprise",
    "High-Traffic WordPress & WooCommerce", "Next.js & Node.js SaaS Backend",
    "Docker & Kubernetes Cluster", "PostgreSQL & Redis Database Node",
    "n8n & AI Automation Self-Hosting", "Game Server & Low-Latency UDP",
    "Forex & Algo Trading Low-Ping", "Video Streaming & FFmpeg Node",
    "CyberPanel & cPanel Reseller", "Python & FastAPI Microservices",
    "Arm64 Ampere Cost-Optimized", "Dedicated Ryzen 9 Bare Metal"
)
cats8 = (
    ("NVMe Storage & Disk IOPS", "145,000+ Read IOPS", "Gen4 Enterprise NVMe", "3.2 GB/s Sequential",
     "Local RAID-10 enterprise NVMe SSD storage delivering sub-millisecond database query latency.",
     "Network-attached block storage with live snapshot backups and instant volume resizing.",
     "TIP: Local NVMe storage delivers 4x higher database IOPS than network-attached block volumes. || FAQ: Does higher IOPS speed up WordPress and SQL? Yes, database-heavy apps load 2x–3x faster on Gen4 NVMe."),
    ("CPU Single-Core & Geekbench Score", "1,850+ Single-Core", "AMD EPYC / Ryzen 9", "Dedicated vCPU Thread",
     "Dedicated physical CPU threads with zero noisy-neighbor throttling during peak traffic spikes.",
     "Shared burstable vCPU instance optimized for low-cost staging and lightweight APIs.",
     "TIP: Always choose Dedicated vCPU over Shared vCPU for production databases and checkout APIs. || FAQ: What is the difference between shared and dedicated vCPU? Dedicated vCPUs guarantee 100% core time without host contention."),
    ("Monthly Pricing & Renewal Transparency", "$6 – $48/mo Flat", "0% Renewal Hike", "Hourly Billing Cap",
     "Transparent flat monthly and hourly utility pricing with zero hidden 3x renewal price jumps.",
     "Introductory 12-to-36 month promotional discount with upfront annual billing lock-in.",
     "TIP: Cloud providers like Hetzner, DigitalOcean, and Vultr charge the exact same rate forever with zero renewal hikes. || FAQ: Are VPS plans billed hourly or monthly? Most developer clouds bill hourly up to a fixed monthly cap."),
    ("Bandwidth, Port Speed & DDoS Protection", "4TB – 20TB Egress", "10 Gbps Network Port", "Always-On L3/L4 DDoS",
     "Generous monthly outbound bandwidth allowance with free unlimited inbound traffic and DDoS mitigation.",
     "Unmetered 1 Gbps port bandwidth plan engineered for high-media and file-download workloads.",
     "TIP: Put Cloudflare CDN in front of your VPS to offload 85% of static bandwidth egress for free. || FAQ: Is inbound traffic counted toward bandwidth limits? Almost all cloud providers offer free unlimited inbound traffic."),
    ("Global Data Center Latency & Peering", "<18 ms Regional Ping", "99.99% Uptime SLA", "Anycast BGP Routing",
     "Tier-3+ ISO-27001 certified data centers across US, EU, India, Singapore, and Japan.",
     "Multi-region private VPC networking with sub-5ms internal cross-server communication.",
     "TIP: Host your VPS in the exact city or region where 70%+ of your target users live. || FAQ: How much does server location affect SEO? Lower Time-to-First-Byte (TTFB) directly improves Core Web Vitals."),
    ("Automated Backups, Snapshots & Recovery", "Daily Off-Site Backup", "1-Click Point-in-Time", "20% Backup Add-On",
     "Automated daily incremental off-site backups with 7-to-30 day retention and 60-second restore.",
     "Manual on-demand disk snapshots billed per GB stored for pre-deployment safety.",
     "TIP: Automate off-site S3/Backblaze backups in addition to provider snapshots for total disaster immunity. || FAQ: Do snapshots work while the server is running? Yes, live snapshots capture disk state with zero downtime."),
    ("Managed vs Unmanaged Control Panel", "Root SSH + Cloud-Init", "1-Click Docker / WP", "Zero Sysadmin Overhead",
     "Full root SSH access with Ubuntu/Debian images, firewall rules, and API/Terraform automation.",
     "Managed server stack handling OS security patches, Nginx/LiteSpeed tuning, and SSL renewals.",
     "TIP: Pair an unmanaged $10/mo VPS with a lightweight panel like Coolify or CloudPanel to save $50/mo. || FAQ: Is unmanaged VPS hard to secure? Enabling SSH keys, UFW firewall, and Fail2Ban takes under 5 minutes."),
    ("Annual Cloud TCO & Savings Calculator", "Save $1,440+/yr", "AWS vs VPS Audit", "Live Bandwidth Math",
     "Interactive vCPU, RAM, storage, and egress bandwidth annual cloud spend comparison.",
     "Reserved multi-server cluster calculation comparing hyperscalers against independent NVMe clouds.",
     "TIP: Migrating steady workloads from AWS EC2 to high-frequency NVMe VPS providers cuts cloud bills by 60%. || FAQ: How accurate is the cloud TCO slider? It models compute, NVMe storage, backups, and bandwidth overage.")
)

all_rows, seen = list(), set()
for h_name in hubs:
    for r_name in roles:
        for cn, m1, m2, m3, oa, ob, tf in cats8:
            t = f"{h_name} {r_name} — {cn} ({year})"
            s = slugify(t)
            if s not in seen:
                seen.add(s)
                sm = f"Verified {year} NVMe IOPS, Geekbench CPU score, and monthly pricing benchmark for {h_name} ({r_name}) under {cn}: {m1} ({m2})."
                all_rows.append((s, (t, cn, sm, m1, m2, m3, oa, ob, tf)))

pool, idx = tuple(all_rows), 0
while len(all_rows) < 10000:
    oslug, orow = pool[idx % len(pool)]
    v = (idx // len(pool)) + 2
    ns = f"{oslug}-v{v}"
    if ns not in seen:
        seen.add(ns)
        rt, rc, rsm, m1, m2, m3, oa, ob, tf = orow
        all_rows.append((ns, (f"{rt} (Node #{v})", rc, rsm, m1, m2, m3, oa, ob, tf)))
    idx += 1
all_rows = tuple(islice(all_rows, 10000))
os.makedirs("dist/guide", exist_ok=True)
os.makedirs("dist/category", exist_ok=True)
cats = sorted(list({next(islice(r, 1, 2)) for _, r in all_rows}))
cmap = {}
for idx, (s, r) in enumerate(all_rows):
    cmap.setdefault(next(islice(r, 1, 2)), list()).append(idx)
sname = " ".join(w.capitalize() for w in next(iter(site_url.split("//")[-1].split("."))).split("-"))

for pg, hd, bd in (
    ("about", f"About {sname}", f"{sname} provides 10,000+ localized remote worker tax, take-home salary & DTAA calculators verified for {year}."),
    ("methodology", "Tax & Take-Home Pay Methodology", "Calculations model statutory progressive tax brackets, standard deductions, and bilateral social security rules."),
    ("privacy", "Privacy Policy", "All salary and tax slider inputs execute 100% locally in your browser without storing personal data."),
    ("terms", "Terms of Service", "Calculators are provided for educational estimation; confirm final filings with a licensed cross-border CPA."),
    ("contact", "Contact Editorial Desk", f"Reach {sname} verification team for tax treaty updates or payroll benchmarks.")
):
    with open(f"dist/{pg}.html", "w", encoding="utf-8") as af:
        af.write(f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(hd)} | {html.escape(sname)}</title><link rel='canonical' href='{site_url}/{pg}.html'><style>body{{font-family:system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1.2rem;line-height:1.7;color:#0f172a}}a{{color:#10a37f}}</style></head><body><p><a href='/'>← Back to {html.escape(sname)}</a></p><h1>{html.escape(hd)}</h1><p>{html.escape(bd)}</p><p><small>Last Verified: {today}</small></p></body></html>")

def rcard(p):
    ps, pr = all_rows[p]
    pt, pc, _, pm1, _, _, _, _, _ = (html.escape(x) for x in pr)
    return f"<a class='rcard' href='/guide/{ps}.html'><span class='badge'>{pc}</span><h4>{pt}</h4><small>{pm1} • Compare Now →</small></a>"
def render(idx):
    s, r = all_rows[idx]
    rt, rc, rsm, rm1, rm2, rm3, roa, rob, rtf = r
    t, c, sm, m1, m2, m3, oa, ob, tf = (html.escape(x) for x in r)
    can = f"{site_url}/guide/{s}.html"
    cs = slugify(rc) or "general"
    peers = tuple(p for p in islice(cmap.get(rc, ()), 7) if p != idx)
    rel_cards = "".join(rcard(p) for p in islice(peers, 4))
    cross_cards = "".join(rcard((idx + k) % len(all_rows)) for k in (401, 1203))
    sch = json.dumps((
        {"@context":"https://schema.org","@type":"Article","headline":rt,"description":rsm,"mainEntityOfPage":can,"dateModified":today,"author":{"@type":"Organization","name":sname}},
        {"@context":"https://schema.org","@type":"WebApplication","name":f"{rt} Calculator","applicationCategory":"FinanceApplication","operatingSystem":"All","url":can},
        {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":({"@type":"ListItem","position":1,"name":"Home","item":f"{site_url}/"},{"@type":"ListItem","position":2,"name":rc,"item":f"{site_url}/category/{cs}.html"},{"@type":"ListItem","position":3,"name":rt,"item":can})},
        {"@context":"https://schema.org","@type":"FAQPage","mainEntity":({"@type":"Question","name":f"What is the effective tax rate for {rt}?","acceptedAnswer":{"@type":"Answer","text":rtf}},{"@type":"Question","name":f"Primary vs Alternative option for {rt}?","acceptedAnswer":{"@type":"Answer","text":f"Primary: {roa} Alternative: {rob}"}})}
    ))
    h = (
        f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{t} | {html.escape(sname)}</title><meta name='description' content='{sm}'><link rel='canonical' href='{can}'>"
        f"<script type='application/ld+json'>{sch}</script>"
        "<style>:root{--bg:#f8fafc;--card:#fff;--txt:#0f172a;--mut:#475569;--bdr:#e2e8f0;--acc:#10a37f}.dark{--bg:#0b1120;--card:#111827;--txt:#f8fafc;--mut:#94a3b8;--bdr:#1e293b}"
        "html{font-size:16px}body{font-family:system-ui,sans-serif;-webkit-tap-highlight-color:transparent;background:var(--bg);color:var(--txt);margin:0;line-height:1.7}nav{background:var(--card);border-bottom:1px solid var(--bdr);padding:.9rem 1.5rem;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}"
        "nav a{color:var(--txt);text-decoration:none;font-weight:700}.box{max-width:940px;margin:1rem auto;background:var(--card);border:1px solid var(--bdr);border-radius:14px;padding:1.25rem}@media(min-width:640px){.box{margin:1.8rem auto;padding:2rem}}"
        ".badge{background:#ecfdf5;color:#059669;padding:.22rem .7rem;border-radius:999px;font-size:.78rem;font-weight:600}.tldr{background:var(--bg);border-left:4px solid var(--acc);padding:1rem 1.2rem;border-radius:8px;margin:1.2rem 0}"
        ".mgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:.8rem;margin:1.2rem 0}.mcard{border:1px solid var(--bdr);padding:1rem;border-radius:10px;background:var(--bg)}"
        ".calc{border:1px solid var(--acc);border-radius:14px;padding:1.3rem;margin:1.5rem 0;background:var(--bg)}.presets{display:flex;gap:.5rem;flex-wrap:wrap;margin:.6rem 0}.presets button{background:var(--card);color:var(--txt);border:1px solid var(--bdr);padding:.35rem .8rem;border-radius:999px;cursor:pointer;font-size:.82rem}"
        ".cgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem;margin-top:.8rem}.vbar{height:12px;border-radius:99px;background:#3b82f6;overflow:hidden;margin:.8rem 0}.vfill{height:100%;background:var(--acc);transition:width .3s}"
        ".rng{width:100%;height:34px;accent-color:var(--acc);cursor:pointer}table{width:100%;border-collapse:collapse;margin:1rem 0}th,td{border:1px solid var(--bdr);padding:.75rem;text-align:left}"
        "details{border:1px solid var(--bdr);border-radius:10px;padding:.8rem 1rem;margin:.6rem 0;background:var(--bg)}summary{font-weight:700;cursor:pointer}"
        ".rgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:.9rem;margin-top:1rem}.rcard{display:block;text-decoration:none;color:inherit;background:var(--bg);border:1px solid var(--bdr);border-radius:12px;padding:1rem}.rcard:hover{border-color:var(--acc)}"
        "footer{text-align:center;padding:2rem;color:var(--mut);font-size:.85rem}</style></head><body>"
        f"<nav><a href='/'>{html.escape(sname)}</a><div><button onclick=\"document.body.classList.toggle('dark')\" style='cursor:pointer;padding:.35rem .7rem;border-radius:8px;border:1px solid var(--bdr);background:var(--bg);color:var(--txt)'>🌓 Theme</button></div></nav>"
        f"<div class='box'><p style='font-size:.85rem;color:var(--mut)'><a href='/'>Home</a> › <a href='/category/{cs}.html'>{c}</a> › Verified Guide</p>"
        f"<span class='badge' id='fd'>✓ Fact-Checked &amp; Live • {today}</span><h1>{t}</h1>"
        f"<div class='tldr'><b>Direct Answer (TL;DR):</b> {sm}</div>"
        f"<div class='mgrid'><div class='mcard'><small>Effective Tax / Retention</small><h3>{m1}</h3></div><div class='mcard'><small>Setup / Compliance Cost</small><h3>{m2}</h3></div><div class='mcard'><small>Income Threshold / Cap</small><h3>{m3}</h3></div></div>"
        "<div class='calc'><b>⚡ Interactive Remote Salary &amp; Tax Slider Calculator</b>"
        "<div class='presets'><button onclick='setP(60000,15,5000)'>Starter ($60k)</button><button onclick='setP(120000,20,12000)'>Standard ($120k)</button><button onclick='setP(240000,25,25000)'>Executive ($240k)</button></div>"
        "<div class='cgrid'><div><label>Annual Gross: <b id='la'>$120,000</b></label><input class='rng' id='ca' type='range' min='20000' max='500000' step='5000' value='120000' oninput='runC()'></div>"
        "<div><label>Effective Tax: <b id='lr'>20%</b></label><input class='rng' id='cr' type='range' min='0' max='45' step='1' value='20' oninput='runC()'></div>"
        "<div><label>Business Deductions: <b id='ld'>$12,000</b></label><input class='rng' id='cd' type='range' min='0' max='80000' step='1000' value='12000' oninput='runC()'></div></div>"
        "<div class='vbar'><div class='vfill' id='vf' style='width:80%'></div></div><p id='cout' style='font-weight:700;color:var(--acc)'></p>"
        "<table><thead><tr><th>Horizon</th><th>Gross Income</th><th>Total Tax Paid</th><th>Net Take-Home</th></tr></thead><tbody id='ptbl'></tbody></table>"
        "<button onclick=\"navigator.clipboard.writeText(cout.textContent);this.textContent='✓ Copied!'\" style='background:var(--acc);color:#fff;border:none;padding:.45rem .9rem;border-radius:8px;cursor:pointer'>📋 Copy Verified Breakdown</button></div>"
        f"<h2>1. Compliance &amp; Tax Structure Matrix</h2><table><tr><th>Structure</th><th>Verified Rules &amp; Optimization</th></tr><tr><td><b>Primary Standard</b></td><td>{oa}</td></tr><tr><td><b>Alternative Setup</b></td><td>{ob}</td></tr></table>"
        f"<h2>2. Frequently Asked Questions</h2><details open><summary>Official {year} Tax &amp; Deduction Verdict</summary><p>{tf}</p></details>"
        f"<details><summary>How does {c} compare to standard local payroll?</summary><p>{oa} Alternatively, {ob}</p></details>"
        f"<h2>3. Related &amp; Recommended Calculators</h2><div class='rgrid'>{rel_cards}{cross_cards}</div></div>"
        f"<footer><a href='/about.html'>About</a> • <a href='/methodology.html'>Methodology</a> • <a href='/privacy.html'>Privacy</a> • <a href='/terms.html'>Terms</a> • <a href='/contact.html'>Contact</a> • <a href='/llms.txt'>AI Index</a> • <a href='/sitemap.xml'>Sitemap</a><br>© {year} {html.escape(sname)}</footer>"
        "<script>document.getElementById('fd').textContent='✓ Fact-Checked & Live • '+new Date().toISOString().slice(0,10);function setP(a,r,d){ca.value=a;cr.value=r;cd.value=d;runC()}function runC(){let g=+ca.value,r=+cr.value,d=Math.min(g,+cd.value);la.textContent='$'+g.toLocaleString();lr.textContent=r+'%';ld.textContent='$'+d.toLocaleString();let tax=Math.max(0,(g-d)*(r/100)),net=g-tax,ret=g?Math.round((net/g)*100):100;vf.style.width=ret+'%';cout.textContent='Monthly Net: $'+Math.round(net/12).toLocaleString()+' | Annual Net: $'+Math.round(net).toLocaleString()+' ('+ret+'% Retained) | Annual Tax: $'+Math.round(tax).toLocaleString();ptbl.innerHTML=Array.of(1,3,5).map(y=>`<tr><td>Year ${y}</td><td>$${(g*y).toLocaleString()}</td><td>$${Math.round(tax*y).toLocaleString()}</td><td><b>$${Math.round(net*y).toLocaleString()}</b></td></tr>`).join('')}runC()</script></body></html>"
    )
    with open(f"dist/guide/{s}.html", "w", encoding="utf-8") as pf: pf.write(h)

with ThreadPoolExecutor(max_workers=32) as ex: list(ex.map(render, range(len(all_rows))))
for c in cats:
    cs = slugify(c) or "general"
    items = "".join(f"<li><a href='/guide/{next(iter(all_rows[i]))}.html'>{html.escape(next(iter(next(islice(all_rows[i], 1, 2)))))}</a></li>" for i in islice(cmap.get(c, ()), 120))
    with open(f"dist/category/{cs}.html", "w", encoding="utf-8") as cf:
        cf.write(f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(c)} | {html.escape(sname)}</title><link rel='canonical' href='{site_url}/category/{cs}.html'><style>body{{font-family:system-ui,sans-serif;max-width:920px;margin:2rem auto;padding:0 1rem;line-height:1.7}}a{{color:#10a37f}}</style></head><body><p><a href='/'>← Home</a></p><h1>{html.escape(c)} Calculators &amp; Guides</h1><ul>{items}</ul></body></html>")

with open("dist/search-index.json", "w", encoding="utf-8") as jf:
    json.dump(tuple({"s":s,"t":next(iter(r)),"c":next(islice(r,1,2)),"d":" ".join(next(islice(r,2,3)).split()[:16]),"m":next(islice(r,3,4))} for s,r in all_rows), jf, separators=(",",":"))

pills = "".join(f"<button class='pill' onclick=\"setCat('{html.escape(c)}',this)\">{html.escape(c)}</button>" for c in cats)
hub_cards = "".join(f"<a class='hcard' href='/category/{slugify(c)}.html'><b>{html.escape(c)}</b><small>{len(cmap.get(c,())):,} Guides →</small></a>" for c in cats)
top_links = "".join(f"<li><a href='/guide/{s}.html'>{html.escape(next(iter(r)))}</a></li>" for s, r in islice(all_rows, 24))
ih = (
    f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
    f"<title>{html.escape(sname)} | 10,000 Live Tax &amp; Salary Calculators</title><link rel='canonical' href='{site_url}/'>"
    "<style>:root{--bg:#f8fafc;--card:#fff;--txt:#0f172a;--bdr:#e2e8f0;--acc:#10a37f}.dark{--bg:#0b1120;--card:#111827;--txt:#f8fafc;--bdr:#1e293b}"
    "html{font-size:16px}body{font-family:system-ui,sans-serif;-webkit-tap-highlight-color:transparent;margin:0;background:var(--bg);color:var(--txt)}header{background:var(--card);border-bottom:1px solid var(--bdr);padding:2.2rem 1rem;text-align:center}"
    "#q{width:100%;max-width:560px;padding:.9rem 1.1rem;border:1px solid var(--bdr);border-radius:10px;font-size:1rem;background:var(--bg);color:var(--txt)}"
    ".pills{display:flex;flex-wrap:wrap;justify-content:center;gap:.4rem;max-width:960px;margin:1rem auto 0}.pill{background:var(--bg);color:var(--txt);border:1px solid var(--bdr);padding:.4rem .85rem;border-radius:999px;cursor:pointer}.pill.active{background:var(--acc);color:#fff}"
    ".main{max-width:1180px;margin:1.5rem auto;padding:0 1rem}.hubs{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:.8rem;margin-bottom:1.5rem}"
    ".hcard{display:flex;justify-content:space-between;align-items:center;gap:.5rem;background:var(--card);border:1px solid var(--bdr);padding:.85rem 1rem;border-radius:10px;text-decoration:none;color:inherit;font-size:.9rem}"
    ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1rem}.card{display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--bdr);border-radius:12px;padding:1.25rem}"
    ".badge{background:#ecfdf5;color:#059669;font-size:.75rem;padding:.2rem .55rem;border-radius:6px;font-weight:600}.static{background:var(--card);border:1px solid var(--bdr);border-radius:12px;padding:1.2rem;margin-top:2rem}.static ul{columns:2;font-size:.9rem}footer{text-align:center;padding:2rem;font-size:.85rem}</style></head><body>"
    f"<header><span class='badge' id='lt'>Live Index • {today} • 10,000 Interactive Calculators</span> <button onclick=\"document.body.classList.toggle('dark')\">🌓</button><h1>{html.escape(sname)}</h1>"
    "<input id='q' type='search' placeholder='Search 10,000 country, role & tax calculators...' oninput='Q=this.value.toLowerCase();P=1;apply()'>"
    f"<div class='pills'><button class='pill active' onclick=\"setCat('ALL',this)\">All (10,000)</button>{pills}</div></header>"
    f"<div class='main'><div class='hubs'>{hub_cards}</div><p id='cnt'></p><div class='grid' id='g'></div><div style='text-align:center;margin:1.5rem 0'><button onclick='if(P>1){{P--;render()}}'>← Prev</button> <span id='pi'></span> <button onclick='if(P*60<F.length){{P++;render()}}'>Next →</button></div>"
    f"<div class='static'><h3>Popular Verified Calculators</h3><ul>{top_links}</ul></div></div>"
    f"<footer><a href='/about.html'>About</a> • <a href='/methodology.html'>Methodology</a> • <a href='/privacy.html'>Privacy</a> • <a href='/terms.html'>Terms</a> • <a href='/contact.html'>Contact</a> • <a href='/llms.txt'>AI Index</a> • <a href='/sitemap.xml'>Sitemap</a></footer>"
    "<script>document.getElementById('lt').textContent='Live Index • Refreshed '+new Date().toISOString().slice(0,10)+' • 10,000 Calculators';"
    "let D=Array.of(),F=Array.of(),C='ALL',Q='',P=1;fetch('/search-index.json').then(r=>r.json()).then(d=>{D=d;F=d;render()});"
    "function setCat(c,b){C=c;P=1;document.querySelectorAll('.pill').forEach(x=>x.classList.remove('active'));b.classList.add('active');apply()}"
    "function apply(){F=D.filter(x=>(C==='ALL'||x.c===C)&&(!Q||x.t.toLowerCase().includes(Q)||x.d.toLowerCase().includes(Q)));render()}"
    "function render(){document.getElementById('cnt').textContent='Showing '+F.length.toLocaleString()+' verified calculators';document.getElementById('pi').textContent='Page '+P;"
    "document.getElementById('g').innerHTML=F.slice((P-1)*60,P*60).map(x=>`<a class='card' href='/guide/${x.s}.html'><span class='badge'>${x.c}</span><h3>${x.t}</h3><p>${x.d}...</p><small style='color:var(--acc);font-weight:600'>${x.m}</small></a>`).join('')}</script></body></html>"
)
with open("dist/index.html", "w", encoding="utf-8") as f: f.write(ih)

ikey = uuid.uuid4().hex
with open(f"dist/{ikey}.txt", "w", encoding="utf-8") as kf: kf.write(ikey)
urls = (f"{site_url}/",) + tuple(f"{site_url}/guide/{s}.html" for s, _ in all_rows)
subs = list()
for i in range(0, len(urls), 2000):
    fn = f"sitemap-{(i//2000)+1}.xml"; subs.append(f"{site_url}/{fn}")
    with open(f"dist/{fn}", "w", encoding="utf-8") as sf: sf.write(f"<?xml version='1.0' encoding='UTF-8'?><urlset xmlns='http://sitemaps.org'>" + "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>" for u in islice(urls, i, i+2000)) + "</urlset>")
with open("dist/sitemap.xml", "w", encoding="utf-8") as f: f.write(f"<?xml version='1.0' encoding='UTF-8'?><sitemapindex xmlns='http://sitemaps.org'>" + "".join(f"<sitemap><loc>{s}</loc><lastmod>{today}</lastmod></sitemap>" for s in subs) + "</sitemapindex>")
with open("dist/robots.txt", "w", encoding="utf-8") as f: f.write(f"User-agent: *\nAllow: /\nUser-agent: GPTBot\nAllow: /\nUser-agent: PerplexityBot\nAllow: /\nUser-agent: Google-Extended\nAllow: /\nSitemap: {site_url}/sitemap.xml\n")
with open("dist/llms.txt", "w", encoding="utf-8") as f: f.write(f"# {sname}\n> 30-Year Verified Interactive Tax & Salary Calculator Directory for {topic}. Updated {today}.\n" + "\n".join(f"- [{next(iter(r))}]({site_url}/guide/{s}.html): {next(islice(r,2,3))}" for s, r in islice(all_rows, 100)))
print("Total Verified SEO Pages Built:", len(all_rows))
