import csv, html, re
from pathlib import Path
from urllib.parse import urljoin

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'corridors.csv'
STAGE=ROOT/'dist.staging-quality'
SITE='https://global-remittance-fees-atlas.pages.dev/'
AMOUNTS=[25,50,100,200,300,500,750,1000,1500,2000,3000,5000,7500,10000,15000,20000,25000,50000,75000,100000]
SEND=['bank-funded','card-funded','cash-funded','mobile-wallet-funded','other-funding']
PAYOUT=['bank-account','cash-pickup','mobile-wallet','cash-payout','other-payout']

with DATA.open(encoding='utf-8-sig',newline='') as f:
    corridors=list(csv.DictReader(f))
if len(corridors)!=20:
    raise SystemExit('STOP: expected exactly 20 corridors')
for r in corridors:
    for k in ('slug','origin_country','destination_country','origin_currency','destination_currency'):
        if not r.get(k,'').strip():
            raise SystemExit('STOP: missing '+k)
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',r['slug']):
        raise SystemExit('STOP: invalid corridor slug')
if STAGE.exists():
    raise SystemExit('STOP: quality staging already exists; inspect before replacing')

def esc(x):
    return html.escape(str(x or ''),quote=True)

count=0
urls=[SITE]
STAGE.mkdir()
for r in corridors:
    for amount in AMOUNTS:
        for send in SEND:
            for payout in PAYOUT:
                slug=f"{r['slug']}-{amount}-{send}-to-{payout}"
                title=f"{amount:,} {r['origin_currency']} transfer from {r['origin_country']} to {r['destination_country']} via {send} to {payout}"
                canonical=urljoin(SITE,slug+'/')
                method_note=f"Funding category: {send}. Payout category: {payout}. Actual availability is not verified."
                body=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="Calculate the recipient amount and total cost of a {amount:,} {esc(r['origin_currency'])} remittance from {esc(r['origin_country'])} to {esc(r['destination_country'])}. Interactive fee and exchange rate worksheet. Funding: {esc(send)}. Payout: {esc(payout)}.">
<link rel="canonical" href="{esc(canonical)}">
<style>body{{font-family:system-ui,sans-serif;max-width:850px;margin:auto;padding:20px;line-height:1.6}}input{{padding:9px;max-width:220px}}label{{display:block;margin:12px 0}}.box{{border:1px solid #aaa;border-radius:10px;padding:15px;margin:16px 0}}button{{padding:10px 16px}}dt{{font-weight:bold}}dd{{margin-bottom:8px}}</style></head>
<body><main><h1>{esc(title)}</h1>
<p>This interactive worksheet estimates transfer costs using figures you enter. It is not a provider quote or a claim that a particular payment method is available on this route.</p>
<div class="box"><h2>Scenario</h2><dl>
<dt>Sending amount</dt><dd>{amount:,} {esc(r['origin_currency'])}</dd>
<dt>Origin</dt><dd>{esc(r['origin_country'])}</dd>
<dt>Destination</dt><dd>{esc(r['destination_country'])}</dd>
<dt>Recipient currency</dt><dd>{esc(r['destination_currency'])}</dd>
<dt>Funding category</dt><dd>{esc(send)}</dd>
<dt>Payout category</dt><dd>{esc(payout)}</dd></dl><p>{esc(method_note)}</p></div>
<div class="box"><h2>Calculate your transfer</h2>
<label>Transfer fee ({esc(r['origin_currency'])}): <input id="fee" type="number" min="0" step="any" value="0"></label>
<label>Additional sender charges ({esc(r['origin_currency'])}): <input id="extra" type="number" min="0" step="any" value="0"></label>
<label>Exchange rate (recipient currency per 1 {esc(r['origin_currency'])}): <input id="rate" type="number" min="0" step="any" placeholder="Enter quoted rate"></label>
<label>Reference rate (optional): <input id="ref" type="number" min="0" step="any" placeholder="Enter reference rate"></label>
<button type="button" onclick="calc()">Calculate</button><div id="result" aria-live="polite"><p>Enter a quoted exchange rate to calculate.</p></div></div>
<h2>How the calculation works</h2>
<ul><li>Sender cost = transfer amount + transfer fee + additional sender charges.</li>
<li>Recipient amount estimate = transfer amount × quoted exchange rate.</li>
<li>Effective rate = estimated recipient amount ÷ total sender cost.</li>
<li>Estimated exchange-rate difference, when a reference rate is supplied, compares the entered rate with the reference. It is an estimate, not a provider disclosure.</li></ul>
<p>These formulas assume fees are paid separately and the entire transfer amount is converted. If a provider deducts fees from the transfer principal, adjust the amount or calculation to reflect that quote.</p>
<h2>How to compare offers</h2><p>Compare quotes for the same principal, funding category, payout category and recipient currency. Include additional charges and check whether fees are paid separately or deducted from the amount. Delivery time, eligibility, limits and provider availability must be verified directly.</p>
<h2>Scenario limitations</h2><p>This page does not contain verified provider pricing, live exchange rates or confirmed method availability. The scenario is a calculation worksheet. Currency conversion and fees vary by provider, customer, payment method and date.</p>
<p><a href="../">Atlas directory</a></p></main>
<script>
function calc(){{
 const a={amount},f=Number(document.getElementById('fee').value),e=Number(document.getElementById('extra').value),r=Number(document.getElementById('rate').value),v=Number(document.getElementById('ref').value);
 const out=document.getElementById('result');
 if(!Number.isFinite(f)||!Number.isFinite(e)||!Number.isFinite(r)||f<0||e<0||r<=0){{out.innerHTML='<p>Please enter valid non-negative fees and a positive exchange rate.</p>';return;}}
 const received=a*r,cost=a+f+e,eff=received/cost;
 let s='<p><b>Estimated recipient amount:</b> '+received.toLocaleString(undefined,{{maximumFractionDigits:6}})+' {esc(r["destination_currency"])}</p><p><b>Total sender cost:</b> '+cost.toLocaleString(undefined,{{maximumFractionDigits:6}})+' {esc(r["origin_currency"])}</p><p><b>Effective rate:</b> '+eff.toLocaleString(undefined,{{maximumFractionDigits:8}})+' {esc(r["destination_currency"])} per {esc(r["origin_currency"])}</p>';
 if(v>0&&Number.isFinite(v)){{s+='<p><b>Estimated rate difference:</b> '+((v-r)/v*100).toFixed(4)+'% versus entered reference rate (positive means the quoted rate is lower).</p>';}}
 out.innerHTML=s;
}}
</script></body></html>'''
                folder=STAGE/slug
                folder.mkdir()
                (folder/'index.html').write_text(body,encoding='utf-8')
                urls.append(canonical)
                count+=1
                if count % 1000 == 0:
                    print(f"PROGRESS {count//100}% ({count}/10000) - Calculator pages generated", flush=True)

index=(
'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Global Remittance Fees Atlas</title><meta name="description" content="Browse remittance calculation worksheets by corridor and amount."><style>body{font-family:system-ui,sans-serif;max-width:1000px;margin:auto;padding:20px;line-height:1.6}section{border:1px solid #bbb;border-radius:10px;padding:15px;margin:18px 0}</style></head><body><main><h1>Global Remittance Fees Atlas</h1><p>Browse international remittance worksheets. These are calculators, not verified provider offers.</p><h2>Corridors</h2>'''
+ ''.join("<section><h2>"+esc(r["origin_country"])+" to "+esc(r["destination_country"])+"</h2><p>"+esc(r["origin_currency"])+" to "+esc(r["destination_currency"])+"</p><ul>"+"".join("<li><a href=\""+esc(r["slug"])+"-"+str(v)+"-bank-funded-to-bank-account/\">"+format(v,",")+" worksheet</a></li>" for v in [200,500,1000,2000,5000])+"</ul></section>" for r in corridors)
+ '''<h2>How to use</h2><p>Enter fees and exchange rates from independently verified quotes. Confirm provider availability and charges directly.</p><section><h2>SEO verification readiness</h2><p>Verification status: <strong>PENDING</strong>. No ownership verification or submission has been performed.</p><ul><li><a href="https://search.google.com/search-console" target="_blank" rel="noopener">Google Search Console</a> — verify site ownership and inspect indexing.</li><li><a href="https://www.bing.com/webmasters" target="_blank" rel="noopener">Bing Webmaster Tools</a> — verify site ownership and inspect crawling.</li></ul><p>Sitemap: <a href="sitemap.xml">sitemap.xml</a></p><p>Crawl rules: <a href="robots.txt">robots.txt</a></p><p>After verification, submit the sitemap manually and monitor indexing reports. Submission does not guarantee indexing.</p></section></main></body></html>'''
)

(STAGE/'index.html').write_text(index,encoding='utf-8')
xml='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+esc(u)+'</loc></url>' for u in urls)+'</urlset>'
(STAGE/'sitemap.xml').write_text(xml,encoding='utf-8')
(STAGE/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+SITE+'sitemap.xml\n',encoding='utf-8')

if count!=10000:
    raise SystemExit('STOP: unexpected page count')
print('QUALITY STAGING GENERATED:',count)
print('TOTAL HTML:',count+1)
print('PATH:',STAGE)
print('Interactive calculator: included')
print('Existing dist and prior staging preserved; no deployment.')
