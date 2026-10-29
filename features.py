"""Alati, featurei i besplatne ponude na zemljište.hr + koraci za tutorijal.

Svaki korak = jedan screenshot (slajd u karuselu / scena u Reelu) + tekst koji se prikaže
i izgovori. Polja se pronalaze po labeli/placeholderu (provjereno na živoj stranici
28.10.2026.) – ako se forma na sajtu promijeni, ovdje se mijenja samo vrijednost.

Akcije:
  None                         samo screenshot (vrh stranice)
  ("fill_label", label, value) upiše vrijednost u polje s tom labelom
  ("fill_ph", placeholder, v)  upiše vrijednost u polje s tim placeholderom
  ("fill_pick", placeholder, v) isto + odabere prvi prijedlog iz padajuće liste
  ("select", n, label)         u n-tom <select> odabere opciju po nazivu
  ("select_idx", n, i)         u n-tom <select> odabere i-tu opciju
  ("check", css, n)            označi n-ti element (radio/checkbox) za css
  ("click", tekst)             klikne gumb s tim tekstom
  ("scroll_to", tekst)         pomakne stranicu do teksta (bez klika)
  ("scroll", px)               pomakne stranicu za px
NIKAD ne stavljaj klik na "Objavi oglas" ili slično – tutorijal ništa ne šalje.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Step:
    caption: str
    action: tuple | None = None
    wait_ms: int = 700


@dataclass
class Feature:
    slug: str
    name: str
    path: str
    kind: str          # "alat" ili "besplatna ponuda"
    facts: str         # činjenice za AI tekst (samo ono što stvarno piše na stranici)
    steps: list[Step] = field(default_factory=list)


FEATURES: list[Feature] = [
    Feature(
        slug="kalkulator-poreza",
        name="Kalkulator poreza pri prodaji zemljišta",
        path="/alati/kalkulator-poreza",
        kind="alat",
        facts="Besplatan alat. U nekoliko sekundi kaže dugujete li porez na dohodak od otuđenja "
              "pri prodaji zemljišta i koliko približno. 4 kratka pitanja. Rezultat odmah, "
              "bez slanja podataka i bez registracije. Uz alat postoji detaljan članak o pravilima.",
        steps=[
            Step("Otvorite besplatni kalkulator poreza na zemljište.hr – bez registracije."),
            Step("Upišite datum kada ste kupili zemljište.", ("fill_label", "Datum kupnje", "2025-02-10")),
            Step("Upišite nabavnu cijenu – koliko ste platili zemljište.", ("fill_label", "Nabavna cijena", "40000")),
            Step("Upišite datum prodaje.", ("fill_label", "Datum prodaje", "2026-11-15")),
            Step("Upišite prodajnu cijenu.", ("fill_label", "Prodajna cijena", "65000")),
            Step("Rezultat se prikaže odmah: dugujete li porez i koliko približno.", ("scroll", 650), 1200),
        ],
    ),
    Feature(
        slug="kalkulator-kig-kis",
        name="Kalkulator maksimalne izgradnje (KIG i KIS)",
        path="/alati/kalkulator-kig-kis",
        kind="alat",
        facts="Besplatan alat. Unesete površinu parcele i koeficijente iz prostornog plana (KIG, KIS) "
              "i odmah dobijete procjenu koliko m² tlocrta i bruto razvijene površine smijete graditi. "
              "3 pitanja, rezultat odmah, bez slanja podataka.",
        steps=[
            Step("Koliko smijete izgraditi na svojoj parceli? Otvorite besplatni KIG/KIS kalkulator."),
            Step("Upišite površinu parcele u kvadratnim metrima.", ("fill_ph", "npr. 1000", "800")),
            Step("Upišite KIG iz prostornog plana.", ("fill_ph", "npr. 0.30", "0.3")),
            Step("Upišite KIS – ovaj korak nije obavezan.", ("fill_ph", "npr. 0.90", "0.8")),
            Step("Odmah vidite koliko m² tlocrta i bruto površine smijete graditi.", ("scroll", 650), 1200),
        ],
    ),
    Feature(
        slug="procjena-vrijednosti",
        name="Procjena vrijednosti zemljišta",
        path="/alati/procjena-vrijednosti-zemljista",
        kind="alat",
        facts="Besplatan alat. Orijentacijska procjena tržišne vrijednosti zemljišta u Hrvatskoj, "
              "izračunata iz stvarnih cijena objavljenih oglasa na Zemljište.hr. Tri koraka: osnovni "
              "podaci (tip zemljišta, županija, mjesto, površina), dodatni faktori, rezultat.",
        steps=[
            Step("Koliko vrijedi vaše zemljište? Otvorite besplatnu procjenu na zemljište.hr."),
            Step("Odaberite tip zemljišta.", ("check", 'input[name="kind"]', 0)),
            Step("Odaberite županiju.", ("select", 0, "Splitsko-dalmatinska")),
            Step("Odaberite grad ili općinu.", ("select_idx", 1, 1)),
            Step("Upišite površinu i kliknite Dalje.", ("fill_ph", "npr. 800", "800")),
            Step("Označite dodatne faktore koji vrijede za vašu parcelu.", ("click", "Dalje"), 1200),
            Step("Dobivate procjenu na temelju stvarnih cijena oglasa.", ("click", "Dalje"), 2000),
        ],
    ),
    Feature(
        slug="sto-mogu-graditi",
        name="Što možete izgraditi na ovoj parceli?",
        path="/alati/cestica",
        kind="alat",
        facts="Besplatan alat s podacima DGU. Unesete katastarsku općinu i broj čestice i odmah "
              "doznate površinu, lokaciju na karti i procjenu što smijete graditi. Karta ima slojeve "
              "Katastar, Prostorni plan i Satelit.",
        steps=[
            Step("Što smijete graditi na parceli? Provjerite besplatno na zemljište.hr."),
            Step("Upišite katastarsku općinu.", ("fill_pick", "npr. Split, Zagreb, Pula...", "Rovinjsko Selo")),
            Step("Upišite broj čestice.", ("fill_ph", "npr. 123/4", "1560/4")),
            Step("Kliknite Pronađi česticu – parcela se prikaže na karti.", ("click", "Pronađi česticu"), 5000),
            Step("Uključite sloj Prostorni plan i provjerite namjenu.", ("click", "Prostorni plan"), 4000),
        ],
    ),
    Feature(
        slug="besplatna-objava-oglasa",
        name="Besplatna objava oglasa",
        path="/dodaj-oglas",
        kind="besplatna ponuda",
        facts="Besplatna objava oglasa za prodaju zemljišta u Hrvatskoj. Unosi se naziv, opis, "
              "kategorija (građevinsko, poljoprivredno, šumsko, ostalo), županija, mjesto, površina, "
              "fotografije, cijena i kontakt. Moguće je koristiti kontakt podatke portala.",
        steps=[
            Step("Prodajete zemljište? Objava oglasa na zemljište.hr je besplatna."),
            Step("Upišite naziv oglasa.", ("fill_ph", "Kratki opis npr. Građevinsko zemljište Sesvete 1200m²",
                                           "Građevinsko zemljište Sesvete 1200 m²")),
            Step("Opišite lokaciju, namjenu i pristup.", ("fill_ph", "Opišite zemljište detaljno — lokacija, namjena, pristup, posebnosti...",
                                                          "Ravna parcela uz asfaltiranu cestu, 10 minuta od centra.")),
            Step("Odaberite kategoriju zemljišta.", ("select", 0, "Građevinsko")),
            Step("Odaberite županiju.", ("select", 1, "Zagrebačka")),
            Step("Upišite površinu.", ("fill_ph", "Npr. 1200", "1200")),
            Step("Dodajte fotografije, cijenu i kontakt – i kliknite Objavi oglas.", ("scroll_to", "Objavi oglas"), 1000),
        ],
    ),
    Feature(
        slug="trazim-zemljiste",
        name="Tražim zemljište",
        path="/trazim",
        kind="besplatna ponuda",
        facts="Opišete kakvo zemljište tražite (kategorija, jedna ili više županija, površina, budžet), "
              "a Zemljište.hr vas spaja s pravim oglasom ili obavještava čim se pojavi.",
        steps=[
            Step("Ne možete pronaći pravo zemljište? Recite nam što tražite."),
            Step("Odaberite kategoriju zemljišta.", ("select", 0, "Građevinsko")),
            Step("Označite jednu ili više županija.", ("check", 'input[type="checkbox"]', 0)),
            Step("Upišite željenu površinu.", ("fill_ph", "npr. 500", "600")),
            Step("Upišite budžet.", ("fill_ph", "npr. 80000", "90000")),
            Step("Javljamo vam se čim se pojavi odgovarajući oglas.", ("scroll", 700), 1000),
        ],
    ),
    Feature(
        slug="zk-izvadak",
        name="ZK izvadak – besplatni uvid online",
        path="/alati/zk-izvadak",
        kind="besplatna ponuda",
        facts="Vodič kako besplatno provjeriti zemljišnoknjižni izvadak online preko e-Pravosuđa: "
              "vlasništvo, tereti, hipoteke. Za oko 2 minute, bez registracije i bez OIB-a. "
              "Stranica ima odgovore na česta pitanja (posjedovni list, aktualnost izvatka, dokaz vlasništva).",
        steps=[
            Step("Prije kupnje zemljišta provjerite ZK izvadak – besplatno i online."),
            Step("Vlasništvo, tereti i hipoteke – za oko dvije minute, bez registracije.", ("scroll", 600)),
            Step("Pratite vodič korak po korak.", ("scroll", 700)),
            Step("Tu su i odgovori na najčešća pitanja.", ("scroll_to", "Je li ZK izvadak besplatan?")),
        ],
    ),
]


def by_slug(slug: str) -> Feature:
    for f in FEATURES:
        if f.slug == slug:
            return f
    raise KeyError(f"Nepoznat feature: {slug}. Dostupni: {[f.slug for f in FEATURES]}")
