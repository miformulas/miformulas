import asyncio
from playwright.async_api import async_playwright
URL="http://localhost:8765/"
async def main():
    fouten=[]
    def check(c,m):
        print(("OK   " if c else "FOUT ")+m)
        if not c: fouten.append(m)
    async with async_playwright() as p:
        b=await p.chromium.launch(); ctx=await b.new_context(); page=await ctx.new_page()
        errs=[]; page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
        await page.goto(URL); await page.wait_for_timeout(600)
        await page.evaluate("new Promise(r=>{const t=idb.db.transaction('kv','readwrite').objectStore('kv').clear(); t.onsuccess=r; t.onerror=r;})")
        await page.goto(URL); await page.wait_for_timeout(600)
        check(await page.evaluate("document.getElementById('storageHint').hidden"), "landing: balk verborgen")
        await page.click("#btnStarter"); await page.wait_for_timeout(800)
        persisted=await page.evaluate("navigator.storage.persisted()")
        hidden=await page.evaluate("document.getElementById('storageHint').hidden")
        check(hidden == persisted, f"na laden: balk zichtbaar precies als niet persistent (persisted={persisted}, hidden={hidden})")
        txt=await page.text_content("#storageHintText")
        check("kept in this browser" in txt and "Save it to a data file" in txt, f"tekst voor niet-fallback: {txt[:90]}…")
        await page.wait_for_timeout(3200)
        check(await page.evaluate("saveData._persistAsked === true"), "persist() eenmalig aangevraagd bij de eerste opslag")
        await page.click("#storageHintClose"); await page.wait_for_timeout(200)
        check(await page.evaluate("document.getElementById('storageHint').hidden"), "sluitknop verbergt de balk")
        await page.goto(URL); await page.wait_for_timeout(900)
        check(await page.evaluate("document.getElementById('storageHint').hidden"), "zelfde sessie: blijft verborgen (sessionStorage)")
        # nieuwe browsersessie: balk terug (tenzij persistent)
        await ctx.close(); ctx=await b.new_context(); page=await ctx.new_page()
        page.on("pageerror", lambda e: errs.append(str(e)))
        await page.goto(URL); await page.wait_for_timeout(900)
        # nieuwe context = lege IndexedDB, dus landing; laad starter en kijk
        await page.click("#btnStarter"); await page.wait_for_timeout(800)
        p2=await page.evaluate("navigator.storage.persisted()")
        h2=await page.evaluate("document.getElementById('storageHint').hidden")
        check(h2 == p2, f"nieuwe sessie: balk volgt persisted (persisted={p2}, hidden={h2})")
        # FALLBACK-tekst simuleren
        await page.evaluate("FALLBACK = true; updateStorageHint()"); await page.wait_for_timeout(200)
        txt=await page.text_content("#storageHintText")
        check("cannot write to files" in txt and "Chrome or Edge" in txt, f"fallback-tekst: {txt[-80:]}")
        # REMOTE/HANDLE: balk weg
        await page.evaluate("DEMO=false; updateStorageHint()"); await page.wait_for_timeout(200)
        check(await page.evaluate("document.getElementById('storageHint').hidden"), "buiten DEMO: balk verborgen")
        check(not errs, "geen JavaScript-fouten"+("" if not errs else ": "+errs[0][:150]))
        await b.close()
    print("\n"+("%d probleem(en)"%len(fouten) if fouten else "alles in orde"))
asyncio.run(main())
