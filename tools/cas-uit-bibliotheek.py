#!/usr/bin/env python3
"""Zoek CAS-nummers voor de starterset op in de eigen materialenbibliotheek.

Alleen deterministische regels, geen fuzzy matching: een naam wordt tot een
set varianten herleid (leverancier tussen haakjes weg, oplosmiddel weg,
kwaliteitsaanduiding weg, EO en oil gelijkgesteld) en een treffer telt enkel
als precies één bibliotheekmateriaal met dezelfde variant overblijft.
"""
import json, re, unicodedata, collections, sys

LIB = "/mnt/user-data/uploads/miFormulas/miformulas-data.json"
SET = "/home/claude/out/miformulas-starter.json"

SOLV = r"(?:DEP|DPG|TEC|IPM|BB|EtOH|ethanol|jojo|jojoba|MCT)"
KWAL = {"extra", "pure", "nat", "natural", "coeur", "cur", "coz", "co2",
        "abs", "absolute", "resinoid", "eo", "oil", "op", "md", "cp", "fcf", "dark",
        "dhm", "ibq", "pela", "terpenes", "hydrosol"}


GRIEKS = {"\u03b1": "alpha", "\u03b2": "beta", "\u00df": "beta", "\u03b3": "gamma",
          "\u03b4": "delta", "\u0153": "oe", "\u0152": "oe"}


def norm(s):
    for k, v in GRIEKS.items():
        s = s.replace(k, " " + v + " ")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


def varianten(naam):
    """Alle vormen waaronder deze naam mag matchen."""
    uit = set()
    s = naam
    s = re.sub(r"\([^)]*\)", " ", s)                       # (IFF), (Giv), (Firm)
    s = re.sub(r"\b\d+(?:[.,]\d+)?\s*%", " ", s)           # 50%
    s = re.sub(r"\bin\s+" + SOLV + r"\b", " ", s, flags=re.I)
    s = re.sub(r"\b" + SOLV + r"\b", " ", s, flags=re.I)
    n = norm(s)
    uit.add(n)
    w = n.split()
    # kwaliteitsaanduidingen en losse getallen achteraan afpellen
    while w and (w[-1] in KWAL or re.fullmatch(r"\d+x?", w[-1])):
        w = w[:-1]
        if w:
            uit.add(" ".join(w))
    uit.add(norm(naam))
    uit.discard("")
    return uit


lib = json.load(open(LIB, encoding="utf-8"))
idx = collections.defaultdict(set)
byname = {}
for m in lib["materials"]:
    cas = (m.get("cas") or "").split("\\")[0].strip()
    if not re.fullmatch(r"\d{2,7}-\d{2}-\d", cas or ""):
        continue
    byname[m["name"]] = cas
    for v in varianten(m["name"]):
        idx[v].add(m["name"])

data = json.load(open(SET, encoding="utf-8"))
gevonden, meerdere, geen = [], [], []
for m in sorted(data["materials"], key=lambda x: x["name"].lower()):
    kand = set()
    for v in varianten(m["name"]):
        kand |= idx.get(v, set())
    if len(kand) == 1:
        bron = kand.pop()
        gevonden.append((m["name"], byname[bron], bron))
    elif kand:
        meerdere.append((m["name"], sorted(kand)))
    else:
        geen.append(m["name"])

print("GEVONDEN (%d)" % len(gevonden))
print("%-34s %-16s %s" % ("starterset", "CAS", "uit de bibliotheek"))
for n, c, b in gevonden:
    print("%-34s %-16s %s" % (n, c, "" if norm(n) == norm(b) else b))
print()
print("MEERDERE KANDIDATEN, niet overgenomen (%d)" % len(meerdere))
for n, k in meerdere:
    print("  %-30s %s" % (n, ", ".join(k)[:80]))
print()
eerste = collections.defaultdict(set)
for naam in byname:
    w = norm(naam).split()
    if w:
        eerste[w[0]].add(naam)

sugg = {}
print("NIET GEVONDEN (%d) - met wat er in de bibliotheek op lijkt" % len(geen))
for n in geen:
    w = norm(n).split()
    kand = set()
    for woord in w[:2]:
        kand |= eerste.get(woord, set())
    kand = sorted(kand)[:4]
    if kand:
        sugg[n] = kand
    print("  %-32s %s" % (n, ", ".join(kand)))
json.dump(sugg, open("/home/claude/cas_suggesties.json", "w"), ensure_ascii=False, indent=1)

json.dump({n: c for n, c, _ in gevonden}, open("/home/claude/cas_gevonden.json", "w"),
          ensure_ascii=False, indent=1)
