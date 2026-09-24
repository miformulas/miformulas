"""Terugzetten terwijl de app loopt (bouw 260922k, B23 en C-d 33 van de vijfde audit): Restore a Backup… en Restore
daily snapshot in het venster Import & export, en niet op de Welcome-pagina. Wat terugkomt vervangt al je data waar
ze staat (browseropslag, een databestand, een server), na een vraag met wat beide bevatten, en is één stap voor Undo;
het Backup-bestand zelf blijft ongemoeid; Cancel verandert niets; een bestand dat geen data is of geen JSON, zegt dat;
de dagsnapshot staat er alleen voor de data waarvan ze genomen is, en een snapshot gelijk aan je data zegt dat er niets
terug te zetten is; in een tweede venster (alleen-lezen) staan beide knoppen uit.
Vereist een webserver met de inhoud van public\\ op poort 8765 (cd public && python -m http.server 8765)."""
import hashlib, json, os, tempfile
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
BASE = "http://127.0.0.1:8765"
URL = BASE + "/index.html"
API = BASE + "/api"
STARTER = open(os.path.join(PUB, "data", "miformulas-starter.json"), encoding="utf-8").read()
ST = json.loads(STARTER)
N = len(ST["formulas"])
FIRST = ST["formulas"][0]["name"]
BK = json.loads(STARTER); BK["formulas"][0]["name"] = "Uit de Backup"; del BK["formulas"][-1]
TMP = tempfile.mkdtemp()
def put(name, text):
    path = os.path.join(TMP, name); open(path, "w", encoding="utf-8").write(text); return path
BACKUP = put("260924_0912_miformulas-data.json", json.dumps(BK, indent=1))
NOTDATA = put("formule.json", json.dumps({"type": "miformulas-import", "name": "Een formule", "lines": []}))
BROKEN = put("kapot.json", '{"formulas": [')
md5 = lambda path: hashlib.md5(open(path, "rb").read()).hexdigest()
BACKUP_MD5 = md5(BACKUP)
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

FAKE_FS = """
  function FakeHandle(name){ this.name = name; this.kind = 'file'; this.__fake = true; }
  FakeHandle.prototype.queryPermission = async () => 'granted';
  FakeHandle.prototype.requestPermission = async () => 'granted';
  FakeHandle.prototype.getFile = async function(){ return new File([localStorage.getItem('fakefile') || '{}'], this.name); };
  FakeHandle.prototype.createWritable = async () => ({ write: async (s) => { localStorage.setItem('fakefile', s); }, close: async () => {} });
  const desc = Object.getOwnPropertyDescriptor(IDBRequest.prototype, 'result');
  Object.defineProperty(IDBRequest.prototype, 'result', { get(){ const v = desc.get.call(this); if (v && v.__fake) Object.setPrototypeOf(v, FakeHandle.prototype); return v; } });
  window.showOpenFilePicker = async () => [new FakeHandle('mydata.json')];
  window.showSaveFilePicker = async (opts) => new FakeHandle(opts.suggestedName);
"""

with sync_playwright() as p:
    b = p.chromium.launch()
    def page(ctx=None, init=None):
        ctx = ctx or b.new_context(viewport={"width": 1280, "height": 900})
        pg = ctx.new_page(); pg.msgs = []; pg.answers = []
        def on_dialog(d):
            pg.msgs.append(d.message)
            if d.type == "confirm" and pg.answers and not pg.answers.pop(0): d.dismiss()
            else: d.accept()
        pg.on("dialog", on_dialog)
        if init: pg.add_init_script(init)
        return pg
    names = lambda pg: pg.evaluate("DATA.formulas.map(f => f.name)")
    undos = lambda pg: pg.evaluate("UNDO.length")
    def io(pg):
        pg.click("#btnIO"); pg.wait_for_timeout(400)
    def close_io(pg):
        if pg.evaluate("$('#dlg').open"): pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
    def restore_backup(pg, path, answer=True):
        io(pg)
        if not pg.locator("#ioRestore").count(): close_io(pg); return False
        pg.answers = [answer]; n0 = len(pg.msgs)
        with pg.expect_file_chooser() as fc: pg.click("#ioRestore")
        fc.value.set_files(path); pg.wait_for_timeout(700)
        return pg.msgs[n0:]
    def restore_snap(pg, answer=True):
        io(pg)
        if not pg.locator("#ioSnap").count(): close_io(pg); return False
        pg.answers = [answer]; n0 = len(pg.msgs)
        pg.click("#ioSnap"); pg.wait_for_timeout(700)
        return pg.msgs[n0:]
    stored = lambda pg: pg.evaluate("idb.get('demoData')") or ""
    def undo(pg):   # the Undo button; greyed out when there is nothing to take back (an older build that did nothing)
        if pg.locator("#btnUndo").is_enabled(): pg.click("#btnUndo")
        pg.wait_for_timeout(500)

    # ---------- 1. browser storage ----------
    pg = page()
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.click("#btnStarter"); pg.wait_for_timeout(3500)
    pg.reload(); pg.wait_for_timeout(1500)                     # a start from your own data takes the daily snapshot
    day = pg.evaluate("today()")
    snap = pg.evaluate("idb.get('dailyBak')")
    check(f"de dagsnapshot noemt de data waarvan ze is ({(snap or {}).get('where')!r})", bool(snap) and snap.get("where") == "browser")
    pg.click("#btnHome"); pg.wait_for_timeout(400)
    check("de Welcome-pagina heeft geen knoppen om terug te zetten", "Restore a Backup" not in pg.locator("#content").inner_text()
          and not pg.locator("#ioRestore").count())
    io(pg)
    check("Import & export heeft Restore a Backup…", pg.locator("#ioRestore").is_visible() and pg.locator("#ioRestore").inner_text() == "Restore a Backup…")
    check(f"en Restore daily snapshot met de datum ({day})", pg.locator("#ioSnap").is_visible() and day in pg.locator("#ioSnap").inner_text())
    close_io(pg)

    u0 = undos(pg)
    got = restore_snap(pg)
    check(f"een snapshot gelijk aan je data: niets terug te zetten, geen undo-stap ({[m[:60] for m in got or []]})",
          bool(got) and "nothing to put back" in got[0] and undos(pg) == u0)

    # this morning's mistake: a formula renamed and another one deleted
    pg.evaluate("""() => { const c = structuredClone(DATA.formulas); pushUndo(() => { DATA.formulas = c; });
        DATA.formulas[0].name = "Vergissing van vanmorgen"; DATA.formulas.splice(1, 1); markDirty(); }""")
    pg.wait_for_timeout(3000)
    got = restore_snap(pg)
    print("     ", [m[:150].replace("\n", " ") for m in got or []])
    check("de dagsnapshot vraagt eerst, met wat beide bevatten",
          bool(got) and f"daily snapshot of {day}" in got[0] and f"It holds {N} formulas" in got[0] and f"your data now holds {N-1} formulas" in got[0])
    check(f"en zet de stand van de eerste opening terug ({len(names(pg))} formules)", names(pg)[0] == FIRST and len(names(pg)) == N)
    pg.wait_for_timeout(3500)
    check("in de browseropslag, waar de data staat", FIRST in stored(pg) and "Vergissing van vanmorgen" not in stored(pg))
    undo(pg)
    check("Undo neemt het in één stap terug", names(pg)[0] == "Vergissing van vanmorgen" and len(names(pg)) == N - 1)

    got = restore_backup(pg, BACKUP)
    print("     ", [m[:150].replace("\n", " ") for m in got or []])
    check("Restore a Backup… vraagt eerst, met de naam van het bestand en wat beide bevatten",
          bool(got) and "260924_0912_miformulas-data.json" in got[0] and f"It holds {N-1} formulas" in got[0] and f"now holds {N-1} formulas" in got[0])
    check("en zet de Backup in de plaats van al je data", names(pg)[0] == "Uit de Backup" and len(names(pg)) == N - 1)
    pg.wait_for_timeout(3500)
    check("in de browseropslag", "Uit de Backup" in stored(pg))
    check("het Backup-bestand zelf blijft ongemoeid", md5(BACKUP) == BACKUP_MD5)
    undo(pg)
    check("Undo brengt de data van vóór het terugzetten terug", names(pg)[0] == "Vergissing van vanmorgen")

    u0, n0 = undos(pg), names(pg)
    got = restore_backup(pg, BACKUP, answer=False)
    check("Cancel verandert niets en maakt geen undo-stap", bool(got) and names(pg) == n0 and undos(pg) == u0)
    got = restore_backup(pg, NOTDATA)
    check(f"een bestand dat geen data is, zegt dat ({[m[:50] for m in got or []]})", bool(got) and "not a miFormulas data file" in got[0] and names(pg) == n0)
    got = restore_backup(pg, BROKEN)
    check(f"een bestand dat geen JSON is, zegt dat ({[m[:50] for m in got or []]})", bool(got) and "not valid JSON" in got[0] and names(pg) == n0)

    pg.evaluate("""async () => { const s = await idb.get("dailyBak"); await idb.set("dailyBak", {...s, where: "file andere.json"}); }""")
    io(pg)
    check("de snapshot van andere data wordt niet aangeboden", pg.locator("#ioRestore").count() == 1 and not pg.locator("#ioSnap").count())
    close_io(pg)
    pg.evaluate("""async () => { const s = await idb.get("dailyBak"); delete s.where; await idb.set("dailyBak", s); }""")
    io(pg)
    check("een snapshot van een vorige bouw, zonder die vermelding, wel", pg.locator("#ioSnap").count() == 1)
    close_io(pg)

    # ---------- 2. a second window only reads ----------
    pg2 = page(ctx=pg.context)
    pg2.goto(URL); pg2.wait_for_timeout(1500)
    io(pg2)
    check("in een tweede venster staan beide knoppen uit",
          pg2.evaluate("LOCKED") and pg2.locator("#ioRestore").count() == 1 and pg2.locator("#ioRestore").is_disabled()
          and (not pg2.locator("#ioSnap").count() or pg2.locator("#ioSnap").is_disabled()))
    pg.context.close()

    # ---------- 3. on a server ----------
    puts = []
    def srv(route):
        r = route.request
        h = {"Access-Control-Allow-Origin": "*", "Access-Control-Expose-Headers": "ETag"}
        if r.method == "GET": return route.fulfill(status=200, content_type="application/json", headers={**h, "ETag": '"e1"'}, body=STARTER)
        puts.append({"ifm": r.headers.get("if-match", ""), "body": r.post_data or ""})
        route.fulfill(status=200, content_type="application/json", headers={**h, "ETag": '"e2"'}, body='{"ok":true}')
    pg = page()
    pg.route("**/api*", srv)
    pg.goto(URL); pg.wait_for_timeout(700)
    pg.evaluate(f"async () => {{ await idb.set('serverUrl', {json.dumps(API)}); await idb.set('token', 'tok'); }}")
    pg.reload(); pg.wait_for_timeout(1500)
    io(pg)
    check("op een server: de snapshot van die server wordt aangeboden", pg.evaluate("REMOTE") and pg.locator("#ioSnap").count() == 1)
    close_io(pg)
    got = restore_backup(pg, BACKUP)
    pg.wait_for_timeout(3500)
    last = puts[-1] if puts else {"ifm": "", "body": ""}
    check(f"op een server: de Backup gaat naar de server, met de gewone conflictwacht ({last['ifm']})",
          bool(got) and "Uit de Backup" in last["body"] and last["ifm"] == '"e1"')
    pg.context.close()

    # ---------- 4. in a data file ----------
    pg = page(init=FAKE_FS)
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.evaluate("s => localStorage.setItem('fakefile', s)", STARTER)
    pg.click("#btnOpen"); pg.wait_for_timeout(1500)
    check("in een databestand: de app werkt in mydata.json", pg.evaluate("HANDLE && HANDLE.name") == "mydata.json")
    got = restore_backup(pg, BACKUP)
    pg.wait_for_timeout(3500)
    check("en de Backup komt in dat databestand, niet in de Backup", bool(got) and "Uit de Backup" in (pg.evaluate("localStorage.getItem('fakefile')") or "")
          and md5(BACKUP) == BACKUP_MD5)
    pg.context.close()
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
