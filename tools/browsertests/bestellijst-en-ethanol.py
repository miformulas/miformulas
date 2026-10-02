"""To order compacter en ethanol als diluent, bouw 261002c (2/10/2026).
To order: de kop is Material, Note, Amount, Price €, Product en de knoppen (geen Product URL, geen Added); de datum
staat in de tooltip van de naam en in de lijst links; een productlink toont de winkel met ↗ (de volledige link in de
tooltip, https:// erbij als het ontbreekt) en ✎ ernaast, zonder link een smal veld; Search my shops of Search the web is
een vergrootglas met die woorden als tooltip en als naam voor een schermlezer. Op 1280 px met de lijst links is elke
regel hoogstens 60 px hoog, past de tabel en staan de drie knoppen op één regel; op 1600 px rekt de notitie mee; op 1024
px blijven Delivered… en ✕ bereikbaar. ✎ zet alleen die regel terug in een veld, met de focus erin en de link
geselecteerd; Escape verandert niets, Enter bewaart een nieuwe link met één Undo-stap, Ctrl+Z zet de vorige terug, en een
gewiste link geeft het veld terug.
Ethanol: de starterset draagt geen notitie "in DEP" meer, en de Help zegt dat ethanol het diluent is; §13 beschrijft de
koppeling, ✎ en het vergrootglas.
Vereist een webserver met de inhoud van public\\ op poort 8765 (cd public && python -m http.server 8765)."""
import sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

HEK = "https://www.hekserij.nl/iso-e-super-50-gram"
NIEUW = "https://www.example.com/iso-e-super"

def tap(pg, sel):
    """Klikt als het element er is: op een oudere bouw faalt dan de controle, niet het hele script."""
    if pg.query_selector(sel):
        pg.click(sel); return True
    return False

ROW = """(i) => { const tr = document.querySelectorAll("#content table.ord tbody tr")[i]; if (!tr) return null;
    const a = tr.querySelector("a.shoplink"), inp = tr.querySelector("input[data-ourl]");
    return {link: a ? a.textContent.replace(/\\s+/g, " ").trim() : null, href: a ? a.getAttribute("href") : null,
            target: a ? a.getAttribute("target") : null, rel: a ? a.getAttribute("rel") || "" : "",
            titel: a ? a.getAttribute("title") : null, veld: !!inp, hint: inp ? inp.getAttribute("placeholder") : null,
            veldbreedte: inp ? Math.round(inp.getBoundingClientRect().width) : null,
            naamtip: tr.cells[0].getAttribute("title")}; }"""

MAAT = """() => { const wr = document.querySelector("#content .tblwrap"); if (!wr) return null;
    const rows = [...wr.querySelectorAll("tbody tr")].map(tr => Math.round(tr.getBoundingClientRect().height));
    const mid = s => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect();
        return Math.round(b.top + b.height / 2); };
    const note = wr.querySelector("input[data-onote='0']");
    return {rijen: rows, tabel: Math.round(wr.querySelector("table").getBoundingClientRect().width), wrapper: wr.clientWidth,
            knoppen: ["[data-osearch='0']", "[data-odeliv='0']", "[data-odel='0']"].map(mid),
            notitie: note ? Math.round(note.getBoundingClientRect().width) : 0,
            lijst: getComputedStyle(document.getElementById("sidebar")).display !== "none"}; }"""

RAAK = """(sel) => { const e = document.querySelector(sel); if (!e) return "ontbreekt";
    const b = e.getBoundingClientRect(), x = b.left + b.width/2, y = b.top + b.height/2;
    if (x < 0 || x > innerWidth || y < 0 || y > innerHeight) return "buiten het venster";
    const el = document.elementFromPoint(x, y);
    return el === e || e.contains(el) ? "raakt" : "afgedekt"; }"""

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 950})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(900)

    # ---------- ethanol: de starterset en de Help
    dep = page.evaluate("""() => DATA.materials.filter(m => (m.dilutions||[]).some(d => /in DEP/i.test(d.notes||""))).length""")
    check(f"de starterset draagt geen notitie \"in DEP\" meer ({dep} materialen)", dep == 0)
    help_ = page.evaluate("() => { const t = document.getElementById('manualTpl'); return t ? t.innerHTML : ''; }")
    check("de Help zegt dat ethanol het diluent is (§3)", "<strong>Ethanol is the diluent.</strong> The app takes every dilution to be in ethanol" in help_)
    check("§13: de koppeling met ✎", "A link shows as the name of the shop with ↗, which opens the page; <strong>✎</strong> beside it changes the link." in help_)
    check("§13: het vergrootglas heet Search my shops, en Search the web zonder winkels",
          "The magnifier, <strong>Search my shops</strong>," in help_ and "it is <strong>Search the web</strong>" in help_)
    check("§13: de datum in de lijst links en in de tooltip van de naam",
          "The date an entry was added is in the list on the left and in the tooltip of its name." in help_)
    check("de Help noemt geen kolom Product URL meer (§2)", "Product URL" not in help_ and "<strong>Price €</strong> and <strong>Product</strong>" in help_)

    # ---------- drie bestelregels: een link, geen link, een link zonder https://
    page.evaluate("""([hek]) => { const iso = DATA.materials.find(m => m.name === "Iso E Super"), hed = DATA.materials.find(m => m.name === "Hedione");
        DATA.orderList = [
          {id:"o1", materialId: iso.id, name: iso.name, note: "for the iris trial", amount: 50, unit: "g", price: "12.50", url: hek, added: "2026-09-28"},
          {id:"o2", materialId: null, name: "Orris Absolute", note: "", price: "", added: "2026-10-01"},
          {id:"o3", materialId: hed.id, name: hed.name, note: "", amount: 100, unit: "g", price: "", url: "perfumersapprentice.com/hedione", added: "2026-10-02"}];
        markDirty(); switchTab("T", null, null); }""", [HEK])
    page.wait_for_timeout(600)

    kol = page.evaluate("""() => [...document.querySelectorAll("table.lines.ord thead th")]
        .map(th => getComputedStyle(th).display === "none" ? null : th.textContent.trim()).filter(x => x !== null)""")
    check(f"de kop: Material, Note, Amount, Price €, Product en de knoppen ({kol})",
          kol == ["Material", "Note", "Amount", "Price €", "Product", ""])
    r0, r1, r2 = (page.evaluate(ROW, i) for i in range(3))
    check(f"de datum staat in de tooltip van de naam ({r0 and r0['naamtip']!r})", r0 and r0["naamtip"] == "Added 2026-09-28")
    sub = page.evaluate("() => { const e = document.querySelector(\"#list .item[data-id='o1'] .sub\"); return e ? e.textContent.trim() : null; }")
    check(f"en in de lijst links ({sub!r})", sub == "2026-09-28")
    check(f"een link toont de winkel met ↗ ({r0 and r0['link']!r})", r0 and r0["link"] == "hekserij.nl ↗")
    check(f"de koppeling opent de pagina in een nieuw tabblad, de volledige link in de tooltip ({r0})",
          r0 and r0["href"] == HEK and r0["target"] == "_blank" and "noopener" in r0["rel"] and r0["titel"] == HEK)
    check(f"een regel met een link heeft geen veld, wel ✎ ({r0 and r0['veld']})",
          r0 and not r0["veld"] and page.query_selector("[data-oedit='0']") is not None)
    check(f"een link zonder https:// krijgt het erbij ({r2 and (r2['link'], r2['href'])})",
          r2 and r2["link"] == "perfumersapprentice.com ↗" and r2["href"] == "https://perfumersapprentice.com/hedione")
    check(f"zonder link een smal veld ({r1 and (r1['link'], r1['hint'], r1['veldbreedte'])})",
          r1 and r1["link"] is None and r1["veld"] and r1["hint"] == "paste link…" and r1["veldbreedte"] <= 140)
    zoek = page.evaluate("""() => { const e = document.querySelector("[data-osearch='0']"); if (!e) return null;
        return {svg: !!e.querySelector("svg"), tekst: e.textContent.trim(), naam: e.getAttribute("aria-label"), titel: e.getAttribute("title") || ""}; }""")
    check(f"het vergrootglas: een icoon zonder tekst, Search the web als naam en tooltip ({zoek})",
          zoek and zoek["svg"] and zoek["tekst"] == "" and zoek["naam"] == "Search the web for Iso E Super"
          and zoek["titel"].startswith("Search the web:"))

    # ---------- de maten
    m = page.evaluate(MAAT)
    check(f"1280 px met de lijst links: elke regel hoogstens 60 px ({m and (m['lijst'], m['rijen'])})",
          m and m["lijst"] and len(m["rijen"]) == 3 and max(m["rijen"]) <= 60)
    check(f"1280 px: de tabel past in haar wrapper ({m and (m['tabel'], m['wrapper'])})", m and m["tabel"] <= m["wrapper"])
    k = m and m["knoppen"]
    check(f"1280 px: vergrootglas, Delivered… en ✕ op één regel ({k})", k and None not in k and max(k) - min(k) <= 3)
    w1280 = m and m["notitie"]
    page.set_viewport_size({"width": 1600, "height": 950}); page.wait_for_timeout(450)
    m = page.evaluate(MAAT)
    check(f"1600 px: het notitieveld rekt mee ({w1280} → {m and m['notitie']} px)", m and m["notitie"] - w1280 > 150)
    page.set_viewport_size({"width": 1024, "height": 950}); page.wait_for_timeout(450)
    raak = {n: page.evaluate(RAAK, s) for n, s in (("Delivered", "[data-odeliv='0']"), ("✕", "[data-odel='0']"))}
    check(f"1024 px: Delivered… en ✕ blijven bereikbaar ({raak})", all(v == "raakt" for v in raak.values()))
    page.set_viewport_size({"width": 1280, "height": 950}); page.wait_for_timeout(450)

    # ---------- ✎, Escape, Enter, Ctrl+Z
    tap(page, "[data-oedit='0']"); page.wait_for_timeout(300)
    st = page.evaluate("""() => { const i = document.querySelector("#content [data-ourl='0']"); if (!i) return null;
        return {focus: document.activeElement === i, alles: i.selectionStart === 0 && i.selectionEnd === i.value.length,
                waarde: i.value}; }""")
    check(f"✎ zet de regel terug in een veld, met de focus erin en de link geselecteerd ({st})",
          st and st["focus"] and st["alles"] and st["waarde"] == HEK)
    r2 = page.evaluate(ROW, 2)
    check(f"de andere regels houden hun koppeling ({r2 and r2['link']!r})", r2 and r2["link"] == "perfumersapprentice.com ↗")
    stappen = page.evaluate("UNDO.length")
    if st:
        page.keyboard.press("Escape"); page.wait_for_timeout(300)
    r0 = page.evaluate(ROW, 0)
    na = page.evaluate("[DATA.orderList[0].url, UNDO.length]")
    check(f"Escape: de koppeling terug, de link ongewijzigd, geen Undo-stap ({r0 and r0['link']!r}, {na}, {stappen})",
          r0 and r0["link"] == "hekserij.nl ↗" and na == [HEK, stappen])
    tap(page, "[data-oedit='0']"); page.wait_for_timeout(300)
    if page.query_selector("#content [data-ourl='0']"):
        page.fill("#content [data-ourl='0']", NIEUW); page.press("#content [data-ourl='0']", "Enter"); page.wait_for_timeout(400)
    r0 = page.evaluate(ROW, 0)
    na = page.evaluate("[DATA.orderList[0].url, UNDO.length]")
    check(f"Enter bewaart de nieuwe link, met één Undo-stap ({r0 and r0['link']!r}, {na}, {stappen})",
          r0 and r0["link"] == "example.com ↗" and na == [NIEUW, stappen + 1])
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    r0 = page.evaluate(ROW, 0)
    na = page.evaluate("DATA.orderList[0].url")
    check(f"Ctrl+Z zet de vorige link terug ({r0 and r0['link']!r}, {na!r})", r0 and r0["link"] == "hekserij.nl ↗" and na == HEK)
    tap(page, "[data-oedit='0']"); page.wait_for_timeout(300)
    if page.query_selector("#content [data-ourl='0']"):
        page.fill("#content [data-ourl='0']", ""); page.press("#content [data-ourl='0']", "Enter"); page.wait_for_timeout(400)
    r0 = page.evaluate(ROW, 0)
    check(f"een gewiste link geeft het smalle veld terug ({r0 and (r0['link'], r0['veld'], r0['hint'])})",
          r0 and r0["link"] is None and r0["veld"] and r0["hint"] == "paste link…" and page.evaluate("DATA.orderList[0].url") == "")

    check(f"geen paginafouten ({errs[:2]})", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
sys.exit(1 if fail else 0)
