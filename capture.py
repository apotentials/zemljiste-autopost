"""Playwright (besplatno): otvori alat na sajtu kao mobitel, odradi korake i snimi screenshot
svakog koraka. Polje koje se popunjava označi se zlatnim okvirom."""
from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

import config
from features import Feature

HIGHLIGHT = "el => { el.style.outline = '5px solid #C9A227'; el.style.outlineOffset = '3px'; " \
            "el.scrollIntoView({block: 'center'}); }"
CLEAR = "() => document.querySelectorAll('*').forEach(e => { if (e.style && e.style.outline) e.style.outline = ''; })"


def _dismiss_banners(page: Page) -> None:
    for name in ("Odbij", "Samo nužni", "Zatvori"):
        btn = page.get_by_role("button", name=re.compile(name, re.I))
        if btn.count():
            try:
                btn.first.click(timeout=1500)
            except Exception:
                pass


def _run(page: Page, action: tuple):
    """Izvrši akciju; vrati locator elementa koji treba istaknuti (ili None)."""
    kind, *args = action
    if kind == "fill_label":
        loc = page.get_by_label(args[0], exact=False).first
        loc.fill(args[1])
    elif kind in ("fill_ph", "fill_pick"):
        loc = page.get_by_placeholder(args[0], exact=True).first
        loc.fill(args[1])
        if kind == "fill_pick":
            # Polje s prijedlozima (autocomplete): odaberi prvi vidljivi prijedlog ako se pojavi
            page.wait_for_timeout(1500)
            option = page.locator('[role="option"]:visible, [cmdk-item]:visible')
            if option.count():
                option.first.click()
    elif kind == "select":
        loc = page.locator("select").nth(args[0])
        loc.select_option(label=args[1])
    elif kind == "select_idx":
        loc = page.locator("select").nth(args[0])
        page.wait_for_function("s => s.options.length > 1", arg=loc.element_handle(), timeout=8000)
        loc.select_option(index=args[1])
    elif kind == "check":
        loc = page.locator(args[0]).nth(args[1])
        loc.check(force=True)
        loc = loc.locator("xpath=..")  # istakni labelu oko radio/checkboxa
    elif kind == "click":
        loc = page.get_by_role("button", name=args[0]).first
        loc.scroll_into_view_if_needed()
        loc.click()
        return None  # nakon klika pokazujemo rezultat, ne gumb
    elif kind == "scroll_to":
        loc = page.get_by_text(args[0]).first
    elif kind == "scroll":
        page.mouse.wheel(0, args[0])
        return None
    else:
        raise ValueError(f"Nepoznata akcija: {kind}")
    return loc


def capture_feature(feature: Feature, dest: Path) -> list[Path]:
    """Vrati listu screenshotova (jedan po koraku). Baca grešku ako neki korak ne uspije,
    da se ne objavi neispravan tutorijal."""
    dest.mkdir(parents=True, exist_ok=True)
    shots: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 412, "height": 860},
            device_scale_factor=2.5,      # oštri screenshotovi (1030 px širine)
            is_mobile=True,
            has_touch=True,
            locale="hr-HR",
        )
        page = ctx.new_page()
        page.goto(config.SITE_URL + feature.path, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(1500)
        _dismiss_banners(page)

        for i, step in enumerate(feature.steps):
            page.evaluate(CLEAR)
            if step.action:
                try:
                    loc = _run(page, step.action)
                except Exception as e:
                    browser.close()
                    raise RuntimeError(f"Korak {i + 1} ({step.action}) nije uspio – provjeri features.py: {e}")
                if loc is not None:
                    loc.evaluate(HIGHLIGHT)
            page.wait_for_timeout(step.wait_ms)
            shot = dest / f"step_{i:02d}.png"
            page.screenshot(path=str(shot))
            shots.append(shot)
        browser.close()
    return shots
