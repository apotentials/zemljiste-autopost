"""Centralna konfiguracija. Vrijednosti dolaze iz .env (lokalno) ili GitHub Secrets."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
OUT_DIR = BASE_DIR / "out"
STATE_FILE = BASE_DIR / "state" / "state.json"


def env(name: str, default: str = "") -> str:
    return os.getenv(name) or default


def require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Nedostaje varijabla okruženja: {name}")
    return value


# --- Sajt -----------------------------------------------------------------
SITE_URL = env("SITE_URL", "https://www.xn--zemljite-bxb.hr")  # = www.zemljište.hr
PUBLIC_DOMAIN = "zemljište.hr"                                   # za prikaz u tekstovima
SEO_PARAM = "__seo=1"  # tjera Cloudflare middleware da vrati pun HTML (seo-render)

# Supabase anon ključ je javan (nalazi se u JS-u sajta) i čita samo public_listings.
SUPABASE_URL = env("SUPABASE_URL", "https://hyomxftxxcndnpmmaxxy.supabase.co")
SUPABASE_ANON_KEY = env(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh5b214ZnR4eGNuZG5wbW1heHh5Iiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3NzQwMTc3MDAsImV4cCI6MjA4OTU5MzcwMH0.bhkXMoDlQ89LZgnYeXKaK4ACKvMi6mLfbAcY9qKAsnE",
)
LISTING_LOOKBACK_DAYS = int(env("LISTING_LOOKBACK_DAYS", "21"))
MAX_IMAGES = int(env("MAX_IMAGES", "8"))

# --- Gemini ---------------------------------------------------------------
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-2.5-flash")

# --- Glas i video ---------------------------------------------------------
TTS_VOICE = env("TTS_VOICE", "hr-HR-SreckoNeural")  # ženski: hr-HR-GabrijelaNeural
TTS_RATE = env("TTS_RATE", "+5%")
FONT_PATH = env("FONT_PATH")

# --- Meta Graph API -------------------------------------------------------
GRAPH_VERSION = env("GRAPH_VERSION", "v23.0")
META_PAGE_ID = env("META_PAGE_ID")
META_PAGE_TOKEN = env("META_PAGE_TOKEN")
IG_USER_ID = env("IG_USER_ID")

# --- E-mail s paketom za Google Business + LinkedIn (opcionalno) ------------
SMTP_USER = env("SMTP_USER")            # npr. tvoj@gmail.com
SMTP_PASSWORD = env("SMTP_PASSWORD")    # Gmail "App password" (ne obična lozinka)
NOTIFY_TO = env("NOTIFY_TO", SMTP_USER)

# --- Ponašanje ------------------------------------------------------------
DRY_RUN = env("DRY_RUN", "false").lower() == "true"
PUBLISH_FACEBOOK = env("PUBLISH_FACEBOOK", "true").lower() == "true"
PUBLISH_INSTAGRAM = env("PUBLISH_INSTAGRAM", "true").lower() == "true"

# Tjedni raspored (0 = ponedjeljak). Vrste: listing, blog, feature_carousel, feature_reel
WEEKLY_PLAN = {
    0: "listing",
    1: "blog",
    2: "feature_carousel",
    3: "listing",
    4: "feature_reel",
    5: "listing",
    6: "blog",
}
