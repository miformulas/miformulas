"""Bouw 261015a: de teksten van de audit v3 (E1 tot E9) en wat C8 openliet (op bouw 261014b). Faalt op 261014b.
E1 De tooltip van ⚠ zegt wat er is en wat je eraan doet, zonder je een nieuwe versie voor te schrijven; de importpagina
   (één formule en een bestand met meerdere) en de handleiding schrijven die ook niet meer voor.
E2 De tooltip van ⚙ in de volgorde van het venster. E7 De tooltip van ✕ op de opslagbalk wijst naar Welcome.
E3 "Shift-click ticks a range" in Classify several…, Browse the library… en Export my inventory as a library… met een
   muis, en niet op een aanraakscherm.
E4 Eén formulering: "your inventory is not touched" (het laden en vervangen van een library, Remove, Import & export).
E5, E6, C8 Settings op 1366×660 met een library, browseropslag en Install as an app: alles in beeld zonder scrollen,
   Open where you left off en de library elk op één regel, Save to a data file… en Delete the data kept in this browser
   op één rij; op een telefoon geen horizontale schuif.
E8 Geen commentaar meer over Change category. E9 Bij een zoekterm toont een formule zonder categorie haar aantal versies.
Vereist de lokale webserver op poort 8765 (zie README)."""
import json, os, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
TMP = tempfile.mkdtemp()
# zo lang als de gepubliceerde library: haar regel in Settings is de langste die een gebruiker ziet
LIB = {"type": "miformulas-materials", "name": "miFormulas materials library", "version": "2026-10-10c", "licence": "CC BY 4.0",
       "attribution": "miFormulas materials library, https://miformulas.com",
       "source": "Compiled for miFormulas from public sources; odour words, impact and substantivity in our own words.",
       "materials": [{"name": "Ambroxide", "aliases": ["Ambroxan"], "cas": "6790-58-5", "category": "Amber", "pyramid": 4}]
                    + [{"name": f"Proefstof {i:04d}", "category": "Woody", "pyramid": 3} for i in range(1247)]}
E1 = "Not one of this material's dilutions. Change it to one it has with Preserve rel % and exchange solvent."

ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

def pagina(b, **kw):
    ctx = b.new_context(viewport=kw.pop("viewport", {"width": 1280, "height": 900}), **kw)
    ctx.set_default_timeout(8000)
    p = ctx.new_page(); p.msgs = []; p.errs = []
    p.on("dialog", lambda d: (p.msgs.append(d.message), d.accept()))
    p.on("pageerror", lambda e: p.errs.append(str(e)))
    p.goto(URL); p.wait_for_timeout(700); p.click("#btnStarter"); p.wait_for_timeout(1200)
    p.evaluate("pkg => { setMaterialList(normLibrary(pkg)); UNDO.length = 0; render(); }", LIB)
    return ctx, p

def schrijf(naam, tekst):
    pad = os.path.join(TMP, naam); open(pad, "w", encoding="utf-8", newline="").write(tekst); return pad

def open_f(p, naam):
    fid = p.evaluate("n => DATA.formulas.find(x => x.name === n).id", naam)
    p.evaluate("id => { HOMEVIEW = false; HELPVIEW = false; const f = DATA.formulas.find(x => x.id === id); switchTab('F', id, {type: 'v', idx: f.versions.length - 1}); }", fid)
    p.wait_for_timeout(200)
    return fid

def hint(p):   # de uitleg boven de lijst van een venster
    return p.evaluate("() => [...document.querySelectorAll('#dlg .hint')].map(h => h.textContent).join(' | ')")

APP = open(os.path.join(PUB, "index.html"), encoding="utf-8").read()
MAN = open(os.path.join(PUB, "docs", "manual.md"), encoding="utf-8").read()

with sync_playwright() as pw:
    b = pw.chromium.launch()

    # ================= E1: de ⚠, de importpagina en de handleiding =================
    ctx, p = pagina(b)
    fid = open_f(p, "1881 for men")
    p.evaluate("""id => { const v = DATA.formulas.find(x => x.id === id).versions.at(-1);
        const L = v.lines.find(l => !matById(l.materialId).isSolvent); L.dilutionPct = 7.7; render(); }""", fid)
    p.wait_for_timeout(200)
    tips = p.evaluate("() => [...document.querySelectorAll('#content span[title]')].filter(s => s.textContent.trim() === '⚠').map(s => s.title)")
    check(f"E1 de tooltip van ⚠ ({tips[:1]})", tips == [E1])
    een = {"type": "miformulas-import", "name": "Twee sterktes", "lines": [
        {"material": "Brandnew X", "dilutionPct": 10, "weightG": 1}, {"material": "Brandnew X", "dilutionPct": 100, "weightG": 1}]}
    p.set_input_files("#impFile", schrijf("een.json", json.dumps(een))); p.wait_for_timeout(600)
    t = p.text_content("#content")
    check(f"E1 één formule: de importpagina noemt de ⚠ zonder voorschrift ({t[t.find('matched'):][:100]!r})",
          "1 with a dilution you don’t stock (⚠)" in t and "next version" not in t)
    if p.locator("#btnImpCancel").count(): p.click("#btnImpCancel"); p.wait_for_timeout(200)
    meer = {"type": "miformulas-import", "formulas": [
        {"name": "Een", "versions": [{"lines": [{"material": "Brandnew Y", "dilutionPct": 10, "weightG": 1}]}]},
        {"name": "Twee", "versions": [{"lines": [{"material": "Brandnew Y", "dilutionPct": 100, "weightG": 1}]}]}]}
    p.set_input_files("#impFile", schrijf("meer.json", json.dumps(meer))); p.wait_for_timeout(600)
    w = p.evaluate("() => document.querySelector('#impWarn')?.textContent || ''")
    check(f"E1 een bestand met meerdere formules: de ⚠ zonder voorschrift ({w!r})", w == "1 line(s) use a dilution you do not stock (⚠).")
    oud = ["(⚠ convert them in a next version)", "(⚠ convert in a next version)", "available dilution (dilution dialog"]
    check(f"E1 geen tekst in de app schrijft nog een volgende versie voor ({[x for x in oud if x in APP]})", not any(x in APP for x in oud))
    oud = ["when you next make a version, convert", "convert it themselves in a new version", "and you convert in a next version",
           "a dilution you have in a next version"]
    check(f"E1 de handleiding laat de keuze aan jou ({[x for x in oud if x in MAN]})", not any(x in MAN for x in oud)
          and MAN.count("**Preserve rel % and exchange solvent**") >= 2)

    # ================= E2, E7, E8 =================
    check(f"E2 de tooltip van ⚙ ({p.get_attribute('#btnSettings', 'title')!r})",
          p.get_attribute("#btnSettings", "title") == "Settings: number format, materials library, server; install, download or update the app")
    check(f"E7 de tooltip van ✕ op de opslagbalk ({p.get_attribute('#storageHintClose', 'title')!r})",
          p.get_attribute("#storageHintClose", "title") == "Hide this reminder (the Welcome page tells you where your data lives)")
    check("E8 geen commentaar meer over Change category", "Change category / Copy" not in APP)

    # ================= E9 =================
    p.evaluate("() => { HOMEVIEW = false; HELPVIEW = false; switchTab('F', null, null); }"); p.wait_for_timeout(200)
    p.evaluate("""() => { const f = DATA.formulas.find(x => x.name === '1881 for men'); f.category = 'Uncategorised';
        const g = DATA.formulas.find(x => x.name === 'Acqua di Gio for men'); g.category = 'Fougère'; render(); }""")
    p.fill("#searchBox", "for men"); p.wait_for_timeout(300)
    subs = p.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#list .item')].map(r => [r.firstElementChild.textContent,
        [r.querySelector('.sub').firstChild.textContent.replace(/ · $/, ''), r.querySelector('.sub').title]]))""")
    a, g = subs.get("1881 for men"), subs.get("Acqua di Gio for men")
    check(f"E9 een formule zonder categorie toont haar aantal versies, de tooltip blijft ({a})",
          a and a[0].endswith(("version", "versions")) and a[1].startswith("Uncategorised · "))
    check(f"E9 een formule met een categorie toont die nog ({g})", g and g[0] == "Fougère")
    p.fill("#searchBox", ""); p.wait_for_timeout(200)

    # ================= E3 met een muis =================
    p.evaluate("() => classifyItems('M')"); p.wait_for_timeout(300)
    h1 = hint(p); p.click("#dlgCancel"); p.wait_for_timeout(200)
    p.evaluate("() => browseList()"); p.wait_for_timeout(300)
    h2 = hint(p); p.click("#dlgCancel"); p.wait_for_timeout(200)
    p.click("#btnIO"); p.wait_for_timeout(300)
    io = p.text_content("#dlg")
    p.click("#btnExpL"); p.wait_for_timeout(300)
    h3 = hint(p); p.keyboard.press("Escape"); p.wait_for_timeout(200)
    check("E3 met een muis noemen de drie vensters Shift-click", all("Shift-click ticks a range" in h for h in (h1, h2, h3)))

    # ================= E4 =================
    check("E4 Import & export: your inventory is not touched", "your inventory is not touched" in io)
    p.msgs.clear()
    lib2 = dict(LIB, name="Tweede library", materials=LIB["materials"][:3])
    p.set_input_files("#impList", schrijf("lib2.json", json.dumps(lib2))); p.wait_for_timeout(700)
    vervang = [m for m in p.msgs if m.startswith("Replace the materials library")]
    geladen = [m for m in p.msgs if m.startswith("Materials library loaded")]
    check(f"E4 een library vervangen en laden ({p.msgs})", vervang and vervang[0].endswith("\n\nYour inventory is not touched.")
          and geladen and geladen[0].endswith("; your inventory is not touched."))
    p.msgs.clear(); p.click("#btnSettings"); p.wait_for_timeout(300)
    if p.locator("#setListDel").count(): p.click("#setListDel"); p.wait_for_timeout(300)
    check(f"E4 Remove the library ({p.msgs[:1]})", p.msgs and p.msgs[0].endswith("? Your inventory is not touched."))
    oud = ["The materials you own are not touched", "your inventory is unchanged", "your inventory is untouched"]
    check(f"E4 geen andere formulering meer in de app ({[x for x in oud if x in APP]})", not any(x in APP for x in oud))
    check(f"E1-E9 geen paginafouten ({p.errs[:2]})", not p.errs)
    ctx.close()

    # ================= E5, E6, C8: Settings op een laptop =================
    for install in (False, True):
        ctx, p = pagina(b, viewport={"width": 1366, "height": 660})
        if install: p.evaluate("INSTALL_EVT = {prompt(){}, userChoice: Promise.resolve()}")
        p.evaluate("openSettings()"); p.wait_for_timeout(400)
        r = p.evaluate("""() => { const d = document.querySelector('#dlg'), lh = e => Math.round(e.getBoundingClientRect().height);
            const lib = [...d.querySelectorAll('.hint')].find(h => /materials · CC BY/.test(h.textContent));
            const top = id => document.getElementById(id) ? Math.round(document.getElementById(id).getBoundingClientRect().top) : null;
            return {over: d.scrollHeight - d.clientHeight, label: lh(d.querySelector('label[for=setOpenLast]')), lib: lib ? lh(lib) : 0,
              libText: lib ? lib.textContent : '', save: top('setToFile'), del: top('setReset'), inst: top('setInstall'), dl: top('setDownload')}; }""")
        naam = "met Install as an app" if install else "zonder Install as an app"
        check(f"E5/C8 Settings op 1366×660 {naam}: alles in beeld ({r['over']} px te veel)", r["over"] <= 0)
        if not install:
            check(f"E6 Open where you left off op één regel ({r['label']} px)", 0 < r["label"] < 26)
            check(f"E5 de library op één regel ({r['lib']} px: {r['libText']!r})", 0 < r["lib"] < 26 and r["libText"].startswith("Library: "))
            check(f"C8 Save to a data file… en Delete the data kept in this browser op één rij ({r['save']}, {r['del']})",
                  r["save"] is not None and r["save"] == r["del"])
        else:
            check(f"C8 Install as an app en Download the app staan er allebei ({r['inst']}, {r['dl']})", r["inst"] and r["dl"] and r["dl"] > r["inst"])
        ctx.close()

    # ================= E3 en Settings op een telefoon =================
    ctx, p = pagina(b, viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    aanraak = p.evaluate("TOUCHONLY()")
    p.evaluate("() => classifyItems('M')"); p.wait_for_timeout(300)
    h1 = hint(p); p.click("#dlgCancel"); p.wait_for_timeout(200)
    p.evaluate("() => browseList()"); p.wait_for_timeout(300)
    h2 = hint(p); p.click("#dlgCancel"); p.wait_for_timeout(200)
    check(f"E3 op een aanraakscherm ({aanraak}) geen Shift-click ({h1[:60]!r})", aanraak and not any("Shift-click" in h for h in (h1, h2))
          and h1.startswith("Tick the materials, then choose what they get."))
    p.evaluate("openSettings()"); p.wait_for_timeout(400)
    r = p.evaluate("() => { const d = document.querySelector('#dlg'); return [d.scrollWidth - d.clientWidth, Math.round(d.getBoundingClientRect().width), getComputedStyle(d.querySelector('.fieldGrid')).gridTemplateColumns]; }")
    check(f"C8 Settings op een telefoon: geen horizontale schuif, één kolom ({r})", r[0] <= 0 and r[1] <= 390 and len(r[2].split()) == 1)
    check(f"E3/C8 geen paginafouten op de telefoon ({p.errs[:2]})", not p.errs)
    ctx.close()
    b.close()
print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
