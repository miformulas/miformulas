"""Bouw 261011c (bouw 4 van de analyse van 10/10): de geselecteerde rij en het piramide-icoontje.
- De lijst links: een ander item openen, met de muis of met Enter, laat de rijen staan; de markering verhuist op de rij
  zelf, en de rij die je aanklikte houdt de focus. Er is altijd hoogstens één rij gemarkeerd, die van het open item: geen
  zonder open item, geen in To order, geen als een zoekterm het open item niet toont. Een veld op de pagina laat de
  rijen ook staan; een zoekterm en een ander tabblad bouwen de lijst nog.
- Het icoontje: één span zonder kinderen in de lijst, de materiaalpagina, de formuletabel, de bench, Compare en het
  weegblad, nergens nog een svg; de klasse volgt het niveau (lv0 tot lv4, lvx zonder niveau), de achtergrond is de kleur
  van de categorie, de maat 12, 13 of 20 px; zes verschillende maskers. Het tekent wat het oude icoontje tekende (naast
  elkaar in de pagina, pixel voor pixel). Op papier blijft het staan: print-color-adjust en een pdf zonder achtergronden.
Vereist de lokale webserver op poort 8765 (zie README); de pdf-controle vraagt pdftoppm (poppler-utils)."""
import io, shutil, subprocess, tempfile, os
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops

URL = "http://localhost:8765/index.html"
ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

# het icoontje zoals het tot 261011b getekend werd: een svg met vijf vlakken
OUD = """(level, colour, size) => { let s = `<svg width="${size}" height="${size}" viewBox="0 0 14 14">`;
  for (let i = 0; i < 5; i++){ const y1 = 1 + 12*i/5, y2 = 1 + 12*(i+1)/5, hw = y => (y-1)/12*6;
    s += `<polygon points="${(7-hw(y1)).toFixed(2)},${y1.toFixed(2)} ${(7+hw(y1)).toFixed(2)},${y1.toFixed(2)} ${(7+hw(y2)).toFixed(2)},${y2.toFixed(2)} ${(7-hw(y2)).toFixed(2)},${y2.toFixed(2)}" fill="${i===level?colour:"none"}" stroke="${colour}" stroke-width="0.7"/>`; }
  return s + "</svg>"; }"""
RIJEN = "() => [...document.querySelectorAll('#list .item')]"
SEL = "() => [...document.querySelectorAll('#list .item.sel')].map(r => r.dataset.id)"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    c = b.new_context(viewport={"width": 1400, "height": 900}, locale="en-GB")
    page = c.new_page(); errs = []
    page.on("pageerror", lambda e: errs.append(str(e))); page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1500)

    # ======================= de geselecteerde rij =======================
    page.click("#tabM"); page.wait_for_timeout(400)
    page.evaluate(f"() => {{ window.__rijen = ({RIJEN})(); }}")
    n = page.evaluate("window.__rijen.length")
    page.locator("#list .item").nth(3).click(); page.wait_for_timeout(300)
    id3 = page.evaluate("window.__rijen[3].dataset.id")
    check(f"een materiaal aanklikken opent het ({n} rijen)", page.evaluate("VIEW.id") == id3 and page.evaluate("VIEW.tab") == "M")
    page.locator("#list .item").nth(10).click(); page.wait_for_timeout(300)
    id10 = page.evaluate("window.__rijen[10].dataset.id")
    zelfde = f"() => {{ const nu = ({RIJEN})(); return nu.length === window.__rijen.length && nu.every((r, i) => r === window.__rijen[i]); }}"
    check("een ander materiaal openen laat de rijen van de lijst staan (geen nieuwe lijst)", page.evaluate(zelfde))
    check(f"alleen de rij van het open materiaal is gemarkeerd ({page.evaluate(SEL)})", page.evaluate(SEL) == [id10])
    check("de rij die je aanklikte houdt de focus", page.evaluate("document.activeElement === window.__rijen[10]"))
    page.keyboard.press("Tab"); page.wait_for_timeout(100)
    check("Tab gaat van die rij naar de volgende rij", page.evaluate("document.activeElement === window.__rijen[11]"))
    page.keyboard.press("Enter"); page.wait_for_timeout(300)
    id11 = page.evaluate("window.__rijen[11].dataset.id")
    check("Enter opent die rij; de markering verhuist, de focus blijft, de rijen ook",
          page.evaluate("VIEW.id") == id11 and page.evaluate(SEL) == [id11]
          and page.evaluate("document.activeElement === window.__rijen[11]") and page.evaluate(zelfde))
    sup = page.locator('#content input[data-f="supplier"]').first
    sup.fill("A supplier of mine"); sup.press("Tab"); page.wait_for_timeout(500)
    check("een veld op de materiaalpagina laat de rijen en de markering staan", page.evaluate(zelfde) and page.evaluate(SEL) == [id11])
    naam11 = page.evaluate("id => DATA.materials.find(m => m.id === id).name", id11)
    page.fill("#searchBox", naam11[:4]); page.wait_for_timeout(500)
    check(f"een zoekterm bouwt de lijst opnieuw, met het open materiaal gemarkeerd als het erbij staat ({naam11[:4]!r})",
          not page.evaluate(zelfde) and page.evaluate(SEL) == [id11])
    page.fill("#searchBox", "zzzqqq"); page.wait_for_timeout(400)
    check("staat het open materiaal er niet bij, dan is niets gemarkeerd", page.evaluate(SEL) == [])
    page.fill("#searchBox", ""); page.wait_for_timeout(400)
    check("zonder zoekterm weer de hele lijst, met de markering", page.evaluate(f"({RIJEN})().length") == n and page.evaluate(SEL) == [id11])
    page.evaluate("() => switchTab('M', null, null)"); page.wait_for_timeout(300)
    check("zonder open materiaal is niets gemarkeerd", page.evaluate(SEL) == [])
    page.click("#tabF"); page.wait_for_timeout(400)
    page.evaluate(f"() => {{ window.__rijen = ({RIJEN})(); }}")
    page.locator("#list .item").nth(2).click(); page.wait_for_timeout(300)
    page.locator("#list .item").nth(5).click(); page.wait_for_timeout(300)
    f5 = page.evaluate("window.__rijen[5].dataset.id")
    check("in Formulas hetzelfde: de rijen blijven, één markering, de focus op de rij",
          page.evaluate(zelfde) and page.evaluate(SEL) == [f5] and page.evaluate("document.activeElement === window.__rijen[5]"))
    page.click("#tabM"); page.wait_for_timeout(300)
    page.locator("#list .item").first.click(); page.wait_for_timeout(300)
    page.click("#btnToOrder"); page.wait_for_timeout(300)
    page.click("#tabT"); page.wait_for_timeout(400)
    check(f"To order markeert geen rij, zoals voordien ({page.evaluate(f'({RIJEN})().length')} rij)",
          page.evaluate(f"({RIJEN})().length") >= 1 and page.evaluate(SEL) == [])

    # ======================= het piramide-icoontje =======================
    page.click("#tabM"); page.wait_for_timeout(400)
    lijst = page.evaluate("""() => { const uit = {svg: document.querySelectorAll('#list svg').length, rijen: 0, fout: []};
      for (const r of document.querySelectorAll('#list .item')){ const m = DATA.materials.find(x => x.id === r.dataset.id);
        const i = r.querySelector('.pyricon'); uit.rijen++;
        const lv = [0, 1, 2, 3, 4].indexOf(m.pyramid), want = 'pyricon lv' + (lv < 0 ? 'x' : lv);
        if (!i || i.tagName !== 'SPAN' || i.childElementCount || i.className !== want) uit.fout.push(m.name + ': ' + (i ? i.tagName + ' ' + i.getAttribute('class') : 'geen'));
      } return uit; }""")
    check(f"in de lijst een span per rij, zonder kinderen, met de klasse van het niveau ({lijst['rijen']} rijen, {lijst['fout'][:2]})",
          lijst["svg"] == 0 and lijst["rijen"] > 100 and not lijst["fout"])
    niveaus = page.evaluate("() => [...new Set([...document.querySelectorAll('#list .pyricon')].map(i => i.getAttribute('class')))].sort()")
    check(f"de starterset toont alle niveaus en het icoontje zonder niveau ({niveaus})",
          niveaus == ["pyricon lv0", "pyricon lv1", "pyricon lv2", "pyricon lv3", "pyricon lv4", "pyricon lvx"])
    kleur = page.evaluate("""() => { const t = document.createElement('i'); document.body.append(t); const fout = [];
      for (const r of document.querySelectorAll('#list .item')){ const m = DATA.materials.find(x => x.id === r.dataset.id);
        t.style.background = catColour(m); const w = getComputedStyle(t).backgroundColor, i = r.querySelector('.pyricon');
        if (getComputedStyle(i).backgroundColor !== w) fout.push(m.name); } t.remove(); return fout; }""")
    check(f"de achtergrond van elk icoontje is de kleur van zijn categorie ({kleur[:3]})", not kleur)
    maskers = page.evaluate("""() => ['x', 0, 1, 2, 3, 4].map(lv => { const i = document.querySelector('#list .pyricon.lv' + lv);
      if (!i) return 'geen'; const s = getComputedStyle(i); return s.maskImage || s.webkitMaskImage; })""")
    check(f"zes verschillende maskers, elk een svg ({[m[:34] for m in maskers[:1]]})",
          len(set(maskers)) == 6 and all(m.startswith('url("data:image/svg+xml') for m in maskers))
    maat = page.evaluate("() => { const r = document.querySelector('#list .pyricon').getBoundingClientRect(); return [r.width, r.height]; }")
    check(f"in de lijst 12 bij 12 px ({maat})", maat == [12, 12])
    page.locator("#list .item").nth(4).click(); page.wait_for_timeout(300)
    h2 = page.evaluate("() => { const i = document.querySelector('#content h2 .pyricon'); if (!i) return null; const r = i.getBoundingClientRect(); return [i.tagName, r.width, r.height]; }")
    check(f"op de materiaalpagina een span van 20 px voor de naam ({h2})", h2 == ["SPAN", 20, 20])

    fid = page.evaluate("DATA.formulas.find(f => f.name === 'Angel').id")
    tel = "() => [document.querySelectorAll('#content svg.pyricon, #printArea svg.pyricon').length, document.querySelectorAll('#content span.pyricon').length, (() => { const i = document.querySelector('#content span.pyricon'); return i ? i.getBoundingClientRect().width : 0; })()]"
    page.evaluate("id => switchTab('F', id, {type: 'v', idx: 1})", fid); page.wait_for_timeout(400)
    t1 = page.evaluate(tel)
    page.evaluate("id => switchTab('F', id, {type: 'v', idx: 1, bench: true})", fid); page.wait_for_timeout(400)
    t2 = page.evaluate(tel)
    page.evaluate("id => switchTab('F', id, {type: 'v', idx: 1})", fid); page.wait_for_timeout(300)
    page.click("#btnCmp"); page.wait_for_timeout(400)
    t3 = page.evaluate(tel)
    page.click("#btnCmpClose"); page.wait_for_timeout(300)
    check(f"de formuletabel, de bench en Compare: spans van 13 px, geen svg ({t1}, {t2}, {t3})",
          all(t[0] == 0 and t[1] > 10 and t[2] == 13 for t in (t1, t2, t3)))

    # tekent hetzelfde als het oude icoontje: naast elkaar in de pagina, elk niveau, twee kleuren, groot
    page.evaluate(f"""() => {{ const oud = {OUD}; const d = document.createElement('div'); d.id = 'vgl';
      d.style.cssText = 'position:fixed;left:0;top:0;z-index:99999;background:#fff;padding:4px;display:grid;grid-template-columns:repeat(2,48px);gap:4px';
      let h = ''; for (const c of ['#7A4FB0', '#C0392B']) for (const lv of [null, 0, 1, 2, 3, 4])
        h += `<div class="o">${{oud(lv, c, 40)}}</div><div class="n">${{pyrIcon(lv, c, 40)}}</div>`;
      d.innerHTML = h; document.body.append(d);
      d.querySelectorAll('div').forEach(x => {{ x.style.cssText = 'width:44px;height:44px;line-height:0;padding:2px;background:#fff'; }});
      d.querySelectorAll('svg, .pyricon').forEach(i => {{ i.style.margin = '0'; i.style.display = 'block'; }}); }}""")
    page.wait_for_timeout(200)
    oud, nieuw = page.locator("#vgl .o"), page.locator("#vgl .n")
    slechtst, inkt = (0, 0.0), []
    for k in range(oud.count()):
        a = Image.open(io.BytesIO(oud.nth(k).screenshot())).convert("RGB")
        z = Image.open(io.BytesIO(nieuw.nth(k).screenshot())).convert("RGB")
        d = list(ImageChops.difference(a, z).convert("L").getdata()) if a.size == z.size else [255]
        slechtst = max(slechtst, (max(d), sum(1 for x in d if x > 48) / len(d)))
        inkt.append(sum(1 for p in z.convert("L").getdata() if p < 200))
    check(f"het nieuwe icoontje tekent wat het oude tekende, bij elk niveau, in twee kleuren en op 40 px (grootste verschil "
          f"{slechtst[0]} op 255, {slechtst[1]:.1%} van de pixels meer dan 48)", slechtst[0] <= 64 and slechtst[1] < 0.01)
    check(f"en het tekent echt iets: elk niveau vult een vlak bij de omtrek ({inkt[:6]})",
          all(inkt[s] > 100 and all(inkt[s + k] > inkt[s] for k in range(1, 6)) and inkt[s + 5] > inkt[s] + 80 for s in (0, 6)))
    page.evaluate("() => document.querySelector('#vgl').remove()")

    # op papier: het weegblad, zonder de achtergronden van de browser
    page.evaluate("() => { window.print = () => {}; }")
    page.evaluate("id => switchTab('F', id, {type: 'v', idx: 1})", fid); page.wait_for_timeout(300)
    page.click("#btnPrint"); page.wait_for_timeout(400)
    page.emulate_media(media="print")
    druk = page.evaluate("""() => { const i = [...document.querySelectorAll('#printArea .pyricon')]; const s = i[0] && getComputedStyle(i[0]);
      return [i.length, i.filter(x => x.tagName === 'SPAN').length, s ? (s.printColorAdjust || s.webkitPrintColorAdjust) : null]; }""")
    page.emulate_media(media="screen")
    check(f"het weegblad heeft de spans, met print-color-adjust exact, zodat de kleur op papier blijft ({druk})",
          druk[0] > 10 and druk[1] == druk[0] and druk[2] == "exact")
    if shutil.which("pdftoppm"):
        tmp = tempfile.mkdtemp(); pdf = os.path.join(tmp, "weegblad.pdf")
        page.pdf(path=pdf, print_background=False)
        subprocess.run(["pdftoppm", "-r", "100", "-png", "-f", "1", "-l", "1", pdf, os.path.join(tmp, "blad")], check=True)
        png = [f for f in os.listdir(tmp) if f.endswith(".png")][0]
        im = Image.open(os.path.join(tmp, png)).convert("RGB")
        gekleurd = sum(1 for (r, g, bl) in im.getdata() if max(r, g, bl) - min(r, g, bl) > 40)
        check(f"in een pdf zonder achtergronden staan de icoontjes in kleur op het weegblad ({gekleurd} gekleurde pixels)", gekleurd > 500)
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        print("     (geen pdftoppm: de pdf van het weegblad is niet nagekeken)")
    check(f"geen fouten in de pagina ({errs[:2]})", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
