"""Formulair-datums in de tijd van de computer (bouw 260922h, C-c 27). Formulair toont een datum in lokale tijd; de twee
omzetters lazen ze in UTC, zodat een formule van na middernacht in Brussel de dag ervoor kreeg (90 van de 698 formules
van een echte databank). Een kleine databank met formules van 00:30 en 01:30 Brusselse tijd, gelezen door
formulair-naar-json.py en door formulair-import.html in dezelfde tijdzone: allebei de Brusselse dag, en allebei hetzelfde.
Vereist de lokale webserver op poort 8765; de test maakt zijn eigen databank en heeft de jouwe niet nodig."""
import datetime, json, os, sqlite3, subprocess, sys, tempfile
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
FNJ = os.path.join(HERE, "..", "formulair-naar-json.py")
URL = "http://localhost:8765/formulair-import.html"
ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

E = datetime.datetime(2001, 1, 1, tzinfo=datetime.timezone.utc)
def ts(y, mo, d, h, mi, tz="Europe/Brussels"):   # seconden sinds 2001-01-01 UTC, zoals Core Data ze bewaart
    return (datetime.datetime(y, mo, d, h, mi, tzinfo=ZoneInfo(tz)) - E).total_seconds()

def maak_db(pad):
    c = sqlite3.connect(pad)
    c.executescript("""
    create table ZRMCATEGORY(Z_PK integer primary key, ZNAME text, ZCOLOUR blob);
    create table ZFCATEGORY(Z_PK integer primary key, ZNAME text);
    create table ZSUPPLIER(Z_PK integer primary key, ZNAME text);
    create table ZINGREDIENT(Z_PK integer primary key, ZNAME text, ZCAS text, ZCATEGORY integer, ZSUPPLIER integer, ZCOST real, ZIFRA real, ZINVENTORY text, ZPYRAMID integer, ZISSOLVENT integer, ZODOURDESCRIPTION text, ZTIMESTAMP real);
    create table ZDILUTIONENTRY(Z_PK integer primary key, ZINGREDIENT integer, ZDILUTION real, ZISBASEDILUTION integer, ZDATE real, ZNOTES text);
    create table ZFORMULAENTRY(Z_PK integer primary key, ZFORMULA integer, ZDILUTIONENTRY integer, ZQUANTITY real, ZREMARK integer, ZDATEADDED real);
    create table ZFORMULA(Z_PK integer primary key, ZTITLE text, ZCATEGORY integer, ZDATE real, ZNOTES text);
    """)
    c.executemany("insert into ZRMCATEGORY values (?,?,?)", [(1, "Woods", b"0.1 0.2 0.3")])
    c.executemany("insert into ZFCATEGORY values (?,?)", [(1, "Trials")])
    c.executemany("insert into ZSUPPLIER values (?,?)", [(1, "Supplier A")])
    c.executemany("insert into ZINGREDIENT values (?,?,?,?,?,?,?,?,?,?,?,?)", [
        (1, "Vetiver Oil", "8016-96-4", 1, 1, 0.5, 99, "50 g", 4, 0, "from Java", ts(2026, 3, 5, 0, 20)),
        (2, "Hedione", "24851-98-7", 1, 1, 0.05, None, None, 2, 0, "", ts(2026, 3, 6, 12, 0))])
    c.executemany("insert into ZDILUTIONENTRY values (?,?,?,?,?,?)", [
        (1, 1, 100, 1, ts(2026, 3, 5, 0, 15), ""), (2, 1, 10, 0, ts(2026, 3, 5, 0, 16), "night dilution"), (3, 2, 100, 1, None, "")])
    c.executemany("insert into ZFORMULA values (?,?,?,?,?)", [
        (1, "Nacht", 1, ts(2026, 3, 5, 0, 30), "made at half past midnight, winter time"),
        (2, "Middag", 1, ts(2026, 3, 6, 12, 0), ""),
        (3, "Zomernacht", 1, ts(2026, 7, 10, 1, 30), "made at half past one, summer time")])
    c.executemany("insert into ZFORMULAENTRY values (?,?,?,?,?,?)", [
        (1, 1, 1, 10.0, 1, 1.0), (2, 1, 3, 5.0, 2, 2.0), (3, 2, 2, 3.0, 1, 1.0), (4, 3, 3, 1.0, 1, 1.0)])
    c.commit(); c.close()

tmp = tempfile.mkdtemp()
db = os.path.join(tmp, "DataModel.sqlite")
maak_db(db)

def python_ref(tz):
    uit = os.path.join(tmp, f"ref-{tz.replace('/', '-')}.json")
    subprocess.run([sys.executable, FNJ, db, uit], check=True, env={**os.environ, "TZ": tz}, stdout=subprocess.DEVNULL)
    return json.load(open(uit, encoding="utf-8"))

def browser(pw, tz):
    b = pw.chromium.launch()
    ctx = b.new_context(timezone_id=tz, accept_downloads=True); page = ctx.new_page(); errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(500)
    page.set_input_files("#file", db)
    page.wait_for_selector("#btnDl", timeout=30000); page.wait_for_timeout(500)
    with page.expect_download() as dl:
        page.click("#btnDl")
    uit = os.path.join(tmp, f"browser-{tz.replace('/', '-')}.json"); dl.value.save_as(uit)
    b.close()
    return json.load(open(uit, encoding="utf-8")), errs

def dagen(d):
    f = {x["name"]: x for x in d["formulas"]}
    vet = next(m for m in d["materials"] if m["name"] == "Vetiver Oil")
    return {"Nacht": f["Nacht"]["created"], "Middag": f["Middag"]["created"], "Zomernacht": f["Zomernacht"]["created"],
            "versie": f["Nacht"]["versions"][0].get("date"), "dilutie": sorted(x["date"] for x in vet["dilutions"])}

def zonder_tijdstempel(d):
    d = json.loads(json.dumps(d)); d.get("meta", {}).pop("generated", None); return d

with sync_playwright() as pw:
    ref = python_ref("Europe/Brussels")
    br, errs = browser(pw, "Europe/Brussels")
    rd, bd = dagen(ref), dagen(br)
    check(f"Python in Brussel: de dag van Formulair, ook na middernacht ({rd})",
          rd["Nacht"] == "2026-03-05" and rd["Zomernacht"] == "2026-07-10" and rd["Middag"] == "2026-03-06"
          and rd["versie"] in (None, "2026-03-05") and rd["dilutie"] == ["2026-03-05", "2026-03-05"])
    check(f"de browser in Brussel leest dezelfde dagen ({bd})", bd == rd)
    check("en beide omzetters geven hetzelfde bestand", zonder_tijdstempel(ref) == zonder_tijdstempel(br))
    stempel = next(x for x in br["formulas"] if x["name"] == "Nacht")["modified"]
    check(f"het tijdstempel van de wijziging staat ook in lokale tijd ({stempel})", stempel.startswith("2026-03-05T00:30"))
    check(f"geen paginafouten ({errs[:1]})", not errs)
    # de tijd van de computer, niet die van Brussel: in UTC lezen beide de UTC-dag, en ze blijven het eens
    ref_u = python_ref("UTC")
    br_u, errs_u = browser(pw, "UTC")
    check(f"in UTC lezen beide de UTC-dag ({dagen(ref_u)['Nacht']}, {dagen(br_u)['Nacht']})",
          dagen(ref_u)["Nacht"] == dagen(br_u)["Nacht"] == "2026-03-04" and zonder_tijdstempel(ref_u) == zonder_tijdstempel(br_u))
    check(f"geen paginafouten in UTC ({errs_u[:1]})", not errs_u)

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
