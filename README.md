# miFormulas

A perfume formulation notebook that runs as a single HTML file in your browser.
No installation, no account, no server required. Your data stays in a JSON file
that you own.

Try it at **https://miformulas.com**

## Download and install

There is nothing to install. The whole app is one file, `index.html`, and it
runs in any modern browser.

- **Just try it.** Open https://miformulas.com. Your work is kept in the
  browser's own storage on that computer; use *Backup* to download a copy.
- **Keep it on your own computer.** Open https://miformulas.com, click
  **Download the app** on the start screen and save the file (it is called
  `miFormulas.html`). Double-click it to open it in your browser. In Chrome or
  Edge, *Open data file…* then reads and writes a data file of your own, so
  your formulas live where you can see and back them up. Firefox cannot write
  to a file; there you keep working in the browser's storage and use *Backup*
  to save.
- **Coming from Formulair?** Open https://miformulas.com/formulair-import.html;
  it converts your Formulair database in the browser, nothing is uploaded. See
  *Coming from Formulair* below.
- **Everything at once.** On this GitHub page click the green **Code** button,
  then **Download ZIP**. The ZIP holds the app, the Formulair importer, the
  starter data, the server endpoint and the tools.

Updating is the same as installing: download the new `miFormulas.html` and
open it. Your data file is separate and stays untouched.

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

The manual is in `docs/`.

## Three ways to keep your data

- **In the browser.** On miformulas.com the app keeps your data in the browser's
  own storage. Good for trying it out; use Backup to download a file.
- **In a file.** Download the app (one HTML file) and open it from your computer
  in Chrome or Edge. "Open data file…" then reads and writes a JSON file of your own.
- **On a server.** Put `index.html` and `server/data.php` on any web server with
  PHP, create a writable `data` folder beside them, set a token in `data.php`, and
  give the same token in Settings on each device. The endpoint returns the JSON
  with an ETag on GET and refuses a PUT whose `If-Match` is stale, so two devices
  never overwrite each other; it also keeps daily snapshots.

## Coming from Formulair

`formulair-import.html` reads the Formulair database (`DataModel.sqlite`, on the
Mac under `~/Library/Containers/co.uk.lux-terra.Formulair/…/Formulair/`) entirely
in your browser and turns it into a miFormulas data file. Every formula comes over
with its notes, date, category and colour marks, and every material with its
dilutions, CAS, supplier, cost, IFRA limit, pyramid level, stock and description.
Formulas stay flat and frozen, one version each; grouping them into base formulas
with versions is something you do afterwards, in the app. Quit Formulair before
copying the file. The same conversion exists as a command-line script in
`tools/formulair-naar-json.py`.

## Licence

GPL v3, with two additional terms under section 7: the name **miFormulas** is
reserved, and every copy must carry the attribution

> Based on miFormulas by Mathieu Isenbaert, https://miformulas.com

See `LICENSE` and `NOTICE`.
