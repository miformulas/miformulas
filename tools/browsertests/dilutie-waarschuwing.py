"""The ⚠ beside a dilution the material does not have (build 261004b): only in the version you can still edit. An
older, frozen or imported version no longer changes, so it goes without the mark; a new version made from one shows
it again, and the line keeps its value throughout. Also the texts of this build: section 7 says where the mark shows,
and section 18 step 5 follows the Cloudflare dashboard (the Bindings block under Settings), as does the comment at the
top of server/worker.js.
Needs the local web server on port 8765 (see README)."""
import os, sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
PUB = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
WARN = 'table.ftable tbody span[title^="This dilution is not among"]'
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 950})
    page = ctx.new_page(); errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1600)

    # a material with 100 % and 10 %, and lines that use it at 5 %, a dilution it does not have:
    # a formula of your own with two versions, and a frozen Formulair import
    page.evaluate("""() => {
      const m = {id:"m-w1", name:"Warning test material", cas:"", category:"Uncategorised", supplier:"", costPerGram:null,
        ifraLimit:null, inventory:"", pyramid:5, isSolvent:false, description:"",
        dilutions:[{pct:100, isBase:true, date:today(), notes:""}, {pct:10, isBase:false, date:today(), notes:""}]};
      DATA.materials.push(m);
      const L = () => [{id:uid("l-"), materialId:m.id, dilutionPct:5, weightG:1, remark:1}];
      DATA.formulas.push({id:"f-w1", name:"Warning own", category:"Uncategorised", created:today(), frozenImport:false,
        versions:[{v:1, date:today(), notes:"", lines:L()}, {v:2, date:today(), notes:"", lines:L()}]});
      DATA.formulas.push({id:"f-w2", name:"Warning Formulair", category:"Uncategorised", created:today(), frozenImport:true,
        versions:[{v:1, date:today(), notes:"", imported:true, sourceName:"Warning Formulair", lines:L()}]});
      invalidateMats(); buildUsage(); render();
    }""")

    def show(fid, idx):
        page.evaluate("([id, i]) => switchTab('F', id, {type:'v', idx:i})", [fid, idx]); page.wait_for_timeout(500)
        row = page.locator("table.ftable tbody tr", has_text="Warning test material").first.inner_text()
        return page.locator(WARN).count(), row

    n, row = show("f-w1", 1)
    check(f"the latest version, which you can edit, shows the ⚠ ({n})", n == 1)
    n, row = show("f-w1", 0)
    check(f"an older version of the same formula does not ({n})", n == 0)
    check(f"and its line keeps its 5 % ({row.split(chr(9))[2:3]})", "5%" in row)
    n, row = show("f-w2", 0)
    check(f"a frozen Formulair import does not ({n})", n == 0)
    check("and its line keeps its 5 % too", "5%" in row)

    # + New version from the older version: the copy is the one you edit, and the mark is back
    show("f-w1", 0)
    page.click("#btnNewV"); page.wait_for_timeout(700)
    cur = page.evaluate("[DATA.formulas.find(f => f.id === 'f-w1').versions.length, VIEW.sub && VIEW.sub.idx]")
    n = page.locator(WARN).count()
    check(f"+ New version from the older version opens the new version {cur} and shows the ⚠ again ({n})", cur[0] == 3 and cur[1] == 2 and n == 1)
    check(f"no errors in the page ({errs[:2]})", not errs)
    b.close()

# the texts of this build
man = open(os.path.join(PUB, "docs", "manual.md"), encoding="utf-8").read()
app = open(os.path.join(PUB, "index.html"), encoding="utf-8").read()
wjs = open(os.path.join(PUB, "server", "worker.js"), encoding="utf-8").read()
zin = "Only the version you can still edit shows the mark; a new version made from an older or frozen one shows it again."
check("section 7 says where the ⚠ shows, in the manual and in the Help", zin in man and zin in app)
check("section 18 step 5: the Settings tab and the Bindings block, then Add Binding",
      "open its **Settings** tab and press **Add binding** in the **Bindings** block" in man
      and "press **Add Binding**; in the form that follows" in man and "Bindings** tab" not in man)
check("section 18 step 5 says the Wrangler notice can be closed", "A notice about a Wrangler configuration may appear" in man)
check("the comment at the top of worker.js names the Bindings block under Settings",
      "tab Settings, block Bindings" in wjs and "tab Bindings " not in wjs)

print(f"\n{ok} OK, {fail} FAIL")
sys.exit(1 if fail else 0)
