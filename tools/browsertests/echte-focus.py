"""Echte focus: een veld dat je nog aan het typen bent, terwijl je even weg bent (A1 van de mini-audit op 260922m).

Playwright houdt elk venster vooraan, dus wat een browser doet als je van tabblad wisselt of een ander programma
naar voren haalt, ziet de rest van de reeks niet. Hier draait Chromium met een echt venster op een virtueel scherm
(Xvfb) onder een vensterbeheerder (openbox); xdotool klikt en typt zoals een mens, en CDP leest de app uit.
Chromium stuurt `change` zodra zijn venster de focus verliest: bij een ander tabblad, bij een ander programma ernaast
en bij een programma dat het venster bedekt. Tot en met bouw 260922m tekende de app het gewicht daarna opnieuw,
met de hele waarde geselecteerd: "12" getypt, weg, "5" erbij, en de regel zei 5 g.

    sudo apt-get install -y xvfb openbox xdotool && pip install python-xlib websocket-client
    cd public && python -m http.server 8765
    python tools/browsertests/echte-focus.py

Zonder een van die onderdelen stopt het script met exitcode 2 en zegt het wat ontbreekt, zodat het in een reeks geen
valse fout geeft. Het gebruikt de Chromium van Playwright.
"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request

URL = os.environ.get("MIF_URL", "http://localhost:8765/index.html")
DISPLAY, PORT = ":57", 9333
ok = fail = 0


def check(naam, cond, extra=""):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam + (("  <- " + extra) if (extra and not cond) else ""), flush=True)


ontbreekt = [x for x in ("Xvfb", "openbox", "xdotool") if not shutil.which(x)]
try:
    import websocket
    from Xlib import X, display as xdisplay
except ImportError as e:
    ontbreekt.append(str(e.name))
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        CHROME = p.chromium.executable_path
    if not os.path.exists(CHROME):
        ontbreekt.append("Chromium van Playwright")
except Exception:
    ontbreekt.append("playwright")
if ontbreekt:
    print("Overgeslagen: dit ontbreekt: " + ", ".join(ontbreekt) + " (zie de kop van dit bestand)")
    sys.exit(2)


class Tab:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=30, suppress_origin=True)
        self.n, self.events = 0, []

    def send(self, method, params=None):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params or {}}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == self.n:
                return m.get("result", m)
            if "method" in m:
                self.events.append(m)

    def pump(self, secs):
        end = time.time() + secs
        self.ws.settimeout(0.1)
        try:
            while time.time() < end:
                try:
                    m = json.loads(self.ws.recv())
                    if "method" in m:
                        self.events.append(m)
                except websocket.WebSocketTimeoutException:
                    pass
        finally:
            self.ws.settimeout(30)

    def js(self, expr):
        r = self.send("Runtime.evaluate", {"expression": expr, "awaitPromise": True, "returnByValue": True})
        if "exceptionDetails" in r:
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:400])
        return r.get("result", {}).get("value")


def xdo(*a):
    return subprocess.run(["xdotool", *a], env={**os.environ, "DISPLAY": DISPLAY}, capture_output=True, text=True).stdout.strip()


class Scherm:
    """Xvfb, openbox en één Chromium met de app, de starterset geladen."""
    def __init__(self):
        self.xv = subprocess.Popen(["Xvfb", DISPLAY, "-screen", "0", "1400x1000x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.2)
        env = {**os.environ, "DISPLAY": DISPLAY}
        self.wm = subprocess.Popen(["openbox"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.8)
        self.prof = tempfile.mkdtemp()
        self.ch = subprocess.Popen([CHROME, f"--remote-debugging-port={PORT}", f"--user-data-dir={self.prof}", "--no-first-run",
                                    "--no-default-browser-check", "--no-sandbox", "--window-size=1200,900", "about:blank"],
                                   env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                self.eerste = [t for t in self.tabs() if t["type"] == "page"][0]; break
            except Exception:
                time.sleep(0.2)
        self.d = xdisplay.Display(DISPLAY)
        self.A = Tab(self.eerste["webSocketDebuggerUrl"])
        time.sleep(0.4)
        self.venster = xdo("search", "--onlyvisible", "--class", "chromium").split("\n")[0]
        xdo("windowactivate", "--sync", self.venster); time.sleep(0.3)
        self.A.send("Page.enable")
        self.A.send("Page.navigate", {"url": URL}); time.sleep(2.5)
        self.A.js("document.querySelector('#btnStarter').click()"); time.sleep(2.5)

    def tabs(self):
        return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json").read())

    def klik(self, sel_js):   # een echte muisklik op het element, via het scherm
        r = self.A.js(f"""(() => {{ const e = {sel_js}; e.scrollIntoView({{block: "center"}}); const b = e.getBoundingClientRect();
            return [b.x + Math.min(20, b.width / 2), b.y + b.height / 2, window.screenX, window.screenY,
                    window.outerHeight - window.innerHeight, window.outerWidth - window.innerWidth]; }})()""")
        xdo("mousemove", str(int(r[2] + r[5] / 2 + r[0])), str(int(r[3] + r[4] + r[1]))); xdo("click", "1"); time.sleep(0.3)

    def ander_programma(self, bedekt):
        s = self.d.screen()
        geo = (0, 0, 1400, 1000) if bedekt else (1215, 40, 170, 120)
        w = s.root.create_window(*geo, 0, s.root_depth, X.InputOutput, X.CopyFromParent, background_pixel=s.white_pixel)
        w.set_wm_name("ander programma"); w.map(); self.d.sync(); time.sleep(0.8)
        xdo("windowactivate", "--sync", str(w.id)); time.sleep(1.2)
        xdo("windowactivate", "--sync", self.venster); time.sleep(1.2)
        w.destroy(); self.d.sync()

    def ander_tabblad(self):
        urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/json/new?about:blank", method="PUT")); time.sleep(1.2)
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/activate/" + self.eerste["id"]); time.sleep(1.2)

    def sluiten_en_blijven(self):
        self.A.events.clear()
        self.A.ws.send(json.dumps({"id": 99999, "method": "Page.reload", "params": {}})); self.A.pump(1.5)
        vraag = [e for e in self.A.events if e["method"] == "Page.javascriptDialogOpening"]
        if vraag:
            self.A.send("Page.handleJavaScriptDialog", {"accept": False}); time.sleep(0.8)
        xdo("windowactivate", "--sync", self.venster); time.sleep(0.4)
        return bool(vraag)

    def dicht(self):
        try:
            self.A.ws.close()
        except Exception:
            pass
        for p in (self.ch, self.wm, self.xv):
            p.terminate()
            try:
                p.wait(10)
            except Exception:
                p.kill()
        for _ in range(50):
            if not os.path.exists(f"/tmp/.X{DISPLAY[1:]}-lock"):
                break
            time.sleep(0.1)
        shutil.rmtree(self.prof, ignore_errors=True)


OPEN = """(() => { const f = DATA.formulas.find(x => !x.frozenImport && x.versions.length
            && !x.versions[x.versions.length - 1].frozen && x.versions[x.versions.length - 1].lines.length > 2);
    switchTab("F", f.id, {type: "v", idx: f.versions.length - 1}); })()"""
GEW = """(() => { const f = DATA.formulas.find(x => x.id === VIEW.id), v = f.versions[f.versions.length - 1];
    return v.lines[+document.querySelectorAll("input.w")[1].dataset.i].weightG; })()"""
HIER = "(() => { const a = document.activeElement; return [a.className, a.value, a.selectionStart, a.selectionEnd]; })()"
WEG = [("een ander tabblad", lambda s: s.ander_tabblad()),
       ("een ander programma ernaast", lambda s: s.ander_programma(False)),
       ("een ander programma dat het venster bedekt", lambda s: s.ander_programma(True)),
       ("sluiten, en blijven op de vraag", lambda s: s.sluiten_en_blijven())]

try:
    for naam, weg in WEG:
        s = Scherm()
        try:
            s.A.js(OPEN); time.sleep(0.4)
            voor, n0 = s.A.js(GEW), s.A.js("UNDO.length")
            s.klik("document.querySelectorAll('input.w')[1]"); xdo("key", "ctrl+a"); xdo("type", "12"); time.sleep(0.3)
            r = weg(s)
            if r is not None:
                check(f"{naam}: de browser vraagt eerst", r)
            st = s.A.js(HIER)
            check(f"{naam}: terug staat er wat je typte, met de cursor achteraan ({st})", st == ["w", "12", 2, 2])
            xdo("type", "5"); xdo("key", "Return"); time.sleep(0.6)
            na, n1 = s.A.js(GEW), s.A.js("UNDO.length")
            check(f"{naam}: '5' en Enter maken 125 g, in één Undo-stap ({na} g, {n1 - n0} stap)", na == 125 and n1 - n0 == 1)
            s.A.js("undo()"); time.sleep(0.3)
            check(f"{naam}: één Undo zet het oude gewicht terug ({s.A.js(GEW)} tegenover {voor})", s.A.js(GEW) == voor)
        finally:
            s.dicht()

    # een notitie: dezelfde textarea blijft staan, de cursor ook
    s = Scherm()
    try:
        s.A.js(OPEN); time.sleep(0.4)
        s.A.js("(() => { const d = document.querySelector('#notesEd').closest('details'); if (d) d.open = true; })()")
        NOT = "(() => { const f = DATA.formulas.find(x => x.id === VIEW.id); return f.versions[f.versions.length - 1].notes || ''; })()"
        voor, n0 = s.A.js(NOT), s.A.js("UNDO.length")
        s.klik("document.querySelector('#notesEd')"); xdo("key", "ctrl+End"); xdo("type", " dag 3"); time.sleep(0.3)
        s.ander_programma(False)
        xdo("type", " top"); time.sleep(0.3)
        s.klik("document.querySelector('#content h2') || document.querySelector('#content')"); time.sleep(0.4)
        na, n1 = s.A.js(NOT), s.A.js("UNDO.length")
        check(f"een notitie: verder typen na een ander programma, in één stap ({na[-12:]!r}, {n1 - n0} stap)",
              na == voor + " dag 3 top" and n1 - n0 == 1)
    finally:
        s.dicht()

    # de naam van een materiaal: die tekent de pagina opnieuw
    s = Scherm()
    try:
        mid = s.A.js("(() => { const m = DATA.materials.find(x => /^Ambrox/.test(x.name)) || DATA.materials[3]; switchTab('M', m.id); return m.id; })()")
        time.sleep(0.5)
        NAAM = f"DATA.materials.find(x => x.id === '{mid}').name"
        voor, n0 = s.A.js(NAAM), s.A.js("UNDO.length")
        s.klik("document.querySelector('[data-f=\"name\"]')"); xdo("key", "End"); xdo("type", " Su"); time.sleep(0.3)
        s.ander_tabblad()
        xdo("type", "per"); xdo("key", "Return"); time.sleep(0.6)
        na, n1 = s.A.js(NAAM), s.A.js("UNDO.length")
        check(f"de naam van een materiaal: verder typen na een ander tabblad, in één stap ({na!r}, {n1 - n0} stap)",
              na == voor + " Super" and n1 - n0 == 1)
    finally:
        s.dicht()
except Exception as e:
    check(f"de proef liep niet tot het einde ({str(e)[:200]})", False)

print(f"\n{ok} OK, {fail} FAIL")
sys.exit(1 if fail else 0)
