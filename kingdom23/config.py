from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SITE_URL = "https://global-travel-esim-atlas.pages.dev"
PROJECT_NAME = "global-travel-esim-atlas"
STAGE = ROOT / "dist.staging-quality"
OUTPUT = ROOT / "dist"
SITEMAP_SHARD_LIMIT = 2000
LANGUAGE = "en"
