name: Cloud-to-Cloud SEO Empire Factory

on:
  workflow_dispatch:
    inputs:
      kingdom_name:
        description: 'Exact Subdomain (e.g. global-airport-transfers-atlas)'
        required: true
      kingdom_topic:
        description: 'Empire Niche & Detailed Instructions'
        required: true

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Factory
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Gemini SDK & Netlify CLI
        run: |
          pip install google-genai pydantic
          npm install -g netlify-cli

      - name: Lock Exact Subdomain & Clean Empty Sites on Netlify
        id: lock_domain
        env:
          NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
          KINGDOM_NAME: ${{ github.event.inputs.kingdom_name }}
        run: |
          python3 -c '
          import os, json, subprocess
          name = os.environ["KINGDOM_NAME"].strip().lower()
          sites = json.loads(subprocess.check_output(["netlify", "api", "listSites"]))
          for s in sites:
              if not s.get("published_deploy") and s.get("name") != name:
                  try:
                      subprocess.check_output(["netlify", "api", "deleteSite", "--data", json.dumps({"site_id": s["id"]})])
                      print("🧹 Deleted empty draft site:", s.get("name"))
                  except Exception:
                      pass
          existing = next((s for s in sites if s.get("name") == name), None)
          if existing:
              site_id = existing["id"]
          else:
              created = json.loads(subprocess.check_output(["netlify", "api", "createSite", "--data", json.dumps({"body": {"name": name}})]))
              site_id = created["id"]
          site_url = f"https://{name}.netlify.app"
          with open(os.environ["GITHUB_OUTPUT"], "a") as f:
              f.write(f"site_id={site_id}\n")
              f.write(f"site_url={site_url}\n")
          print("🔒 Locked Exact Subdomain:", site_url)
          '

      - name: Build Full SEO Directory, Pages, Sitemap & Canonical Tags
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          SITE_URL: ${{ steps.lock_domain.outputs.site_url }}
          KINGDOM_TOPIC: ${{ github.event.inputs.kingdom_topic }}
        run: python build.py

      - name: Deploy Production Empire to Locked Subdomain
        env:
          NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
        run: netlify deploy --prod --dir=dist --site="${{ steps.lock_domain.outputs.site_id }}"
