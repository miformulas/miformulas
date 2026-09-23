#!/usr/bin/env python3
"""Zet een Formulair-database (DataModel.sqlite) om naar een miFormulas-databestand.

Referentie-implementatie; de browserversie in formulair-import.html volgt exact
dezelfde regels en wordt hiertegen getest.

  python3 formulair-naar-json.py DataModel.sqlite [uitvoer.json]

Vlakke import: elke Formulair-formule wordt een bevroren miFormulas-formule met
één versie. Notities, kleurmarkeringen, datums, categorieën met kleur,
leveranciers, diluties en voorraad gaan mee. Niets wordt omgerekend.

Formulair-conventies:
  - hoeveelheden in gram
  - ZREMARK 1 = geen markering; 0, 2, 3, 4 = de vier kleuren
  - Core Data-datums = seconden sinds 2001-01-01
  - ZPYRAMID 0..4 = Top..Base, 5 = onbekend
  - ZIFRA -1 = fout (zelfde codering als miFormulas), leeg = niet ingegeven
  - kleuren als NSKeyedArchiver-plist; de RGB-drieslag staat er als tekst in
"""
import sqlite3, json, sys, re, os, datetime, math, unicodedata

EPOCH = datetime.datetime(2001, 1, 1)


CAS_RE = re.compile(r"\b\d{2,7}-\d{2}-\d\b")

def split_cas(s):
    """Formulair-gewoonte: synoniemen naast het CAS-nummer. Het nummer blijft, de rest wordt alternative names."""
    s = (s or "").strip(); hit = CAS_RE.search(s)
    if not hit or hit.group(0) == s:
        return s, ""
    rest = s.replace(hit.group(0), "", 1)
    rest = re.sub(r"^[\s\\/,;:·–-]+|[\s\\/,;:·–-]+$", "", rest)
    rest = re.sub(r"\s*[\\/]\s*", "; ", rest).strip()
    return hit.group(0), rest

# Formulair toont zijn datums in de tijd van de computer, en miFormulas ook (bouw 260922h). In UTC gelezen kreeg een
# formule van na middernacht in Brussel de dag ervoor: 90 van de 698 formules van een echte databank. Dezelfde
# lezing als de browser (getFullYear en de rest): de tijdzone van deze computer, of die van TZ.
EPOCH_UNIX = 978307200   # 2001-01-01 in seconden sinds 1970


def cd_local(ts):
    return datetime.datetime.fromtimestamp(ts + EPOCH_UNIX)


def cd_date(ts):
    if ts is None:
        return ""
    return cd_local(ts).strftime("%Y-%m-%d")


def cd_stamp(ts):
    if ts is None:
        return ""
    return cd_local(ts).strftime("%Y-%m-%dT%H:%M:%S")


def half_up(x):
    """Zoals Math.round in de browser: 0,5 gaat omhoog. Pythons round() rondt
    naar het even getal, dus 127,5 werd 128 in de browser en 128 hier alleen bij
    toeval; op 0,5 exact liepen de twee omzettingen uiteen."""
    return int(math.floor(x + 0.5))


LIGATUREN = [("\u0153", "oe"), ("\u00e6", "ae"), ("\u00f8", "o"), ("\u00df", "ss"),
             ("\u0111", "d"), ("\u00f0", "d"), ("\u0142", "l")]


def sort_key(s):
    """Zoals localeCompare("en"), en zoals fold() in de app: een accent telt niet
    mee in de volgorde maar scheidt nog wel twee namen die verder gelijk zijn, en
    een ligatuur telt als de letters waar ze uit bestaat. str.lower() alleen zette
    Élemi achter Ylang en Œillet achter Zdravetz, want é en œ staan na z in de
    codetabel."""
    low = s.lower()
    folded = "".join(ch for ch in unicodedata.normalize("NFD", low)
                     if not unicodedata.combining(ch))
    for k, v in LIGATUREN:
        folded = folded.replace(k, v)
    return (folded, low)


def colour_of(blob):
    """'#RRGGBB' uit de plist-blob, of None. De blob bevat de kleur als tekst
    'r g b' met waarden 0..1; bij dynamische kleuren nemen we de eerste."""
    if not blob:
        return None
    m = re.search(rb"(\d\.\d+|\d) (\d\.\d+|\d) (\d\.\d+|\d)", blob)
    if not m:
        return None
    r, g, b = (half_up(float(x) * 255) for x in m.groups())
    return "#%02X%02X%02X" % (r, g, b)


def convert(path):
    c = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    q = lambda s: c.execute(s).fetchall()

    rmcat = {pk: (name or "Uncategorised") for pk, name in q("select Z_PK, ZNAME from ZRMCATEGORY")}
    fcat = {pk: (name or "Uncategorised") for pk, name in q("select Z_PK, ZNAME from ZFCATEGORY")}
    supp = {pk: (name or "") for pk, name in q("select Z_PK, ZNAME from ZSUPPLIER")}
    colours = {}
    for pk, name, blob in q("select Z_PK, ZNAME, ZCOLOUR from ZRMCATEGORY"):
        col = colour_of(blob)
        if name and col:
            colours[name] = col

    # materialen
    materials, mat_by_pk = [], {}
    for row in q("""select Z_PK, ZNAME, ZCAS, ZCATEGORY, ZSUPPLIER, ZCOST, ZIFRA, ZINVENTORY,
                    ZPYRAMID, ZISSOLVENT, ZODOURDESCRIPTION, ZTIMESTAMP from ZINGREDIENT order by Z_PK"""):
        pk, name, cas, cat, sup, cost, ifra, inv, pyr, solv, desc, ts = row
        m = {
            "id": "m-f%d" % pk,
            "name": (name or "").strip(),
            "cas": split_cas(cas)[0], "aliases": split_cas(cas)[1],
            "category": rmcat.get(cat, "Uncategorised"),
            "supplier": supp.get(sup, ""),
            "costPerGram": cost if cost not in (None, 0) else None,
            "ifraLimit": None if ifra is None else ifra,
            "inventory": (inv or "").strip() or None,
            "pyramid": None if pyr is None or pyr > 4 else int(pyr),
            "isSolvent": bool(solv),
            "description": (desc or "").strip(),
            "dilutions": [],
            "locations": {},
            "density": None,
            "modified": cd_stamp(ts),
        }
        materials.append(m)
        mat_by_pk[pk] = m

    # diluties
    dil_by_pk = {}
    for pk, ing, pct, base, date, notes in q(
            "select Z_PK, ZINGREDIENT, ZDILUTION, ZISBASEDILUTION, ZDATE, ZNOTES from ZDILUTIONENTRY order by Z_PK"):
        m = mat_by_pk.get(ing)
        if m is None:
            continue
        pct = float(pct if pct is not None else 100)
        dil_by_pk[pk] = (m, pct)
        if not any(abs(d["pct"] - pct) < 1e-9 for d in m["dilutions"]):
            m["dilutions"].append({"pct": pct, "isBase": bool(base), "date": cd_date(date), "notes": (notes or "").strip()})
    for m in materials:
        m["dilutions"].sort(key=lambda d: -d["pct"])
        if m["dilutions"] and not any(d["isBase"] for d in m["dilutions"]):
            m["dilutions"][0]["isBase"] = True

    # formules
    lines_by_f = {}
    for fpk, dpk, qty, remark, added in q(
            "select ZFORMULA, ZDILUTIONENTRY, ZQUANTITY, ZREMARK, ZDATEADDED from ZFORMULAENTRY order by ZDATEADDED, Z_PK"):
        d = dil_by_pk.get(dpk)
        if d is None:
            continue
        m, pct = d
        lines_by_f.setdefault(fpk, []).append({
            "materialId": m["id"],
            "dilutionPct": pct,
            "weightG": round(float(qty or 0), 6),
            "remark": None if remark in (None, 1) else int(remark),
        })

    formulas = []
    for pk, title, cat, date, notes in q("select Z_PK, ZTITLE, ZCATEGORY, ZDATE, ZNOTES from ZFORMULA order by ZTITLE"):
        title = (title or "").strip() or ("Formula %d" % pk)
        day = cd_date(date)
        formulas.append({
            "id": "f-f%d" % pk,
            "name": title,
            "category": fcat.get(cat, "Uncategorised"),
            "created": day,
            "modified": cd_stamp(date),
            "frozenImport": True,
            "versions": [{
                "v": 1, "name": "", "date": day,
                "notes": (notes or "").strip(),
                "lines": lines_by_f.get(pk, []),
                "sourceName": title, "imported": True, "frozen": True,
            }],
        })

    mcats = sorted({m["category"] for m in materials} | set(rmcat.values()), key=sort_key)
    fcats = sorted({f["category"] for f in formulas} | set(fcat.values()), key=sort_key)
    return {
        "meta": {"schema": 1, "generated": datetime.date.today().isoformat(),
                 "source": "Formulair DataModel.sqlite (flat import)", "uiLanguage": "en"},
        "materialCategories": mcats,
        "formulaCategories": fcats,
        "suppliers": sorted({s for s in supp.values() if s}, key=sort_key),
        "materials": materials,
        "formulas": formulas,
        "categoryColours": colours,
        "shopSites": [],
        "orderList": [],
    }


if __name__ == "__main__":
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "miformulas-data.json"
    data = convert(src)

    def rond(o):   # zoals de app bij het opslaan: niet-gehele getallen op 6 decimalen
        if isinstance(o, float):
            return int(o) if o.is_integer() else round(o, 6)   # 100, niet 100.0: precies wat de app schrijft
        if isinstance(o, dict):
            return {k: rond(v) for k, v in o.items()}
        if isinstance(o, list):
            return [rond(x) for x in o]
        return o
    json.dump(rond(data), open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    nl = sum(len(f["versions"][0]["lines"]) for f in data["formulas"])
    nn = sum(1 for f in data["formulas"] if f["versions"][0]["notes"])
    print("%d materialen, %d formules, %d regels, %d formules met notitie, %d kleuren -> %s (%d kB)" % (
        len(data["materials"]), len(data["formulas"]), nl, nn, len(data["categoryColours"]), out,
        os.path.getsize(out) // 1024))
