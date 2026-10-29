"""2. AI TEKST: Google Gemini (besplatni tier) preko službene knjižnice `google-genai`.
(gemini-1.5-flash i `google-generativeai` su ugašeni – model se mijenja kroz GEMINI_MODEL.)"""
from __future__ import annotations

import json
import time

from google import genai
from google.genai import types

import config

BASE_RULES = """Ti si social media copywriter za zemljište.hr – specijalizirani hrvatski portal
isključivo za zemljišta (oglasi, besplatni alati, edukativni blog).

PRAVILA (obavezno):
- Standardni hrvatski jezik, prirodan ton, bez klišeja ("jedinstvena prilika", "ne propustite", "raj").
- Koristi ISKLJUČIVO činjenice iz PODATAKA. Ne izmišljaj brojeve, udaljenosti, pogled, dozvole,
  zakonske stope ni rokove. Ako nešto ne piše u podacima – izostavi.
- Ignoriraj uvjete poslovanja agencija, cjenike i linkove na druge sajtove iz opisa.
- Brend se piše "zemljište.hr".

PODACI:
{data}

Vrati JSON s ključevima:
- "caption": tekst za Instagram i Facebook (do 900 znakova): kuka u prvom retku, 2-4 kratka odlomka,
  poziv na akciju s linkom {url}, na kraju 8-12 relevantnih hashtagova (#zemljište #zemljistehr ...).
- "linkedin": B2B objava (do 1100 znakova) za investitore, agencije, geodete i developere,
  bez emojija, link {url}, najviše 3 hashtaga.
- "gbp": objava za Google Business profil (60-150 riječi), bez hashtagova i emojija,
  jasan poziv na akciju, završi s linkom {url}.
{extra}"""

EXTRA = {
    "listing": """- "reels_script": tekst za AI glas, 55-80 riječi. Samo izgovoreni tekst, bez emojija,
  hashtagova i URL-ova. Brojeve piši kako se izgovaraju. Završi s: "Više na zemljište točka ha-er." """,
    "blog": """- "card_subtitle": jedna rečenica (do 110 znakova) za sliku uz naslov članka – konkretna korist za čitatelja.
Caption neka izvuče 2-3 najkorisnije informacije iz članka (samo ako su u podacima) i pozove na čitanje.""",
    "feature": """- "hook": naslov za prvi slajd (do 60 znakova), pitanje ili problem koji alat rješava.
- "intro_voice": jedna izgovorena rečenica (do 20 riječi) koja otvara video, bez URL-a.
- "outro_voice": jedna izgovorena rečenica (do 18 riječi) koja poziva da isprobaju besplatno na zemljište točka ha-er.
Caption neka kratko objasni korake (pratite slajdove/video) i naglasi da je besplatno, ako to piše u podacima.""",
}


def generate(kind: str, data: dict, url: str, retries: int = 3) -> dict[str, str]:
    """kind: 'listing' | 'blog' | 'feature'"""
    client = genai.Client(api_key=config.require("GEMINI_API_KEY"))
    prompt = BASE_RULES.format(
        data=json.dumps(data, ensure_ascii=False, indent=2), url=url, extra=EXTRA[kind]
    )
    for attempt in range(1, retries + 1):
        try:
            resp = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7, response_mime_type="application/json"),
            )
            out = json.loads(resp.text)
            for key in ("caption", "linkedin", "gbp"):
                if not out.get(key):
                    raise ValueError(f"nedostaje '{key}'")
            return {k: str(v).strip() for k, v in out.items()}
        except Exception as e:  # 429 rate limit ili neispravan JSON
            print(f"  ! Gemini pokušaj {attempt}/{retries}: {e}")
            if attempt == retries:
                raise
            time.sleep(20 * attempt)
    raise RuntimeError("unreachable")
