"""Opstelling en servers (bouw 260922k, ronde 3 van de vijfde audit): wat de app onthoudt en zegt wanneer een server nog
niet klaar is of een verkeerd adres heeft, een schrijfbeurt die blijft hangen, en de server weer verlaten.
B18: het eerste bezoek onthoudt alleen een duidelijk antwoord van data.php (een data.php die zegt wat er ontbreekt, telt
als gevonden; geen antwoord of een vreemde fout wordt de volgende start opnieuw gevraagd). B19: de app toont de melding
die de server meestuurt, bij laden en bij bewaren. C-d 32: een adres dat een webpagina teruggeeft (ook een 404-pagina)
zegt dat, in plaats van een ETag-waarschuwing en "restore a backup". C-d 28: een schrijfbeurt zonder antwoord geeft het op,
en Settings wacht er zichtbaar op. B22: de server leegmaken neemt je data mee naar deze browser, ook als de laatste
wijziging de server niet meer haalt, en vergeet een onthouden databestand.
Vereist een webserver met de inhoud van public\\ op poort 8765 (cd public && python -m http.server 8765)."""
import http.server, json, threading
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765"
URL = BASE + "/index.html"
API = BASE + "/api"
def data_with(*names):
    return json.dumps({"meta": {"schema": 1}, "materials": [], "formulas": [
        {"id": "f%d" % i, "name": n, "category": "Uncategorised", "versions": [{"v": 1, "date": "2026-09-20", "notes": "", "lines": []}]}
        for i, n in enumerate(names)]})
SERVER = data_with("Op de server")
OLD = data_with("Oude browserkopie")
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

# A server of its own that gives the data and takes a write without ever answering it: a write that hangs on a real
# connection, which a route in the page cannot make without leaving a handler waiting. Another port, so the app talks
# to it as to a Worker, with its CORS block.
class Hang(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def cors(self):
        for k, v in (("Access-Control-Allow-Origin", "*"), ("Access-Control-Allow-Methods", "GET, PUT, OPTIONS"),
                     ("Access-Control-Allow-Headers", "Content-Type, X-Token, If-Match"), ("Access-Control-Expose-Headers", "ETag")):
            self.send_header(k, v)
    def do_OPTIONS(self):
        self.send_response(204); self.cors(); self.end_headers()
    def do_GET(self):
        body = SERVER.encode()
        self.send_response(200); self.cors(); self.send_header("Content-Type", "application/json"); self.send_header("ETag", '"e1"')
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_PUT(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        threading.Event().wait()   # taken, and never answered
HANGSRV = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Hang); HANGSRV.daemon_threads = True
threading.Thread(target=HANGSRV.serve_forever, daemon=True).start()
HANG_API = "http://127.0.0.1:%d/api" % HANGSRV.server_address[1]

JSONH = {"Access-Control-Allow-Origin": "*", "Access-Control-Expose-Headers": "ETag"}
def answer(route, status, body, etag=None, ctype="application/json"):
    h = dict(JSONH)
    if etag: h["ETag"] = etag
    route.fulfill(status=status, content_type=ctype, headers=h, body=body)

with sync_playwright() as p:
    b = p.chromium.launch()
    def browser(route_glob=None, handler=None, answers=None):
        """A browser of its own (its own IndexedDB). answers: what to say to confirm(), in turn (default yes)."""
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = ctx.new_page(); msgs = []; q = list(answers or [])
        def on_dialog(d):
            msgs.append(d.message)
            if d.type == "prompt": d.accept("tok")
            elif d.type == "confirm" and q: (d.accept() if q.pop(0) else d.dismiss())
            else: d.accept()
        pg.on("dialog", on_dialog)
        if route_glob: pg.route(route_glob, handler)
        return pg, msgs
    stored = lambda pg: pg.evaluate("""async () => { const u = await idb.get("serverUrl");
        return {undef: u === undefined, url: u === undefined ? "(not remembered)" : u, REMOTE, DEMO}; }""")
    names = lambda pg: pg.evaluate("DATA ? DATA.formulas.map(f => f.name) : null")
    state = lambda pg: pg.locator("#saveState").inner_text()
    def to_server(pg, api):   # a device with a server set in Settings
        pg.goto(URL); pg.wait_for_timeout(700)
        pg.evaluate(f"""async () => {{ await idb.set('serverUrl', {json.dumps(api)}); await idb.set('token', 'tok'); }}""")
        pg.reload(); pg.wait_for_timeout(1500)

    # ---------- 1. B18: the first visit, while data.php is not ready ----------
    mode = {"m": "500"}
    def dataphp(route):
        r = route.request
        if mode["m"] == "500": return answer(route, 500, '{"error":"data.php: set $TOKEN first"}')
        if r.headers.get("x-token", "") != "tok": return answer(route, 401, '{"error":"invalid token"}')
        if r.method == "GET": return answer(route, 200, SERVER, '"e1"')
        return answer(route, 200, '{"ok":true,"etag":"\\"e2\\""}', '"e2"')
    pg, msgs = browser("**/data.php*", dataphp)
    pg.goto(URL); pg.wait_for_timeout(1500)
    s = stored(pg)
    print("     ", s, [m[:90] for m in msgs])
    check(f"data.php die zegt wat er ontbreekt, telt als gevonden: de app blijft in serverstand ({s['url']!r})",
          s["url"] == "data.php" and s["REMOTE"] is True)
    check("en toont de melding van data.php zelf", any("HTTP 500" in m and "set $TOKEN first" in m for m in msgs))
    check("het startscherm biedt Connect to server aan", pg.locator("#btnOpen").inner_text() == "Connect to server")
    mode["m"] = "ready"; msgs.clear()      # het token is ingevuld op de server
    pg.click("#btnOpen"); pg.wait_for_timeout(1500)
    check(f"na het herstel volstaat Connect to server: het token wordt gevraagd en de data geladen ({names(pg)})",
          any("Access token" in m for m in msgs) and names(pg) == ["Op de server"] and not pg.locator("#landing").is_visible())
    pg.context.close()

    def ready(route):   # a data.php that is set up: it wants the token, and then gives the data
        if route.request.headers.get("x-token", "") != "tok": return answer(route, 401, '{"error":"invalid token"}')
        answer(route, 200, SERVER, '"e1"')
    for label, fn, remembered in [
        ("geen data.php (404)", lambda r: answer(r, 404, "<html>Not Found</html>", ctype="text/html"), True),
        ("een pagina die geen data is (200)", lambda r: answer(r, 200, "<!doctype html><title>Home</title>", ctype="text/html"), True),
        ("een fout die niet van data.php komt (503)", lambda r: answer(r, 503, "Service Unavailable", ctype="text/plain"), False),
        ("geen antwoord (netwerkfout)", lambda r: r.abort(), False),
        ("de bron van data.php als tekst: PHP draait nog niet", lambda r: answer(r, 200, "<?php\n$TOKEN = 'x';", ctype="text/plain"), False)]:
        pg, msgs = browser("**/data.php*", fn)
        pg.goto(URL); pg.wait_for_timeout(1300)
        s = stored(pg)
        if remembered:
            check(f"{label}: onthouden als geen server ({s['url']!r}), browseropslag", s["url"] is None and not s["undef"] and s["DEMO"] is True)
        else:
            check(f"{label}: niets onthouden, de volgende start vraagt opnieuw ({s['url']!r}), intussen browseropslag",
                  s["undef"] and s["DEMO"] is True and not s["REMOTE"])
        if not remembered and label.startswith("een fout"):
            pg.unroute("**/data.php*"); pg.route("**/data.php*", ready)
            pg.reload(); pg.wait_for_timeout(1500)
            s = stored(pg)
            check(f"en een data.php die er nu wel is, wordt bij de volgende start gevonden ({s['url']!r}, {names(pg)})",
                  s["url"] == "data.php" and s["REMOTE"] is True and names(pg) == ["Op de server"])
        pg.context.close()

    # ---------- 2. B19: the server's own words, loading and saving ----------
    def dirgone(route):
        answer(route, 500, '{"error":"data directory missing: /srv/www/data"}')
    pg, msgs = browser("**/api*", dirgone)
    to_server(pg, API)
    print("     ", [m[:110] for m in msgs])
    check("laden: de app toont wat de server zegt, niet alleen HTTP 500",
          any("HTTP 500" in m and "data directory missing: /srv/www/data" in m for m in msgs))
    pg.context.close()

    def nosnap(route):
        if route.request.method == "GET": return answer(route, 200, SERVER, '"e1"')
        answer(route, 500, '{"error":"could not write the daily snapshot, so nothing was saved: is the disk full?"}')
    pg, msgs = browser("**/api*", nosnap)
    to_server(pg, API)
    pg.evaluate("() => { DATA.formulas[0].name += ' x'; markDirty(); }"); pg.wait_for_timeout(3500)
    st = state(pg)
    check(f"bewaren: de balk zegt wat de server zegt ({st!r})", "Save failed (server 500" in st and "daily snapshot" in st)
    pg.context.close()

    # ---------- 3. C-d 32: an address that answers with a web page ----------
    pg, msgs = browser()
    to_server(pg, BASE + "/")
    print("     ", [m[:80] for m in msgs])
    check(f"het adres van de site zelf: één melding, en die zegt dat het een webpagina is ({len(msgs)})",
          len(msgs) == 1 and "web page" in msgs[0] and "Settings" in msgs[0])
    check("geen ETag-waarschuwing en geen 'restore a backup' voor een tikfout", not any("ETag" in m or "could not be read" in m for m in msgs))
    pg.context.close()
    pg, msgs = browser()
    to_server(pg, BASE + "/api-met-een-tikfout")
    check(f"een adres dat een 404-pagina geeft: dezelfde melding ({[m[:60] for m in msgs]})", len(msgs) == 1 and "web page" in msgs[0])
    check("en het startscherm doet niet alsof een lege server wacht op de starterset",
          pg.evaluate("SERVER_EMPTY") is False and not pg.locator("#btnStarter").is_visible())
    pg.context.close()
    def empty(route):   # the real "no data file yet" of both endpoints
        answer(route, 404, '{"error":"no data file yet"}')
    pg, msgs = browser("**/api*", empty)
    to_server(pg, API)
    check("een lege server blijft een lege server: de starterset wordt aangeboden, zonder melding",
          pg.evaluate("SERVER_EMPTY") is True and pg.locator("#btnStarter").is_visible() and not msgs)
    pg.context.close()

    # ---------- 4. C-d 28: a write that never answers ----------
    pg, msgs = browser(answers=[False])
    to_server(pg, HANG_API)
    pg.evaluate("PUTWAIT = 1500")
    pg.evaluate("() => { DATA.formulas[0].name += ' x'; markDirty(); }")
    pg.wait_for_timeout(6000)
    st = state(pg)
    check(f"een schrijfbeurt zonder antwoord geeft het op: 'Server not reachable' ({st!r})", "not reachable" in st)
    check("en de poort gaat weer open voor de volgende", pg.evaluate("SAVING === null") and pg.evaluate("DIRTY") is True)   # SAVING itself is a promise: evaluate would wait on it
    pg.click("#btnSettings"); pg.wait_for_timeout(400)
    pg.fill("#setServer", HANG_API + "?v=2"); pg.click("#dlgOk"); pg.wait_for_timeout(300)
    st = state(pg)
    check(f"Settings zegt dat het wacht ({st!r})", st.startswith("Saving"))
    pg.wait_for_timeout(6000)
    print("     ", [m[:70] for m in msgs])
    check("en na de time-out vraagt het, in plaats van eindeloos te wachten", any("could not be saved" in m for m in msgs))
    check("Cancel laat de server staan", pg.evaluate("idb.get('serverUrl')") == HANG_API)
    pg.context.close()

    # ---------- 5. B22: leaving the server ----------
    for label, put_ok in [("met een geslaagde laatste schrijfbeurt", True), ("terwijl de server onbereikbaar is", False)]:
        def srv(route, put_ok=put_ok):
            if route.request.method == "GET": return answer(route, 200, SERVER, '"e1"')
            if put_ok: return answer(route, 200, '{"ok":true}', '"e2"')
            route.abort()
        pg, msgs = browser("**/api*", srv)
        pg.goto(URL); pg.wait_for_timeout(700)
        pg.evaluate(f"""async () => {{ await idb.set('demoData', {json.dumps(OLD)}); await idb.set('fileHandle', {{name: 'oud.json'}});
            await idb.set('serverUrl', {json.dumps(API)}); await idb.set('token', 'tok'); }}""")
        pg.reload(); pg.wait_for_timeout(1500)
        check(f"{label}: de app draait op de server ({names(pg)})", pg.evaluate("REMOTE") and names(pg) == ["Op de server"])
        pg.evaluate("() => { const f = DATA.formulas[0]; snapF(f); f.name = 'Op de server, gewijzigd'; markDirty(); }")
        pg.wait_for_timeout(3500)
        pg.click("#btnSettings"); pg.wait_for_timeout(400)
        hint = pg.locator("#dlg").inner_text()
        check(f"{label}: Settings zegt wat leegmaken doet", "Emptying it takes your data" in hint and "come back to the file" not in hint)
        msgs.clear()
        pg.fill("#setServer", "")
        with pg.expect_navigation(timeout=15000):
            pg.click("#dlgOk")
        pg.wait_for_timeout(1500)
        r = pg.evaluate("""async () => ({DEMO, REMOTE, names: DATA ? DATA.formulas.map(f => f.name) : null,
            handle: await idb.get("fileHandle"), url: await idb.get("serverUrl")})""")
        print("     ", r, [m[:60] for m in msgs])
        check(f"{label}: na het leegmaken werkt de app in deze browser met de data van zonet, niet met de oude kopie",
              r["DEMO"] and not r["REMOTE"] and r["names"] == ["Op de server, gewijzigd"])
        check(f"{label}: het onthouden databestand is vergeten", r["handle"] is None and r["url"] is None)
        check(f"{label}: zonder vraag, want er gaat niets verloren", not any("could not be saved" in m or "Leave" in m for m in msgs))
        pg.unroute_all(behavior="ignoreErrors"); pg.context.close()

    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
