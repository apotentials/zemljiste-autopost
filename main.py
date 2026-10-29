"""Zemljište.hr – dnevna automatizacija objava.

Svaki dan objavi JEDNU stvar prema tjednom rasporedu (config.WEEKLY_PLAN):
  Pon/Čet/Sub  listing           novi oglas → Reel (fotke + AI glas)
  Uto/Ned      blog              članak → slika 4:5 s naslovom
  Sri          feature_carousel  alat/besplatna ponuda → karusel "korak po korak"
  Pet          feature_reel      isti alat → Reel sa snimkama ekrana i AI glasom
Uz svaku objavu stigne e-mail s tekstom za Google Business i LinkedIn.

Primjeri:
  python main.py                                # današnja objava po rasporedu
  DRY_RUN=true python main.py --type blog       # test bez objave
  python main.py --type feature_reel --feature kalkulator-kig-kis
  python main.py --type listing --slug 506762-matulji-...
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import config
import media
import sources
from ai_text import generate
from capture import capture_feature
from features import FEATURES, by_slug
from meta_publish import publish_carousel, publish_image, publish_video
from notify import send_package

TZ = ZoneInfo("Europe/Zagreb")


# ---------------------------------------------------------------------------
# Stanje (što je već objavljeno) – sprema se u repozitorij
# ---------------------------------------------------------------------------
def load_state() -> dict:
    state = {"listings": [], "blog_history": [], "feature_index": 0, "log": []}
    if config.STATE_FILE.exists():
        state.update(json.loads(config.STATE_FILE.read_text(encoding="utf-8")))
    return state


def save_state(state: dict) -> None:
    state["log"] = state["log"][-200:]
    config.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def workdir(name: str):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:50]
    path = config.OUT_DIR / f"{datetime.now(TZ):%Y%m%d}-{slug}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_texts(work, texts: dict) -> None:
    for k, v in texts.items():
        (work / f"{k}.txt").write_text(v, encoding="utf-8")


def publish(fn, *args) -> dict:
    if config.DRY_RUN:
        print("  · DRY_RUN – objava preskočena")
        return {"dry_run": True}
    return fn(*args)


# ---------------------------------------------------------------------------
# Vrste objava
# ---------------------------------------------------------------------------
def run_listing(state: dict, slug: str | None) -> dict:
    if slug:
        row = {"slug": slug}
    else:
        row = sources.pick_listing(set(state["listings"]))
        if not row:
            raise RuntimeError("Nema novih oglasa s dovoljno slika.")
    listing = sources.build_listing(row)
    print(f"Oglas: {listing.title} | {listing.location} | {listing.price}")
    work = workdir(listing.title)

    images = sources.download_images(listing.images, work / "images")
    if len(images) < 2:
        raise RuntimeError("Premalo dostupnih slika za video.")
    texts = generate("listing", listing.to_dict(), listing.url)
    save_texts(work, texts)

    audio = media.tts(texts["reels_script"], work / "voice.mp3")
    info = " · ".join(x for x in (listing.location.split(",")[0], listing.area, listing.price) if x)
    video = media.listing_video(images, audio, listing.title, info, work / "reel.mp4")

    result = publish(publish_video, video, texts["caption"])
    send_package(f"Zemljište.hr · oglas · {listing.title[:60]}", texts, listing.url, images[0])
    if not config.DRY_RUN:
        state["listings"].append(row["slug"])
    return {"type": "listing", "url": listing.url, **result}


def run_blog(state: dict, url: str | None) -> dict:
    url = url or sources.pick_blog(state["blog_history"])
    post = sources.parse_blog(url)
    print(f"Blog: {post.title}")
    work = workdir(post.title)

    texts = generate("blog", post.to_dict(), url)
    save_texts(work, texts)
    card = media.blog_card(post.title, texts.get("card_subtitle", post.summary), work / "blog_card.jpg")

    result = publish(publish_image, card, texts["caption"])
    send_package(f"Zemljište.hr · blog · {post.title[:60]}", texts, url, card)
    if not config.DRY_RUN:
        state["blog_history"].append(url)
    return {"type": "blog", "url": url, **result}


def run_feature(state: dict, as_reel: bool, slug: str | None) -> dict:
    feature = by_slug(slug) if slug else FEATURES[state["feature_index"] % len(FEATURES)]
    url = config.SITE_URL + feature.path
    print(f"Feature: {feature.name} ({'reel' if as_reel else 'karusel'})")
    work = workdir(f"{feature.slug}-{'reel' if as_reel else 'karusel'}")

    shots = capture_feature(feature, work / "screens")
    data = {"naziv": feature.name, "vrsta": feature.kind, "činjenice": feature.facts,
            "koraci": [s.caption for s in feature.steps]}
    texts = generate("feature", data, url)
    save_texts(work, texts)
    hook = texts.get("hook") or feature.name

    if as_reel:
        video = media.tutorial_reel(feature, shots, hook,
                                    texts.get("intro_voice", hook),
                                    texts.get("outro_voice", "Isprobajte besplatno na zemljište točka ha-er."),
                                    work)
        result = publish(publish_video, video, texts["caption"])
        attachment = None
    else:
        slides = media.tutorial_carousel(feature, shots, hook, work / "slides")
        result = publish(publish_carousel, slides, texts["caption"])
        attachment = slides[0]

    send_package(f"Zemljište.hr · {feature.kind} · {feature.name}", texts, url,
                 attachment or (work / "slides" / "slide_00.jpg"))
    # Nakon Reela (petak) prelazimo na sljedeći alat
    if as_reel and not slug and not config.DRY_RUN:
        state["feature_index"] += 1
    return {"type": "feature", "feature": feature.slug, "url": url, **result}


# ---------------------------------------------------------------------------
def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--type", choices=["listing", "blog", "feature_carousel", "feature_reel"])
    p.add_argument("--slug", help="slug oglasa (za --type listing)")
    p.add_argument("--url", help="URL blog članka (za --type blog)")
    p.add_argument("--feature", help=f"jedan od: {', '.join(f.slug for f in FEATURES)}")
    args = p.parse_args()

    kind = args.type or config.WEEKLY_PLAN[datetime.now(TZ).weekday()]
    print(f"=== {datetime.now(TZ):%A %d.%m.%Y} · {kind} ===")
    state = load_state()

    try:
        if kind == "listing":
            result = run_listing(state, args.slug)
        elif kind == "blog":
            result = run_blog(state, args.url)
        else:
            result = run_feature(state, kind == "feature_reel", args.feature)
    except Exception as e:
        print(f"GREŠKA: {e}", file=sys.stderr)
        return 1

    result["date"] = datetime.now(timezone.utc).isoformat()
    print("Rezultat:", result)
    if not config.DRY_RUN:
        if not ({"facebook", "instagram"} & result.keys()):
            print("Ništa nije objavljeno – stanje se ne sprema (sutra pokušava ponovno).", file=sys.stderr)
            return 1
        state["log"].append(result)
        save_state(state)
    return 1 if result.get("errors") else 0


if __name__ == "__main__":
    sys.exit(main())
