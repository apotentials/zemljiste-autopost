"""1. IZVORI SADRŽAJA: oglasi (Supabase + BeautifulSoup) i blog (sitemap + BeautifulSoup)."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import config

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; ZemljisteAutopost/1.0)",
    "Accept-Language": "hr-HR,hr;q=0.9",
})


def fetch_html(url: str) -> BeautifulSoup:
    """Zemljište.hr je React (CSR) – s ?__seo=1 dobijemo pun HTML koji BeautifulSoup može čitati."""
    full = url + ("&" if "?" in url else "?") + config.SEO_PARAM
    r = SESSION.get(full, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")


def json_ld(soup: BeautifulSoup, type_name: str) -> dict:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for obj in data if isinstance(data, list) else [data]:
            if isinstance(obj, dict) and obj.get("@type") == type_name:
                return obj
    return {}


def fmt_price(value) -> str:
    try:
        return f"{float(value):,.0f} €".replace(",", ".")
    except (TypeError, ValueError):
        return ""


def fmt_area(value) -> str:
    try:
        return f"{float(value):,.0f} m²".replace(",", ".")
    except (TypeError, ValueError):
        return ""


# ===========================================================================
# OGLASI
# ===========================================================================
@dataclass
class Listing:
    url: str
    title: str = ""
    category: str = ""
    location: str = ""
    price: str = ""
    area: str = ""
    description: str = ""
    facts: dict = field(default_factory=dict)  # dozvole, KIG, pogled na more...
    images: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def pick_listing(already_posted: set[str]) -> dict | None:
    """Odabir oglasa iz Supabase public_listings: novi (zadnjih N dana), s barem 3 slike,
    s cijenom, sortirano po quality_score pa datumu. Vraća sirovi red iz baze."""
    since = (datetime.now(timezone.utc) - timedelta(days=config.LISTING_LOOKBACK_DAYS)).isoformat()
    r = SESSION.get(
        f"{config.SUPABASE_URL}/rest/v1/public_listings",
        headers={"apikey": config.SUPABASE_ANON_KEY, "Authorization": f"Bearer {config.SUPABASE_ANON_KEY}"},
        params={
            "select": "*",
            "status": "eq.approved",
            "price_on_request": "eq.false",
            "created_at": f"gte.{since}",
            "order": "quality_score.desc.nullslast,created_at.desc",
            "limit": "200",
        },
        timeout=30,
    )
    r.raise_for_status()
    for row in r.json():
        if row["slug"] in already_posted or len(row.get("images") or []) < 3:
            continue
        return row
    return None


def build_listing(row: dict) -> Listing:
    """Spoji podatke iz baze s onim što BeautifulSoup pročita na stranici oglasa."""
    url = f"{config.SITE_URL}/oglasi/{row['slug']}"
    listing = Listing(
        url=url,
        title=row.get("title", ""),
        category=row.get("category") or "",
        location=", ".join(x for x in (row.get("city"), row.get("county")) if x),
        price=fmt_price(row.get("price")),
        area=fmt_area(row.get("area_m2")),
        description=row.get("description") or "",
        images=[i for i in (row.get("images") or []) if isinstance(i, str)][: config.MAX_IMAGES],
    )
    # Samo činjenice koje stvarno postoje u bazi (AI ih ne smije izmišljati)
    fact_fields = {
        "building_permit": "građevinska dozvola", "location_permit": "lokacijska dozvola",
        "has_building_permit_detected": "građevinska dozvola (iz opisa)",
        "sea_view_detected": "pogled na more (iz opisa)", "kig": "KIG", "kis": "KIS",
        "infrastructure_electricity": "struja", "infrastructure_water": "voda",
        "infrastructure_road": "pristupni put", "terrain": "teren",
    }
    listing.facts = {label: row[k] for k, label in fact_fields.items() if row.get(k) not in (None, False, "")}

    # BeautifulSoup: provjera s javne stranice (i rezervni izvor ako baza nešto nema)
    try:
        soup = fetch_html(url)
        ld = json_ld(soup, "RealEstateListing")
        listing.title = listing.title or ld.get("name", "")
        listing.price = listing.price or fmt_price(ld.get("price"))
        if not listing.images and ld.get("image"):
            listing.images = ld["image"][: config.MAX_IMAGES]
        opis = soup.find("h2", string=re.compile("Opis"))
        if opis and not listing.description:
            listing.description = "\n".join(p.get_text("\n") for p in opis.find_next_siblings("p"))
    except requests.RequestException as e:
        print(f"  ! stranica oglasa nedostupna, koristim samo bazu: {e}")

    listing.description = listing.description[:2500]
    return listing


def download_images(urls: list[str], dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, u in enumerate(urls):
        try:
            r = SESSION.get(u, timeout=30)
            r.raise_for_status()
            if r.headers.get("Content-Type", "").startswith("image"):
                p = dest / f"img_{i:02d}.jpg"
                p.write_bytes(r.content)
                paths.append(p)
        except requests.RequestException as e:
            print(f"  ! slika preskočena: {e}")
    return paths


# ===========================================================================
# BLOG
# ===========================================================================
@dataclass
class BlogPost:
    url: str
    title: str = ""
    summary: str = ""
    body: str = ""
    faq: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def blog_urls() -> list[str]:
    r = SESSION.get(f"{config.SITE_URL}/sitemap-main.xml", timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "xml")
    return [loc.text.strip() for loc in soup.find_all("loc") if "/blog/" in loc.text]


def pick_blog(history: list[str]) -> str:
    """Rotacija: prvo članci koji nikad nisu objavljeni, zatim onaj objavljen najdavnije."""
    urls = blog_urls()
    never = [u for u in urls if u not in history]
    if never:
        return never[0]
    return min(urls, key=lambda u: max(i for i, h in enumerate(history) if h == u))


def parse_blog(url: str) -> BlogPost:
    soup = fetch_html(url)
    article = json_ld(soup, "Article")
    faq = json_ld(soup, "FAQPage")
    main = soup.find("main") or soup.body
    post = BlogPost(
        url=url,
        title=article.get("headline") or (soup.h1.get_text(strip=True) if soup.h1 else ""),
        summary=article.get("description", ""),
        body=main.get_text("\n", strip=True)[:6000] if main else "",
        faq=[{"q": q.get("name"), "a": q.get("acceptedAnswer", {}).get("text")}
             for q in faq.get("mainEntity", [])][:5],
    )
    return post
