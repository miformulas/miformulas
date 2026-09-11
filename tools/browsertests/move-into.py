"""Move into…: an imported (flat) formula becomes a version or a frozen variation of another formula.
Uses the starter set; two formulas are marked as imported the way the Formulair importer does.
Needs the local web server on port 8765 (see README)."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    msgs = []
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1200)

    # a normal starter formula has no Move into… button
    page.locator("#list").get_by_text("Rose de Mai 68", exact=True).click(); page.wait_for_timeout(400)
    check("no Move into… on an ordinary formula", page.locator("#btnMoveF").count() == 0)

    # make "Oeillet 35" and "Althenol" look like Formulair imports: "Aura v04" and "Aura v05"
    page.evaluate("""() => {
      const f4 = DATA.formulas.find(f => f.name === "Oeillet 35"), f5 = DATA.formulas.find(f => f.name === "Althenol");
      for (const [f, n] of [[f4, "Aura v04"], [f5, "Aura v05"]]){
        f.name = n; f.frozenImport = true; const v = f.versions[0]; v.sourceName = n; v.imported = true; v.frozen = true;
        v.notes = "notes of " + n; v.trials = [{date: "2026-09-01", text: "trial of " + n}]; v.lines[0].remark = 2;
      }
      buildUsage(); render();
    }""")
    page.wait_for_timeout(300)
    nBefore = page.evaluate("DATA.formulas.length")
    page.locator("#list").get_by_text("Aura v05", exact=True).click(); page.wait_for_timeout(400)
    check("Move into… shown on an imported formula", page.locator("#btnMoveF").is_visible())
    page.click("#btnMoveF"); page.wait_for_timeout(400)
    dlg = page.locator("#dlg")
    check("dialog opens", dlg.evaluate("d => d.open"))
    target = page.locator("#mvTarget")
    sel_name = target.evaluate("s => s.options[s.selectedIndex].textContent")
    check("suggests Aura v04 (names differ only in the number)", sel_name.startswith("Aura v04"))
    check("suggestion hint shown", "Suggested" in dlg.inner_text())
    check("next version number announced", page.locator("#mvVno").inner_text().strip() == "(v2)")
    check("variation base list holds v1", page.locator("#mvBase option").count() == 1)

    # 1. as a version
    page.click("#dlgOk"); page.wait_for_timeout(600)
    f4 = page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Aura v04"); return {n: f.versions.length, v: f.versions[1] && f.versions[1].v,
      src: f.versions[1] && f.versions[1].sourceName, imp: f.versions[1] && f.versions[1].imported, fr: f.versions[1] && f.versions[1].frozen,
      notes: f.versions[1] && f.versions[1].notes, trials: f.versions[1] && f.versions[1].trials && f.versions[1].trials.length,
      remark: f.versions[1] && f.versions[1].lines[0].remark, lines: f.versions[1] && f.versions[1].lines.length}; }""")
    check("target has two versions, the new one is v2", f4["n"] == 2 and f4["v"] == 2)
    check("moved version keeps the import name, frozen and imported", f4["src"] == "Aura v05" and f4["imp"] and f4["fr"])
    check("notes, trial log, colour mark and lines came along", f4["notes"] == "notes of Aura v05" and f4["trials"] == 1 and f4["remark"] == 2 and f4["lines"] == 12)
    check("source formula is gone", page.evaluate("DATA.formulas.length") == nBefore - 1 and page.evaluate("!DATA.formulas.some(f => f.name === 'Aura v05')"))
    check("app shows Aura v04 at v2", page.locator("#content h2").first.inner_text().startswith("Aura v04") and page.locator("#verSel").input_value() == "1")
    check("list counter reads 2v", "2v" in page.locator("#list .item", has_text="Aura v04").first.inner_text())

    # Undo brings everything back in one step
    page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    check("undo: source formula is back", page.evaluate("DATA.formulas.length") == nBefore and page.evaluate("DATA.formulas.some(f => f.name === 'Aura v05')"))
    check("undo: target has one version again", page.evaluate("DATA.formulas.find(x => x.name === 'Aura v04').versions.length") == 1)

    # 2. as a frozen variation
    page.locator("#list").get_by_text("Aura v05", exact=True).click(); page.wait_for_timeout(400)
    page.click("#btnMoveF"); page.wait_for_timeout(400)
    page.fill("#mvLabel", "v05"); page.wait_for_timeout(100)
    check("typing a label selects the variation mode", page.evaluate("document.querySelector('input[name=mvMode][value=var]').checked"))
    page.click("#dlgOk"); page.wait_for_timeout(600)
    va = page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Aura v04"); const va = f.variations[0]; return va && {label: va.label, frozen: va.frozen,
      from: va.frozenFrom, fromName: va.frozenFromName, src: va.sourceName, lines: va.lines.length, nv: f.versions.length}; }""")
    check("target got a frozen variation with the label, frozen from v1", va and va["label"] == "v05" and va["frozen"] and va["from"] == 1 and va["fromName"] == "v1" and va["lines"] == 12 and va["nv"] == 1)
    check("import reference kept on the variation", va and va["src"] == "Aura v05")
    check("app shows the variation", "viewing a variation" in page.locator("#verSel option:checked").inner_text())
    check("source formula is gone again", page.evaluate("!DATA.formulas.some(f => f.name === 'Aura v05')"))
    page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    check("undo restores both formulas", page.evaluate("DATA.formulas.some(f => f.name === 'Aura v05') && DATA.formulas.find(x => x.name === 'Aura v04').variations.length === 0"))

    # cancel does nothing; the moved-in formula is not offered as its own target
    page.locator("#list").get_by_text("Aura v05", exact=True).click(); page.wait_for_timeout(400)
    page.click("#btnMoveF"); page.wait_for_timeout(300)
    own = page.evaluate("[...document.querySelectorAll('#mvTarget option')].map(o => o.textContent).filter(t => t.includes('Aura v05'))")
    check(f"the formula itself is in the target list only as 'this formula' ({own})", own == ["this formula (Aura v05)"])
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    check("cancel changes nothing", page.evaluate("DATA.formulas.length") == nBefore)

    # Move together: companions with the same name stem come pre-ticked, the target is disabled, another one can be added
    page.evaluate("""() => {
      const pick = ["Jasmin 231", "Brut", "Angel"], names = ["Aura v06", "Aura v05 20%", "Vetiver Test"];
      pick.forEach((n, i) => { const f = DATA.formulas.find(x => x.name === n); f.name = names[i]; f.frozenImport = true;
        const v = f.versions[0]; v.sourceName = names[i]; v.imported = true; v.frozen = true; v.date = "2026-0" + (i+1) + "-01"; });
      buildUsage(); render();
    }""")
    page.wait_for_timeout(300)
    n0 = page.evaluate("DATA.formulas.length")
    page.locator("#list").get_by_text("Aura v05", exact=True).click(); page.wait_for_timeout(400)
    page.click("#btnMoveF"); page.wait_for_timeout(400)
    rows = page.evaluate("[...document.querySelectorAll('#mvTogether input.mvTog')].map(cb => [cb.parentElement.textContent.trim(), cb.checked, cb.disabled])")
    check(f"Move together lists the other Aura formulas ({rows})", sorted(r[0] for r in rows) == ["Aura v04", "Aura v05 20%", "Aura v06"])
    check("the suggested target Aura v04 is listed but disabled and unticked", any(r[0] == "Aura v04" and not r[1] and r[2] for r in rows))
    check("the others are ticked", all(r[1] for r in rows if r[0] != "Aura v04"))
    check("Vetiver Test is not a companion but can be added", page.locator("#mvAddList option[value='Vetiver Test']").count() == 1)
    page.fill("#mvAdd", "Vetiver Test"); page.dispatch_event("#mvAdd", "change"); page.wait_for_timeout(200)
    check("added formula appears ticked", page.evaluate("(() => { const cb = [...document.querySelectorAll('#mvTogether input.mvTog')].find(c => c.parentElement.textContent.includes('Vetiver Test')); return cb && cb.checked; })()"))
    page.evaluate("[...document.querySelectorAll('#mvTogether input.mvTog')].find(c => c.parentElement.textContent.includes('Vetiver Test')).checked = false")
    page.click("#dlgOk"); page.wait_for_timeout(700)
    f4 = page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Aura v04"); return {n: f.versions.length,
      order: f.versions.map(v => v.sourceName || ""), vs: f.versions.map(v => v.v)}; }""")
    check(f"three formulas moved in as versions, numbered by the number in the name ({f4['order']})", f4["n"] == 4 and f4["order"][1:] == ["Aura v05", "Aura v05 20%", "Aura v06"] and f4["vs"] == [1, 2, 3, 4])
    check("the three sources are gone, the unticked one stays", page.evaluate("DATA.formulas.length") == n0 - 3 and page.evaluate("DATA.formulas.some(f => f.name === 'Vetiver Test') && !DATA.formulas.some(f => f.name === 'Aura v06')"))
    page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    check("one Undo brings all three back", page.evaluate("DATA.formulas.length") == n0 and page.evaluate("DATA.formulas.find(x => x.name === 'Aura v04').versions.length") == 1)
    # as variations: labels are the names without the shared part
    page.locator("#list").get_by_text("Aura v05", exact=True).click(); page.wait_for_timeout(400)
    page.click("#btnMoveF"); page.wait_for_timeout(400)
    page.check('input[name="mvMode"][value="var"]')
    page.click("#dlgOk"); page.wait_for_timeout(700)
    labels = page.evaluate("DATA.formulas.find(x => x.name === 'Aura v04').variations.map(v => v.label)")
    check(f"as variations: labels without the shared part ({labels})", labels == ["v05", "v05 20%", "v06"])
    page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    check("Undo again restores everything", page.evaluate("DATA.formulas.length") == n0)

    # opened on the lowest number: the formula itself is the target, and the others move into it
    page.locator("#list").get_by_text("Aura v04", exact=True).click(); page.wait_for_timeout(400)
    page.click("#btnMoveF"); page.wait_for_timeout(400)
    sel_name = page.locator("#mvTarget").evaluate("s => s.options[s.selectedIndex].textContent")
    check(f"opened on Aura v04: 'this formula' is suggested ({sel_name})", sel_name == "this formula (Aura v04)")
    check("hint says the others move into it", "this formula has the lowest number" in dlg.inner_text())
    check("intro speaks of the ticked formulas", "ticked under Move together become part of" in page.locator("#mvIntro").inner_text())
    check("label field of the opened formula is disabled", page.locator("#mvLabel").is_disabled())
    rows = page.evaluate("[...document.querySelectorAll('#mvTogether input.mvTog')].map(cb => [cb.parentElement.textContent.trim(), cb.checked, cb.disabled])")
    check(f"companions v05, v05 20%, v06 ticked and enabled ({rows})", sorted(r[0] for r in rows) == ["Aura v05", "Aura v05 20%", "Aura v06"] and all(r[1] and not r[2] for r in rows))
    check("next version number announced", page.locator("#mvVno").inner_text().strip() == "(v2)")
    page.click("#dlgOk"); page.wait_for_timeout(700)
    f4 = page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Aura v04"); return {n: f.versions.length,
      order: f.versions.map(v => v.sourceName || ""), vs: f.versions.map(v => v.v)}; }""")
    check(f"v05, v05 20% and v06 became versions 2 to 4 of Aura v04 ({f4['order']})", f4["n"] == 4 and f4["order"] == ["Aura v04", "Aura v05", "Aura v05 20%", "Aura v06"] and f4["vs"] == [1, 2, 3, 4])
    check("the three sources are gone, Aura v04 stays", page.evaluate("DATA.formulas.length") == n0 - 3 and page.evaluate("DATA.formulas.some(f => f.name === 'Aura v04') && !DATA.formulas.some(f => ['Aura v05', 'Aura v05 20%', 'Aura v06'].includes(f.name))"))
    check("app shows Aura v04", page.locator("#content h2").first.inner_text().startswith("Aura v04"))
    page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    check("one Undo brings all three back and Aura v04 has one version again", page.evaluate("DATA.formulas.length") == n0 and page.evaluate("DATA.formulas.find(x => x.name === 'Aura v04').versions.length") == 1)
    # nothing ticked: a message, and nothing moves
    page.locator("#list").get_by_text("Aura v04", exact=True).click(); page.wait_for_timeout(400)
    page.click("#btnMoveF"); page.wait_for_timeout(400)
    page.evaluate("document.querySelectorAll('#mvTogether input.mvTog').forEach(c => c.checked = false)")
    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(400)
    check(f"nothing ticked: asks to tick formulas ({msgs})", any("Tick the formulas" in m for m in msgs) and page.evaluate("DATA.formulas.length") == n0)
    check("dialog stays open", dlg.evaluate("d => d.open"))
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    # as variations from the lowest one: labels without the shared part, no label needed for the opened formula
    page.click("#btnMoveF"); page.wait_for_timeout(400)
    page.check('input[name="mvMode"][value="var"]')
    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(700)
    f4 = page.evaluate("(() => { const f = DATA.formulas.find(x => x.name === 'Aura v04'); return {labels: f.variations.map(v => v.label), nv: f.versions.length}; })()")
    check(f"as variations of Aura v04 ({f4['labels']})", f4["labels"] == ["v05", "v05 20%", "v06"] and f4["nv"] == 1 and not msgs)
    page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    check("Undo restores everything once more", page.evaluate("DATA.formulas.length") == n0 and page.evaluate("DATA.formulas.find(x => x.name === 'Aura v04').variations.length") == 0)
    check("no page errors", not errs)
    b.close()
print(f"\n{ok} OK, {fail} FAIL")
