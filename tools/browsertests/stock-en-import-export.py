"""Bouw 261017b: een aankoop start het stockboek, en Import & export in de indeling van Settings.
Draait op de lokale webserver (poort 8765, zie README)."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("MIF_URL", "http://localhost:8765/")
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1366, "height": 660})
    errs, msgs = [], []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1200)
    st = lambda mid: page.evaluate("id => { const m = DATA.materials.find(x => x.id === id); const s = stockCalc(m); return {t: s.tracked, q: s.qty, ev: (m.stockEvents||[]).map(e => e.t + ':' + e.g + (e.note ? ' ' + e.note : ''))}; }", mid)
    def open_stock():
        page.evaluate("() => { const d = document.querySelector('#stBuyAmt')?.closest('details'); if (d) d.open = true; }"); page.wait_for_timeout(150)

    # ---------- 1. Purchase › Add op een materiaal zonder stock ----------
    mid = page.evaluate("() => { const m = DATA.materials.find(x => !stockCalc(x).tracked && !x.isSolvent); switchTab('M', m.id, null); return m.id; }")
    page.wait_for_timeout(500); open_stock()
    check("zonder stock zegt het paneel hoe je begint", "set a stocktake or add a purchase to start" in page.text_content("#content"))
    msgs.clear()
    page.fill("#stBuyAmt", "25"); page.click("#btnBuy"); page.wait_for_timeout(400)
    s = st(mid)
    check(f"Add begint meteen te volgen, zonder vraag ({msgs})", not msgs and s["t"])
    check(f"de stock is wat je kocht: 25 g ({s['q']})", s["q"] == 25)
    check(f"met een stocktake van 0 g ervoor ({s['ev']})", s["ev"][-2:] == ["take:0 start of tracking", "buy:25"])
    check("het paneel toont de stand", "25" in page.text_content("details.panelBox summary"))
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    s = st(mid)
    check(f"één Undo neemt beide terug ({s['ev']})", not s["t"] and not s["ev"])
    open_stock(); page.fill("#stBuyAmt", "10"); page.click("#btnBuy"); page.wait_for_timeout(300)
    open_stock(); page.fill("#stBuyAmt", "5"); page.click("#btnBuy"); page.wait_for_timeout(300)
    s = st(mid)
    check(f"een tweede aankoop telt erbij, zonder nieuwe stocktake ({s['q']}, {s['ev']})", s["q"] == 15 and len(s["ev"]) == 3)
    # in ml zonder densiteit begint het niet
    mid2 = page.evaluate("() => { const m = DATA.materials.find(x => !stockCalc(x).tracked && !x.isSolvent && x.density == null); switchTab('M', m.id, null); return m.id; }")
    page.wait_for_timeout(400); open_stock(); msgs.clear()
    page.fill("#stBuyAmt", "30"); page.select_option("#stBuyUnit", "ml"); page.click("#btnBuy"); page.wait_for_timeout(300)
    s = st(mid2)
    check(f"in ml zonder densiteit vraagt het de densiteit en noteert het niets ({msgs[:1]})", msgs and "density" in msgs[0] and not s["ev"])

    # ---------- 2. Delivered… ----------
    def lever(naam, mid=None, aan=True, amt="20"):
        page.evaluate("""([naam, mid]) => { (DATA.orderList ||= []).push({id:'o-' + naam, materialId: mid, name: naam, added: today()});
            markDirty(); VIEW = {tab:'T', id:null, sub:null}; HOMEVIEW = false; setTabs(); render(); }""", [naam, mid])
        page.wait_for_timeout(500)
        rij = page.evaluate("n => [...document.querySelectorAll('[data-odeliv]')].findIndex(b => b.closest('tr').textContent.includes(n))", naam)
        page.fill(f"[data-oamt='{rij}']", amt); page.locator(f"[data-oamt='{rij}']").press("Tab"); page.wait_for_timeout(250)
        page.click(f"[data-odeliv='{rij}']"); page.wait_for_timeout(500)
        info = page.evaluate("() => ({track: !!document.querySelector('#dvTrack'), on: !!document.querySelector('#dvTrack')?.checked, g: document.querySelector('#dvG')?.value, fresh: !!document.querySelector('#dvFresh')})")
        if not aan and info["track"]: page.uncheck("#dvTrack")
        page.click("#dlgOk"); page.wait_for_timeout(700)
        return info
    mid3 = page.evaluate("() => DATA.materials.find(x => !stockCalc(x).tracked && !x.isSolvent && !(x.stockEvents||[]).length && x.id !== '%s').id" % mid)
    naam3 = page.evaluate("id => DATA.materials.find(x => x.id === id).name", mid3)
    info = lever(naam3, mid3)
    check(f"zonder stock: Track stock staat er en is aangevinkt ({info})", info["track"] and info["on"] and not info["fresh"])
    check("het bedrag voor het boek volgt de gekochte hoeveelheid", info["g"] == "20")
    s = st(mid3)
    check(f"na Confirm wordt de stock gevolgd: 20 g ({s['q']}, {s['ev']})", s["t"] and s["q"] == 20 and s["ev"][0] == "take:0 start of tracking")
    page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    check("Undo zet het terug", not st(mid3)["t"])
    info = lever(naam3, mid3, aan=False)
    check(f"vinkje uit: geen stockboek ({st(mid3)['ev']})", not st(mid3)["t"] and not st(mid3)["ev"])
    info = lever("Nieuw geleverd")
    nid = page.evaluate("() => DATA.materials.find(x => x.name === 'Nieuw geleverd')?.id")
    s = st(nid) if nid else {"t": False, "q": None}
    check(f"een nieuw materiaal uit Delivered: vinkje aan en gevolgd ({info['track']}, {s.get('q')})", info["track"] and s["t"] and s["q"] == 20)
    lever(naam3, mid3)          # weer met het vinkje: vanaf nu gevolgd
    info = lever(naam3, mid3)   # gevolgd: Old stock used up, geen Track stock
    check(f"een gevolgd materiaal toont Old stock used up en geen Track stock ({info})", info["fresh"] and not info["track"])

    # ---------- 3. Import & export ----------
    page.evaluate("idb.set('dailyBak', {date: '2026-10-17', json: serialize(), where: snapWhere()})"); page.wait_for_timeout(200)
    page.click("#btnIO"); page.wait_for_timeout(500)
    koppen = page.evaluate("() => [...document.querySelectorAll('#dlg .setSec')].map(e => e.textContent)")
    check(f"drie koppen ({koppen})", koppen == ["Import", "Export", "Back to an earlier state"])
    kol = page.evaluate("""() => { const c = document.querySelector('#dlg .setCols'); const r = e => document.getElementById(e).getBoundingClientRect().left;
        return c ? [getComputedStyle(c).gridTemplateColumns.split(' ').length, r('btnImpF') < r('btnExpF'), Math.abs(r('btnExpF') - r('ioRestore')) < 2] : null; }""")
    check(f"twee kolommen: Import links, Export en de wegen terug rechts ({kol})", kol and kol[0] == 2 and kol[1] and kol[2])
    rood = page.evaluate("() => ['ioRestore', 'ioSnap'].map(id => document.getElementById(id)?.classList.contains('danger'))")
    check(f"de twee herstelknoppen in rood ({rood})", rood == [True, True])
    onder = page.evaluate("() => [...document.querySelectorAll('#dlg .ioItem')].every(i => { const h = i.querySelector(':scope > .hint'), k = i.querySelector('button, a.btn'); return h && k && h.getBoundingClientRect().top >= k.getBoundingClientRect().bottom - 1; })")
    check("de uitleg staat onder de knop", onder)
    over = page.evaluate("() => { const d = document.querySelector('#dlg'); return d.scrollHeight - d.clientHeight; }")
    check(f"past op 1366 × 660 zonder scrollen ({over} px te veel)", over <= 0)
    page.keyboard.press("Escape"); page.wait_for_timeout(200)
    page.set_viewport_size({"width": 800, "height": 900}); page.wait_for_timeout(200)
    page.click("#btnIO"); page.wait_for_timeout(400)
    n = page.evaluate("() => getComputedStyle(document.querySelector('#dlg .setCols')).gridTemplateColumns.split(' ').length")
    check(f"op een smal scherm één kolom ({n})", n == 1)

    check("geen fouten op de pagina", not errs)
    if errs: print(errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
