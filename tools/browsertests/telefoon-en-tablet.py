"""Points from the test rounds on an iPhone and two Android tablets of 6 and 7 October 2026 (build 261007a, and the
release build of v2.2 for 6 and 7).

1. The import page is a page: on a phone the list and the page take turns, and the import page did not count, so
   Import formula… chosen while the list was showing left the list on the screen and the import page hidden behind it
   (standing; turned sideways both fit side by side). Now it comes to the front; ‹ there is Cancel and goes back to the
   list, as the back button of the phone already cancelled (that one lands on Welcome); and Confirm import works from it.
2. Safari on iOS zooms in on a field whose text is smaller than 16 px and stays zoomed in. In Safari and the Home Screen
   app (an iPad in desktop mode included) the viewport has maximum-scale=1, which stops that zoom while the fingers can
   still pinch; Chrome on an iPhone, Android, Safari on a Mac and a desktop keep the viewport as it was.
3. The ✕ of a formula line and of a dilution sits in a cell that clips: Safari drew an ellipsis after it, a dot at the
   end of every line. On a phone and in the narrow layout beside the list.
4. Enter (and the ✓ of the keyboard on the screen, which sends Enter) in a weight on a touch screen: the weight goes in
   and the field is let go, so the keyboard closes and nothing stays selected; with a mouse the field stays in hand
   with its figure selected, as before.
5. The browser does not translate the app or the Formulair importer (translate="no" and the notranslate meta of
   Google): Chrome in Dutch made "Redden" of Save and "formulier" of Formulair, and renamed formulas and materials on
   the screen. The manual and the AI prompts on the site can still be translated, and section 2 says so.
6. The theme button draws its icon (an SVG, the size of ⇅ and ↻) instead of a character, which Android drew from a symbol
   font at half the size: a half, a full or an empty circle, with the state in the tooltip and in aria-label.
7. The manual shows a phone: app-phone.png in section 2, a formula at the width of an iPhone.
Chromium plays the iPhone through its size, touch and user agent. Needs the local webserver
(cd public && python -m http.server 8765). The script ends with exit code 1 when a check fails."""
import os, sys, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
SAFARI_IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                 "Version/18.6 Mobile/15E148 Safari/604.1")
HOMESCREEN = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
CHROME_IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                 "CriOS/129.0.6668.69 Mobile/15E148 Safari/604.1")
MAC_SAFARI = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 "
              "Safari/605.1.15")
ANDROID = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile "
           "Safari/537.36")
TOUCH_POINTS = "Object.defineProperty(Navigator.prototype, 'maxTouchPoints', {get: () => 5});"
PLAIN = "width=device-width, initial-scale=1"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

def phone(b, w=430, h=932, ua=SAFARI_IPHONE):
    ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=True, has_touch=True,
                        user_agent=ua, accept_downloads=True)
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    return ctx, page

def starter(page):
    page.goto(URL); page.wait_for_timeout(700)
    page.locator("#btnStarter").click(); page.wait_for_timeout(900)

def open_1881(page):
    page.locator('.tile[data-tile="F"]').first.click(); page.wait_for_timeout(400)
    page.locator("#list").get_by_text("1881 for men", exact=True).first.click(); page.wait_for_timeout(700)

versions = lambda page: page.evaluate("() => DATA.formulas.find(f => f.name === '1881 for men').versions.length")
showing = lambda page, sel: page.locator(sel).is_visible()

def from_the_list(page, share):
    """Materials open as a list, no material on the page, and then the file, as Import formula… hands it over"""
    for _ in range(3):                     # a phone may be on a page (Welcome after its back button): ‹ to the list
        if page.locator("#tabM").is_visible(): break
        page.locator("#btnBack").click(); page.wait_for_timeout(400)
    page.locator("#tabM").click(); page.wait_for_timeout(400)
    page.set_input_files("#impFile", share); page.wait_for_timeout(900)

with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
    b = p.chromium.launch()
    share = os.path.join(tmp, "1881 for men.json")

    # ---- 1. the import page on a phone, standing
    ctx, page = phone(b)
    starter(page); open_1881(page)
    with page.expect_download() as dl:
        page.get_by_role("button", name="Share this version").click()
    dl.value.save_as(share)
    page.locator("#btnBack").click(); page.wait_for_timeout(400)
    from_the_list(page, share)
    h2 = page.locator("#content h2").first
    check("phone, standing: Import formula… from the list of materials shows the import page, not the list "
          f"({h2.inner_text()!r}, page {showing(page, '#content h2')}, list {showing(page, '#sidebar')})",
          h2.inner_text().startswith("Import formula – 1881 for men") and showing(page, "#content h2")
          and not showing(page, "#sidebar"))
    back = showing(page, "#btnBack")
    check("the import page has ‹ in the header", back)
    if back:
        page.locator("#btnBack").click(); page.wait_for_timeout(500)
    check(f"‹ there is Cancel: the list again, nothing imported (versions of 1881 for men: {versions(page)})",
          back and showing(page, "#sidebar") and not showing(page, "#content")
          and page.evaluate("() => IMPORTP === null") and versions(page) == 2)

    from_the_list(page, share)
    page.go_back(); page.wait_for_timeout(600)
    check("the back button of the phone leaves it as well, without importing (on a phone it lands on Welcome)",
          page.evaluate("() => IMPORTP === null") and versions(page) == 2
          and not page.locator("#content h2").first.inner_text().startswith("Import formula"))

    from_the_list(page, share)
    can = showing(page, "#btnImpOk")
    if can:
        page.locator("#btnImpOk").click(); page.wait_for_timeout(900)
    v3 = versions(page)
    if can:
        page.locator("#btnUndo").click(); page.wait_for_timeout(600)
    check(f"Confirm import is within reach there and works: v3 arrives ({v3} versions), Undo takes it away again ({versions(page)})",
          can and v3 == 3 and versions(page) == 2)
    ctx.close()

    # ---- the same turned sideways: there both panes fit, and the import page was in sight already
    ctx, page = phone(b, 932, 430)
    starter(page); from_the_list(page, share)
    check("phone, sideways: the import page is in sight", showing(page, "#content h2")
          and page.locator("#content h2").first.inner_text().startswith("Import formula"))
    ctx.close()

    # ---- 2. the viewport: no zoom of its own on a field in Safari on iOS, unchanged elsewhere
    def viewport(ua, mobile=True, touch_points=False, size=(430, 932)):
        ctx = b.new_context(viewport={"width": size[0], "height": size[1]}, is_mobile=mobile, has_touch=mobile,
                            **({"user_agent": ua} if ua else {}))
        if touch_points:
            ctx.add_init_script(TOUCH_POINTS)
        page = ctx.new_page(); page.goto(URL); page.wait_for_timeout(600)
        v = page.evaluate("() => document.querySelector('meta[name=\"viewport\"]').content")
        ctx.close()
        return v
    for name, ua, mob, tp, size in (("Safari on an iPhone", SAFARI_IPHONE, True, False, (430, 932)),
                                    ("the Home Screen app", HOMESCREEN, True, False, (430, 932)),
                                    ("an iPad in desktop mode", MAC_SAFARI, False, True, (1024, 1366))):
        v = viewport(ua, mob, tp, size)
        check(f"{name}: maximum-scale=1, so Safari no longer zooms in on a field ({v!r})",
              v == PLAIN + ", maximum-scale=1")
    for name, ua, mob, size in (("Chrome on an iPhone", CHROME_IPHONE, True, (430, 932)),
                                ("Chrome on Android", ANDROID, True, (412, 915)),
                                ("Safari on a Mac", MAC_SAFARI, False, (1280, 800)),
                                ("Chromium on a desktop", None, False, (1280, 800))):
        v = viewport(ua, mob, False, size)
        check(f"{name}: the viewport as it was ({v!r})", v == PLAIN)

    # ---- 3. the cell of the ✕ clips, the other cells keep their ellipsis
    cells = """sel => { const td = [...document.querySelectorAll('#content table.lines tbody td')];
        const x = td.filter(c => c.querySelector(sel));
        return {n: x.length, clip: x.every(c => getComputedStyle(c).textOverflow === 'clip'),
                rest: td.filter(c => !c.querySelector(sel)).some(c => getComputedStyle(c).textOverflow === 'ellipsis')}; }"""
    ctx, page = phone(b)
    starter(page); open_1881(page)
    r = page.evaluate(cells, "[data-del]")
    check(f"phone: the ✕ of every formula line sits in a cell that clips ({r['n']} lines), the other cells still end in …",
          r["n"] >= 10 and r["clip"] and r["rest"])
    page.locator("#content a.matlink", has_text="Iso E Super").first.click(); page.wait_for_timeout(600)
    r = page.evaluate(cells, "[data-deldil]")
    check(f"phone: so does the ✕ of a dilution on the page of a material ({r['n']})", r["n"] >= 1 and r["clip"])
    ctx.close()

    ctx = b.new_context(viewport={"width": 900, "height": 900}); page = ctx.new_page(); page.on("dialog", lambda d: d.accept())
    starter(page); open_1881(page)
    r = page.evaluate(cells, "[data-del]")
    check(f"beside the list at 900 px: the same ({r['n']} lines)", r["n"] >= 10 and r["clip"] and r["rest"])
    ctx.close()

    # ---- 4. Enter in a weight: let go on a touch screen, kept in hand with a mouse
    state = '''() => { const a = document.activeElement;
        const f = DATA.formulas.find(x => x.name === '1881 for men'), v = f.versions[f.versions.length - 1];
        const l = v.lines.find(x => (DATA.materials.find(m => m.id === x.materialId) || {}).name === 'Labdanum Absolute');
        return {weight: l.weightG, field: a && a.matches && a.matches('input.w'), sel: a && a.matches && a.matches('input.w')
                ? [a.selectionStart, a.selectionEnd, a.value.length] : null}; }'''
    def labdanum(page):
        return page.locator("#content tr", has=page.locator("a.matlink", has_text="Labdanum Absolute")).locator("input.w").first
    for name, ctxargs, w in (("a tablet", dict(viewport={"width": 1280, "height": 800}, is_mobile=True, has_touch=True,
                                                user_agent=ANDROID.replace(" Mobile", "")), "1,5"),
                             ("a phone", dict(viewport={"width": 430, "height": 932}, is_mobile=True, has_touch=True,
                                              user_agent=ANDROID), "1,6")):
        ctx = b.new_context(**ctxargs); page = ctx.new_page(); page.on("dialog", lambda d: d.accept())
        starter(page); open_1881(page)
        touch = page.evaluate("() => matchMedia('(hover: none) and (pointer: coarse)').matches")
        f = labdanum(page); f.tap(); f.fill(w); page.keyboard.press("Enter"); page.wait_for_timeout(500)
        s = page.evaluate(state)
        check(f"{name} (touch {touch}): Enter puts {w} g in and lets the field go, nothing selected ({s})",
              touch and abs(s["weight"] - float(w.replace(",", "."))) < 1e-9 and not s["field"])
        f = labdanum(page); f.tap(); page.keyboard.press("Enter"); page.wait_for_timeout(400)
        s = page.evaluate(state)
        check(f"{name}: Enter without a change lets go as well ({s})", not s["field"])
        ctx.close()
    ctx = b.new_context(viewport={"width": 1280, "height": 800}); page = ctx.new_page(); page.on("dialog", lambda d: d.accept())
    starter(page); open_1881(page)
    f = labdanum(page); f.click(); f.fill("1,5"); page.keyboard.press("Enter"); page.wait_for_timeout(500)
    s = page.evaluate(state)
    check(f"with a mouse: Enter puts 1.5 g in and keeps the field in hand, its figure selected, as before ({s})",
          abs(s["weight"] - 1.5) < 1e-9 and s["field"] and s["sel"] and s["sel"][0] == 0 and s["sel"][1] == s["sel"][2] > 0)
    at = page.evaluate("() => document.activeElement.dataset.i")
    page.keyboard.type("1,7"); page.keyboard.press("Tab"); page.wait_for_timeout(500)
    nxt = page.evaluate("() => document.activeElement.matches('input.w') ? document.activeElement.dataset.i : null")
    s = page.evaluate(state)
    check(f"and a weight changed with Tab still goes on to the next weight (line {at} to {nxt}, {s['weight']} g)",
          nxt is not None and nxt != at and abs(s["weight"] - 1.7) < 1e-9)
    ctx.close()

    # ---- 5. not translated by the browser: the app and the importer; the manual and the prompts on the site can be
    marks = "() => ({lang: document.documentElement.lang, tr: document.documentElement.getAttribute('translate'), " \
            "meta: !!document.querySelector('meta[name=google][content=notranslate]')})"
    page = b.new_page()
    for path in ("", "formulair-import.html"):
        page.goto(URL + path); page.wait_for_timeout(500)
        m = page.evaluate(marks)
        check(f"{path or 'the app'}: the browser leaves it untranslated ({m})", m == {"lang": "en", "tr": "no", "meta": True})
    for path in ("docs/manual.html", "docs/ai-prompts.html"):
        page.goto(URL + path); page.wait_for_timeout(300)
        m = page.evaluate(marks)
        check(f"{path}: can still be translated ({m})", m["lang"] == "en" and m["tr"] != "no" and not m["meta"])
    page.goto(URL); page.wait_for_timeout(600)
    page.locator("#btnStarter").click(); page.wait_for_timeout(900)
    page.locator("#btnHelp").click(); page.wait_for_timeout(500)
    check("section 2 of the Help says that the app stays in English and the manual on the site can be translated",
          "The app stays in English" in page.inner_text("#content"))
    page.close()

    # ---- 6. the theme icon is drawn, not a character
    page = b.new_page(viewport={"width": 1280, "height": 800}); page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(600)
    page.locator("#btnStarter").click(); page.wait_for_timeout(900)
    icon = """() => { const b = document.querySelector('#btnTheme'), s = b.querySelector('svg'), io = document.querySelector('#btnIO svg');
        const r = s && s.getBoundingClientRect(), q = io.getBoundingClientRect();
        const filled = s ? [...s.querySelectorAll('circle,path')].map(e => (e.getAttribute('fill') || 'none') + ':' + e.tagName).join(' ') : '';
        return {svg: !!s, text: b.textContent.trim(), size: s ? [Math.round(r.width), Math.round(r.height)] : null,
                io: [Math.round(q.width), Math.round(q.height)], filled, label: b.getAttribute('aria-label') || '', title: b.title,
                theme: document.documentElement.dataset.theme || 'auto'}; }"""
    seen = []
    for _ in range(3):
        seen.append(page.evaluate(icon))
        page.locator("#btnTheme").click(); page.wait_for_timeout(200)
    seen.append(page.evaluate(icon))
    a, d, l, back = seen
    check(f"the theme button draws its icon, the size of the icon of ⇅, without a character ({a['size']} against {a['io']}, {a['text']!r})",
          a["svg"] and not a["text"] and a["size"] == a["io"])
    check(f"auto: a circle with its left half filled; dark: a full circle; light: an empty one ({a['filled']} | {d['filled']} | {l['filled']})",
          a["theme"] == "auto" and "currentColor:path" in a["filled"] and "none:circle" in a["filled"]
          and d["theme"] == "dark" and d["filled"] == "currentColor:circle" and l["theme"] == "light" and l["filled"] == "none:circle")
    check(f"each state is named in the tooltip and in aria-label, and a fourth click is auto again ({d['label']!r}, {back['theme']})",
          a["label"].startswith("Theme: auto") and d["label"] == "Theme: dark" and l["label"] == "Theme: light"
          and all(x["title"].startswith(x["label"]) for x in (a, d, l)) and back["theme"] == "auto")
    page.close()

    # ---- 7. a phone in the manual
    page = b.new_page()
    page.goto(URL + "docs/manual.html"); page.wait_for_timeout(500)
    page.evaluate("() => document.querySelector('img[src=\"img/app-phone.png\"]')?.scrollIntoView()"); page.wait_for_timeout(800)
    fig = page.evaluate("""() => { const i = document.querySelector('img[src="img/app-phone.png"]'); if (!i) return null;
        const f = i.closest('figure'), h = [...document.querySelectorAll('h2')].filter(x => x.compareDocumentPosition(i) & 4).pop();
        return {w: i.naturalWidth, small: f.classList.contains('small'), section: h ? h.textContent : ''}; }""")
    check(f"section 2 of the manual shows a phone: app-phone.png, 860 px wide (430 at 2x), as a small figure ({fig})",
          fig and fig["w"] == 860 and fig["small"] and fig["section"].startswith("2."))
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
sys.exit(1 if fail else 0)
