# Global Travel eSIM Atlas — Kingdom 23

Independent static programmatic SEO project.

## Identity
- Project: `global-travel-esim-atlas`
- Canonical origin: `https://global-travel-esim-atlas.pages.dev`
- Language: English
- Build output: `dist.staging-quality`
- Production output: `dist`

## Data files
- `data/destinations.csv`: destination and country metadata
- `data/providers.csv`: eSIM provider identity and official links
- `data/plan_observations.csv`: dated plan observations
- `data/source_registry.csv`: source provenance and verification
- `data/page_topics.csv`: approved page topics and relationships

## Evidence policy
- Never invent provider prices, data allowances, validity, coverage, speeds,
  supported networks, hotspot rules, or activation conditions.
- Record observation dates and official source URLs.
- Distinguish verified facts, secondary references, and user-entered assumptions.
- Treat plan prices and availability as time-sensitive observations, not guarantees.
- Calculators must clearly identify user-entered inputs and disclose limitations.
- Do not claim rankings, indexing, revenue, or provider endorsement.

## Build and deployment safety
- Build and audit locally before any deployment.
- Keep all build logic and output inside this project directory.
- Sitemap index: `sitemap.xml`; child shards: `sitemap-1.xml`, etc.
- Maximum 2,000 URLs per sitemap shard.
- Include `lastmod` for sitemap and URL entries.
- Deployment requires a separate explicit manual approval.
- Never modify or deploy Kingdom 21 or Kingdom 22 from this project.
