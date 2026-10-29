# Zemljište.hr – automatske objave (besplatno)

## Što dobivaš

Jedna objava dnevno na **Facebook + Instagram**, bez tvog rada:

| Dan | Objava | Kako izgleda |
|---|---|---|
| Pon, Čet, Sub | **Novi oglas** | Reel 25–30 s: fotke parcele + AI glas + traka s cijenom |
| Uto, Ned | **Blog članak** | Slika s naslovom članka + opis s linkom |
| Sri | **Alat / besplatna ponuda** | Karusel „Korak 1, 2, 3…“ sa screenshotovima sajta |
| Pet | **Isti alat** | Reel: screenshotovi koraka + AI glas koji vodi kroz alat |

Alati i ponude se vrte redom (svaki tjedan jedan): kalkulator poreza, KIG/KIS kalkulator, procjena vrijednosti,
„Što možete izgraditi“, besplatna objava oglasa, „Tražim zemljište“, ZK izvadak. Novi se dodaje u `features.py`.

Uz svaku objavu stiže ti **e-mail** s gotovim tekstom i slikom za **Google Business** i **LinkedIn** – samo copy-paste.

## Što trebaš napraviti (jednom, ~1,5 h)

**1. Gemini ključ (5 min)** – aistudio.google.com → *Get API key*.

**2. Meta podaci (30–60 min)** – Instagram je već povezan sa stranicom.
1. developers.facebook.com → *Create App* → tip *Business*.
2. *Tools → Graph API Explorer* → odaberi app → *Get User Access Token* s dozvolama:
   `pages_show_list, pages_read_engagement, pages_manage_posts, instagram_basic, instagram_content_publish`
3. Produži token (Access Token Debugger → *Extend Access Token*).
4. U Exploreru s produženim tokenom: `me/accounts` → `id` = **META_PAGE_ID**, `access_token` = **META_PAGE_TOKEN** (ne istječe).
5. `{META_PAGE_ID}?fields=instagram_business_account` → `id` = **IG_USER_ID**.

**3. Gmail App password (5 min)** – myaccount.google.com → Sigurnost → 2-Step Verification → *App passwords* → kopiraj 16 znakova.

**4. GitHub (15 min)**
1. Novi repozitorij `zemljiste-autopost` (**ne** `zemljistehr` – svaki commit tamo pokreće novi build sajta).
2. Ubaci sve datoteke iz ove mape.
3. *Settings → Secrets and variables → Actions* → dodaj:
   `GEMINI_API_KEY`, `META_PAGE_ID`, `META_PAGE_TOKEN`, `IG_USER_ID`, `SMTP_USER`, `SMTP_PASSWORD`, `NOTIFY_TO`

**5. Test (15 min)** – *Actions → Zemljište.hr – dnevna objava → Run workflow* (kvačica „Samo test“ je uključena).
Isprobaj svaku vrstu (`listing`, `blog`, `feature_carousel`, `feature_reel`). Rezultat skini iz *Artifacts* na dnu runa.
Kad je sve OK, ne radiš ništa – od sutra ide samo.

## Google Business – automatika kasnije

Google API za objave je besplatan, ali traži odobrenje: developers.google.com/my-business → *Prerequisites* → zahtjev za pristup
(profil mora biti verificiran 60+ dana). Dok ne odobre, tekst ti stiže e-mailom. Kad odobre, dodaje se jedna funkcija.

## Lokalno pokretanje (opcionalno)

```bash
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env               # upiši ključeve
python main.py --type feature_carousel --feature kalkulator-kig-kis   # DRY_RUN=true u .env
```

## Datoteke

| Datoteka | Što radi |
|---|---|
| `main.py` | raspored i glavni tok |
| `sources.py` | oglasi (Supabase `public_listings` + BeautifulSoup) i blog (sitemap + BeautifulSoup) |
| `features.py` | popis alata/ponuda i koraci tutorijala |
| `capture.py` | Playwright otvori alat kao mobitel, ispuni ga primjerom i snimi svaki korak |
| `ai_text.py` | Gemini: FB/IG opis, LinkedIn, Google Business, tekst za glas |
| `media.py` | edge-tts glas, slajdovi (Pillow), video (moviepy) |
| `meta_publish.py` | Facebook i Instagram (video, slika, karusel) |
| `notify.py` | e-mail s paketom za Google Business + LinkedIn |
| `state/state.json` | što je već objavljeno (nema duplikata) |

## Ograničenja besplatnih alata

- **edge-tts** je neslužbeni Microsoftov servis – besplatan, ali bez garancije.
- **Tutorijali** ovise o izgledu forme na sajtu. Ako promijeniš formu u Lovableu, run javi grešku (ništa neispravno se ne objavi) – popravak je jedna linija u `features.py`.
- **Instagram**: max 25 objava / 24 h, opis max 2.200 znakova.
- GitHub Actions: javni repo neograničeno; privatni 2.000 min/mj (jedan run ≈ 3–6 min).
