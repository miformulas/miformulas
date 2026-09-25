"""Checks every reference to a chapter of the manual, everywhere outside the manual itself.

    python tools/controleer-ankers.py

Three passes, in a second, without a browser and without a network:

A. Anchors. docs/manual.md and docs/ai-prompts.md hold the headings; tools/bouw-docs.py turns each into
   an id with its slug(). Every "#s<n>-<slug>" in index.html, docs/manual.html, docs/ai-prompts.html,
   formulair-import.html and tools/formulair-import.src.html has to be one of the ids of the page it
   points at (the manual, or the prompts page). An anchor that is not is an error: the reader lands at
   the top of that page instead of on the chapter.

B. The number against the anchor. Where a sentence says "section 19" next to a link "#s19-...", the two
   have to agree. A renumbering that moves a chapter but leaves the sentence alone shows up here.

C. The bare mentions. Files that name a chapter without linking to it (server/worker.js, README.md,
   docs/ai-prompts.md, the app's own texts) cannot be judged by a script: it does not know what was
   meant. They are printed with the title of the chapter the number now points at, for a glance. This
   is where "Section 20 -> 20. Import and export" in worker.js gives itself away.

D. The numbers the documentation copies out of the code. The build stamp in "This manual describes build
   ..." and the Worker's VERSION in `{"worker":N}` are written by hand into the texts, and both have
   already travelled wrong into a release. Every mention has to match what the code says. So does the
   number of fetch( calls that section 3 counts for whoever wants to check what the app does on the
   network: build 260922g added one and the sentence stayed at six.

Run it after every renumbering of the manual and before a release. Exit code 1 when A, B or D find
something; pass C never fails the run.
"""
import importlib.util, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, ".."))
# the files that link to the manual, and the files that only name a chapter
LINKERS = ["index.html", "docs/manual.html", "docs/ai-prompts.html",
           "formulair-import.html", "tools/formulair-import.src.html"]
NAMERS = ["index.html", "formulair-import.html", "tools/formulair-import.src.html",
          "server/worker.js", "server/data.php", "docs/ai-prompts.md", "README.md"]

ANCHOR = re.compile(r"#(s\d+-[a-z0-9-]+)")
SECTION = re.compile(r"\b([Ss]ections?)\s+(\d+)\b")
fouten = []


def lees(rel):
    p = os.path.join(PUB, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def zonder_handleiding(rel, s):
    """index.html carries the whole manual as its Help text; that part is generated, so pass C skips it."""
    if rel != "index.html":
        return s
    m = re.search(r"<!-- MANUAL:BEGIN.*?<!-- MANUAL:END -->", s, flags=re.S)
    return s[:m.start()] + " " * (m.end() - m.start()) + s[m.end():] if m else s


def slugger():
    """the slug() of bouw-docs.py itself, so the two can never drift apart"""
    spec = importlib.util.spec_from_file_location("bouwdocs", os.path.join(HERE, "bouw-docs.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.slug


def koppen(md, htm):
    """{number: (id, title)} of a Markdown source, or of the built page when bouw-docs is not importable"""
    try:
        slug = slugger()
    except Exception as e:
        print(f"   (bouw-docs.py not importable: {e}; ids read from the built page)")
        ids = re.findall(r'<h2 id="(s\d+-[a-z0-9-]+)"[^>]*>(.*?)</h2>', lees(htm) or "")
        return {int(re.match(r"s(\d+)-", i).group(1)): (i, re.sub("<[^>]+>", "", t)) for i, t in ids}
    out = {}
    for t in re.findall(r"^## (.+)$", open(os.path.join(PUB, md), encoding="utf-8").read(), flags=re.M):
        m = re.match(r"(\d+)\.", t)
        if m:
            out[int(m.group(1))] = (slug(t), t)
    return out


HOOFD = koppen("docs/manual.md", "docs/manual.html")            # the manual
PROMPT = koppen("docs/ai-prompts.md", "docs/ai-prompts.html")   # the prompts page
IDS = {i for i, _ in HOOFD.values()}
PIDS = {i for i, _ in PROMPT.values()}


def doel(voor):
    """which page an anchor points at, read from the url right in front of the #"""
    url = re.search(r'[\"\'`(]([^\"\'`(]*)$', voor)
    u = (url.group(1) if url else "").lower()
    return "prompts" if ("ai-prompts" in u or "prompts}" in u) else "manual"


print(f"miFormulas: de verwijzingen naar de handleiding "
      f"({len(HOOFD)} genummerde hoofdstukken in docs/manual.md, {len(PROMPT)} prompts in ai-prompts.md)\n")

# ---------- A. de ankers ----------
print("A. Ankers")
for rel in LINKERS:
    s = lees(rel)
    if s is None:
        continue
    gevonden, stuk = set(), []
    for m in ANCHOR.finditer(s):
        a, waar = m.group(1), doel(s[max(0, m.start() - 120):m.start()])
        gevonden.add(a)
        if a not in (PIDS if waar == "prompts" else IDS):
            regel = s[:m.start()].count("\n") + 1
            stuk.append(a)
            fouten.append(f"{rel}:{regel}: #{a} bestaat niet in "
                          + ("docs/ai-prompts.md" if waar == "prompts" else "docs/manual.md"))
    print(f"   {rel:<32} {len(gevonden):>3} uniek" + ("" if not stuk else "   DOOD: " + ", ".join(sorted(set(stuk)))))

# ---------- B. het getal tegenover het anker ----------
print("\nB. Het getal tegenover het anker")
paren = 0
for rel in LINKERS:
    s = lees(rel)
    if s is None:
        continue
    for m in ANCHOR.finditer(s):
        voor, na = s[max(0, m.start() - 110):m.start()], s[m.end():m.end() + 60]
        if doel(voor) == "prompts":
            continue                                     # a prompt number is not a chapter number
        nr = int(re.match(r"s(\d+)-", m.group(1)).group(1))
        # "section <a href="#s20-...">20</a>" puts the number in the link text, right after the anchor
        tekst = re.search(r'^[^>]*>\s*(\d+)\s*<', na)
        vorige = list(SECTION.finditer(voor))
        if tekst:
            gezegd, waar = int(tekst.group(1)), "in de linktekst"
        elif vorige and "GPL" not in voor[-60:] and "additional terms" not in voor[-60:]:
            gezegd, waar = int(vorige[-1].group(2)), "in de zin ervoor"
        else:
            continue
        paren += 1
        if gezegd != nr:
            regel = s[:m.start()].count("\n") + 1
            fouten.append(f"{rel}:{regel}: de zin zegt {gezegd} ({waar}), het anker #{m.group(1)} wijst naar {nr}")
print(f"   {paren} paren gecontroleerd")

# ---------- C. de kale vermeldingen ----------
print("\nC. Kale vermeldingen (nazien; het script kan hier niet beslissen)")
rijen = []
for rel in NAMERS:
    s = lees(rel)
    if s is None:
        continue
    s = zonder_handleiding(rel, s)
    for m in SECTION.finditer(s):
        nr = int(m.group(2))
        rond = s[max(0, m.start() - 40):m.end() + 40]
        if "GPL" in rond or "additional terms" in rond:
            continue                                     # "section 7 of the GPL" is not a chapter
        if ANCHOR.search(s[m.end():m.end() + 80]) or ANCHOR.search(s[max(0, m.start() - 80):m.start()]):
            continue                                     # that one was pass B's business
        titel = HOOFD.get(nr, (None, "BESTAAT NIET"))[1]
        rijen.append((rel, s[:m.start()].count("\n") + 1, m.group(0), titel))
for rel, regel, tekst, titel in rijen:
    print(f"   {rel + ':' + str(regel):<34} {tekst:<12} -> {titel}")
if not rijen:
    print("   geen")

# ---------- D. de getallen die de documentatie uit de code overschrijft ----------
# Twee getallen staan in de teksten omdat de code ze zegt, en ze reizen met de hand mee. Allebei zijn ze
# al eens verkeerd in een release beland: de bouwstempel in v1.6 (de handleiding noemde 260920n terwijl
# de app 260920o was) en het workernummer bij 260920i (de handleiding hield 3 aan terwijl de code 5 werd).
print("\nD. Getallen die de code bepaalt")


def uit_code(rel, patroon, wat):
    s = lees(rel)
    m = re.search(patroon, s or "")
    if not m:
        fouten.append(f"{rel}: {wat} niet gevonden, dus niets om de teksten tegen te houden")
        return None
    return m.group(1)


def vergelijk(waarde, patroon, wat, bestanden):
    """Elke plaats waar de teksten dit getal noemen, moet het getal van de code noemen."""
    n = 0
    for rel in bestanden:
        s = lees(rel)
        if s is None:
            continue
        for m in re.finditer(patroon, s):
            n += 1
            if m.group(1) != waarde:
                regel = s[:m.start()].count("\n") + 1
                fouten.append(f"{rel}:{regel}: {wat} staat hier op {m.group(1)}, de code zegt {waarde}")
    print(f"   {wat}: {waarde} volgens de code, {n} vermelding(en) in de teksten")
    return n


bouw = uit_code("index.html", r'id="build"[^>]*>\s*([0-9a-z]+)\s*<', "de bouwstempel")
if bouw:
    vergelijk(bouw, r"describes build ([0-9a-z]+)", "de bouwstempel",
              ["docs/manual.md", "docs/manual.html", "index.html"])
wv = uit_code("server/worker.js", r"const VERSION = (\d+)", "het versienummer van de Worker")
if wv:
    vergelijk(wv, r'"worker":\s*(\d+)', "het versienummer van de Worker",
              ["docs/manual.md", "docs/manual.html", "index.html", "server/worker.js", "README.md",
               "docs/ai-prompts.md", "docs/ai-prompts.html"])

# §3 telt de fetch( van de code in woorden ("There are seven in the code", "the eighth hit is this sentence"): de
# handleiding zit zelf in index.html, dus die ene treffer telt er één bij
TAL = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
RANG = ["zeroth", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
        "eleventh", "twelfth", "thirteenth"]
nf = zonder_handleiding("index.html", lees("index.html") or "").count("fetch(")
if not nf:
    fouten.append("index.html: geen enkele fetch( gevonden, dus niets om §3 tegen te houden")
else:
    n = 0
    for rel in ["docs/manual.md", "docs/manual.html", "index.html"]:
        s = lees(rel)
        if s is None:
            continue
        for patroon, lijst, moet, wat in [(r"There are (\w+) in the code", TAL, nf, "het aantal"),
                                          (r"the (\w+) hit is this sentence", RANG, nf + 1, "de treffer van de zin zelf")]:
            for m in re.finditer(patroon, s):
                n += 1
                if m.group(1) not in lijst or lijst.index(m.group(1)) != moet:
                    regel = s[:m.start()].count("\n") + 1
                    fouten.append(f"{rel}:{regel}: §3 zegt '{m.group(1)}' voor {wat}, de code heeft {nf} fetch(")
    print(f"   het aantal fetch( in de code: {nf}, {n} vermelding(en) in de teksten")
    if not n:
        fouten.append("docs/manual.md: de telling van fetch( in §3 niet gevonden")

print()
for f in fouten:
    print("FOUT " + f)
print(f"{len(fouten)} probleem(en)" if fouten else "geen problemen")
sys.exit(1 if fouten else 0)
