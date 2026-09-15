"""Settings: het serverveld verdwijnt in de gedownloade app, en Open where you left off (bouw 260915j).
Deel A en B draaien op de lokale webserver (poort 8765, zie README), deel C op public\\index.html via file://."""
import json, os, re
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
APP = "file://" + os.path.join(PUB, "index.html")
STARTER = open(os.path.join(PUB, "data", "miformulas-starter.json"), encoding="utf-8").read()

ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

def herlaad(page):
    """Wacht de debounce van rememberView uit, schrijf de data weg (de autosave duurt seconden) en herstart."""
    page.wait_for_timeout(1400)
    page.evaluate("() => { saveData(); }")
    page.wait_for_timeout(700)
    page.reload(); page.wait_for_timeout(1700)

with sync_playwright() as p:
    b = p.chromium.launch()

    # ---------------- A en B: op de site ----------------
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1200)

    # ---- A. de servervelden op de site
    page.click("#btnSettings"); page.wait_for_timeout(400)
    check("op de site staat het serverveld er", page.locator("#setServer").count() == 1)
    check("op de site staat het tokenveld er", page.locator("#setToken").count() == 1)
    dlg = page.text_content("#dlg")
    check("de hint legt de server uit", "A server is optional" in dlg)
    check("zonder databestand geen zin over het databestand", "instead of your data file" not in dlg)
    check("het vinkje staat er", page.locator("#setOpenLast").count() == 1)
    check("het vinkje staat standaard uit", not page.locator("#setOpenLast").is_checked())
    check("elk label wijst naar zijn eigen veld", page.evaluate(
        "() => [...document.querySelectorAll('.fieldGrid label')].every(l => l.htmlFor && document.getElementById(l.htmlFor))"))
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    # met een databestand open zegt de hint wat een server daarmee doet
    page.evaluate("() => { window.__h = HANDLE; HANDLE = {name: 'miformulas-data.json'}; }")
    page.click("#btnSettings"); page.wait_for_timeout(400)
    check("met een bestand open waarschuwt de hint", "instead of your data file" in page.text_content("#dlg"))
    page.click("#dlgCancel"); page.wait_for_timeout(200)
    page.evaluate("() => { HANDLE = window.__h || null; }")

    # ---- B. Open where you left off
    check("de instelling staat standaard uit", not page.evaluate("idb.get('openLast')"))
    check("er is nog niets onthouden", not page.evaluate("idb.get('lastView')"))

    # de starterset heeft alleen formules met één versie: er eerst een tweede bij maken,
    # anders zegt "de versie waar je stond" niets
    page.click("#list .item >> nth=0"); page.wait_for_timeout(500)
    page.click("#btnNewV"); page.wait_for_timeout(700)
    fid = page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === VIEW.id);
        return {id: f.id, name: f.name, n: f.versions.length}; }""")
    check(f"de proefformule heeft nu twee versies ({fid['n']})", fid["n"] == 2)
    idx = 1
    page.evaluate("a => switchTab('F', a.id, {type:'v', idx:a.idx})", {"id": fid["id"], "idx": idx})
    page.wait_for_timeout(1400)
    check("uit: er wordt nog altijd niets onthouden", not page.evaluate("idb.get('lastView')"))
    herlaad(page)
    check("uit: na een herstart geen formule open", page.evaluate("VIEW.id") is None)

    # aanzetten
    page.click("#btnSettings"); page.wait_for_timeout(400)
    page.check("#setOpenLast"); page.click("#dlgOk"); page.wait_for_timeout(500)
    check("de instelling is bewaard", page.evaluate("idb.get('openLast')") is True)
    page.evaluate("a => switchTab('F', a.id, {type:'v', idx:a.idx})", {"id": fid["id"], "idx": idx})
    page.wait_for_timeout(1400)
    lv = page.evaluate("idb.get('lastView')")
    check(f"de plek is onthouden ({lv})", lv and lv["id"] == fid["id"] and lv["sub"]["idx"] == idx and lv["tab"] == "F")

    herlaad(page)
    check("na een herstart staat de formule weer open", page.evaluate("VIEW.id") == fid["id"])
    check("en de versie waar je stond", page.evaluate("VIEW.sub && VIEW.sub.idx") == idx)
    check("de kop toont die formule", fid["name"] in page.locator("#content h2").first.inner_text())
    check("de lijst toont ze als gekozen", page.locator("#list .item.sel").count() == 1)

    # ook een materiaal en het tabblad To order komen terug
    mid = page.evaluate("DATA.materials[3].id")
    page.evaluate("id => switchTab('M', id, null)", mid)
    herlaad(page)
    check("een materiaal komt net zo goed terug",
          page.evaluate("VIEW.tab") == "M" and page.evaluate("VIEW.id") == mid)
    page.evaluate("() => switchTab('T')")
    herlaad(page)
    check("het tabblad To order komt terug", page.evaluate("VIEW.tab") == "T")

    # een formule die er niet meer is: terug naar de standaard, zonder fout
    page.evaluate("() => { saveData(); }"); page.wait_for_timeout(700)
    page.evaluate("() => idb.set('lastView', {tab:'F', id:'f-bestaatniet', sub:{type:'v',idx:0}, home:false})")
    page.wait_for_timeout(400)
    page.reload(); page.wait_for_timeout(1700)
    check("een verdwenen formule geeft de standaard, geen fout", page.evaluate("VIEW.id") is None)

    # uitzetten wist wat onthouden was
    page.evaluate("id => switchTab('F', id, {type:'v', idx:0})", fid["id"]); page.wait_for_timeout(1400)
    page.click("#btnSettings"); page.wait_for_timeout(400)
    page.uncheck("#setOpenLast"); page.click("#dlgOk"); page.wait_for_timeout(500)
    check("de instelling staat weer uit", not page.evaluate("idb.get('openLast')"))
    check("en wat onthouden was is gewist", not page.evaluate("idb.get('lastView')"))
    page.evaluate("id => switchTab('F', id, {type:'v', idx:0})", fid["id"]); page.wait_for_timeout(1400)
    check("uit onthoudt ook niets meer", not page.evaluate("idb.get('lastView')"))
    herlaad(page)
    check("en de app begint weer bovenaan", page.evaluate("VIEW.id") is None)
    check(f"geen paginafouten op de site ({errs[:2]})", not errs)
    ctx.close()

    # ---------------- C: de gedownloade app, via file:// ----------------
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    errs2 = []
    page.on("pageerror", lambda e: errs2.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.route("https://miformulas.com/data/miformulas-starter.json",
               lambda r: r.fulfill(status=200, content_type="application/json", body=STARTER,
                                   headers={"Access-Control-Allow-Origin": "*"}))
    page.add_init_script("""
      function FakeHandle(name){ this.name = name; this.kind = 'file'; this.__fake = true; }
      FakeHandle.prototype.queryPermission = async () => 'granted';
      FakeHandle.prototype.requestPermission = async () => 'granted';
      FakeHandle.prototype.getFile = async function(){ return new File([localStorage.getItem('fakefile') || '{}'], this.name); };
      FakeHandle.prototype.createWritable = async () => ({ write: async (s) => localStorage.setItem('fakefile', s), close: async () => {} });
      const desc = Object.getOwnPropertyDescriptor(IDBRequest.prototype, 'result');
      Object.defineProperty(IDBRequest.prototype, 'result', { get(){ const v = desc.get.call(this); if (v && v.__fake) Object.setPrototypeOf(v, FakeHandle.prototype); return v; } });
      window.showOpenFilePicker = async () => { throw new Error('no picker in test'); };
      window.showSaveFilePicker = async (o) => new FakeHandle(o.suggestedName);
    """)
    page.goto(APP); page.wait_for_timeout(900)
    check("protocol is file:", page.evaluate("location.protocol") == "file:")
    page.click("#btnStarter"); page.wait_for_timeout(1200)
    page.click("#dlgOk"); page.wait_for_timeout(1500)          # Choose location…
    check("de gedownloade app is opgestart", page.evaluate("!!DATA"))

    page.click("#btnSettings"); page.wait_for_timeout(500)
    check("geen serverveld in de gedownloade app", page.locator("#setServer").count() == 0)
    check("geen tokenveld in de gedownloade app", page.locator("#setToken").count() == 0)
    dlg = page.text_content("#dlg")
    check("de hint zegt waar de data zit", "keeps its data in the data file next to it" in dlg)
    check("en waar een server dan wel ingesteld wordt", "A server is set up on the site" in dlg)
    check("het vinkje staat er wel", page.locator("#setOpenLast").count() == 1)
    page.check("#setOpenLast"); page.click("#dlgOk"); page.wait_for_timeout(600)
    check("Apply loopt niet stuk zonder de servervelden", page.evaluate("idb.get('openLast')") is True)
    check("en laat de bewaarde serverinstelling met rust", page.evaluate("idb.get('serverUrl')") in (None, ""))
    check(f"geen paginafouten in de gedownloade app ({errs2[:2]})", not errs2)

    print("\n%d OK, %d FAIL" % (ok, fail))
    b.close()
    raise SystemExit(1 if fail else 0)
