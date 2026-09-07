import asyncio, json, time
from playwright.async_api import async_playwright
SQ="/mnt/user-data/uploads/miFormulas/co.uk.lux-terra.Formulair/Data/Library/Application Support/Formulair/DataModel.sqlite"
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); ctx=await b.new_context(accept_downloads=True); page=await ctx.new_page()
        errs=[]; page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("console", lambda m: errs.append("console."+m.type+": "+m.text) if m.type=="error" else None)
        await page.goto("http://localhost:8765/formulair-import.html"); await page.wait_for_timeout(500)
        t0=time.time()
        await page.set_input_files("#file", SQ)
        await page.wait_for_selector("#btnDl", timeout=180000)
        dt=time.time()-t0
        print("OK   pagina las 214 MB en converteerde in %.1f s"%dt)
        box=await page.text_content("#out")
        print("     samenvatting:", " ".join(box.split())[:220])
        warn = "-wal" in box
        print(("OK   " if warn else "FOUT ")+"WAL-waarschuwing getoond (database staat in WAL-modus)")
        async with page.expect_download() as dl:
            await page.click("#btnDl")
        d=await dl.value; path=await d.path()
        got=json.load(open(path,encoding='utf-8'))
        ref=json.load(open('/home/claude/ref-cloud.json',encoding='utf-8'))
        got['meta']['generated']=ref['meta']['generated']
        same = json.dumps(got,sort_keys=True,ensure_ascii=False)==json.dumps(ref,sort_keys=True,ensure_ascii=False)
        print(("OK   " if same else "FOUT ")+"gedownloade JSON is byte-voor-byte gelijk aan de Python-referentie")
        if not same:
            for k in ref:
                a=json.dumps(got.get(k),sort_keys=True); r=json.dumps(ref.get(k),sort_keys=True)
                if a!=r: print("     verschil in", k, len(a), len(r))
        print(("OK   " if not errs else "FOUT ")+"geen JavaScript-fouten"+("" if not errs else ": "+errs[0][:200]))
        # geheugen
        mem=await page.evaluate("performance.memory ? Math.round(performance.memory.usedJSHeapSize/1048576) : -1")
        print("     JS-heap na conversie: %d MB"%mem)
        json.dump(got, open('/home/claude/browser-out.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
        await b.close()
asyncio.run(main())
