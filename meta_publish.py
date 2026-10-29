"""4. OBJAVA: Facebook stranica + Instagram Business preko službenog Meta Graph API-ja (besplatno).

Dozvole tokena: pages_show_list, pages_read_engagement, pages_manage_posts,
instagram_basic, instagram_content_publish.

Instagram traži javni URL slike. Da ne trebamo hosting, sliku prvo uploadamo na Facebook
stranicu kao neobjavljenu i Instagramu damo njezin Facebook CDN link.
Video (Reel) ide "resumable" uploadom izravno s diska.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests

import config

GRAPH = f"https://graph.facebook.com/{config.GRAPH_VERSION}"
GRAPH_VIDEO = f"https://graph-video.facebook.com/{config.GRAPH_VERSION}"


def _token() -> str:
    return config.META_PAGE_TOKEN


def _check(r: requests.Response) -> dict:
    data = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in data:
        raise RuntimeError(f"Meta API {r.status_code}: {data.get('error', data)}")
    return data


# ===========================================================================
# FACEBOOK
# ===========================================================================
def fb_upload_photo(path: Path, message: str = "", published: bool = True) -> str:
    with open(path, "rb") as f:
        r = requests.post(
            f"{GRAPH}/{config.META_PAGE_ID}/photos",
            data={"message": message, "published": str(published).lower(), "access_token": _token()},
            files={"source": (path.name, f, "image/jpeg")},
            timeout=120,
        )
    return _check(r)["id"]


def fb_photo_url(photo_id: str) -> str:
    """Javni CDN link Facebook fotografije (koristi ga Instagram)."""
    r = requests.get(f"{GRAPH}/{photo_id}", params={"fields": "images", "access_token": _token()}, timeout=30)
    images = _check(r)["images"]
    return max(images, key=lambda i: i["width"])["source"]


def fb_publish_photo(path: Path, message: str) -> str:
    return fb_upload_photo(path, message, published=True)


def fb_publish_album(paths: list[Path], message: str) -> tuple[str, list[str]]:
    """Objava s više slika. Vraća (id objave, ID-jevi slika – za Instagram karusel)."""
    ids = [fb_upload_photo(p, published=False) for p in paths]
    data = {"message": message, "access_token": _token()}
    for i, pid in enumerate(ids):
        data[f"attached_media[{i}]"] = f'{{"media_fbid":"{pid}"}}'
    r = requests.post(f"{GRAPH}/{config.META_PAGE_ID}/feed", data=data, timeout=60)
    return _check(r)["id"], ids


def fb_publish_video(path: Path, description: str) -> str:
    with open(path, "rb") as f:
        r = requests.post(
            f"{GRAPH_VIDEO}/{config.META_PAGE_ID}/videos",
            data={"description": description, "access_token": _token()},
            files={"source": (path.name, f, "video/mp4")},
            timeout=600,
        )
    return _check(r)["id"]


# ===========================================================================
# INSTAGRAM
# ===========================================================================
def _ig_wait(container_id: str, timeout_s: int = 600) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        r = requests.get(f"{GRAPH}/{container_id}",
                         params={"fields": "status_code,status", "access_token": _token()}, timeout=30)
        data = _check(r)
        if data.get("status_code") == "FINISHED":
            return
        if data.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram obrada nije uspjela: {data.get('status')}")
        time.sleep(10)
    raise TimeoutError("Instagram obrada traje predugo.")


def _ig_create(**fields) -> str:
    r = requests.post(f"{GRAPH}/{config.IG_USER_ID}/media", data={**fields, "access_token": _token()}, timeout=60)
    return _check(r)["id"]


def _ig_publish(container_id: str) -> str:
    _ig_wait(container_id)
    r = requests.post(f"{GRAPH}/{config.IG_USER_ID}/media_publish",
                      data={"creation_id": container_id, "access_token": _token()}, timeout=60)
    return _check(r)["id"]


def ig_publish_image(image_url: str, caption: str) -> str:
    return _ig_publish(_ig_create(image_url=image_url, caption=caption[:2200]))


def ig_publish_carousel(image_urls: list[str], caption: str) -> str:
    children = [_ig_create(image_url=u, is_carousel_item="true") for u in image_urls[:10]]
    for c in children:
        _ig_wait(c)
    return _ig_publish(_ig_create(media_type="CAROUSEL", children=",".join(children), caption=caption[:2200]))


def ig_publish_reel(path: Path, caption: str) -> str:
    container = _ig_create(media_type="REELS", upload_type="resumable", caption=caption[:2200], share_to_feed="true")
    with open(path, "rb") as f:
        r = requests.post(
            f"https://rupload.facebook.com/ig-api-upload/{config.GRAPH_VERSION}/{container}",
            headers={"Authorization": f"OAuth {_token()}", "offset": "0", "file_size": str(os.path.getsize(path))},
            data=f,
            timeout=600,
        )
    _check(r)
    return _ig_publish(container)


# ===========================================================================
# Zajedničke funkcije po vrsti objave. Greška na jednoj mreži ne ruši drugu –
# zapisuje se u result["errors"].
# ===========================================================================
def _safe(result: dict, network: str, fn, *args):
    try:
        result[network] = fn(*args)
    except Exception as e:
        result.setdefault("errors", []).append(f"{network}: {e}")
        print(f"  ! {network}: {e}")
    return result.get(network)


def publish_video(path: Path, caption: str) -> dict:
    result: dict = {}
    if config.PUBLISH_FACEBOOK:
        _safe(result, "facebook", fb_publish_video, path, caption)
    if config.PUBLISH_INSTAGRAM:
        _safe(result, "instagram", ig_publish_reel, path, caption)
    return result


def publish_image(path: Path, caption: str) -> dict:
    result: dict = {}
    if config.PUBLISH_FACEBOOK:
        photo_id = _safe(result, "facebook", fb_publish_photo, path, caption)
    else:
        photo_id = _safe(result, "hosting", fb_upload_photo, path, "", False)
    if config.PUBLISH_INSTAGRAM and photo_id:
        _safe(result, "instagram", lambda: ig_publish_image(fb_photo_url(photo_id), caption))
    return result


def publish_carousel(paths: list[Path], caption: str) -> dict:
    result: dict = {}
    if config.PUBLISH_FACEBOOK:
        out = _safe(result, "facebook", fb_publish_album, paths, caption)
        photo_ids = out[1] if out else None
        if out:
            result["facebook"] = out[0]
    else:
        photo_ids = _safe(result, "hosting", lambda: [fb_upload_photo(p, "", False) for p in paths])
    if config.PUBLISH_INSTAGRAM and photo_ids:
        _safe(result, "instagram", lambda: ig_publish_carousel([fb_photo_url(i) for i in photo_ids], caption))
    return result
