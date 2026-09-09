import asyncio, time
from playwright.async_api import async_playwright
SQ="/mnt/user-data/uploads/miFormulas/co.uk.lux-terra.Formulair/Data/Library/Application Support/Formulair/DataModel.sqlite"
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); ctx=await b.new_context(); page=await ctx.new_page()
        errs=[]; page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
        await page.goto("http://localhost:8765/formulair-import.html"); await page.wait_for_timeout(400)
        await page.set_input_files("#file", SQ)
        await page.wait_for_selector("#btnOpen", timeout=60000)
        await page.click("#btnOpen")
        await page.wait_for_url("**/index.html", timeout=30000); await page.wait_for_timeout(2500)
        n=await page.evaluate("DATA ? [DATA.formulas.length, DATA.materials.length, DEMO, REMOTE] : null")
        # lege browser: "Add to miFormulas" maakt de import tot de data (bouw 260909d); met bestaande data wordt samengevoegd (merge-import.py)
        print(("OK   " if n and n[0]==698 and n[1]==694 and n[2] and not n[3] else "FOUT ")+"na Add to miFormulas start miFormulas met de Formulair-data: %s"%n)
        st=await page.text_content("#saveState")
        print("     statusregel: %r"%st)
        # notities en kleuren aanwezig?
        info=await page.evaluate("""(()=>{const f=DATA.formulas.find(x=>x.name==='Aura v06'); const v=f&&f.versions[0];
          return f?{notes:(v.notes||'').slice(0,60), frozen:v.frozen, lines:v.lines.length, marks:v.lines.filter(l=>l.remark!=null).length, cat:f.category, created:f.created}:null})()""")
        print(("OK   " if info and info['notes'] and info['frozen'] else "FOUT ")+"Aura v06: notitie, bevroren, regels, kleurmarkeringen: %s"%info)
        cols=await page.evaluate("Object.keys(DATA.categoryColours).length")
        print(("OK   " if cols==22 else "FOUT ")+"22 categoriekleuren overgenomen (%d)"%cols)
        # formulepagina openen en rekenen
        await page.click("#tabF"); await page.wait_for_timeout(300)
        await page.fill("#searchBox","Bewonder v09"); await page.wait_for_timeout(300)
        await page.click("#list .item >> nth=0"); await page.wait_for_timeout(500)
        tot=await page.evaluate("(()=>{const f=DATA.formulas.find(x=>x.name==='Bewonder v09 45gr'); const K=calc(f.versions[0].lines); return [K.totalW.toFixed(3), K.totalAbsPct.toFixed(2)]})()")
        print(("OK   " if tot==["46.256","85.12"] else "FOUT ")+"Bewonder v09 45gr in de app: %s g / %s %%"%tuple(tot))
        badge=await page.evaluate("[...document.querySelectorAll('#content .badge')].map(b=>b.textContent).join('|')")
        print("     badges op de formulepagina: %s"%badge)
        print(("OK   " if not errs else "FOUT ")+"geen JavaScript-fouten"+("" if not errs else ": "+errs[0][:200]))
        await b.close()
asyncio.run(main())
