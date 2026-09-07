#!/usr/bin/env python3
"""Zet de twaalf xls-reconstructies om naar het miFormulas-starterdatabestand.

Opbouw van de bronbestanden: rij 1 is de titel (met soms een restgetal uit een
oudere versie), daarna de regels, en onderaan een rij TOTAL als controlegetal.
Kolom A is de materiaalnaam, de laatste gevulde kolom het gewicht in mg. De
dilutie staat ofwel achter de naam ("Beta damascone 10% DEP") ofwel in een
aparte tekstkolom ertussen ("10% DEP"). Beide worden gelezen.

Materiaalnamen worden via materials_map.MAP naar een canonieke naam gebracht;
spellingvarianten, Franse namen en dubbels vallen daardoor samen. Categorie en
piramideniveau komen uit materials_map.INFO. Prijs, voorraad, leverancier en
aankoopgegevens gaan nooit mee.

  python3 xls-naar-starterdata.py [map-met-xls] [uitvoermap]
"""
import xlrd, glob, os, re, json, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from materials_map import MAP, INFO, CAS, IFRA, HERNOEM

UP = sys.argv[1] if len(sys.argv) > 1 else "/root/.claude/uploads/8cbb310b-5c78-50f4-9e56-b2aa6d4eaa97"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/claude/out"

TITLES = {
    "1881_for_men_N.Cerruti":                    "1881 for men",
    "Tommy_Girl_T.Hilfiger":                     "T. Girl",
    "Ho_Hang_Balenciaga":                        "Ho Hang",
    "Bulgari_for_men_Bulgari":                   "Bv for men",
    "Cool_Water_Z_.Davidoff":                    "Cool Water for men",
    "A_Men_T.Mugler":                            "A Men",
    "Azzaro_Chrome__Bendoni":                    "Chrome",
    "Brut_Faberg_":                              "Brut",
    "Angel.T.Mugler":                            "Angel",
    "Armani_Acqua_di_Gio_Men__OG_form__Bendoni": "Acqua di Gio for men",
    "Chanel_Egoiste__Bendoni":                   "Egoiste",
    "Vetyver_de_Carven_Carven":                  "Vetiver de C",
    "Althenol":                                  "Althenol",
    "Jasmin_231":                                "Jasmin 231",
    "Rose_de_Mai_68_oil":                        "Rose de Mai 68",
    "Oeillet_35":                                "Oeillet 35",
}

# Een formule waarvan de titel ook als materiaal in de set voorkomt, is een
# basis: ze krijgt de categorie hieronder en het gelijknamige materiaal krijgt
# een Engelse notitie die naar de formule verwijst. Een nieuwe basis toevoegen
# vraagt dus alleen een regel in TITLES; de rest gaat vanzelf.
BASISCATEGORIE = "Bases & Accords"

# Solventen die altijd in de starterset zitten, ook als geen formule ze gebruikt:
# zonder ethanol kan de gebruiker geen dilutie aanmaken en werkt de solventwissel niet.
# (naam, CAS, IFRA, bron van het CAS)
SOLVENT_SET = [
    ("Ethanol",          "64-17-5",    99,  "algemeen bekend"),
    ("DEP",              "84-66-2",    99,  "eigen bibliotheek: Diethyl phtalate (DEP)"),
    ("DPG",              "25265-71-8", 99,  "algemeen bekend; eigen bibliotheek zonder CAS"),
    ("IPM",              "110-27-0",   99,  "eigen bibliotheek: Isopropyl myristate IPM"),
    ("TEC",              "77-93-0",    99,  "algemeen bekend; eigen bibliotheek zonder CAS"),
    ("Benzyl Benzoate",  "120-51-4",   4.8, "eigen bibliotheek, IFRA 4,8"),
]

# correcties op de bron, per (bestandsstam, rijnummer zoals in Excel)
FIXES = {("Chanel_Egoiste__Bendoni", 14): "Osyrol"}          # naam ontbrak
SKIP  = {("Vetyver_de_Carven_Carven", 35)}                   # verdwaald totaal "DEP 1000"

SOLVENTS = {"DEP", "DPG", "TEC", "IPM", "BB", "ETOH", "ETHANOL", "MIGLYOL"}
DILTAIL = re.compile(r"\s*[\(\[]?\s*(\d+(?:[.,]\d+)?)\s*%\s*([A-Za-z]{2,8})?\s*[\)\]]?\s*$")
DILCELL = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*%\s*([A-Za-z]{2,8})?\s*$")


# afkortingen die hun hoofdletters houden
KEEP = {"DEP", "DPG", "TEC", "IPM", "BB", "BHT", "DM", "EO", "MNA", "IFF", "DL", "B"}


def titlecase(s):
    """Kleine letters, elk woord een hoofdletter. Bekende afkortingen en
    codes met cijfers (C12, 345) blijven staan zoals ze zijn."""
    out = []
    for w in s.split():
        if w.upper() in KEEP or re.fullmatch(r"[A-Z]?[0-9]+[A-Z]*", w.upper()):
            out.append(w.upper() if w.upper() in KEEP else w)
        else:
            out.append("-".join(p[:1].upper() + p[1:].lower() for p in w.split("-")))
    return " ".join(out)


def key(s):
    """Opzoeksleutel: hoofdletterongevoelig, leestekens en spaties genegeerd."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


MAPK = {key(k): v for k, v in MAP.items()}
INFOK = {key(k): v for k, v in INFO.items()}


def parse_row(vals):
    name = str(vals[0]).strip()
    nums = [float(v) for v in vals[1:] if isinstance(v, (int, float)) and not isinstance(v, bool) and v]
    mg = nums[-1] if nums else None
    mids = [str(v).strip() for v in vals[1:] if isinstance(v, str) and str(v).strip()]
    pct, solv = 100.0, None
    for cell in mids:
        m = DILCELL.match(cell)
        if m:
            pct = float(m.group(1).replace(",", "."))
            solv = (m.group(2) or "").upper() or None
    if pct == 100.0:
        m = DILTAIL.search(name)
        if m and (m.group(2) is None or m.group(2).upper() in SOLVENTS):
            pct = float(m.group(1).replace(",", "."))
            solv = (m.group(2) or "").upper() or None
            name = name[: m.start()].strip()
    return name, pct, solv, mg


def sheet_rows(path):
    """Rijen als lijsten, uit .xls (xlrd) of .xlsx (openpyxl)."""
    if path.lower().endswith(".xlsx"):
        from openpyxl import load_workbook
        ws = load_workbook(path, data_only=True).worksheets[0]
        return [[("" if v is None else v) for v in row]
                for row in ws.iter_rows(min_row=1, values_only=True)]
    sh = xlrd.open_workbook(path).sheet_by_index(0)
    return [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(sh.nrows)]


def read_sheet(path, stem):
    alle = sheet_rows(path)
    rows, total, notes = [], None, []
    for r in range(1, len(alle)):
        excel_row = r + 1
        if (stem, excel_row) in SKIP:
            notes.append("rij %d overgeslagen (verdwaald totaal)" % excel_row)
            continue
        vals = alle[r]
        first = str(vals[0]).strip()
        nums = [float(v) for v in vals[1:] if isinstance(v, (int, float)) and not isinstance(v, bool) and v]
        if not first:
            fix = FIXES.get((stem, excel_row))
            if fix and nums:
                vals = [fix] + list(vals[1:])
                notes.append("rij %d: naam aangevuld als '%s'" % (excel_row, fix))
            else:
                if nums:
                    notes.append("rij %d: %.0f mg zonder materiaalnaam, weggelaten" % (excel_row, nums[-1]))
                continue
        elif first.upper().startswith("TOTAL"):
            total = nums[-1] if nums else None
            continue
        name, pct, solv, mg = parse_row(vals)
        if mg is None:
            notes.append("rij %d: '%s' zonder gewicht, weggelaten" % (excel_row, name[:40]))
            continue
        rows.append((name, pct, solv, mg))
    return rows, total, notes


def main():
    os.makedirs(OUT, exist_ok=True)
    materials, byname, formulas, report = [], {}, [], []
    onbekend = set()
    seq = [0]

    def uid():
        seq[0] += 1
        return "m%d" % seq[0]

    for path in sorted(set(glob.glob(UP + "/*.xls") + glob.glob(UP + "/*.XLS") + glob.glob(UP + "/*.xlsx"))):
        stem = re.sub(r"^[0-9a-f]{8}-", "", os.path.basename(path)).rsplit(".", 1)[0]
        title = TITLES.get(stem)
        if title is None:            # geen formulebestand (bv. een werkblad in dezelfde map)
            continue
        rows, total, notes = read_sheet(path, stem)
        lines = []
        for raw, pct, solv, mg in rows:
            canon = MAPK.get(key(raw))
            if canon is None:
                canon = titlecase(raw)
            if canon not in byname:
                cat, pyr, _ = INFOK.get(key(canon), ("Uncategorised", None, ""))
                if key(canon) not in INFOK:
                    onbekend.add(canon)
                byname[canon] = {
                    "id": uid(), "name": canon, "cas": CAS.get(canon, ""), "category": cat,
                    "supplier": "", "costPerGram": None, "ifraLimit": IFRA.get(canon),
                    "inventory": None, "pyramid": pyr,
                    "isSolvent": cat == "Solvents",
                    "description": "", "dilutions": [], "locations": {},
                    "density": None, "modified": "2026-09-07",
                    "starter": True,          # came with the app; shown as a badge, searchable as "starter"
                }
                materials.append(byname[canon])
            mat = byname[canon]
            if not any(abs(d["pct"] - pct) < 1e-9 for d in mat["dilutions"]):
                mat["dilutions"].append({"pct": pct, "isBase": not mat["dilutions"],
                                         "date": "", "notes": ("in " + solv) if solv else ""})
            lines.append({"materialId": mat["id"], "dilutionPct": pct,
                          "weightG": round(mg / 1000.0, 6), "remark": None})
        formulas.append({
            "id": "f-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-"),
            "name": title, "category": "Uncategorised",   # bases worden hierna herkend
            "created": "2026-09-07", "modified": "2026-09-07",
            "versions": [{"v": 1, "name": "", "date": "", "notes": "", "lines": lines}],
            "variations": [],
            "starter": True,
        })
        som = sum(l["weightG"] for l in lines) * 1000
        ctl = ("geen TOTAL-rij" if total is None else
               "TOTAL %.0f OK" % total if abs(som - total) < 0.5 else
               "AFWIJKING som %.0f vs TOTAL %.0f" % (som, total))
        report.append((title, len(lines), som, ctl, notes))
        print("%-22s %3d regels %8.0f mg  %s" % (title, len(lines), som, ctl))
        for n in notes:
            print("      · " + n)

    # vaste solventen: aanvullen wat ontbreekt, en CAS/IFRA zetten op wat er al is
    for naam, cas, ifra, _bron in SOLVENT_SET:
        mat = byname.get(naam)
        if mat is None:
            mat = {
                "id": uid(), "name": naam, "cas": cas, "category": "Solvents",
                "supplier": "", "costPerGram": None, "ifraLimit": ifra,
                "inventory": None, "pyramid": None, "isSolvent": True,
                "description": "", "dilutions": [{"pct": 100.0, "isBase": True, "date": "", "notes": ""}],
                "locations": {}, "density": None, "modified": "2026-09-07", "starter": True,
            }
            byname[naam] = mat
            materials.append(mat)
        else:
            mat["cas"] = mat["cas"] or cas
            if mat["ifraLimit"] is None:
                mat["ifraLimit"] = ifra
            mat["category"] = "Solvents"
            mat["isSolvent"] = True

    # hernoemen naar de naam uit de eigen bibliotheek, als laatste stap zodat
    # INFO, CAS en IFRA op de canonieke sleutel opgezocht blijven
    for mat in materials:
        nieuw = HERNOEM.get(mat["name"])
        if nieuw:
            byname.pop(mat["name"], None)
            mat["name"] = nieuw
            byname[nieuw] = mat
            # CAS en IFRA staan voor deze materialen op de nieuwe naam
            if not mat["cas"]:
                mat["cas"] = CAS.get(nieuw, "")
            if mat["ifraLimit"] is None:
                mat["ifraLimit"] = IFRA.get(nieuw)

    # bases herkennen: formuletitel die ook een materiaalnaam is
    bases = []
    for f in formulas:
        mat = byname.get(f["name"])
        if mat is None:
            continue
        f["category"] = BASISCATEGORIE
        mat["description"] = ("Base with its own formula in this library: see the formula "
                              "\u201c%s\u201d under %s." % (f["name"], BASISCATEGORIE))
        bases.append(f["name"])
    print()
    print("bases met een eigen formule (%d): %s" % (len(bases), ", ".join(sorted(bases))))

    # elke dilutie die in een formule gebruikt wordt, moet bij het materiaal staan
    for m in materials:
        m["dilutions"].sort(key=lambda d: -d["pct"])
        for i, d in enumerate(m["dilutions"]):
            d["isBase"] = i == 0

    lib_cats = ["Additives", "Aldehydes", "Amber", "Animalic", "Balsamic/coumarinic",
                "Bases & replacers", "Citrus", "Earthy", "Flowers - green", "Flowers - red",
                "Flowers - spicy", "Flowers - white", "Fresh", "Fruits", "Herbal - Green",
                "Moss", "Musks", "Phenolic", "Predils", "Solvents", "Spices",
                "Uncategorised", "Woody", "Woody - amber", "Woody - green", "Woody - sandal"]
    colours = {"Moss": "#398256", "Animalic": "#791A3D", "Amber": "#C96E12",
               "Aldehydes": "#A8853C", "Solvents": "#FFFFFF", "Earthy": "#785800",
               "Woody - sandal": "#AA723E", "Woody - green": "#807638", "Musks": "#406291",
               "Phenolic": "#707070", "Flowers - white": "#48484A", "Woody": "#845E3A",
               "Balsamic/coumarinic": "#86503B", "Spices": "#B51A00", "Herbal - Green": "#5AD800",
               "Flowers - spicy": "#D38301", "Flowers - green": "#73B05E", "Fresh": "#62BAA5",
               "Uncategorised": "#636366", "Fruits": "#FF8648", "Woody - amber": "#AEB15E",
               "Flowers - red": "#E22400", "Citrus": "#F5EC00", "Bases & replacers": "#FFFFFF",
               "Additives": "#48484A", "Predils": "#7A5EA8"}

    starter = {
        "meta": {"schema": 1, "generated": "2026-09-07",
                 "source": "miFormulas starter data", "uiLanguage": "en"},
        "materialCategories": lib_cats,
        "formulaCategories": ["Bases & Accords", "Prediluties", "Uncategorised"],
        "suppliers": [], "materials": materials, "formulas": formulas,
        "categoryColours": colours, "shopSites": [], "orderList": [],
    }
    p = os.path.join(OUT, "miformulas-starter.json")
    json.dump(starter, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    zonder = [m["name"] for m in materials if m["category"] == "Uncategorised"]
    print()
    print("%d formules, %d materialen, %d kB" % (len(formulas), len(materials), os.path.getsize(p) // 1024))
    print("zonder categorie: %d" % len(zonder))
    if onbekend:
        print("zonder voorstel in materials_map (%d):" % len(onbekend))
        for n in sorted(onbekend):
            print("   ", n)


main()
