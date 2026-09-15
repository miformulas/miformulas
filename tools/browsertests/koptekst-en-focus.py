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

    check(f"geen paginafouten ({errs[:2]})", not errs)
    b.close()
print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
