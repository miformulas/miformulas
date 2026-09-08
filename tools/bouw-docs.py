"""Builds the HTML pages of the documentation from the Markdown sources, and optionally the PDF.

    python tools/bouw-docs.py          # docs/manual.html, docs/ai-prompts.html, and the Help text in the app
    python tools/bouw-docs.py --pdf    # also docs/miFormulas-manual.pdf (needs Playwright with Chromium)
    python tools/bouw-docs.py --app PATH   # the app file to update (default: ../miFormulas.html next to
                                           # the repo if it exists, else index.html); --no-app skips it

The Help button of the app shows the same manual: the script writes it, without the images, into
<template id="manualTpl"> between the MANUAL:BEGIN / MANUAL:END markers of the app file. Copy the
app file to deploy/index.html and public/index.html afterwards, as after any change to the app.

Requires the "markdown" package (pip install markdown). The Markdown files stay the source:
edit docs/manual.md or docs/ai-prompts.md and run this script again. The pages embed their
CSS and a few lines of script (the copy buttons); images stay in docs/img.
"""
import html, os, re, sys
import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, ".."))
DOCS = os.path.join(PUB, "docs")

CSS = """
:root{--ground:#FBFCFD;--surface:#FFFFFF;--panel:#EDF1F5;--ink:#212A33;--muted:#6C7A88;--line:#DCE3EA;
  --accent:#A2277E;--accent-ink:#7E1B62;--accent-soft:#F9E3F1;--amber:#DD8500;--amber-soft:#FFEFD2}
@media (prefers-color-scheme: dark){:root{--ground:#1C1122;--surface:#2A1833;--panel:#241430;--ink:#F2E6F2;--muted:#B292BC;
  --line:#453050;--accent:#E667B0;--accent-ink:#F08CC5;--accent-soft:#3A1F38;--amber:#FFB454;--amber-soft:#3B2A12}}
html{background:var(--ground)}
body{margin:0;color:var(--ink);font:16px/1.55 "Segoe UI",system-ui,-apple-system,sans-serif}
main{max-width:52rem;margin:0 auto;padding:1.5rem 1.2rem 4rem}
nav.top{display:flex;flex-wrap:wrap;gap:.4rem 1.2rem;align-items:baseline;font-size:.9rem;color:var(--muted);border-bottom:1px solid var(--line);padding-bottom:.6rem;margin-bottom:1.6rem}
nav.top b{color:var(--accent-ink);font-size:1rem}
nav.top a{color:var(--accent-ink)}
h1{font-size:2rem;line-height:1.2;margin:.2rem 0 1rem}
h2{font-size:1.4rem;margin:2.6rem 0 .8rem;padding-top:.4rem;border-top:1px solid var(--line);color:var(--accent-ink)}
h3{font-size:1.1rem;margin:1.6rem 0 .5rem}
p,li{max-width:46rem}
a{color:var(--accent-ink)}
code{font:.92em/1.4 ui-monospace,Consolas,"SF Mono",Menlo,monospace;background:var(--panel);padding:.05em .3em;border-radius:3px}
pre{background:var(--panel);padding:.8rem 1rem;border-radius:6px;overflow:auto;font:.88rem/1.45 ui-monospace,Consolas,"SF Mono",Menlo,monospace}
pre code{background:none;padding:0;font:inherit}
ol.toc{columns:2;column-gap:2rem;padding-left:2rem;font-size:.95rem}
ol.toc li{break-inside:avoid;padding:.08rem 0}
ol.toc a{text-decoration:none}
ol.toc a:hover{text-decoration:underline}
figure{margin:1.1rem 0 1.4rem;max-width:46rem}
figure img{display:block;max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:#fff}
figure.small img{max-width:min(100%,30rem)}
figcaption{font-size:.86rem;color:var(--muted);margin-top:.4rem}
li > figure{margin-left:0}
hr{border:0;border-top:1px solid var(--line);margin:1.6rem 0}
.prompt{position:relative;margin:1rem 0 1.4rem;border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:6px;background:var(--surface)}
.prompt pre{margin:0;background:none;white-space:pre-wrap;word-wrap:break-word;padding:1rem 5.5rem 1rem 1rem;font:.9rem/1.5 "Segoe UI",system-ui,-apple-system,sans-serif}
.prompt button{position:absolute;top:.5rem;right:.5rem;font:.82rem system-ui,sans-serif;padding:.3rem .7rem;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--ink);cursor:pointer}
.prompt button:hover{border-color:var(--accent)}
.prompt button.done{background:var(--accent-soft);border-color:var(--accent)}
.footer{margin-top:3rem;padding-top:.8rem;border-top:1px solid var(--line);font-size:.85rem;color:var(--muted)}
@media print{
  html{background:#fff} body{font-size:10.5pt;color:#000}
  main{max-width:none;padding:0}
  nav.top{display:none}
  h2{break-before:page;border-top:0;margin-top:0;color:#000}
  h2#contents,h2:first-of-type{break-before:auto}
  h2.no-break{break-before:auto}
  figure{break-inside:avoid}
  figure img{border-color:#bbb;max-height:40vh;width:auto}
  figure.small img{max-width:min(100%,22rem)}
  a{color:#000;text-decoration:none}
  ol.toc{columns:2}
  pre{white-space:pre-wrap;word-break:break-all}
  .prompt{break-inside:avoid;border-color:#bbb}
  .prompt button{display:none}
}
"""

JS = """
document.querySelectorAll('.prompt button').forEach(b => b.addEventListener('click', async () => {
  const t = b.parentElement.querySelector('pre').textContent;
  try{ await navigator.clipboard.writeText(t); b.textContent = 'Copied'; b.classList.add('done'); }
  catch(e){ const r = document.createRange(); r.selectNodeContents(b.parentElement.querySelector('pre'));
    const s = getSelection(); s.removeAllRanges(); s.addRange(r); b.textContent = 'Select and copy'; }
  setTimeout(() => { b.textContent = 'Copy'; b.classList.remove('done'); }, 2500);
}));
"""

def slug(text):
    t = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    t = re.sub(r"[\s]+", "-", t)
    return ("s" + t) if t[:1].isdigit() else t   # "s4-download-and-install": an id may start with a digit, a CSS selector may not

def figures(h, base):
    """<p><img alt></p> becomes <figure><img><figcaption>; warns for missing files."""
    def rep(m):
        alt, src = m.group("alt"), m.group("src")
        path = os.path.join(base, src.replace("/", os.sep))
        if not os.path.exists(path):
            print("  warning: image not found:", src)
        cls = ' class="small"' if re.search(r"(dialog|prompt|settings|start-|dock|icon|predilution|new-variation|go-to-folder)", src) else ""
        cap = f"<figcaption>{alt}</figcaption>" if alt else ""
        return f'<figure{cls}><img src="{src}" alt="{alt}" loading="lazy">{cap}</figure>'
    return re.sub(r'<p>\s*<img alt="(?P<alt>[^"]*)" src="(?P<src>[^"]+)"\s*/?>\s*</p>', rep, h)

def autolink(h):
    """bare URLs in text become links (not the ones already inside a tag)"""
    return re.sub(r'(?<![">=/\w])(https?://[^\s<)"]+?)(?=[.,;:)]?(?:\s|<|$))', r'<a href="\1">\1</a>', h)

def convert(md_text):
    m = markdown.Markdown(extensions=["toc", "tables", "sane_lists"],
                          extension_configs={"toc": {"slugify": lambda v, s: slug(v), "toc_depth": "2-3"}})
    return m.convert(md_text)

def page(title, body, nav, description=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="icon" href="../icons/icon-192.png">
<style>{CSS}</style>
</head>
<body>
<main>
{nav}
{body}
<div class="footer">miFormulas is free software (GPL v3 with two additional terms, see the licence section). Source and issues: <a href="https://github.com/miformulas/miformulas">github.com/miformulas/miformulas</a>.</div>
</main>
<script>{JS}</script>
</body>
</html>
"""

def nav(current):
    items = [("https://miformulas.com", "miformulas.com"), ("manual.html", "Manual"), ("ai-prompts.html", "AI prompts"),
             ("miFormulas-manual.pdf", "Manual as PDF"), ("https://github.com/miformulas/miformulas", "GitHub")]
    return '<nav class="top"><b>miFormulas</b>' + "".join(
        f'<span>{label}</span>' if href == current else f'<a href="{href}">{label}</a>' for href, label in items) + "</nav>"

def manual_html():
    """the manual as an HTML fragment (before figures), plus its h2 list and the source text"""
    src = open(os.path.join(DOCS, "manual.md"), encoding="utf-8").read()
    h = convert(src)
    # the Contents list becomes a linked table of contents built from the h2 headings
    heads = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', h)
    strip_no = lambda t: re.sub(r"^\d+\.\s*", "", t)
    toc = "".join(f'<li><a href="#{i}">{strip_no(t)}</a></li>' for i, t in heads if t != "Contents")
    h = re.sub(r'(<h2 id="contents">Contents</h2>)\s*<ol>.*?</ol>', r'\1<ol class="toc">' + toc + "</ol>", h, count=1, flags=re.S)
    # "section 19" in the text links to that section
    ids = {re.match(r"(\d+)\.", t).group(1): i for i, t in heads if re.match(r"\d+\.", t)}
    h = re.sub(r"\b([Ss]ections?) (\d+)\b(?! of the G)", lambda m: f'{m.group(1)} <a href="#{ids[m.group(2)]}">{m.group(2)}</a>' if m.group(2) in ids else m.group(0), h)
    return h, heads, src

def build_manual():
    h, heads, src = manual_html()
    h = figures(h, DOCS)
    h = h.replace("<code>docs/ai-prompts.md</code>", '<a href="ai-prompts.html"><code>docs/ai-prompts.md</code></a>')
    h = autolink(h)
    m = re.search(r"describes build (\w+)", src)
    desc = "User manual of miFormulas, the perfume formulation app" + (f" (build {m.group(1)})" if m else "")
    out = page("miFormulas manual", h, nav("manual.html"), desc)
    open(os.path.join(DOCS, "manual.html"), "w", encoding="utf-8", newline="\n").write(out)
    print("wrote docs/manual.html", f"({len(heads)} sections, {h.count('<figure')} figures)")

def build_prompts():
    src = open(os.path.join(DOCS, "ai-prompts.md"), encoding="utf-8").read()
    # the text between two horizontal rules is a prompt: shown verbatim, with a copy button
    parts = re.split(r"^---\s*$", src, flags=re.M)
    if len(parts) % 2 == 0:
        print("  warning: odd number of --- rules in ai-prompts.md")
    out, prompts = [], []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            prompts.append(part.strip("\n"))
            out.append(f"\n\nPROMPTBLOCK{len(prompts)-1}\n\n")
        else:
            out.append(part)
    h = convert("".join(out))
    for i, p in enumerate(prompts):
        block = f'<div class="prompt"><button type="button" title="Copy this prompt to the clipboard">Copy</button><pre>{html.escape(p)}</pre></div>'
        h = re.sub(rf"<p>PROMPTBLOCK{i}</p>", lambda m: block, h)
    h = h.replace("<code>docs/manual.md</code>", '<a href="manual.html"><code>docs/manual.md</code></a>')
    h = autolink(h)
    out = page("miFormulas and your own AI assistant", h, nav("ai-prompts.html"),
               "Ready-made prompts for using an AI assistant with miFormulas: photo to import file, materials check, Formulair grouping, server setup")
    open(os.path.join(DOCS, "ai-prompts.html"), "w", encoding="utf-8", newline="\n").write(out)
    print("wrote docs/ai-prompts.html", f"({len(prompts)} prompts)")

ONLINE = "https://miformulas.com/docs/manual.html"

def build_fragment():
    """the manual for the Help button: same text, each figure replaced by a link to the online page"""
    h, heads, src = manual_html()
    def rep(m):
        alt = m.group("alt")
        before = h[:m.start()]
        i = before.rfind('<h2 id="')
        sec = before[i + 8:before.find('"', i + 8)] if i >= 0 else "contents"
        return f'<p class="helpfig">Screenshot in the online manual: <a href="{ONLINE}#{sec}">{alt}</a></p>'
    h = re.sub(r'<p>\s*<img alt="(?P<alt>[^"]*)" src="(?P<src>[^"]+)"\s*/?>\s*</p>', rep, h)
    h = h.replace("<code>docs/ai-prompts.md</code>", '<a href="https://miformulas.com/docs/ai-prompts.html"><code>docs/ai-prompts.md</code></a>')
    h = autolink(h)
    assert "</template>" not in h and "<script" not in h.lower()
    return h

def update_app(path):
    s = open(path, encoding="utf-8").read()
    m = re.search(r"(<!-- MANUAL:BEGIN[^\n]*-->\n)(.*?)(<!-- MANUAL:END -->)", s, flags=re.S)
    if not m:
        print("  no MANUAL:BEGIN / MANUAL:END markers in", path, "- app not updated"); return
    frag = '<template id="manualTpl">' + build_fragment() + "</template>\n"
    out = s[:m.start(2)] + frag + s[m.start(3):]
    if out == s:
        print("app already up to date:", os.path.relpath(path, PUB)); return
    open(path, "w", encoding="utf-8", newline="\n").write(out)
    print("updated Help text in", os.path.relpath(path, PUB), f"({len(frag)//1024} kB)")

def build_pdf():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed; PDF skipped"); return
    # print from a temporary copy with the images reduced to 1000 px wide and JPEG-compressed
    # (same file names, so manual.html needs no change): the screenshots are taken at 2x for the
    # web pages, and as PNG at full size the PDF would be six times larger
    import shutil, tempfile
    tmp = tempfile.mkdtemp(prefix="miformulas-pdf-")
    shutil.copy(os.path.join(DOCS, "manual.html"), tmp)
    os.makedirs(os.path.join(tmp, "img"))
    try:
        from PIL import Image
    except ImportError:
        Image = None
    for f in os.listdir(os.path.join(DOCS, "img")):
        srcf, dstf = os.path.join(DOCS, "img", f), os.path.join(tmp, "img", f)
        if Image and f.lower().endswith(".png"):
            im = Image.open(srcf).convert("RGB")
            if im.width > 1000:
                im = im.resize((1000, round(im.height * 1000 / im.width)), Image.LANCZOS)
            # JPEG goes into the PDF as it is; a PNG would be re-encoded much larger
            im.save(dstf, format="JPEG", quality=82, optimize=True)
        else:
            shutil.copy(srcf, dstf)
    src = "file://" + os.path.join(tmp, "manual.html").replace("\\", "/")
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        pg.goto(src)
        # lazy images outside the viewport would stay empty in the PDF: load them all first
        pg.evaluate("document.querySelectorAll('img').forEach(i => i.loading = 'eager')")
        pg.wait_for_function("[...document.images].every(i => i.complete)")
        pg.wait_for_timeout(500)
        pg.emulate_media(media="print")
        pg.pdf(path=os.path.join(DOCS, "miFormulas-manual.pdf"), format="A4", print_background=True,
               margin={"top": "18mm", "bottom": "16mm", "left": "17mm", "right": "17mm"},
               display_header_footer=True,
               header_template='<div style="font-size:8pt;color:#777;width:100%;padding:0 17mm;display:flex;justify-content:space-between"><span>miFormulas manual</span><span>miformulas.com</span></div>',
               footer_template='<div style="font-size:8pt;color:#777;width:100%;text-align:center"><span class="pageNumber"></span> / <span class="totalPages"></span></div>')
        b.close()
    shutil.rmtree(tmp, ignore_errors=True)
    print("wrote docs/miFormulas-manual.pdf")

if __name__ == "__main__":
    build_manual()
    build_prompts()
    if "--no-app" not in sys.argv:
        if "--app" in sys.argv:
            app = sys.argv[sys.argv.index("--app") + 1]
        else:
            master = os.path.join(PUB, "..", "miFormulas.html")
            app = master if os.path.exists(master) else os.path.join(PUB, "index.html")
        update_app(os.path.abspath(app))
    if "--pdf" in sys.argv:
        build_pdf()
