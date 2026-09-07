"""Bestandsmodus (gedownloade app geopend via file://): hint, starterset, aanmaak van het databestand.
Draait rechtstreeks op public\index.html; de starterset wordt vanaf schijf geserveerd omdat de test miformulas.com nabootst."""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
APP = "file://" + os.path.join(PUB, "index.html")
STARTER = open(os.path.join(PUB, "data", "miformulas-starter.json"), encoding="utf-8").read()
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += cond; fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    page = ctx.new_page()
    written = []
    # the site is not reachable from here: serve the starter set for the absolute URL
    page.route("https://miformulas.com/data/miformulas-starter.json",
               lambda r: r.fulfill(status=200, content_type="application/json", body=STARTER,
                                   headers={"Access-Control-Allow-Origin": "*"}))
    # fake File System Access API: showSaveFilePicker returns a handle that records what is written
    page.add_init_script("""
      window.__written = [];
      window.showOpenFilePicker = async () => { throw new Error('no picker in test'); };
      window.showSaveFilePicker = async (opts) => {
        window.__pickerOpts = opts;
        return { name: opts.suggestedName, kind: 'file',
          queryPermission: async () => 'granted', requestPermission: async () => 'granted',
          getFile: async () => new File([window.__written.at(-1) || '{}'], opts.suggestedName),
          createWritable: async () => ({ write: async (s) => window.__written.push(s), close: async () => {} }) };
      };
    """)
    msgs = []
    page.on("console", lambda m: msgs.append(m.text))
    page.on("dialog", lambda d: (msgs.append("DIALOG " + d.message), d.dismiss()))
    page.goto(APP)
    page.wait_for_timeout(800)

    check("protocol is file:", page.evaluate("location.protocol") == "file:")
    check("build stamp 260907b", page.locator("#build").inner_text().strip() == "260907b")
    hint = page.locator("#landingHint").inner_text()
    check("hint mentions own computer", "from your own computer" in hint)
    check("hint recommends Documents\\miFormulas", "Documents\\miFormulas" in hint)
    check("hint mentions backups subfolder", "backups" in hint)
    check("starter button visible", page.locator("#btnStarter").is_visible())
    check("open data file visible", page.locator("#btnOpen").is_visible())
    check("download link hidden in file mode", not page.locator("#btnDownload").is_visible())
    check("STARTER_URL absolute", page.evaluate("STARTER_URL") == "https://miformulas.com/data/miformulas-starter.json")

    page.click("#btnStarter")
    page.wait_for_timeout(1500)
    check("landing gone", not page.locator("#landing").is_visible())
    opts = page.evaluate("window.__pickerOpts")
    check("save picker suggested miformulas-data.json", opts and opts.get("suggestedName") == "miformulas-data.json")
    check("save picker id miformulas-data", opts and opts.get("id") == "miformulas-data")
    w = page.evaluate("window.__written")
    check("data file written once", len(w) == 1)
    d = json.loads(w[0]) if w else {}
    check("written file has 16 formulas", len(d.get("formulas", [])) == 16)
    check("written file has 199 materials", len(d.get("materials", [])) == 199)
    st = page.locator("#saveState").inner_text()
    check("state shows Saved (file)", st.startswith("Saved") and "browser" not in st)
    check("no dialogs", not any(m.startswith("DIALOG") for m in msgs))
    

    # cancelled picker: app runs without a file
    page2 = ctx.new_page()
    page2.route("https://miformulas.com/data/miformulas-starter.json",
                lambda r: r.fulfill(status=200, content_type="application/json", body=STARTER,
                                    headers={"Access-Control-Allow-Origin": "*"}))
    page2.add_init_script("window.showSaveFilePicker = async () => { throw new DOMException('cancel','AbortError'); }; window.showOpenFilePicker = async () => {};")
    page2.goto(APP); page2.wait_for_timeout(800)
    page2.click("#btnStarter"); page2.wait_for_timeout(1500)
    check("cancelled picker: app still boots", not page2.locator("#landing").is_visible())
    st2 = page2.locator("#saveState").inner_text()
    check("cancelled picker: no file access state", "No file access" in st2 or "Unsaved" in st2)

    # offline: clear message
    page3 = ctx.new_page()
    page3.route("https://miformulas.com/data/miformulas-starter.json", lambda r: r.abort())
    dl = []
    page3.on("dialog", lambda d: (dl.append(d.message), d.dismiss()))
    page3.goto(APP); page3.wait_for_timeout(800)
    page3.click("#btnStarter"); page3.wait_for_timeout(1500)
    check("offline: alert mentions internet", any("internet connection" in m for m in dl))
    check("offline: landing stays", page3.locator("#landing").is_visible())
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
sys.exit(1 if fail else 0)
