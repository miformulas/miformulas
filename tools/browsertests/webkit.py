"""WebKit tegenover Chromium: dezelfde app, dezelfde proeven, twee motoren (bouw 260920o).

De hele reeks draait op Chromium, dus een verschil dat alleen WebKit maakt ziet niemand. WebKit is de
motor van Safari (JavaScriptCore en WebCore), dus wat hier uiteenloopt, loopt in Safari waarschijnlijk
ook uiteen. Omgekeerd geldt dat niet: dit is WebKitGTK op Linux, geen Safari. Wat het NIET kan zien
staat onderaan in dit bestand.

    sudo apt-get install -y webkit2gtk-driver xvfb && pip install selenium
    cd public && python -m http.server 8765
    python tools/browsertests/webkit.py

Zonder WebKitWebDriver stopt het script met exitcode 2 en zegt het welk pakket ontbreekt, zodat het in
een reeks geen valse fout geeft. Een pad als argument test een andere kopie van de app.
"""
import json, os, shutil, subprocess, sys, tempfile, time

URL = os.environ.get("MIF_URL", "http://localhost:8765/")
HERE = os.path.dirname(os.path.abspath(__file__))
ok = fail = 0


def check(naam, cond, extra=""):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam + (("  <- " + extra) if (extra and not cond) else ""))


# ---------------------------------------------------------------- de proeven
# Elke proef is JavaScript dat in beide motoren draait, na het laden van de starterset. Wat hier
# uiteenloopt is een motorverschil, geen appfout: daarom staat de uitkomst van Chromium naast die van
# WebKit in de melding, en niet een verwachte waarde in dit bestand.
PROEVEN = {
    # de rekenkern: elke versie van elke formule, tot op de milligram
    "rekenkern": """(() => DATA.formulas.map(f => f.name + "|" + f.versions.map(v => {
        const K = calc(v.lines);
        return [K.totalW.toFixed(3), K.totalAbsPct.toFixed(2), K.totalCost.toFixed(4),
                v.lines.length].join(":");
      }).join(",")).join("\\n"))()""",
    # elke regel apart: dilutiefactor, inhoud, rel % en abs %
    "regels": """(() => DATA.formulas.slice(0, 6).map(f => {
        const v = f.versions[f.versions.length - 1], K = calc(v.lines);
        return K.rows.map(r => [r.w, r.dil, r.cont, r.rel, r.absPct].map(x =>
          typeof x === "number" ? x.toFixed(6) : String(x)).join("/")).join(";");
      }).join("\\n"))()""",
    # getalnotatie: de app draait op de taal van het toestel, dus die zetten we vast
    "getallen": """(() => ["fmt", "fmtS", "fmtIn"].map(n =>
        typeof window[n] === "function"
          ? [0, 0.00045, 0.0004999, 1/3, 46.2564, 1234.5678, 1e6].map(x => String(window[n](x, 3))).join("|")
          : "geen " + n).join("\\n"))()""",
    "parse": """(() => ["2,5", "1,234.5", "2.5", " 7 ", "1e3", "abc", "", "-3"].map(s =>
        String(typeof parseNum === "function" ? parseNum(s) : "geen parseNum")).join("|"))()""",
    "csv_getal": """(() => typeof wCsv === "function"
        ? [0.0004, 0.004, 1.5, 1/3, 98.9, 0].map(x => wCsv(x)).join("|") : "geen wCsv")()""",
    # tekst: vouwing en volgorde beslissen welk materiaal een regel raakt
    "vouwing": """(() => typeof fold === "function"
        ? ["Patchouli C\\u0153ur", "Ha\\u00efti", "Stra\\u00dfe", "\\u0141\\u00f3d\\u017a", "\\u00c6gir",
           "\\u00d8re", "\\u0110uro"].map(s => fold(s)).join("|") : "geen fold")()""",
    "volgorde": """(() => ["Ylang","\\u00c9lemi","Zdravetz","Ambrette","\\u0152illet","\\u00c6gir",
        "elemi","\\u00c5ngstr\\u00f6m"].sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase(), "en")).join("|"))()""",
    "normname": """(() => typeof normName === "function"
        ? normName("  Vertofix   C\\u0153ur  ") + "|" + normName("HEDIONE") : "geen normName")()""",
    # datums: de app schrijft ze zelf en leest ze terug
    "datums": """(() => [typeof today === "function" ? today() : "geen today",
        new Date("2026-09-22").toISOString().slice(0, 10),
        new Date("2026-09-22T00:00:00").getFullYear() + "-" + (new Date("2026-09-22T00:00:00").getMonth() + 1),
        String(new Date("21/09/2026").getTime())].join("|"))()""",
    # de app zelf
    "gebruiksindex": "Object.keys(USAGE || {}).length",
    "materialen": "DATA.materials.length + '/' + DATA.formulas.length",
    "opslagstand": "[DEMO, REMOTE, !!HANDLE].join('|')",
    # de uitvoer die de gebruiker uit de app draagt
    "uitvoer_json": """(() => typeof serialize === "function" ? String(serialize().length) : "geen serialize")()""",
    "csv_kolommen": """(() => typeof CSV_FIELDS === "undefined" ? "geen CSV_FIELDS"
        : CSV_FIELDS.map(f => f.label).join("~"))()""",
    "csv_cel": """(() => typeof nBE === "function"
        ? [0.12, 0.96, 1/3, 1234.5, 0].map(x => String(nBE(x))).join("|") : "geen nBE")()""",
    "csv_scheiding": """(() => [typeof CSVSEP === "undefined" ? "?" : CSVSEP,
        (1.5).toLocaleString(LOCALE), (1234.5).toLocaleString(LOCALE)].join("|"))()""",
}

# Wat de motor wel of niet heeft. Hier staat de uitkomst van Chromium er niet naast: dit zijn
# eigenschappen waarvan de app aanneemt dat ze er zijn, of juist dat ze er niet hoeven te zijn.
AANWEZIG = """(() => {
  const g = {
    structuredClone: typeof structuredClone,
    queueMicrotask: typeof queueMicrotask,
    indexedDB: typeof indexedDB,
    dialogElement: typeof HTMLDialogElement,
    showModal: typeof HTMLDialogElement !== "undefined" && typeof HTMLDialogElement.prototype.showModal,
    replaceAll: typeof String.prototype.replaceAll,
    at: typeof Array.prototype.at,
    hasOwn: typeof Object.hasOwn,
    flat: typeof Array.prototype.flat,
    IntlNumberFormat: typeof Intl.NumberFormat,
    localeCompare: typeof String.prototype.localeCompare,
    CSSsupports: typeof CSS.supports,
    has_selector: CSS.supports("selector(:has(a))"),
    aspect_ratio: CSS.supports("aspect-ratio: 1"),
    inset: CSS.supports("inset: 0"),
    gap_flex: CSS.supports("gap: 1px"),
    lookbehind: (() => { try { new RegExp("(?<=a)b"); return true; } catch (e) { return false; } })(),
    namedGroups: (() => { try { return "ab".replace(/(?<x>a)/, "$<x>") === "ab"; } catch (e) { return false; } })(),
    // deze twee mogen ontbreken: de bestandsmodus is Chrome en Edge
    showSaveFilePicker: typeof window.showSaveFilePicker,
    showOpenFilePicker: typeof window.showOpenFilePicker,
    storagePersist: typeof (navigator.storage && navigator.storage.persist),
  };
  return g;
})()"""

# Elke stijlregel die de motor werkelijk heeft ingelezen. Een regel die Chromium wel leest en WebKit
# niet, is een stuk opmaak dat in Safari ontbreekt zonder dat iets het zegt.
CSSREGELS = """(() => {
  const uit = [];
  // Een gewone stijlregel draagt sinds CSS-nesting zelf ook een (lege) cssRules, dus op die eigenschap
  // alleen aftakken laat elke selector vallen. Allebei kijken dus.
  const loop = (lijst, pad) => { for (const r of lijst) {
      if (r.selectorText) uit.push(pad + r.selectorText);
      if (r.cssRules && r.cssRules.length)
        loop(r.cssRules, pad + (r.conditionText || (r.media && r.media.mediaText) || r.name || r.selectorText || "") + " { ");
    } };
  for (const sh of document.styleSheets) { let rs; try { rs = sh.cssRules; } catch (e) { continue; } loop(rs, ""); }
  return uit;
})()"""


def chromium_run():
    from playwright.sync_api import sync_playwright
    uit = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, locale="en-GB")
        pg = ctx.new_page()
        fouten = []
        pg.on("pageerror", lambda e: fouten.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(900)
        pg.click("#btnStarter"); pg.wait_for_timeout(2500)
        for k, js in PROEVEN.items():
            try: uit[k] = pg.evaluate("(" + js + ")")
            except Exception as e: uit[k] = "FOUT " + str(e)[:150]
        uit["__aanwezig"] = pg.evaluate("(" + AANWEZIG + ")")
        uit["__css"] = pg.evaluate("(" + CSSREGELS + ")")
        uit["__fouten"] = fouten
        b.close()
    return uit


def webkit_run():
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    os.environ["DISPLAY"] = ":99"
    os.environ.setdefault("LANG", "en_GB.UTF-8")
    xv = subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1400x1000x24"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    o = webdriver.WebKitGTKOptions(); o.add_argument("--automation")
    d = webdriver.WebKitGTK(options=o)
    uit = {}
    try:
        d.set_window_size(1280, 900)
        d.get(URL)
        d.execute_script("window.__err=[]; window.addEventListener('error', e => window.__err.push(String(e.message)));")
        time.sleep(2)
        d.find_element(By.ID, "btnStarter").click(); time.sleep(3)
        for k, js in PROEVEN.items():
            try: uit[k] = d.execute_script("return (" + js + ")")
            except Exception as e: uit[k] = "FOUT " + str(e)[:150]
        uit["__aanwezig"] = d.execute_script("return (" + AANWEZIG + ")")
        uit["__css"] = d.execute_script("return (" + CSSREGELS + ")")
        uit["__fouten"] = d.execute_script("return window.__err")
        # eigen proeven die niet over pariteit gaan maar over Safari zelf
        uit["__idb"] = d.execute_script("return !!idb.db")
        d.execute_script("DATA.formulas[0].name = 'WebKit round trip'; markDirty(); saveData();")
        time.sleep(1.5)
        d.get(URL); time.sleep(3)
        uit["__naherladen"] = d.execute_script(
            "return DATA ? DATA.formulas.map(f => f.name).indexOf('WebKit round trip') : -2")
        uit["__balk"] = d.execute_script(
            "return document.querySelector('#storageHint') ? !document.querySelector('#storageHint').hidden : null")
    finally:
        try: d.quit()
        except Exception: pass
        xv.terminate()
    return uit


def main():
    if not shutil.which("WebKitWebDriver"):
        print("WebKitWebDriver ontbreekt: sudo apt-get install -y webkit2gtk-driver xvfb")
        sys.exit(2)
    if not shutil.which("Xvfb"):
        print("Xvfb ontbreekt: sudo apt-get install -y xvfb")
        sys.exit(2)

    print("Chromium…"); c = chromium_run()
    print("WebKit…");   w = webkit_run()
    uitslag = os.path.join(tempfile.gettempdir(), "webkit-uitslag.json")
    json.dump({"chromium": c, "webkit": w}, open(uitslag, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print()
    check("de app start in WebKit en laadt de starterset",
          isinstance(w.get("materialen"), str) and w["materialen"] == c["materialen"],
          "WebKit %r, Chromium %r" % (w.get("materialen"), c.get("materialen")))
    check("geen JavaScript-fouten in WebKit", not w.get("__fouten"), str(w.get("__fouten"))[:200])
    check("geen JavaScript-fouten in Chromium", not c.get("__fouten"), str(c.get("__fouten"))[:200])

    for k in PROEVEN:
        a, b = w.get(k), c.get(k)
        kort = lambda x: (x if isinstance(x, str) else json.dumps(x))[:120]
        check("zelfde uitkomst in beide motoren: " + k, a == b,
              "WebKit %s | Chromium %s" % (kort(a), kort(b)))

    # de eigenschappen die er moeten zijn
    moet = ["structuredClone", "queueMicrotask", "indexedDB", "dialogElement", "showModal", "replaceAll",
            "at", "hasOwn", "flat", "IntlNumberFormat", "localeCompare", "CSSsupports", "lookbehind",
            "namedGroups", "has_selector", "aspect_ratio", "inset", "gap_flex"]
    wa = w.get("__aanwezig") or {}
    ontbreekt = [k for k in moet if not wa.get(k) or wa.get(k) == "undefined"]
    check("WebKit heeft alles wat de app nodig heeft", not ontbreekt, "ontbreekt: " + ", ".join(ontbreekt))
    check("de bestandsmodus is er in WebKit niet, en dat hoort zo",
          wa.get("showSaveFilePicker") == "undefined", "typeof = %r" % wa.get("showSaveFilePicker"))
    check("de app staat daardoor in browseropslag, niet in bestandsmodus",
          w.get("opslagstand", "").startswith("true|"), "opslagstand %r" % w.get("opslagstand"))

    # de opmaak
    cs, ws = set(c.get("__css") or []), set(w.get("__css") or [])
    weg = sorted(cs - ws)
    check("WebKit leest elke stijlregel die Chromium leest (%d regels)" % len(cs), not weg,
          "%d regel(s) vallen weg, o.a.: %s" % (len(weg), " ;; ".join(weg[:5])))
    extra = sorted(ws - cs)
    if extra:
        print("     (WebKit leest er %d die Chromium niet leest: %s)" % (len(extra), " ;; ".join(extra[:3])))

    # Safari-eigen gedrag, geen pariteit
    check("IndexedDB werkt in WebKit", w.get("__idb") is True, "idb.db = %r" % w.get("__idb"))
    check("een wijziging overleeft een herlaadbeurt in WebKit",
          isinstance(w.get("__naherladen"), int) and w["__naherladen"] >= 0,
          "index na herladen = %r" % w.get("__naherladen"))

    print("\n%d OK, %d FAIL" % (ok, fail))
    print("volledige uitslag: " + uitslag)
    print("""
Wat deze reeks NIET ziet, en waarvoor een echte Mac of iPhone nodig blijft:
  - Safari's opruiming van IndexedDB na zeven dagen zonder bezoek (de reden voor de opslagbalk)
  - navigator.standalone, Add to Dock en het gedrag van de Dock-app
  - Safari op iOS: beforeunload dat daar niet komt, de viewport, de aanraaklayout
  - Safari's eigen printmotor, en de precieze functieset van de Safari-versie van dat toestel""")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        URL = sys.argv[1]
    main()
