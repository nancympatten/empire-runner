import os
import csv
import json
from google import genai
from google.genai import types
from pydantic import BaseModel

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
kingdom_name = os.environ["KINGDOM_NAME"]
kingdom_topic = os.environ["KINGDOM_TOPIC"]

class DirectoryItem(BaseModel):
    title: str
    category: str
    summary: str
    tag: str

class EmpireData(BaseModel):
    site_title: str
    tagline: str
    items: list[DirectoryItem]

prompt = f"""
Create a complete, high-value directory dataset for '{kingdom_name}'.
Topic & Instructions: {kingdom_topic}
Generate 30 rich, accurate, well-categorized entries.
"""

response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=EmpireData,
        temperature=0.3,
    ),
)

data = json.loads(response.text)

# 1. Save data.csv in cloud
with open("data.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Title", "Category", "Summary", "Tag"])
    for item in data["items"]:
        writer.writerow([item["title"], item["category"], item["summary"], item["tag"]])

# 2. Build fast, responsive dist/index.html
os.makedirs("dist", exist_ok=True)
cards_html = "".join(
    f"<div class='card'><span class='badge'>{i['category']}</span><h3>{i['title']}</h3><p>{i['summary']}</p><small>{i['tag']}</small></div>"
    for i in data["items"]
)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{data['site_title']}</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0f172a;color:#f8fafc;margin:0;padding:2rem}}
header{{text-align:center;max-width:800px;margin:0 auto 2rem}}
h1{{font-size:2.2rem;color:#38bdf8;margin-bottom:.5rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1.2rem;max-width:1200px;margin:0 auto}}
.card{{background:#1e293b;padding:1.4rem;border-radius:12px;border:1px solid #334155}}
.badge{{background:#0284c7;color:#fff;padding:.2rem .6rem;border-radius:999px;font-size:.75rem}}
</style>
</head>
<body>
<header><h1>{data['site_title']}</h1><p>{data['tagline']}</p></header>
<div class="grid">{cards_html}</div>
</body>
</html>"""

with open("dist/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ {kingdom_name} built successfully in cloud!")
