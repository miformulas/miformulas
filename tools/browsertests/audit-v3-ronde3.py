"""Bouw 261014b: ronde 3 van de audit v3, de oudere kleine punten (op bouw 261014a). Faalt op 261014a.
C17 De materialen staan na het inlezen op naam, en Undo van een nieuwe naam, Add line met een nieuw materiaal, Create
    premix…, de CSV-import en Browse the library… geeft serialize() byte voor byte terug; met miformulas-data.json naast
    public verandert het inlezen niets aan die data (op naam en de library ongewijzigd).
C18 Amount purchased: de lijst links toont het meteen.
C19 Een CAS-nummer dat alleen de library kent, geeft de suggestie uit de library; "12" niet.
C20 Compare noemt een versie met de woorden van de keuzelijst (verborgen importreferentie, 🔒).
C21 Target total en Concentration met hetzelfde getal anders geschreven: geen Undo-stap, geen nieuwe datum.
C22 1366×660 met de lijst open en een lange versienaam: Delete version op de regel van + New version.
C24 + New material…: na een treffer in de library de naam veranderen geeft de categorie van daarvoor terug.
C25 De importpagina telt een ⚠ voor een nieuw materiaal op een tweede dilutie (één formule en een bestand met meerdere).
C26 Een library in een bestand met aliassen als tekst: na het inlezen een lijst, en zoeken werkt.
Vereist de lokale webserver op poort 8765 (zie README)."""
import json, os, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
EIGEN = os.path.join(PUB, "..", "miformulas-data.json")
GEPUB = os.path.join(PUB, "..", "miformulas-materials.json")
TMP = tempfile.mkdtemp()
LIB = {"type": "miformulas-materials", "name": "Proeflibrary", "version": "1", "licence": "CC BY 4.0",
       "materials": [{"name": "Ambroxide", "aliases": ["Ambroxan"], "cas": "6790-58-5", "category": "Amber", "pyramid": 4},
                     {"name": "Testamber X", "cas": "99999-11-2", "category": "Amber", "pyramid": 4},
                     {"name": "Zeta lactone", "cas": "12345-67-8", "category": "Fruity", "pyramid": 1}]}

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

def open_f(p, naam, idx=None):
    fid = p.evaluate("n => DATA.formulas.find(x => x.name === n).id", naam)
    p.evaluate("([id, idx]) => { HOMEVIEW = false; HELPVIEW = false; const f = DATA.formulas.find(x => x.id === id); switchTab('F', id, {type: 'v', idx: idx == null ? f.versions.length - 1 : idx}); }", [fid, idx])
    p.wait_for_timeout(200)
    return fid

def open_m(p, naam):
    mid = p.evaluate("n => DATA.materials.find(m => m.name === n).id", naam)
    p.evaluate("id => { HOMEVIEW = false; HELPVIEW = false; switchTab('M', id, null); }", mid); p.wait_for_timeout(200)
    return mid

ser = lambda p: p.evaluate("serialize()")

with sync_playwright() as pw:
    b = pw.chromium.launch()

    # ================= C17: de volgorde van de materialen =================
    ctx, p = pagina(b)
    op_naam = p.evaluate("() => { const n = DATA.materials.map(m => m.name); return n.every((x, i) => !i || n[i - 1].localeCompare(x) <= 0); }")
    check("C17 de starterset staat na het inlezen op naam", op_naam)
    # een nieuwe naam en Undo
    voor = ser(p); open_m(p, "Hedione")
    p.fill('[data-f="name"]', "Zz hernoemd"); p.keyboard.press("Tab"); p.wait_for_timeout(300)
    p.evaluate("undo()"); p.wait_for_timeout(300)
    check("C17 Undo van een nieuwe naam: serialize() byte voor byte terug", ser(p) == voor)
    # Add line met een nieuw materiaal en Undo
    voor = ser(p); open_f(p, "1881 for men")
    p.fill("#addMat", "Aaa nieuwe stof"); p.press("#addMat", "Enter"); p.wait_for_timeout(500)
    nieuw = p.evaluate("DATA.materials.some(m => m.name === 'Aaa nieuwe stof')")
    p.evaluate("undo()"); p.wait_for_timeout(300)
    check(f"C17 Undo van Add line met een nieuw materiaal ({nieuw}): serialize() byte voor byte terug", nieuw and ser(p) == voor)
    # Create premix… en Undo
    voor = ser(p); fid = open_f(p, "Acqua di Gio for men")
    rij = p.evaluate("() => [...document.querySelectorAll('#content table.ftable tbody tr')].filter(tr => !tr.classList.contains('solvent') && tr.querySelector('input.selCb')).slice(0, 3).map(tr => tr.querySelector('input.selCb').dataset.i)")
    for i in rij: p.check(f"input.selCb[data-i='{i}']")
    p.click("#btnPredil"); p.wait_for_timeout(300); p.click("#dlgOk"); p.wait_for_timeout(500)
    gemaakt = p.evaluate("DATA.materials.some(m => / - PREMIX$/.test(m.name))")
    p.evaluate("undo()"); p.wait_for_timeout(300)
    check(f"C17 Undo van Create premix… ({gemaakt}): serialize() byte voor byte terug", gemaakt and ser(p) == voor)
    # de CSV-import en Undo
    voor = ser(p); p.evaluate("() => switchTab('M', null, null)"); p.wait_for_timeout(200)
    p.set_input_files("#impCsv", schrijf("blad.csv", "Name;Category\r\nAaa blad;Woody\r\nZzz blad;Woody\r\n")); p.wait_for_timeout(800)
    p.click("#dlgOk"); p.wait_for_timeout(800)
    p.evaluate("undo()"); p.wait_for_timeout(300)
    check("C17 Undo van de CSV-import: serialize() byte voor byte terug", ser(p) == voor)
    # Browse the library… en Undo
    voor = ser(p); p.evaluate("() => browseList()"); p.wait_for_timeout(300)
    p.fill("#brQ", "testamber"); p.wait_for_timeout(200)
    p.check("#dlg input[type=checkbox]:not(:disabled)"); p.click("#dlgOk"); p.wait_for_timeout(500)
    toegevoegd = p.evaluate("DATA.materials.some(m => m.name === 'Testamber X')")
    p.evaluate("undo()"); p.wait_for_timeout(300)
    check(f"C17 Undo van Browse the library… ({toegevoegd}): serialize() byte voor byte terug", toegevoegd and ser(p) == voor)

    # ================= C18, C19, C20, C21, C24 =================
    mid = open_m(p, "Hedione")
    p.fill('[data-f="inventory"]', "999 gr"); p.keyboard.press("Tab"); p.wait_for_timeout(300)
    sub = p.evaluate("id => document.querySelector(`#list .item[data-id=\"${id}\"] .sub`)?.textContent", mid)
    check(f"C18 Amount purchased: de lijst toont het meteen ({sub!r})", sub == "999 gr")
    p.evaluate("() => switchTab('M', null, null)"); p.fill("#searchBox", "99999-11-2"); p.wait_for_timeout(300)
    lijst = p.text_content("#list")
    check(f"C19 een CAS-nummer dat alleen de library kent, geeft de suggestie ({lijst[:80]!r})", "Testamber X" in lijst and "+ Add" in lijst)
    p.fill("#searchBox", "12"); p.wait_for_timeout(300)
    check("C19 de term 12 geeft geen suggestie op CAS", "Zeta lactone" not in p.text_content("#list"))
    p.fill("#searchBox", ""); p.wait_for_timeout(200)
    fid = open_f(p, "1881 for men")
    p.evaluate("id => { const v = DATA.formulas.find(x => x.id === id).versions[0]; v.sourceName = 'Bron 1881'; v.hideSource = true; v.imported = true; render(); }", fid)
    p.click("#btnCmp"); p.wait_for_timeout(300)
    opt = p.evaluate("() => document.querySelector('#cmpA')?.options[0]?.textContent || ''")
    check(f"C20 Compare: de verborgen referentie blijft verborgen, met 🔒 ({opt!r})", "Bron 1881" not in opt and opt.endswith("🔒"))
    open_f(p, "1881 for men")
    F = f"DATA.formulas.find(x => x.id === {json.dumps(fid)})"
    p.evaluate("() => { const d = document.querySelector('#scaleW').closest('details'); if (d) d.open = true; }"); p.wait_for_timeout(100)
    n0 = p.evaluate("UNDO.length"); mod = p.evaluate(F + ".modified")
    p.fill("#scaleW", "100"); p.click("#btnApplyScale"); p.wait_for_timeout(300)
    check(f"C21 Target total 100 bij 100.000 g: geen Undo-stap, geen nieuwe datum ({p.evaluate('UNDO.length') - n0})",
          p.evaluate("UNDO.length") == n0 and p.evaluate(F + ".modified") == mod)
    abs_ = p.evaluate("$('#targetAbs').value")
    p.fill("#targetAbs", abs_ + "0"); p.click("#btnSetAbs"); p.wait_for_timeout(300)
    check(f"C21 Concentration {abs_}0 bij {abs_}: geen Undo-stap ({p.evaluate('UNDO.length') - n0})", p.evaluate("UNDO.length") == n0)
    p.evaluate("() => switchTab('M', null, null)"); p.wait_for_timeout(200)
    p.click("#btnNewMat"); p.wait_for_timeout(300)
    was = p.evaluate("$('#nmCat').value")
    p.fill("#nmName", "Ambroxide"); p.wait_for_timeout(200)
    hit = p.evaluate("$('#nmCat').value")
    p.fill("#nmName", "Ambroxide eigen"); p.wait_for_timeout(200)
    na = p.evaluate("$('#nmCat').value")
    check(f"C24 + New material…: de categorie van de treffer ({hit}) gaat weer weg ({was!r} → {na!r})", hit == "Amber" and na == was)
    p.click("#dlgCancel"); p.wait_for_timeout(200)
    check(f"C17-C24 geen paginafouten ({p.errs[:2]})", not p.errs)
    ctx.close()

    # ================= C22: Delete version op de regel, op een laptop met de lijst open =================
    ctx, p = pagina(b, viewport={"width": 1366, "height": 660})
    fid = open_f(p, "1881 for men")
    p.evaluate("id => { const v = DATA.formulas.find(x => x.id === id).versions.at(-1); v.sourceName = 'Bewonder v11 met een lange naam erbij'; v.imported = true; v.date = '2026-08-30'; render(); }", fid)
    p.wait_for_timeout(300)
    r = p.evaluate("() => { const a = document.querySelector('#btnNewV').getBoundingClientRect(), d = document.querySelector('#btnDelV').getBoundingClientRect(), s = document.querySelector('#sidebar').getBoundingClientRect(); return [Math.round(a.top), Math.round(d.top), Math.round(s.width)]; }")
    check(f"C22 met de lijst open ({r[2]} px) staat Delete version op de regel van + New version ({r[0]}, {r[1]})", r[2] > 100 and abs(r[0] - r[1]) < 8)
    ctx.close()

    # ================= C25: een nieuw materiaal op twee diluties =================
    ctx, p = pagina(b)
    een = {"type": "miformulas-import", "name": "Twee sterktes", "lines": [
        {"material": "Brandnew X", "dilutionPct": 10, "weightG": 1}, {"material": "Brandnew X", "dilutionPct": 100, "weightG": 1}]}
    p.set_input_files("#impFile", schrijf("een.json", json.dumps(een))); p.wait_for_timeout(600)
    t = p.text_content("#content")
    check(f"C25 één formule: de pagina telt de tweede sterkte als ⚠ ({t[t.find('matched'):][:110]!r})", "1 with a dilution you don’t stock" in t)
    p.click("#btnImpCancel"); p.wait_for_timeout(200)
    meer = {"type": "miformulas-import", "formulas": [
        {"name": "Een", "versions": [{"lines": [{"material": "Brandnew Y", "dilutionPct": 10, "weightG": 1}]}]},
        {"name": "Twee", "versions": [{"lines": [{"material": "Brandnew Y", "dilutionPct": 100, "weightG": 1}, {"material": "Brandnew Y", "dilutionPct": 10, "weightG": 2}]}]}]}
    p.set_input_files("#impFile", schrijf("meer.json", json.dumps(meer))); p.wait_for_timeout(600)
    w = p.evaluate("() => document.querySelector('#impWarn')?.textContent || ''")
    check(f"C25 een bestand met meerdere formules: één ⚠ ({w!r})", w.startswith("1 line(s) use a dilution"))
    ctx.close()

    # ================= C26 en de eigen data =================
    ctx, p = pagina(b)
    al = p.evaluate("() => migrate({formulas: [], materials: [], materialList: {name: 'L', materials: [{name: 'Rose oxide', aliases: 'Rosenoxid; ROX'}]}}).materialList.materials[0].aliases")
    check(f"C26 aliassen als tekst worden bij het inlezen een lijst ({al})", al == ["Rosenoxid", "ROX"])
    p.evaluate("() => { DATA = migrate({formulas: [], materials: [], materialList: {name: 'L', materials: [{name: 'Rose oxide', aliases: 'Rosenoxid; ROX'}]}}); invalidateMats(); switchTab('M', null, null); render(); }")
    p.fill("#searchBox", "rosenoxid"); p.wait_for_timeout(300)
    check(f"C26 zoeken op zo'n alternatieve naam werkt ({p.errs[:1]})", not p.errs and "Rose oxide" in p.text_content("#list"))
    if os.path.exists(EIGEN):
        lib = json.load(open(GEPUB, encoding="utf-8")) if os.path.exists(GEPUB) else None
        gelijk = p.evaluate("""([t, pkg]) => { DATA = migrate(JSON.parse(t)); if (pkg){ DATA.materialList = null; setMaterialList(normLibrary(pkg)); }
            const s = serialize(); const n = DATA.materials.map(m => m.name);
            return [serialize.call ? JSON.stringify(migrate(JSON.parse(s))) === JSON.stringify(JSON.parse(s)) : false, n.every((x, i) => !i || n[i - 1].localeCompare(x) <= 0)]; }""",
            [open(EIGEN, encoding="utf-8").read(), lib])
        check(f"C17/C26 de eigen data met de library: een tweede keer inlezen verandert niets, en ze staat op naam ({gelijk})", all(gelijk))
    ctx.close()
    b.close()
print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
