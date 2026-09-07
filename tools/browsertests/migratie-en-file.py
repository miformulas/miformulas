import asyncio
from playwright.async_api import async_playwright
URL="http://localhost:8765/"
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); ctx=await b.new_context(); page=await ctx.new_page()
        page.on("dialog", lambda d: asyncio.ensure_future(d.dismiss()))
        # A. bestaand toestel: token in idb, nog geen serverUrl -> moet data.php kiezen zonder probe
        await page.goto(URL); await page.wait_for_timeout(500)
        await page.evaluate("(async()=>{await idb.set('token','kMpd-test'); await idb.set('serverUrl', undefined);})()")
        # idb.put(undefined) slaat undefined op; simuleer 'sleutel ontbreekt' door te verwijderen
        await page.evaluate("new Promise(r=>{const t=idb.db.transaction('kv','readwrite').objectStore('kv').delete('serverUrl'); t.onsuccess=r; t.onerror=r;})")
        await page.goto(URL); await page.wait_for_timeout(1200)
        rem=await page.evaluate("(async()=>[REMOTE, API, await idb.get('serverUrl')])()")
        print(("OK   " if rem[0] and rem[1]=="data.php" and rem[2]=="data.php" else "FOUT ")+"bestaand token zonder serverUrl -> REMOTE met data.php, en onthouden: %s"%rem)
        # B. token mag nooit in de HTML zitten
        html=open('/home/claude/site/index.html',encoding='utf-8').read()
        print(("OK   " if 'kMpd' not in html else "FOUT ")+"geen token in het HTML-bestand")
        await b.close()
        # C. file:// -> klassieke bestandsmodus, geen starterknop, geen probe
        b=await p.chromium.launch(); ctx=await b.new_context(); page=await ctx.new_page()
        errs=[]; page.on("pageerror", lambda e: errs.append(str(e)))
        await page.goto("file:///home/claude/site/index.html"); await page.wait_for_timeout(800)
        st=await page.is_visible("#btnStarter"); op=await page.text_content("#btnOpen")
        modes=await page.evaluate("[DEMO, REMOTE]")
        print(("OK   " if (not st and "Open data file" in op and modes==[False,False]) else "FOUT ")+"file://: bestandsmodus, 'Open data file…', DEMO=REMOTE=false (%s, starterknop %s)"%(modes, st))
        print(("OK   " if not errs else "FOUT ")+"file://: geen JavaScript-fouten"+("" if not errs else ": "+errs[0][:200]))
        await b.close()
asyncio.run(main())
