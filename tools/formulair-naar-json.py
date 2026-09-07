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
import sqlite3, json, sys, re, os, datetime

EPOCH = datetime.datetime(2001, 1, 1)


def cd_date(ts):
    if ts is None:
        return ""
    return (EPOCH + datetime.timedelta(seconds=ts)).strftime("%Y-%m-%d")


def cd_stamp(ts):
    if ts is None:
        return ""
    return (EPOCH + datetime.timedelta(seconds=ts)).strftime("%Y-%m-%dT%H:%M:%S")


def colour_of(blob):
    """'#RRGGBB' uit de plist-blob, of None. De blob bevat de kleur als tekst
    'r g b' met waarden 0..1; bij dynamische kleuren nemen we de eerste."""
    if not blob:
        return None
    m = re.search(rb"(\d\.\d+|\d) (\d\.\d+|\d) (\d\.\d+|\d)", blob)
    if not m:
        return None
    r, g, b = (round(float(x) * 255) for x in m.groups())
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
            "cas": (cas or "").strip(),
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
            "variations": [],
        })

    mcats = sorted({m["category"] for m in materials} | set(rmcat.values()), key=str.lower)
    fcats = sorted({f["category"] for f in formulas} | set(fcat.values()), key=str.lower)
    return {
        "meta": {"schema": 1, "generated": datetime.date.today().isoformat(),
                 "source": "Formulair DataModel.sqlite (flat import)", "uiLanguage": "en"},
        "materialCategories": mcats,
        "formulaCategories": fcats,
        "suppliers": sorted({s for s in supp.values() if s}, key=str.lower),
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
            return o if o == int(o) else round(o, 6)
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
