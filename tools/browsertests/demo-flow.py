"""Browsertest van de demo-flow: landing, starterset laden, badge, settings, opslag in IndexedDB."""
import asyncio, json
from playwright.async_api import async_playwright

URL = "http://localhost:8765/"

async def main():
    fouten = []
    def check(cond, msg):
        print(("OK   " if cond else "FOUT ") + msg)
        if not cond: fouten.append(msg)

    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

        # 1. eerste bezoek: DEMO-modus, starterknop zichtbaar, geen server
        await page.goto(URL)
        await page.wait_for_timeout(800)
        check(await page.is_visible("#btnStarter"), "landing toont 'Start with the starter set'")
        hint = await page.text_content("#landingHint")
        check("stays in this browser" in hint, "landingHint beschrijft browseropslag")
        check(await page.evaluate("DEMO === true && REMOTE === false"), "DEMO=true, REMOTE=false op een webserver zonder data.php")
        check((await page.evaluate("typeof SHOP_DEFAULTS.length === 'number' && SHOP_DEFAULTS.length")) == 0, "SHOP_DEFAULTS is leeg")

        # 2. starterset laden
        await page.click("#btnStarter")
        await page.wait_for_timeout(1200)
        check(not await page.is_visible("#landing"), "landing verdwijnt na laden")
        nF = await page.evaluate("DATA.formulas.length")
        nM = await page.evaluate("DATA.materials.length")
        check(nF == 16 and nM == 199, f"16 formules en 199 materialen geladen (gevonden {nF}/{nM})")
        state = await page.text_content("#saveState")
        check("this browser" in state or "Unsaved" in state, f"saveState verwijst naar browseropslag: '{state}'")

        # 3. autosave naar IndexedDB (markDirty plant saveData na 2,5 s)
        await page.wait_for_timeout(3200)
        stored = await page.evaluate("idb.get('demoData').then(x => x ? x.length : 0)")
        check(stored > 100000, f"demoData in IndexedDB ({stored} tekens)")
        state = await page.text_content("#saveState")
        check(state.startswith("Saved") and "this browser" in state, f"saveState na autosave: '{state}'")

        # 4. materialenlijst: badge 'starter' en zoeken op 'starter'
        await page.click("#tabM")
        await page.wait_for_timeout(300)
        n_badge = await page.evaluate("document.querySelectorAll('#list .item .sub span[title]').length")
        check(n_badge == 199, f"199 materialen tonen het label 'starter' in de lijst (gevonden {n_badge})")
        await page.fill("#searchBox", "starter")
        await page.wait_for_timeout(300)
        n_hit = await page.evaluate("document.querySelectorAll('#list .item').length")
        check(n_hit == 199, f"zoeken op 'starter' vindt alle 199 (gevonden {n_hit})")
        await page.fill("#searchBox", "")
        await page.wait_for_timeout(300)

        # 5. materiaalpagina: badge 'starter set'
        await page.click("#list .item >> nth=0")
        await page.wait_for_timeout(300)
        badge = await page.evaluate("[...document.querySelectorAll('#content .badge')].map(b => b.textContent)")
        check("starter set" in badge, f"materiaalpagina toont badge 'starter set' ({badge})")
        # opzoeklinks: TGSC en Olfactorian via DuckDuckGo op CAS (of naam), IFRA naar de library met de CAS op het klembord
        links = await page.evaluate("[...document.querySelectorAll('#content .metaLine a.lookup')].map(a => [a.textContent.trim(), a.href, a.target, a.rel, a.dataset.copy || ''])")
        cas = await page.evaluate("(document.querySelector('#content input[data-f=cas]').value || document.querySelector('#content input[data-f=name]').value).trim()")
        from urllib.parse import quote
        check(len(links) == 3 and [l[0] for l in links] == ["TGSC ↗", "Olfactorian ↗", "IFRA ↗"], f"drie opzoeklinks in de metaLine ({[l[0] for l in links]})")
        check(links and links[0][1] == "https://duckduckgo.com/?q=" + quote(cas + " tgsc", safe=""), f"TGSC-link zoekt op '{cas} tgsc' via DuckDuckGo")
        check(links and links[1][1] == "https://duckduckgo.com/?q=" + quote("site:olfactorian.com " + cas, safe=""), "Olfactorian-link zoekt met site:olfactorian.com")
        check(links and links[2][1] == "https://ifrafragrance.org/safe-use/library" and links[2][4] == cas, "IFRA-link naar de library met de CAS als data-copy")
        check(all(l[2] == "_blank" and "noopener" in l[3] for l in links), "alle opzoeklinks openen in een nieuw tabblad met noopener")
        await ctx.grant_permissions(["clipboard-read", "clipboard-write"])
        await page.evaluate("navigator.clipboard.writeText('leeg')")
        await page.evaluate("document.querySelector('#content a[data-copy]').addEventListener('click', e => e.preventDefault(), {once:true})")
        await page.click("#content a[data-copy]"); await page.wait_for_timeout(300)
        clip = await page.evaluate("navigator.clipboard.readText()")
        check(clip == cas, f"klik op IFRA zet de CAS op het klembord ('{clip}')")
        # materiaal zonder CAS én zonder naam: geen links
        nolinks = await page.evaluate("lookupLinks({cas:'', name:''}) === '' && lookupLinks({cas:'', name:'Rose Base'}).includes(encodeURIComponent('Rose Base tgsc'))")
        check(nolinks, "zonder CAS zoekt de link op naam; zonder naam en CAS geen links")
        withcas = await page.evaluate("(() => { const h = lookupLinks({cas:'78-70-6', name:'Linalool'}); return h.includes('q=78-70-6%20tgsc') && h.includes('site%3Aolfactorian.com%2078-70-6') && h.includes('data-copy=\"78-70-6\"') && h.includes('CAS number'); })()")
        check(withcas, "met CAS zoeken de links op het CAS-nummer en gaat dat naar het klembord")
        # alternative names: veld, migratie van een vervuild CAS-veld, zoeken, import-matching, zuiver CAS in de links
        check(await page.is_visible("#content input[data-f=aliases]"), "materiaalpagina heeft het veld Alternative names")
        mig = await page.evaluate("(() => { const d = migrate({materials:[{name:'Iso E Super', cas:'54464-57-2 \\\\ patchouli ethanone'}, {name:'Indole', cas:'120-72-9'}, {name:'Ambroxide', cas:'6790-58-5', aliases:'Ambroxan'}]}); return d.materials.map(m => [m.cas, m.aliases]); })()")
        check(mig == [["54464-57-2", "patchouli ethanone"], ["120-72-9", ""], ["6790-58-5", "Ambroxan"]], f"migratie: CAS met extra tekst → CAS + alternative name ({mig})")
        dirty = await page.evaluate("(() => { const h = lookupLinks({cas:'54464-57-2 \\\\ patchouli ethanone', name:'Iso E Super'}); return h.includes('q=54464-57-2%20tgsc') && h.includes('data-copy=\"54464-57-2\"'); })()")
        check(dirty, "opzoeklinks nemen alleen het CAS-nummer uit een vervuild veld")
        await page.evaluate("(() => { const m = DATA.materials.find(x => x.name === 'Iso E Super'); m.aliases = 'patchouli ethanone; Iso E'; })()")
        await page.fill("#searchBox", "patchouli ethanone"); await page.wait_for_timeout(300)
        names = await page.evaluate("[...document.querySelectorAll('#list .item')].map(e => e.querySelector('span').textContent)")
        check(names == ["Iso E Super"], f"zoeken op een alternative name vindt het materiaal ({names})")
        await page.fill("#searchBox", ""); await page.wait_for_timeout(300)
        res = await page.evaluate("(() => { const r = resolveImportLine({material:'Patchouli Ethanone', dilutionPct:100, weightG:1}); return r.m ? r.m.name : null; })()")
        check(res == "Iso E Super", f"een importregel op een alternative name matcht het materiaal ({res})")
        await page.evaluate("(() => { const m = DATA.materials.find(x => x.name === 'Iso E Super'); m.aliases = ''; })()")
        csv = await page.evaluate("exportAllMaterials.toString().includes('\"Alternative names\"') && exportAllMaterials.toString().includes('m.aliases')")
        check(csv, "de materialenexport heeft een kolom Alternative names")

        # 6. formulepagina: badge en rekenkern
        await page.click("#tabF")
        await page.wait_for_timeout(300)
        await page.click("#list .item >> nth=0")
        await page.wait_for_timeout(400)
        fb = await page.evaluate("[...document.querySelectorAll('#content .metaLine .badge')].map(b => b.textContent)")
        check("starter set" in fb, f"formulepagina toont badge 'starter set' ({fb})")
        tot = await page.evaluate("calc(DATA.formulas[0].versions[0].lines).totalW")
        check(tot > 0, f"rekenkern werkt op de starterdata (eerste formule {tot:.3f} g)")

        # 7. settings-dialoog
        await page.click("#btnSettings")
        await page.wait_for_timeout(300)
        check(await page.is_visible("#setLocale") and await page.is_visible("#setServer"), "Settings-dialoog toont locale en server")
        check(await page.is_visible("#setReset"), "Settings toont 'Delete the data kept in this browser' in DEMO")
        await page.select_option("#setLocale", "en-US")
        await page.click("#dlgOk")
        await page.wait_for_timeout(400)
        loc = await page.evaluate("LOCALE")
        check(loc == "en-US", f"locale-instelling toegepast zonder reload ({loc})")
        sample = await page.evaluate("fmt(1234.5)")
        check(sample == "1,234.500", f"fmt volgt de locale: {sample}")

        # 8. herbezoek: data komt terug uit IndexedDB, landing wordt overgeslagen
        await page.goto(URL)
        await page.wait_for_timeout(1000)
        check(not await page.is_visible("#landing"), "herbezoek: landing overgeslagen, data uit browser")
        check(await page.evaluate("DATA && DATA.formulas.length === 16"), "herbezoek: 16 formules terug")
        loc = await page.evaluate("LOCALE")
        check(loc == "en-US", "herbezoek: locale onthouden")

        # 9. server instellen -> reload -> REMOTE-modus, en terug
        await page.click("#btnSettings")
        await page.wait_for_timeout(300)
        await page.fill("#setServer", "data.php")
        await page.fill("#setToken", "abc")
        await page.click("#dlgOk")
        await page.wait_for_timeout(1500)
        check(await page.evaluate("REMOTE === true && API === 'data.php'"), "na serverinstelling: REMOTE-modus met API=data.php")
        btn = await page.text_content("#btnOpen")
        check("Connect to server" in btn, f"landing toont 'Connect to server' ({btn})")
        await page.evaluate("idb.set('serverUrl', null)")
        await page.goto(URL)
        await page.wait_for_timeout(1000)
        check(await page.evaluate("DEMO === true && DATA && DATA.formulas.length === 16"), "server leeg: terug in DEMO met de bewaarde data")

        # 10. reset
        await page.click("#btnSettings")
        await page.wait_for_timeout(300)
        await page.click("#setReset")
        await page.wait_for_timeout(1200)
        check(await page.is_visible("#btnStarter"), "na reset: landing met starterknop")
        check((await page.evaluate("idb.get('demoData').then(x => x || null)")) is None, "na reset: demoData gewist")

        check(not errs, "geen JavaScript-fouten" + ("" if not errs else ": " + "; ".join(errs)[:300]))
        await b.close()
    print()
    print("%d probleem(en)" % len(fouten) if fouten else "alles in orde")

asyncio.run(main())
