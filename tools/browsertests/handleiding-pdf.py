"""The PDF of the manual (build 261006b): every link in it leads to an address on the web and none to a file (the seven
links to the AI prompts pointed into the temporary folder bouw-docs.py prints from); it has bookmarks, one per section;
and a code block in the printed manual wraps only between words (break-all split "file" and "Users", and a browser
also breaks after a hyphen, as in "--app" or "miformulas-data"), stays inside its box, and still scrolls on screen.
Reads docs/miFormulas-manual.pdf and docs/manual.html of this repository; needs no web server. The script ends with
exit code 1 when a check fails."""
import os, re, sys
from playwright.sync_api import sync_playwright

PUB = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PDF = open(os.path.join(PUB, "docs", "miFormulas-manual.pdf"), "rb").read()
HTML = open(os.path.join(PUB, "docs", "manual.html"), encoding="utf-8").read()
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

def pdf_string(raw):
    """a PDF string as text: (literal) with its escapes, or <hex>, UTF-16 when it starts with FEFF"""
    if raw[:1] == b"<":
        b = bytes.fromhex(raw[1:-1].decode())
    else:
        b = re.sub(rb"\\([()\\])", rb"\1", raw[1:-1])
    return b[2:].decode("utf-16-be") if b[:2] == b"\xfe\xff" else b.decode("latin-1")

uris = [pdf_string(m.group(1)) for m in re.finditer(rb"/URI\s*(\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f]*>)", PDF)]
other = sorted({u for u in uris if not u.startswith("https://")})
check(f"every link in the PDF is an address on the web, none a file ({len(uris)} links; {other[:3]})", uris and not other)
want = HTML.count('<a href="ai-prompts.html"><code>docs/ai-prompts.md</code></a>')
got = uris.count("https://miformulas.com/docs/ai-prompts.html")
check(f"the links to docs/ai-prompts.md lead to the prompts page on the site ({got} of {want})", want and got == want)

titles = [pdf_string(m.group(1)) for m in re.finditer(rb"/Title\s*(\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f]*>)", PDF)]
sections = [re.sub(r"<[^>]+>", "", t) for t in re.findall(r'<h2 id="s\d+[^"]*">(.*?)</h2>', HTML)]
missing = [s for s in sections if s not in titles]
check(f"the PDF has bookmarks, one for each of the {len(sections)} sections (missing: {missing[:3]})",
      b"/Outlines" in PDF and len(sections) == 23 and not missing)

with sync_playwright() as p:
    b = p.chromium.launch()
    # the width the PDF is laid out at: A4 less the two margins of 17 mm that bouw-docs.py gives it
    page = b.new_page(viewport={"width": round((210 - 34) / 25.4 * 96), "height": 1000})
    page.goto("file://" + os.path.join(PUB, "docs", "manual.html").replace(os.sep, "/"))
    page.emulate_media(media="print")
    blocks = page.evaluate("""() => [...document.querySelectorAll('pre')].map(pre => {
        const w = document.createTreeWalker(pre, NodeFilter.SHOW_TEXT);
        let prev = null, wraps = 0;
        const bad = [];
        for (let n; (n = w.nextNode()); )
            for (let i = 0; i < n.data.length; i++) {
                const c = n.data[i];
                if (c === '\\n') { prev = null; continue; }
                const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + 1);
                const rc = r.getClientRects();
                if (!rc.length) continue;
                const top = rc[0].top;
                if (prev && top > prev.top + 4) { wraps++; if (!/\\s/.test(prev.c)) bad.push(prev.c + '|' + c); }
                prev = {c, top};
            }
        return {wraps, bad, over: pre.scrollWidth > pre.clientWidth + 1};
    })""")
    check(f"printed, the long commands of the manual wrap ({len(blocks)} code blocks, {sum(x['wraps'] for x in blocks)} wraps)",
          len(blocks) >= 4 and sum(x["wraps"] for x in blocks) >= 3)
    bad = [y for x in blocks for y in x["bad"]]
    check(f"and only between words, never inside one ({bad[:6]})", not bad)
    check(f"no code block runs out of its box ({sum(x['over'] for x in blocks)})", not any(x["over"] for x in blocks))
    page.emulate_media(media="screen")
    ws = page.evaluate("[...document.querySelectorAll('pre')].map(e => getComputedStyle(e).whiteSpace)")
    check(f"on screen a code block does not wrap but scrolls ({sorted(set(ws))})", ws and set(ws) == {"pre"})
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
sys.exit(1 if fail else 0)
