#!/usr/bin/env python3
"""Bouwt public/formulair-import.html uit de bron en sql.js.

  python3 bouw-formulair-import.py <bron.src.html> <map met sql.js dist> <uitvoer.html>

sql.js (MIT) wordt ingebed: sql-wasm.js als script, sql-wasm.wasm als base64.
Alleen nodig als sql.js bijgewerkt wordt; het resultaat staat in de repo.
"""
import sys, base64, json, os, re

src, dist, out = sys.argv[1:4]
js = open(os.path.join(dist, "sql-wasm.js"), encoding="utf-8").read()
wasm = base64.b64encode(open(os.path.join(dist, "sql-wasm.wasm"), "rb").read()).decode("ascii")
pkg = json.load(open(os.path.join(dist, "..", "package.json")))
html = open(src, encoding="utf-8").read()
for k, v in [("@@SQLJS_VERSION@@", pkg["version"]), ("@@SQLJS_JS@@", js), ("@@SQLJS_WASM_B64@@", wasm)]:
    assert html.count(k) == 1, k
    html = html.replace(k, v)
assert "@@" not in re.sub(r"[A-Za-z0-9+/=]{1000,}", "", html), "placeholder over"
open(out, "w", encoding="utf-8").write(html)
print("%s: %d kB (sql.js %s, wasm %d kB als base64)" % (out, len(html.encode()) // 1024, pkg["version"], len(wasm) // 1024))
