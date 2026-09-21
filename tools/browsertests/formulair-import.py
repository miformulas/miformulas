import asyncio, importlib.util, json, os, subprocess, sys, time
from playwright.async_api import async_playwright
# Een Formulair-database is die van jezelf en staat niet in de repo, dus wijs hem aan:
#   MIF_SQLITE=/pad/naar/DataModel.sqlite python formulair-import.py
# MIF_REF is de uitvoer van tools/formulair-naar-json.py op diezelfde database; ontbreekt ze, dan maakt
# de test ze zelf aan. MIF_OUT is waar wat de browser maakte blijft staan. Beide staan standaard hier.
HERE = os.path.dirname(os.path.abspath(__file__))
SQ = os.environ.get("MIF_SQLITE", "")
if not SQ or not os.path.exists(SQ):
    sys.exit("zet MIF_SQLITE op het pad van DataModel.sqlite (de kopie die je na File > Close in Formulair maakte)")
REF = os.environ.get("MIF_REF", os.path.join(HERE, "formulair-ref.json"))
OUT = os.environ.get("MIF_OUT", os.path.join(HERE, "formulair-browser-out.json"))
if not os.path.exists(REF):
    print("referentie ontbreekt; formulair-naar-json.py maakt ze nu aan:", REF)
    subprocess.run([sys.executable, os.path.join(HERE, "..", "formulair-naar-json.py"), SQ, REF], check=True)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); ctx=await b.new_context(accept_downloads=True); page=await ctx.new_page()
        errs=[]; page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("console", lambda m: errs.append("console."+m.type+": "+m.text) if m.type=="error" else None)
        await page.goto("http://localhost:8765/formulair-import.html"); await page.wait_for_timeout(500)
        # De pagina en formulair-naar-json.py moeten dezelfde database op dezelfde manier lezen, dus ook op de
        # twee plaatsen waar Python en JavaScript uit zichzelf uiteenlopen: een kleurwaarde die precies op een
        # halve landt (Python rondde naar het even getal, de browser omhoog) en een naam met een accent
        # (Python sorteerde op codetabel, de browser op taal, en zonder taal op die van het toestel).
        spec=importlib.util.spec_from_file_location("fnj", os.path.join(HERE,"..","formulair-naar-json.py"))
        fnj=importlib.util.module_from_spec(spec); spec.loader.exec_module(fnj)
        BLOBS=["0.00196078431372549 0.00980392156862745 0.01764705882352941",
               "0.03333333333333333 0.06470588235294118 0.0803921568627451",
               "0 1 0.7509803921568627"]
        kleur=await page.evaluate("bs => bs.map(s => colourOf(new TextEncoder().encode(s)))", BLOBS)
        pyk=[fnj.colour_of(s.encode("latin1")) for s in BLOBS]
        print(("OK   " if kleur==pyk else "FOUT ")+"zelfde kleur uit dezelfde blob, ook op een halve: %s (Python %s)"%(kleur,pyk))
        NAMEN=["Ylang","Élemi","Zdravetz","Ambrette","elemi","Ångström","Oakmoss","Œillet",
               "Ægir","Łódź","Øre","Straße"]
        vol=await page.evaluate("n => [...n].sort(byLower)", NAMEN)
        pyv=sorted(NAMEN, key=fnj.sort_key)
        print(("OK   " if vol==pyv else "FOUT ")+"zelfde volgorde voor namen met een accent: %s (Python %s)"%(vol,pyv))
        t0=time.time()
        await page.set_input_files("#file", SQ)
        await page.wait_for_selector("#btnDl", timeout=180000)
        dt=time.time()-t0
        print("OK   pagina las 214 MB en converteerde in %.1f s"%dt)
        box=await page.text_content("#out")
        print("     samenvatting:", " ".join(box.split())[:220])
        # bouw 260920o: elke Formulair-database staat in WAL-modus, dus dit was een alarm bij elke import.
        # Het is een nota geworden die zegt welk bestand het antwoord draagt, en ze staat niet meer in de amberkleurige bak.
        note = "-wal" in box and "Is this copy complete?" in box
        print(("OK   " if note else "FOUT ")+"nota over de -wal-buur getoond, met de vraag erboven")
        amber = await page.evaluate("[...document.querySelectorAll('#out .box')].some(b => b.classList.contains('warn'))")
        print(("OK   " if not amber else "FOUT ")+"de nota is geen waarschuwing (geen .warn-bak op de pagina)")
        async with page.expect_download() as dl:
            await page.click("#btnDl")
        d=await dl.value; path=await d.path()
        got=json.load(open(path,encoding='utf-8'))
        ref=json.load(open(REF,encoding='utf-8'))
        got['meta']['generated']=ref['meta']['generated']
        same = json.dumps(got,sort_keys=True,ensure_ascii=False)==json.dumps(ref,sort_keys=True,ensure_ascii=False)
        print(("OK   " if same else "FOUT ")+"gedownloade JSON gelijk aan de Python-referentie (ontleed vergeleken, meta.generated genormaliseerd)")
        if not same:
            for k in ref:
                a=json.dumps(got.get(k),sort_keys=True); r=json.dumps(ref.get(k),sort_keys=True)
                if a!=r: print("     verschil in", k, len(a), len(r))
        print(("OK   " if not errs else "FOUT ")+"geen JavaScript-fouten"+("" if not errs else ": "+errs[0][:200]))
        # geheugen
        mem=await page.evaluate("performance.memory ? Math.round(performance.memory.usedJSHeapSize/1048576) : -1")
        print("     JS-heap na conversie: %d MB"%mem)
        json.dump(got, open(OUT,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
        await b.close()
asyncio.run(main())
