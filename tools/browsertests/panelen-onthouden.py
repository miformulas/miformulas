"""Bouw 261019c: de panelen onder een formule en op een materiaalpagina beginnen dicht en onthouden hoe je ze liet
(Mathieu, 19/10, 13:00 en 13:15). Notes en Trial log volgden de inhoud en gingen bij elke andere formule of versie weer
open, de panelen van een materiaal ook; Pyramid & categories en IFRA check onthielden hun stand alleen tot je herlaadde.
Nu: dicht om te beginnen, de titel zegt wat erin staat ("Notes – recorded", "Trial log – 1 entry", "Dilutions – 100%
base, 10%"), en één stand per paneel voor alle formules en materialen, op het toestel bewaard (niet in het databestand,
dus geen Undo-stap en niets in een Backup).
Daarnaast de twee kolommen van een materiaalpagina: in 261019b liep de linker over de rechter tussen ongeveer 1170 en
1390 px met de lijst open (audit van de handleiding, 19/10); nu staan ze alleen naast elkaar waar beide passen.
Draait op de lokale webserver (poort 8765, zie README)."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("MIF_URL", "http://localhost:8765/")
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

BOXES = ("notesBox", "trialBox", "catsBox", "ifraBox")

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1366, "height": 900})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1500)

    def open_f(name):
        page.evaluate("n => { const f = DATA.formulas.find(x => x.name === n); switchTab('F', f.id, {type: 'v', idx: f.versions.length - 1}); }", name)
        page.wait_for_timeout(400)
    stand = lambda: page.evaluate("ids => ids.map(i => { const d = document.getElementById(i); return d ? d.open : null; })", list(BOXES))
    titel = lambda i: (page.text_content(f"#{i} summary") or "").strip()
    def herlaad():
        page.reload(); page.wait_for_timeout(1500)

    # notes and one trial-log entry on the latest version of Jasmin 231; Brut keeps none
    page.evaluate("""async () => { const f = DATA.formulas.find(x => x.name === 'Jasmin 231'); const v = f.versions[f.versions.length - 1];
        v.notes = 'Idem als v1 maar met de helft Ald C10.'; v.trials = [{date: '2026-10-19', text: 'day 3, top too sharp'}];
        markDirty(); await saveData(); }""")
    herlaad()

    # ---------- 1. closed to start, and the titles say what is in them ----------
    open_f("Jasmin 231")
    check(f"de vier panelen zijn dicht bij een eerste bezoek ({stand()})", stand() == [False, False, False, False])
    check(f"Notes met inhoud zegt het in de titel ({titel('notesBox')!r})", titel("notesBox") == "Notes – recorded")
    check(f"Trial log telt zijn regels ({titel('trialBox')!r})", titel("trialBox") == "Trial log – 1 entry")
    open_f("Brut")
    check(f"Notes zonder inhoud zegt empty ({titel('notesBox')!r})", titel("notesBox") == "Notes – empty")
    check("ook daar alles dicht", stand() == [False, False, False, False])

    # ---------- 2. one state per panel, for every formula ----------
    open_f("Jasmin 231")
    page.click("#notesBox summary"); page.wait_for_timeout(200)
    open_f("Brut")
    check(f"Notes opengezet blijft open op een andere formule, ook zonder inhoud ({stand()})", stand()[0] is True)
    open_f("Jasmin 231")
    check("en terug op de eerste formule", stand()[0] is True)
    page.evaluate("() => { const f = DATA.formulas.find(x => x.name === 'Jasmin 231'); switchTab('F', f.id, {type: 'v', idx: 0}); }"); page.wait_for_timeout(400)
    check("ook op een andere versie", stand()[0] is True)
    open_f("Jasmin 231")
    page.click("#notesBox summary"); page.wait_for_timeout(200)
    open_f("Brut"); open_f("Jasmin 231")
    check(f"dichtgezet blijft dicht, ook met inhoud ({stand()})", stand()[0] is False)

    # ---------- 3. kept on the device, not in the data ----------
    keys0 = page.evaluate("Object.keys(JSON.parse(serialize())).sort().join(',')")
    for i in ("notesBox", "trialBox", "catsBox", "ifraBox"):
        page.click(f"#{i} summary"); page.wait_for_timeout(150)
    check(f"alle vier open ({stand()})", stand() == [True, True, True, True])
    check("een paneel open of dicht zetten is geen wijziging van de data (geen Unsaved changes)",
          page.evaluate("DIRTY") is False and "Unsaved" not in (page.text_content("#saveState") or ""))
    check("en het databestand krijgt er niets bij", page.evaluate("Object.keys(JSON.parse(serialize())).sort().join(',')") == keys0)
    page.wait_for_timeout(300)
    herlaad(); open_f("Jasmin 231")
    check(f"na herladen staan ze zoals je ze liet, ook Pyramid & categories en IFRA check ({stand()})", stand() == [True, True, True, True])
    page.click("#notesBox summary"); page.click("#ifraBox summary"); page.wait_for_timeout(300)
    herlaad(); open_f("Brut")
    check(f"Notes en IFRA check dicht, Trial log en Pyramid & categories open, na herladen en op een andere formule ({stand()})",
          stand() == [False, True, True, False])
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    check("Undo verandert niets aan de panelen", stand() == [False, True, True, False])

    # ---------- 4. the panels of a material ----------
    MB = ["dilBox", "stockBox", "descBox", "useBox"]
    def open_m(name):
        page.evaluate("n => { const m = DATA.materials.find(x => x.name === n); switchTab('M', m.id, null); }", name); page.wait_for_timeout(400)
    mstand = lambda: page.evaluate("ids => ids.map(i => { const d = document.getElementById(i); return d ? d.open : null; })", MB)
    open_m("Geraniol")
    check(f"de vier panelen van een materiaal zijn dicht bij een eerste bezoek ({mstand()})", mstand() == [False, False, False, False])
    ts = [titel(i) for i in MB]
    check(f"hun titels zeggen wat erin staat ({ts})", ts[0] == "Dilutions – 100% base, 10%" and ts[1] == "Stock – not tracked"
          and ts[2] == "Description – empty" and ts[3] == "Usage in formulas – 5 formulas")
    page.evaluate("async () => { const m = DATA.materials.find(x => x.name === 'Geraniol'); m.description = 'Rosy, fresh.'; markDirty(); await saveData(); render(); }")
    page.wait_for_timeout(300)
    check(f"Description met inhoud zegt recorded ({titel('descBox')!r})", titel("descBox") == "Description – recorded" and mstand()[2] is False)
    page.click("#dilBox summary"); page.click("#descBox summary"); page.wait_for_timeout(200)
    open_m("Benzyl Acetate")
    check(f"Dilutions en Description opengezet blijven open op een ander materiaal ({mstand()})", mstand() == [True, False, True, False])
    page.wait_for_timeout(300)
    herlaad(); open_m("Geraniol")
    check(f"ook na herladen ({mstand()})", mstand() == [True, False, True, False])

    # ---------- 5. the two columns of a material page never run over each other ----------
    JS = """() => { const g = [...document.querySelectorAll('.mCols > .fieldGrid')]; if (g.length !== 2) return null;
      const [a, b] = g.map(x => x.getBoundingClientRect()); const c = document.querySelector('.mCols').getBoundingClientRect();
      const right = el => Math.max(...[...el.querySelectorAll('*')].map(e => e.getBoundingClientRect()).filter(r => r.width).map(r => r.right));
      return {two: Math.abs(a.top - b.top) < 4, gap: Math.round(b.left - right(g[0])), out: Math.round(Math.max(right(g[0]), right(g[1])) - c.right)}; }"""
    for zij in ("met de lijst open", "met de lijst dicht"):
        slecht, twee = [], []
        for w in range(1000, 1941, 20):
            page.set_viewport_size({"width": w, "height": 900}); page.wait_for_timeout(40)
            r = page.evaluate(JS)
            if not r or (r["two"] and r["gap"] < 8) or r["out"] > 1: slecht.append((w, r))
            if r and r["two"]: twee.append(w)
        check(f"de velden overlappen nergens tussen 1000 en 1940 px, {zij} ({slecht[:3]})", not slecht)
        check(f"en ze staan naast elkaar vanaf {twee[0] if twee else '–'} px", bool(twee) and twee[-1] == 1940)
        page.keyboard.press("Control+b"); page.wait_for_timeout(300)
    page.set_viewport_size({"width": 740, "height": 900}); page.keyboard.press("Control+b"); page.wait_for_timeout(300)
    r = page.evaluate(JS)
    check(f"op een smal venster met de lijst open loopt niets buiten de pagina ({r})", r and r["out"] <= 1)
    page.set_viewport_size({"width": 1366, "height": 900})

    # ---------- 6. another browser (another device) starts closed ----------
    ctx2 = b.new_context(viewport={"width": 1366, "height": 900})
    p2 = ctx2.new_page()
    p2.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    p2.goto(URL); p2.wait_for_timeout(800); p2.click("#btnStarter"); p2.wait_for_timeout(1500)
    p2.evaluate("() => { const f = DATA.formulas.find(x => x.name === 'Brut'); switchTab('F', f.id, {type: 'v', idx: f.versions.length - 1}); }"); p2.wait_for_timeout(400)
    st2 = p2.evaluate("ids => ids.map(i => document.getElementById(i)?.open)", list(BOXES))
    check(f"een ander toestel begint dicht ({st2})", st2 == [False, False, False, False])
    p2.evaluate("() => { const m = DATA.materials.find(x => x.name === 'Geraniol'); switchTab('M', m.id, null); }"); p2.wait_for_timeout(400)
    st3 = p2.evaluate("ids => ids.map(i => document.getElementById(i)?.open)", ["dilBox", "stockBox", "descBox", "useBox"])
    check(f"ook op een materiaalpagina ({st3})", st3 == [False, False, False, False])

    check("geen fouten op de pagina", not errs)
    if errs: print(errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
