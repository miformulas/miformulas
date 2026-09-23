"""B21 of the review of 22/09 (build 260922g): a 409 that is our own write. When the answer to a PUT goes missing
(the connection drops after the server wrote), Chromium sends the same PUT again by itself, with the same If-Match,
and that one meets our own write: the app used to call that "changed on another device" and stayed in conflict for
every save after it. Likewise a write the app counted as failed may have landed after all.
Runs against the real server/worker.js behind a real HTTP server in a process of its own (worker-server.mjs), because
a fetch replaced inside the page cannot lose an answer the way a network does. Needs node; no web server of its own."""
import json, os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8791
BASE = f"http://127.0.0.1:{PORT}"
STARTER = open(os.path.join(HERE, "..", "..", "data", "miformulas-starter.json"), encoding="utf-8").read()
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)
def ctl(q="", body=None):
    req = urllib.request.Request(BASE + "/__ctl?" + q, data=body.encode() if body else None, method="POST" if body else "GET")
    return json.loads(urllib.request.urlopen(req).read())

srv = subprocess.Popen(["node", os.path.join(HERE, "worker-server.mjs"), str(PORT)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    if "listening" not in srv.stdout.readline():
        print("worker-server.mjs did not start"); sys.exit(2)
    ctl("clear=1"); ctl("seed=1", STARTER)
    with sync_playwright() as p:
        b = p.chromium.launch()
        def device():
            ctx = b.new_context(viewport={"width": 1280, "height": 900})
            pg = ctx.new_page(); msgs = []; errs = []
            pg.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(BASE + "/index.html"); pg.wait_for_timeout(800)
            pg.evaluate(f"""async () => {{ await idb.set('serverUrl', {json.dumps(BASE + '/api')}); await idb.set('token', 'tok-test'); }}""")
            pg.reload(); pg.wait_for_timeout(1500)
            return pg, msgs, errs
        state = lambda pg: pg.locator("#saveState").inner_text()
        add = lambda pg, name: pg.evaluate("""n => { DATA.formulas.push({id: "f-" + n.replace(/\\W/g, ""), name: n, category: "Uncategorised",
            versions: [{v: 1, date: today(), notes: "", lines: []}]}); markDirty(); }""", name)
        on_server = lambda name: f'"name": "{name}"' in (ctl()["data"] or "")

        pg, msgs, errs = device()
        check("de app staat in serverstand, op de echte worker.js", pg.evaluate("[REMOTE, LOADED]") == [True, True])
        add(pg, "Gewoon"); pg.wait_for_timeout(3500)
        check(f"een gewone schrijfbeurt komt aan ({state(pg)!r})", on_server("Gewoon") and "Saved" in state(pg))

        # ---------- 1. het antwoord gaat verloren en Chromium stuurt dezelfde PUT opnieuw ----------
        n0 = len(ctl()["puts"])
        ctl("drop=1")
        add(pg, "Na de breuk"); pg.wait_for_timeout(4500)
        puts = ctl()["puts"][n0:]
        print("     PUTs:", [(x["ifm"][:8], x.get("status"), x.get("dropped", False)) for x in puts])
        check("de schrijfbeurt kwam aan op de server", on_server("Na de breuk"))
        check(f"en de app meldt geen conflict dat er geen is ({state(pg)!r}, {[m[:50] for m in msgs]})",
              "Saved" in state(pg) and not msgs and pg.evaluate("DIRTY") is False)
        add(pg, "Daarna"); pg.wait_for_timeout(3500)
        check(f"de volgende wijziging gaat gewoon naar de server ({state(pg)!r})", on_server("Daarna") and "Saved" in state(pg) and not msgs)

        # ---------- 2. een schrijfbeurt die als mislukt gold, kwam toch aan ----------
        # Met Connection: close op elk antwoord, en de verbindingen die nog openstonden dicht, loopt de PUT over een
        # verse verbinding, en die stuurt de browser niet opnieuw: de fetch faalt, de app zegt "Server not reachable",
        # en de volgende schrijfbeurt treft op de server haar eigen vorige aan.
        ctl("closeall=1")
        pg.wait_for_timeout(500)
        n1 = len(ctl()["puts"])
        ctl("drop=1")
        add(pg, "Verloren antwoord"); pg.wait_for_timeout(4500)
        tussen = state(pg)
        print("     PUTs:", [(x["ifm"][:8], x.get("status"), x.get("dropped", False)) for x in ctl()["puts"][n1:]], "| status:", tussen)
        check("de schrijfbeurt zonder antwoord staat op de server", on_server("Verloren antwoord"))
        check(f"de app hoorde niets terug en zegt dat ook ({tussen!r})", "not reachable" in tussen)
        add(pg, "En verder"); pg.wait_for_timeout(4500)
        check(f"de volgende schrijfbeurt herkent haar eigen vorige en gaat door ({state(pg)!r}, {[m[:50] for m in msgs]})",
              on_server("En verder") and "Saved" in state(pg) and not msgs)
        ctl("closeall=0")

        # ---------- 3. een echt conflict blijft een conflict ----------
        pg2, msgs2, errs2 = device()
        add(pg2, "Van toestel twee"); pg2.wait_for_timeout(3500)
        check("het tweede toestel schrijft", on_server("Van toestel twee"))
        add(pg, "Van toestel een"); pg.wait_for_timeout(4500)
        check(f"het eerste toestel krijgt het conflict te zien ({state(pg)!r})",
              "Conflict" in state(pg) and any("another device" in m for m in msgs))
        check("en de server houdt het werk van het tweede toestel", on_server("Van toestel twee") and not on_server("Van toestel een"))
        check(f"geen paginafouten ({(errs + errs2)[:2]})", not errs and not errs2)
        b.close()
finally:
    srv.terminate()

print(f"\n{ok} OK, {fail} FAIL")
