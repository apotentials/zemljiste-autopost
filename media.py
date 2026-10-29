"""3. GLAS, SLIKE I VIDEO: edge-tts (hrvatski glas), Pillow (slajdovi), moviepy (MP4 9:16)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts
import numpy as np
from moviepy import (AudioFileClip, CompositeAudioClip, CompositeVideoClip, ImageClip,
                     concatenate_videoclips)
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

import config

GREEN = (22, 61, 41)
GREEN_DARK = (14, 40, 27)
GOLD = (201, 162, 39)
WHITE = (255, 255, 255)
REEL = (1080, 1920)   # Reels / TikTok / Shorts
POST = (1080, 1350)   # Instagram 4:5 (karusel, blog)


# ---------------------------------------------------------------------------
# Glas
# ---------------------------------------------------------------------------
async def _tts(text: str, out: Path) -> None:
    await edge_tts.Communicate(text, config.TTS_VOICE, rate=config.TTS_RATE).save(str(out))


def tts(text: str, out: Path) -> Path:
    asyncio.run(_tts(text, out))
    return out


# ---------------------------------------------------------------------------
# Pomoćne funkcije za crtanje
# ---------------------------------------------------------------------------
def font(size: int) -> ImageFont.FreeTypeFont:
    for c in (config.FONT_PATH,
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "C:/Windows/Fonts/arialbd.ttf"):
        if c and Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default(size=size)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_w: int, max_lines: int = 4) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if draw.textlength(test, font=fnt) <= max_w:
            line = test
        else:
            lines.append(line)
            line = word
    lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,") + "…"
    return lines


def draw_lines(draw, xy, lines, fnt, fill, spacing=1.25) -> int:
    x, y = xy
    for ln in lines:
        draw.text((x, y), ln, font=fnt, fill=fill)
        y += int(fnt.size * spacing)
    return y


def brand_footer(img: Image.Image, text: str = "zemljište.hr") -> None:
    d = ImageDraw.Draw(img)
    w, h = img.size
    d.text((w // 2, h - 55), text, font=font(36), fill=GOLD, anchor="mm")


def phone_frame(shot: Path, max_w: int, max_h: int) -> Image.Image:
    """Screenshot mobitela sa zaobljenim rubovima i zlatnim okvirom."""
    img = ImageOps.contain(Image.open(shot).convert("RGB"), (max_w, max_h))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, *img.size], radius=36, fill=255)
    framed = Image.new("RGBA", (img.width + 12, img.height + 12), (0, 0, 0, 0))
    ImageDraw.Draw(framed).rounded_rectangle([0, 0, *framed.size], radius=42, fill=GOLD)
    framed.paste(img, (6, 6), mask)
    return framed


# ---------------------------------------------------------------------------
# OGLAS: video od fotografija
# ---------------------------------------------------------------------------
def listing_frame(img_path: Path, title: str, info: str) -> np.ndarray:
    w, h = REEL
    src = ImageOps.exif_transpose(Image.open(img_path)).convert("RGB")
    bg = ImageOps.fit(src, (w, h)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (w, h), (0, 0, 0)), 0.35)
    fg = ImageOps.contain(src, (w, int(h * 0.62)))
    bg.paste(fg, ((w - fg.width) // 2, int(h * 0.16)))
    d = ImageDraw.Draw(bg)
    d.text((w // 2, 120), "zemljište.hr", font=font(64), fill=WHITE, anchor="mm")
    top = int(h * 0.80)
    d.rectangle([0, top, w, h], fill=GREEN)
    d.rectangle([0, top, w, top + 8], fill=GOLD)
    f = font(50)
    y = draw_lines(d, (60, top + 50), wrap(d, title, f, w - 120, 3), f, WHITE)
    d.text((60, y + 10), info, font=font(46), fill=GOLD)
    return np.array(bg)


def listing_video(images: list[Path], audio_path: Path, title: str, info: str, out: Path) -> Path:
    audio = AudioFileClip(str(audio_path))
    per = (audio.duration + 0.8) / len(images)
    clips = []
    for p in images:
        frame = ImageClip(listing_frame(p, title, info)).with_duration(per)
        zoom = frame.resized(lambda t, d=per: 1 + 0.04 * t / d).with_position("center")  # Ken Burns
        clips.append(CompositeVideoClip([zoom], size=REEL).with_duration(per))
    return _write(concatenate_videoclips(clips, method="compose").with_audio(audio), out)


# ---------------------------------------------------------------------------
# BLOG: kartica 4:5
# ---------------------------------------------------------------------------
def blog_card(title: str, subtitle: str, out: Path) -> Path:
    w, h = POST
    img = Image.new("RGB", (w, h), GREEN)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 14], fill=GOLD)
    d.text((80, 120), "BLOG · VODIČ", font=font(38), fill=GOLD)
    f_title = font(78)
    y = draw_lines(d, (80, 220), wrap(d, title, f_title, w - 160, 6), f_title, WHITE, 1.2)
    d.rectangle([80, y + 40, 220, y + 48], fill=GOLD)
    f_sub = font(44)
    y = draw_lines(d, (80, y + 90), wrap(d, subtitle, f_sub, w - 160, 4), f_sub, (220, 230, 222))
    d.text((80, h - 170), "Pročitajte cijeli članak →", font=font(42), fill=WHITE)
    brand_footer(img)
    img.save(out, quality=92)
    return out


# ---------------------------------------------------------------------------
# TUTORIJAL: slajdovi (karusel) i Reel
# ---------------------------------------------------------------------------
def _step_slide(size, shot: Path, step_no: int, total: int, caption: str) -> Image.Image:
    w, h = size
    img = Image.new("RGB", (w, h), GREEN)
    d = ImageDraw.Draw(img)
    head = 110 if h == POST[1] else 260
    d.text((70, head), f"KORAK {step_no}/{total}", font=font(36), fill=GOLD)
    f = font(52 if h == POST[1] else 60)
    y = draw_lines(d, (70, head + 60), wrap(d, caption, f, w - 140, 3), f, WHITE)
    phone = phone_frame(shot, w - 220, h - y - 140)
    img.paste(phone, ((w - phone.width) // 2, y + 30), phone)
    brand_footer(img)
    return img


def _cover_slide(size, shot: Path, title: str, hook: str, kind: str) -> Image.Image:
    w, h = size
    bg = ImageOps.fit(Image.open(shot).convert("RGB"), (w, h)).filter(ImageFilter.GaussianBlur(18))
    img = Image.blend(bg, Image.new("RGB", (w, h), GREEN_DARK), 0.82)
    d = ImageDraw.Draw(img)
    label = "BESPLATNO · KORAK PO KORAK" if kind == "besplatna ponuda" else "BESPLATAN ALAT · KORAK PO KORAK"
    d.text((80, h * 0.25), label, font=font(36), fill=GOLD)
    f_hook = font(86)
    y = draw_lines(d, (80, h * 0.25 + 80), wrap(d, hook, f_hook, w - 160, 4), f_hook, WHITE, 1.15)
    f_t = font(44)
    draw_lines(d, (80, y + 50), wrap(d, title, f_t, w - 160, 2), f_t, GOLD)
    d.text((80, h - 200), "Listajte →" if h == POST[1] else "", font=font(40), fill=WHITE)
    brand_footer(img)
    return img


def _cta_slide(size, path: str) -> Image.Image:
    w, h = size
    img = Image.new("RGB", (w, h), GREEN)
    d = ImageDraw.Draw(img)
    d.text((w // 2, h * 0.38), "Isprobajte besplatno", font=font(80), fill=WHITE, anchor="mm")
    d.text((w // 2, h * 0.48), f"{config.PUBLIC_DOMAIN}{path}", font=font(46), fill=GOLD, anchor="mm")
    d.text((w // 2, h * 0.58), "Bez registracije · Link u opisu", font=font(38), fill=(220, 230, 222), anchor="mm")
    brand_footer(img)
    return img


def tutorial_carousel(feature, shots: list[Path], hook: str, out_dir: Path) -> list[Path]:
    """Slajdovi 1080x1350: naslovni + koraci + poziv na akciju (Instagram dopušta max 10)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    steps = list(zip(shots, feature.steps))[:8]
    slides = [_cover_slide(POST, shots[0], feature.name, hook, feature.kind)]
    slides += [_step_slide(POST, s, i + 1, len(steps), st.caption) for i, (s, st) in enumerate(steps)]
    slides.append(_cta_slide(POST, feature.path))
    paths = []
    for i, s in enumerate(slides):
        p = out_dir / f"slide_{i:02d}.jpg"
        s.save(p, quality=92)
        paths.append(p)
    return paths


def tutorial_reel(feature, shots: list[Path], hook: str, intro: str, outro: str, work: Path) -> Path:
    """Reel 9:16: svaki korak traje točno koliko i njegov izgovoreni tekst."""
    segments = [(np.array(_cover_slide(REEL, shots[0], feature.name, hook, feature.kind)), intro)]
    total = len(feature.steps)
    for i, (shot, step) in enumerate(zip(shots, feature.steps)):
        segments.append((np.array(_step_slide(REEL, shot, i + 1, total, step.caption)), step.caption))
    segments.append((np.array(_cta_slide(REEL, feature.path)), outro))

    clips, voices, start = [], [], 0.0
    for i, (frame, text) in enumerate(segments):
        voice = AudioFileClip(str(tts(text, work / f"voice_{i:02d}.mp3")))
        duration = voice.duration + 0.45           # kratka pauza između koraka
        clips.append(ImageClip(frame).with_duration(duration))
        voices.append(voice.with_start(start))     # glas kreće s početkom svoje scene
        start += duration

    video = concatenate_videoclips(clips)
    video = video.with_audio(CompositeAudioClip(voices).with_duration(video.duration))
    return _write(video, work / "tutorial_reel.mp4")


def _write(video, out: Path) -> Path:
    video.write_videofile(
        str(out), fps=30, codec="libx264", audio_codec="aac", bitrate="6000k", preset="medium",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"], logger=None,
    )
    video.close()
    return out
