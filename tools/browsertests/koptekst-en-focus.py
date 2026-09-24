"""B11, B12, B13 en E4 van de tweede review: de focus blijft in de gewichtskolom, de bench view past op
1280 px, de telefoon heeft geen doodlopende wegen meer, en de amberkleurige tekst haalt AA-contrast.
Vereist de lokale webserver op poort 8765 (zie README)."""
from playwright.sync_api import sync_playwright
URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

def lum(c):
    c = c.strip()
    if c.startswith("rgb"):
        v = [int(x) for x in c[c.index("(")+1:c.index(")")].replace("rgba", "").split(",")[:3]]
    else:
        c = c.lstrip("#"); v = [int(c[i:i+2], 16) for i in (0, 2, 4)]
    def f(x):
        x /= 255
        return x/12.92 if x <= 0.03928 else ((x+0.055)/1.055) ** 2.4
    return 0.2126*f(v[0]) + 0.7152*f(v[1]) + 0.0722*f(v[2])
def ratio(a, b):
    la, lb = lum(a), lum(b)
    return round((max(la, lb) + 0.05) / (min(la, lb) + 0.05), 2)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 950})
    page = ctx.new_page()
    errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1300)

    # ---------- 1. de focus blijft in de gewichtskolom (B11) ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.versions[0].lines.length > 3);
        switchTab("F", f.id, {type:"v", idx:0}); }""")
    page.wait_for_timeout(500)
    inp = page.locator("input.w").first
    inp.click(); page.keyboard.type("12"); page.keyboard.press("Enter"); page.wait_for_timeout(400)
    na = page.evaluate("""() => { const a = document.activeElement;
        return {tag: a.tagName, cls: a.className, i: a.dataset ? a.dataset.i : null}; }""")
    check(f"na Enter staat de cursor nog in hetzelfde gewichtsveld ({na})", na["cls"] == "w" and na["i"] == "0")
    page.keyboard.type("13"); page.keyboard.press("Tab"); page.wait_for_timeout(400)
    na = page.evaluate("""() => { const a = document.activeElement; return {cls: a.className, i: a.dataset ? a.dataset.i : null}; }""")
    check(f"en Tab gaat naar het volgende gewicht ({na})", na["cls"] == "w" and na["i"] == "1")
    page.keyboard.type("14"); page.keyboard.press("Shift+Tab"); page.wait_for_timeout(400)
    na = page.evaluate("""() => { const a = document.activeElement; return {cls: a.className, i: a.dataset ? a.dataset.i : null}; }""")
    check(f"Shift+Tab gaat een gewicht terug ({na})", na["cls"] == "w" and na["i"] == "0")
    gew = page.evaluate("""() => { const f = DATA.formulas.find(x => x.versions[0].lines.length > 3);
        return f.versions[0].lines.slice(0,2).map(l => l.weightG); }""")
    check(f"en de drie ingaven zijn bewaard ({gew})", gew[0] == 13 and gew[1] == 14)
    msgs.clear()
    page.evaluate("""() => { const i = document.querySelector("input.w"); i.focus(); i.value = "-5";
        i.dispatchEvent(new Event("change", {bubbles:true})); }""")
    page.wait_for_timeout(400)
    na = page.evaluate("""() => { const a = document.activeElement; return a.className; }""")
    check(f"ook na een geweigerd gewicht blijft de cursor staan ({na}, {[m[:30] for m in msgs]})", na == "w")

    # ---------- 2. de bench view past op 1280 px (B12) ----------
    page.click("#btnBenchToggle"); page.wait_for_timeout(600)
    bw = page.evaluate("""(() => { const w = document.querySelector(".benchWrap");
      const cs = getComputedStyle(w);
      const kids = [...w.children].map(k => Math.round(k.getBoundingClientRect().right));
      return {cols: cs.gridTemplateColumns.split(" ").length, max: Math.max(...kids),
              win: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth}; })()""")
    check(f"op 1280 px staat de bench in één kolom en past ze ({bw})", bw["cols"] == 1 and bw["max"] <= bw["win"] and bw["scroll"] <= bw["win"])
    knop = page.evaluate("""(() => { const b = [...document.querySelectorAll("[data-bup],[data-bdown],[data-bempty],[data-bdel]")];
      const w = document.documentElement.clientWidth;
      return {n: b.length, buiten: b.filter(x => x.getBoundingClientRect().right > w + 1).length}; })()""")
    check(f"de groepknoppen ↑ ↓ ⇤ ✕ staan in beeld ({knop})", knop["n"] > 0 and knop["buiten"] == 0)
    page.set_viewport_size({"width": 1500, "height": 950}); page.wait_for_timeout(400)
    bw2 = page.evaluate("""(() => getComputedStyle(document.querySelector(".benchWrap")).gridTemplateColumns.split(" ").length)()""")
    check(f"vanaf 1500 px weer twee kolommen ({bw2})", bw2 == 2)
    page.set_viewport_size({"width": 1280, "height": 950}); page.wait_for_timeout(300)
    page.click("#btnBenchClose"); page.wait_for_timeout(400)

    # ---------- 3. de telefoon: ☰ weg, To order heeft een uitweg (B13) ----------
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(500)
    check("☰ staat niet op een telefoon", not page.locator("#btnBar").is_visible())
    page.click("#btnBack"); page.wait_for_timeout(400)          # terug naar de lijst
    page.evaluate("() => document.body.classList.add('hidebar')")
    page.wait_for_timeout(250)
    zicht = page.evaluate("""(() => ({bar: !!document.querySelector("#sidebar").offsetParent,
        content: !!document.querySelector("#content").offsetParent}))()""")
    check(f"een verborgen zijbalk geeft geen leeg scherm meer ({zicht})", zicht["bar"] or zicht["content"])
    page.evaluate("() => document.body.classList.remove('hidebar')")
    page.wait_for_timeout(250)
    page.click("#tabT"); page.wait_for_timeout(500)
    check("de terugknop van To order wijst naar de vorige tab",
          page.text_content("#btnBack").strip() in ("‹ Formulas", "‹ Materials"))
    page.click("#btnBack"); page.wait_for_timeout(500)
    na = page.evaluate("() => ({tab: VIEW.tab, lijst: !!document.querySelector('#sidebar').offsetParent})")
    check(f"en hij brengt je er ook heen ({na})", na["tab"] != "T" and na["lijst"])
    # de bench view schrijft niet meer in de data van een telefoon die niets kan bewaren (bouw 260918a)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.versions[0].lines.length > 2 && !x.versions[0].bench);
        window.__bid = f.id; window.__demo = DEMO;
        DEMO = false; HANDLE = null; REMOTE = false;          // geen bestand, geen server, geen browseropslag
        switchTab("F", f.id, {type:"v", idx: 0}); }""")
    page.wait_for_timeout(700)
    check("alleen-lezen: de app staat in die stand", page.evaluate("readOnly()") is True)
    vuil = page.evaluate("DIRTY")
    page.click("#btnBenchToggle"); page.wait_for_timeout(800)
    na = page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === window.__bid);
        return {bench: !!f.versions[0].bench, dirty: DIRTY, zicht: !!document.querySelector(".brow")}; }""")
    check(f"alleen-lezen: de bench view opent zonder de data aan te raken ({na})",
          na["zicht"] and not na["bench"] and na["dirty"] == vuil)
    # staart 16 (bouw 260920k): geen sleepaffordance, en een drop die er toch komt schrijft niets
    sleep = page.evaluate("""() => ({rij: document.querySelector(".brow")?.getAttribute("draggable"),
        greep: document.querySelector(".bghandle")?.getAttribute("draggable")})""")
    check(f"alleen-lezen: bench-regels en groepsgrepen bieden geen sleepbeweging aan ({sleep})",
          sleep["rij"] == "false" and sleep["greep"] in (None, "false"))
    undo = page.evaluate("UNDO.length")
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === window.__bid), it = f.versions[0];
        const k = document.querySelector(".brow").dataset.key;
        benchMove(f, it, [k], "0", null); }""")
    page.wait_for_timeout(400)
    na2 = page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === window.__bid);
        return {bench: !!f.versions[0].bench, dirty: DIRTY, undo: UNDO.length, mod: !!f.modified}; }""")
    check(f"alleen-lezen: een drop laat geen undo-stap en geen wijziging achter ({na2})",
          na2["undo"] == undo and not na2["bench"] and na2["dirty"] == vuil)
    page.evaluate("() => { DEMO = window.__demo; render(); }")
    page.wait_for_timeout(400)
    check("en zodra er wél bewaard kan worden, is de regel weer sleepbaar",
          page.evaluate("""() => document.querySelector(".brow")?.getAttribute("draggable")""") == "true")

    page.set_viewport_size({"width": 1280, "height": 950}); page.wait_for_timeout(300)

    # ---------- 4. contrast van de amberkleurige tekst (E4) ----------
    for thema in ("light", "dark"):
        page.evaluate("(t) => document.documentElement.dataset.theme = t", thema)
        page.wait_for_timeout(200)
        v = page.evaluate("""(() => { const cs = getComputedStyle(document.documentElement);
          const g = n => cs.getPropertyValue(n).trim();
          return {ink: g("--amber-ink"), soft: g("--amber-soft"), surface: g("--surface"), ground: g("--ground")}; })()""")
        r1, r2 = ratio(v["ink"], v["surface"]), ratio(v["ink"], v["soft"])
        check(f"{thema}: amberkleurige tekst haalt AA op de achtergrond ({r1}:1)", r1 >= 4.5)
        check(f"{thema}: en op het amberkleurige badge-vlak ({r2}:1)", r2 >= 4.5)
        ph = page.evaluate("""(() => { const i = document.querySelector("#searchBox");
          return getComputedStyle(i, "::placeholder").opacity; })()""")
        check(f"{thema}: de placeholder is niet vervaagd ({ph})", float(ph) >= 0.99)
    page.evaluate("() => delete document.documentElement.dataset.theme")

    # ---------- 5. bouw 260918d: --muted haalt AA op elk vlak van het lichte thema ----------
    page.evaluate("() => document.documentElement.dataset.theme = 'light'")
    page.wait_for_timeout(300)
    kleuren = page.evaluate("""() => { const cs = getComputedStyle(document.documentElement);
      const g = n => cs.getPropertyValue(n).trim();
      return {muted: g("--muted"), surface: g("--surface"), ground: g("--ground"),
              panel: g("--panel"), soft: g("--accent-soft"), amber: g("--amber-soft"),
              frozen: g("--frozen-soft"), danger: g("--danger-soft")}; }""")
    for vlak in ("surface", "ground", "panel", "soft", "amber", "frozen", "danger"):
        r = ratio(kleuren["muted"], kleuren[vlak])
        check(f"licht thema: --muted haalt AA op --{vlak} ({r}:1)", r >= 4.5)

    # ---------- 6. de opslagstand is leesbaar waar het verloop ook staat ----------
    for thema in ("light", "dark"):
        page.evaluate("(t) => document.documentElement.dataset.theme = t", thema)
        page.wait_for_timeout(300)
        st = page.evaluate("""() => { const el = document.querySelector("#saveState");
          const cs = getComputedStyle(el);
          return {kleur: cs.color, grond: cs.backgroundColor, radius: cs.borderRadius}; }""")
        check(f"{thema}: de opslagstand draagt een eigen ondergrond ({st['grond']})",
              st["grond"] not in ("rgba(0, 0, 0, 0)", "transparent"))
        # de donkerste plek van het verloop waar de stand kan staan: het oranje eind met die ondergrond erover
        oranje = page.evaluate("""() => { const cs = getComputedStyle(document.documentElement);
          const g = cs.getPropertyValue("--header-grad");
          const m = g.match(/#[0-9A-Fa-f]{6}/g) || []; return m[m.length - 1]; }""")
        def over(bg, a=0.28):
            bg = bg.lstrip("#"); v = [int(bg[i:i+2], 16) for i in (0, 2, 4)]
            return "#%02X%02X%02X" % tuple(round(x * (1 - a)) for x in v)
        r = ratio(st["kleur"], over(oranje))
        check(f"{thema}: en haalt AA op het oranje eind van het verloop ({r}:1)", r >= 4.5)
        page.evaluate("""() => { setState("Unsaved changes", "", true); }""")
        page.wait_for_timeout(200)
        vuil = page.evaluate("""() => getComputedStyle(document.querySelector("#saveState")).color""")
        r2 = ratio(vuil, over(oranje))
        check(f"{thema}: ook de stand Unsaved changes, de enige die door kleur opvalt ({r2}:1)", r2 >= 4.5)
    page.evaluate("() => delete document.documentElement.dataset.theme")
    page.wait_for_timeout(200)

    # ---------- 7. alleen-lezen laat staan wat niets wijzigt ----------
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(400)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.versions[0].lines.length > 2);
        window.__ro = f.id; DEMO = false; HANDLE = null; REMOTE = false;
        switchTab("F", f.id, {type:"v", idx: 0}); }""")
    page.wait_for_timeout(700)
    zicht = page.evaluate("""() => {
        const z = id => { const e = document.querySelector(id); return e ? !!e.offsetParent && !e.disabled : null; };
        return {sheet: z("#btnSheet"), csv: z("#btnCsv"), share: z("#btnShare"), print: z("#btnPrint"),
                move: z("#btnMoveF"), addline: z("#btnAddLine")}; }""")
    check(f"alleen-lezen: printen, uitvoeren en delen blijven bruikbaar ({zicht})",
          zicht["sheet"] and zicht["csv"] and zicht["share"] and zicht["print"])
    check(f"alleen-lezen: Move into… en Add line zijn weg ({zicht['move']}, {zicht['addline']})",
          not zicht["move"] and not zicht["addline"])
    page.evaluate("() => { DEMO = true; render(); }")
    page.set_viewport_size({"width": 1280, "height": 950}); page.wait_for_timeout(400)

    # ---------- 8. de bestellijst is bedienbaar op een telefoon (B5 en staart 36, bouw 260920c) ----------
    # Een knop die weggeknipt wordt, kan niet aangeraakt worden: wie op zijn telefoon iets op de bestellijst
    # zette, kreeg het er niet meer af. De tabel houdt nu haar eigen breedte binnen haar wrapper.
    page.evaluate("""() => { const m = DATA.materials[0];
        DATA.orderList = [{id:"o1", materialId:m.id, name:m.name, note:"nodig", amount:20, unit:"g",
                           price:"12.50", url:"https://voorbeeld.be/p/123", added:today()}];
        switchTab("T"); }""")
    page.wait_for_timeout(500)
    raak = """(sel) => { const e = document.querySelector(sel); if (!e) return "ontbreekt";
        const b = e.getBoundingClientRect(), x = b.left + b.width/2, y = b.top + b.height/2;
        if (x < 0 || x > innerWidth || y < 0 || y > innerHeight) return "buiten het venster";
        const el = document.elementFromPoint(x, y);
        return el === e || e.contains(el) ? "raakt" : "afgedekt"; }"""
    for w in (360, 390, 430, 700):
        page.set_viewport_size({"width": w, "height": 844}); page.wait_for_timeout(450)
        knop = {n: page.evaluate(raak, s) for n, s in
                (("Search", "[data-osearch='0']"), ("Delivered", "[data-odeliv='0']"), ("✕", "[data-odel='0']"))}
        maat = page.evaluate("""() => { const c = document.querySelector("#content"), wr = c.querySelector(".tblwrap");
            if (!wr) return {tabel: Math.round(c.querySelector("table.lines").getBoundingClientRect().width),
                             wrapper: -1, paneel: c.scrollWidth - c.clientWidth, wrapper_ontbreekt: true};
            return {tabel: Math.round(wr.querySelector("table").getBoundingClientRect().width),
                    wrapper: Math.round(wr.clientWidth), paneel: c.scrollWidth - c.clientWidth}; }""")
        check(f"{w} px: Search, Delivered… en ✕ zijn aan te raken ({knop})",
              all(v == "raakt" for v in knop.values()))
        check(f"{w} px: zonder zijwaarts schuiven, en het paneel schuift evenmin ({maat})",
              maat["tabel"] <= maat["wrapper"] and maat["paneel"] == 0)
    kol = page.evaluate("""() => [...document.querySelectorAll("table.lines.ord thead th")]
        .map(th => getComputedStyle(th).display === "none" ? null : th.textContent.trim()).filter(x => x !== null)""")
    check(f"700 px: alleen materiaal, hoeveelheid en de knoppen ({kol})",
          "Material" in kol and "Amount" in kol and not any(k in kol for k in ("Note", "Price €", "Product URL", "Added")))
    page.set_viewport_size({"width": 1280, "height": 950}); page.wait_for_timeout(450)
    kol = page.evaluate("""() => [...document.querySelectorAll("table.lines.ord thead th")]
        .map(th => getComputedStyle(th).display === "none" ? null : th.textContent.trim()).filter(x => x !== null)""")
    check(f"1280 px: de bureaukolommen staan er weer ({kol})",
          all(k in kol for k in ("Material", "Note", "Amount", "Price €", "Product URL", "Added")))
    br = page.evaluate("""() => { const c = document.querySelector("#content"), wr = c.querySelector(".tblwrap");
        if (!wr) return {tabelSchuift: 0, paneelSchuift: c.scrollWidth - c.clientWidth, kop: 0, kopNa: 0, wrapper_ontbreekt: true};
        const voor = wr.scrollLeft; wr.scrollLeft = 9999; const na = wr.scrollLeft; wr.scrollLeft = voor;
        const kop = document.querySelector("#content h2").getBoundingClientRect().left;
        wr.scrollLeft = 9999; const kopNa = document.querySelector("#content h2").getBoundingClientRect().left;
        wr.scrollLeft = voor;
        return {tabelSchuift: na, paneelSchuift: c.scrollWidth - c.clientWidth, kop, kopNa}; }""")
    check(f"1280 px: de tabel schuift in haar eigen wrapper, niet het paneel ({br})",
          br["tabelSchuift"] > 0 and br["paneelSchuift"] == 0 and br["kop"] == br["kopNa"])

    # de sleepgreep van een bench-regel is zichtbaar zonder hover (staart 20)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.versions[0].lines.length > 2);
        switchTab("F", f.id, {type:"v", idx:0, bench:true}); }""")
    page.wait_for_timeout(700)
    for thema in ("light", "dark"):
        page.evaluate("(t) => document.documentElement.dataset.theme = t", thema)
        page.wait_for_timeout(250)
        kl = page.evaluate("""() => { const g = document.querySelector(".bgrip");
            let el = g.closest(".brow"), bg = getComputedStyle(el).backgroundColor;
            while (bg === "rgba(0, 0, 0, 0)" && el.parentElement){ el = el.parentElement; bg = getComputedStyle(el).backgroundColor; }
            return {grip: getComputedStyle(g).color, bg, hoogte: g.getBoundingClientRect().height}; }""")
        r = ratio(kl["grip"], kl["bg"])
        check(f"{thema}: de sleepgreep haalt 3:1 zonder hover ({r}:1)", r >= 3 and kl["hoogte"] > 0)
    page.evaluate("() => delete document.documentElement.dataset.theme")

    # ---------- 9. B24 (bouw 260920h): de alleen-leesstand houdt ook op in Settings op ----------
    # Dezelfde handeling werd één venster verderop geweigerd: het ⇅-venster schakelde de bibliotheekknoppen uit,
    # Settings niet, en lockInputs bereikt alleen formulierelementen binnen #content.
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(500)
    page.evaluate("""() => { window.__demo2 = DEMO; DEMO = false; HANDLE = null; REMOTE = false;
        HOMEVIEW = true; switchTab("F", null, null); render(); }""")
    page.wait_for_timeout(600)
    check("de app staat in de alleen-leesstand", page.evaluate("readOnly()") is True)
    check("de Formulair-link op de Welcome-pagina is weg",
          page.evaluate("""() => { const a = document.querySelector("#btnImpFormulair");
              return !a || getComputedStyle(a).display === "none"; }"""))
    page.click("#btnSettings"); page.wait_for_timeout(700)
    r = page.evaluate("""() => { const z = id => { const e = document.getElementById(id);
            return e ? (e.disabled ? "uit" : "aan") : "geen"; };
        return {imp: z("setListImp"), get: z("setListGet"),
                uitleg: [...document.querySelectorAll("#dlg .hint")].some(h => /read-only here/.test(h.textContent))}; }""")
    check(f"Settings laat er geen bibliotheek meer in ({r})",
          r["imp"] == "uit" and r["get"] in ("uit", "geen") and r["uitleg"] is True)
    page.evaluate("""() => document.querySelector("#dlgCancel")?.click()"""); page.wait_for_timeout(400)
    page.evaluate("""() => { DEMO = window.__demo2; render(); }"""); page.wait_for_timeout(400)
    page.click("#btnSettings"); page.wait_for_timeout(700)
    check("en zodra er wél ergens bewaard kan worden, staat ze weer open",
          page.evaluate("""() => { const e = document.getElementById("setListImp"); return e && !e.disabled; }"""))
    page.evaluate("""() => document.querySelector("#dlgCancel")?.click()"""); page.wait_for_timeout(300)
    page.set_viewport_size({"width": 1280, "height": 950}); page.wait_for_timeout(400)

    # ---------- staart 37, 38 en 41 (bouw 260920n) ----------
    # de knoppen en de badges op de plek waar het verloop het lichtst is, en de merktekens die betekenis dragen
    KLEUREN = """() => { const cs = getComputedStyle(document.documentElement), v = n => cs.getPropertyValue(n).trim();
      const eind = n => { const m = v(n).match(/#[0-9A-Fa-f]{6}/g) || []; return m[m.length - 1]; };
      return {btnEind: eind("--btn-grad"), kopEind: eind("--header-grad"), kopInkt: v("--header-ink"),
              frozen: v("--frozen"), frozenSoft: v("--frozen-soft"), amberInk: v("--amber-ink"),
              accentSoft: v("--accent-soft"), hl3: v("--hl3"), surface: v("--surface"), accent: v("--accent"),
              ground: v("--ground")}; }"""
    for thema in ("light", "dark"):
        page.evaluate("t => { document.documentElement.dataset.theme = t; }", thema)
        page.wait_for_timeout(300)
        k = page.evaluate(KLEUREN)
        r = ratio("#ffffff", k["btnEind"])
        check(f"{thema}: wit haalt AA op het lichtste eind van een primaire knop ({r}:1)", r >= 4.5)
        r = ratio(k["kopInkt"], k["kopEind"])
        check(f"{thema}: de kopinkt haalt AA op het lichtste eind van de kopbalk ({r}:1)", r >= 4.5)
        r = ratio(k["frozen"], k["frozenSoft"])
        check(f"{thema}: de badges starter en frozen halen AA ({r}:1)", r >= 4.5)
        r = ratio(k["amberInk"], k["accentSoft"])
        check(f"{thema}: amberkleurige tekst op een accentvlak haalt AA ({r}:1)", r >= 4.5)
        r = ratio(k["hl3"], k["surface"])
        check(f"{thema}: het gele merkteken haalt 3:1, want het draagt betekenis ({r}:1)", r >= 3)
        pyr = page.evaluate("""() => { const b = document.createElement("button"); b.className = "sel";
          const w = document.createElement("span"); w.className = "pyr"; w.appendChild(b); document.body.appendChild(w);
          const cs = getComputedStyle(b); const r = {kleur: cs.color, grond: cs.backgroundColor}; w.remove(); return r; }""")
        r = ratio(pyr["kleur"], pyr["grond"])
        check(f"{thema}: de gekozen piramideknop haalt AA ({r}:1, {pyr['kleur']} op {pyr['grond']})", r >= 4.5)
    page.evaluate("() => delete document.documentElement.dataset.theme")
    page.wait_for_timeout(300)

    # elk bedieningselement draagt een naam: zonder naam is het voor een schermlezer een naamloos vakje
    NAMEN = """() => {
      const out = [];
      for (const el of document.querySelectorAll("button, a[href], input:not([type=hidden]), select, textarea")){
        if (el.closest("#manualTpl, .help") || !el.getClientRects().length) continue;
        const lab = el.id ? document.querySelector(`label[for="${CSS.escape(el.id)}"]`) : null;
        const wrap = el.closest("label");
        const naam = (el.getAttribute("aria-label") || "").trim() || (lab ? lab.textContent.trim() : "")
          || (wrap ? wrap.textContent.trim() : "")
          || (el.tagName === "BUTTON" || el.tagName === "A" ? el.textContent.trim() : "")
          || (el.getAttribute("title") || "").trim();
        if (!naam) out.push(el.tagName.toLowerCase() + "#" + (el.id || "-") + "." + (el.className || "-"));
      }
      return [...new Set(out)];
    }"""
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.versions[0].lines.length > 2);
        (DATA.orderList ||= []).push({id:"o-n", name:"Naamtest", added:today()});
        switchTab("F", f.id, {type:"v", idx:0}); }""")
    page.wait_for_timeout(700)
    for naam, js in [("de formulepagina", None),
                     ("de bench view", """() => { VIEW.sub = {...VIEW.sub, bench:true}; render(); }"""),
                     ("een materiaalpagina", """() => switchTab("M", DATA.materials[0].id, null)"""),
                     ("de bestellijst", """() => switchTab("T", null, null)""")]:
        if js: page.evaluate(js); page.wait_for_timeout(600)
        zonder = page.evaluate(NAMEN)
        check(f"{naam}: elk bedieningselement draagt een naam ({zonder})", not zonder)
    page.evaluate("""() => { DATA.orderList = (DATA.orderList||[]).filter(o => o.id !== "o-n"); render(); }""")
    page.wait_for_timeout(300)
    los = page.evaluate("""() => [...document.querySelectorAll("label[for]")]
        .filter(l => !document.getElementById(l.getAttribute("for"))).map(l => l.textContent.trim())""")
    check(f"en geen label wijst naar een veld dat er niet is ({los})", not los)

    # mini-audit C5: dezelfde stof puur en op 10 % is gewoon in de parfumerie, en dan noemden het
    # gewichtsveld, de dilutiekiezer en het bench-vakje alleen het materiaal: twee paar gelijke namen
    page.evaluate("""() => { const m = DATA.materials.find(x => !x.isSolvent);
      DATA.formulas.push({id:"f-tweemaal", name:"Twee keer dezelfde stof", category:"Uncategorised", created:today(),
        versions:[{v:1, date:today(), lines:[
          {id:"t-1", materialId:m.id, dilutionPct:100, weightG:2, remark:1},
          {id:"t-2", materialId:m.id, dilutionPct:10,  weightG:8, remark:1}]}]});
      buildUsage(); switchTab("F", "f-tweemaal", {type:"v", idx:0}); }""")
    page.wait_for_timeout(700)
    for waar, sel in [("het gewichtsveld", "input.w"), ("de dilutiekiezer", "select.d")]:
        namen = page.evaluate("""(s) => [...document.querySelectorAll(s)].map(e => e.getAttribute("aria-label"))""", sel)
        check(f"{waar} van de twee regels heet niet hetzelfde ({namen})",
              len(namen) == 2 and len(set(namen)) == 2 and all("%" in (n or "") for n in namen))
    page.evaluate("""() => { VIEW.sub = {...VIEW.sub, bench:true}; render(); }""")
    page.wait_for_timeout(600)
    bnamen = page.evaluate("""() => [...document.querySelectorAll("input.bsel")].map(e => e.getAttribute("aria-label"))""")
    check(f"en het aankruisvakje in de bench view evenmin ({bnamen})",
          len(bnamen) == 2 and len(set(bnamen)) == 2)
    page.evaluate("""() => { DATA.formulas = DATA.formulas.filter(x => x.id !== "f-tweemaal");
        buildUsage(); switchTab("F", DATA.formulas[0].id, {type:"v", idx:0}); }""")
    page.wait_for_timeout(400)

    check(f"geen paginafouten ({errs[:2]})", not errs)
    b.close()
print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
