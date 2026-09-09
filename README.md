# miFormulas

A perfume formulation notebook that runs as a single HTML file in your browser.
No installation, no account, no server required. Your data stays in a JSON file
that you own.
It will keep working, too: one file, no server, data in plain JSON, and free
software under the GPL, so your copy runs as it is whatever happens to the site or
the author, and anyone can take it further.

Try it at **https://miformulas.com**

## Recommended setup

There is nothing to install in the usual sense: the whole app is one file,
`index.html`, and it runs in any modern browser. The setup that gives you an app
with its own icon and your formulas in a file on your own computer:

1. Open https://miformulas.com in **Chrome** (Windows or Mac). On Windows, Edge is
   already there and works exactly the same.
2. Click *Install as an app* on the start screen and confirm. The app opens in
   its own window with its own icon.
3. Click *Start with the starter set*, or *Import from Formulair*.
4. On the Welcome page click *Save to a data file…* and choose a folder of your
   own, for instance `Documents\miFormulas`; keep the name `miformulas-data.json`.
   From now on the app saves to that file, opens straight into it, and updates
   by itself.

The other ways in:

- **Safari on a Mac.** *File › Add to Dock* gives the same app in the Dock; Safari
  cannot write to a data file, so the data lives in the app's storage and
  *Backup* is your safety net.
- **Just try it.** Open https://miformulas.com and start; your work stays in the
  browser's storage on that computer. *Backup* downloads a copy.
- **The app file on your own computer.** Click *Download the app* on the start
  screen and save `miFormulas.html` in a folder of its own; open it in Chrome or
  Edge, choose *Start with the starter set* and keep `miformulas-data.json` next
  to it. Next time the app offers *Reopen*. Updating: download the new file and
  replace the old one; your data file stays untouched.
- **Coming from Formulair?** Open https://miformulas.com/formulair-import.html or
  click *Import from Formulair* in the app; see *Coming from Formulair* below.
- **Everything at once.** On this GitHub page click the green **Code** button,
  then **Download ZIP**: the app, the Formulair importer, the starter data, the
  server endpoint and the tools.

## What it does

**Two-level formulas.** A base formula keeps an immutable version history. On top
of it sit variations: the same recipe in another presentation. A variation is
either *living* (it stores only the deviations and follows the base) or *frozen*
(a snapshot that never changes).

**Perfumery percentages.** Relative % is the dilution-corrected content of a line
divided by the total non-solvent content, so the column sums to 100 and solvent
lines show a dash. Absolute % is content divided by total weight, so the column
total is the concentration. Solvent lines show their share of the weight.

**Dilutions that behave.** A material offers only the dilutions you actually own.
100 % is not implied and any dilution can be the base dilution. The dilution
dialog offers three methods: keep the weight, keep the percentage, or swap the
solvent, with a check for a shortage of ethanol.

**Materials.** Name, CAS, supplier, category with its own colour, stock, cost per
gram, IFRA limit, pyramid level, solvent flag, description, purchase date,
density and storage location. Cross-reference to every formula a material appears
in. Optional stock ledger per material.

**Working tools.** Batch scaling on a factor, a target weight or a target
absolute %. A prediluting facility that turns ticked lines into a frozen
predilution formula plus a material, and rewrites the version to use it. Colour
marks per line. Bench notes per version and variation. An olfactive pyramid, a
category panel, an IFRA check panel with adjustable dosage, a comparison view
between versions with difference marking, a bench view with draggable groups,
printable weighing and bench sheets, and Excel/CSV export. Undo to 50 steps.

**Storage.** In the browser, in a local JSON file (File System Access API, with a
file picker as a fallback), or on your own server with a conflict check and daily
snapshots. See below.

## Getting started

1. Open the app and choose **Start with the starter set**: sixteen formulas and
   two hundred materials to explore, marked "starter" so you can tell them from
   your own.
2. Or choose **Open data file…** for a file of your own, or **Import from
   Formulair** if that is where you come from.
3. Add materials, then formulas. Ctrl+Z undoes any change.

Which browser: Chrome or Edge (Windows or Mac) give you everything, a data file of
your own and the app installed with its own icon. Safari on a Mac works as a Dock
app with the data in the app's storage. Firefox runs the app but keeps the data in
the browser only and may clear it when it closes: fine for a look, not for daily work.

The manual is at https://miformulas.com/docs/manual.html (also as a PDF:
https://miformulas.com/docs/miFormulas-manual.pdf), and ready-made prompts for an
AI assistant at https://miformulas.com/docs/ai-prompts.html; the Markdown sources
are in `docs/`.

Not there (yet): a built-in materials database; section 7 of the manual says what
covers that today.

## Feedback

Questions, problems and ideas: open an issue at
https://github.com/miformulas/miformulas/issues, or write to info@miformulas.com
if you would rather not use GitHub. Mention your browser, the build number shown
next to the name in the app's header, and what you did.

## Three ways to keep your data

- **In the browser.** On miformulas.com the app keeps your data in the browser's
  own storage. Good for trying it out; use Backup to download a file.
- **In a file.** Download the app (one HTML file) and open it from your computer
  in Chrome or Edge. "Open data file…" then reads and writes a JSON file of your own.
  The same works on miformulas.com itself: open your data file there once and the
  site remembers it (Reopen), so an installed copy of the site keeps your own file.
- **On a server.** Put `index.html` and `server/data.php` on any web server with
  PHP, create a writable `data` folder beside them, set a token in `data.php`, and
  give the same token in Settings on each device. The endpoint returns the JSON
  with an ETag on GET and refuses a PUT whose `If-Match` is stale, so two devices
  never overwrite each other; it also keeps daily snapshots.

## Privacy

Nobody but you sees your formulas. The app runs entirely in your browser and your
data lives where you put it: the browser's storage, a file on your disk, or a server
you own. It never uploads anything, sends no telemetry and loads no scripts from
elsewhere; the downloaded app contacts miformulas.com only to fetch the starter set
when you ask for it, and once you have a data file it makes no network request at
all. You can check this in the code: the whole app is this one readable file, and the
manual (section 3) lists every network call it contains and how to verify them.

## Coming from Formulair

`formulair-import.html` reads the Formulair database (`DataModel.sqlite`, on the
Mac under `~/Library/Containers/co.uk.lux-terra.Formulair/…/Formulair/`) entirely
in your browser and adds everything to miFormulas with one click (materials with
the same name are matched, nothing is replaced, one Undo takes it back), or gives
you the data as a file. Every formula comes over
with its notes, date, category and colour marks, and every material with its
dilutions, CAS, supplier, cost, IFRA limit, pyramid level, stock and description.
Formulas stay flat and frozen, one version each; grouping them into base formulas
with versions is something you do afterwards, in the app. Choose File › Close in
Formulair before copying the file. The same conversion exists as a command-line script in
`tools/formulair-naar-json.py`.

## Licence

GPL v3, with two additional terms under section 7: the name **miFormulas** is
reserved, and every copy must carry the attribution

> Based on miFormulas by Mathieu Isenbaert, https://miformulas.com

See `LICENSE` and `NOTICE`.
