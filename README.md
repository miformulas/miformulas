# miFormulas

A perfume formulation app that runs as a single HTML file in your browser.
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
  browser's storage on that computer. *Backup* writes a copy (Chrome and Edge ask
  where; the others put it in your downloads folder).
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

The idea behind it: **less clicking, more smelling.** Time at the screen is time
away from the materials. So everything the app makes you do between two trials
should be one action, not a dozen edits: shift a handful of materials to another
dilution, bundle the traces into a predilution, start the next version, print the
weighing sheet.

**Tick lines, act on all of them at once.** Tick any number of lines in a formula
(Shift-click ticks a range) and the tick bar does the rest. **Lower** and
**Higher** shift every ticked line to the next dilution that material offers,
keeping the relative percentages and exchanging the solvent in one go. **Create
predilution…** turns the ticked lines into a weighable premix, a material and a
new version of the formula that uses it, in one step and one Undo. Colour marks
and bench groups work the same way. We have not seen this in any other
formulation app.

**Coming from Formulair? Bring everything.** The importer reads Formulair's
database in your browser, nothing is uploaded, and adds every formula and
material to miFormulas: notes, dilutions, colour marks, categories, suppliers,
stock, IFRA limits. Materials are matched by name, formulas already imported are
skipped, one Undo takes the whole import back. Afterwards **Move into…** folds
"Aura v04", "Aura v05" and "Aura v05 20%" into one formula with three versions.

**Bench view.** A formula laid out as a worksheet, the way a batch is built: core
materials first, smell, then the next group. Drag lines into named groups, or
tick them and move them together; each group shows its weight and strength;
print it as a bench sheet in weighing order.

**Version history.** A formula keeps an immutable row of versions: only the
latest one is edited, every earlier one stays exactly as it was. Another
presentation of the same recipe (20 % instead of 15 %, a 44 g batch) is simply
a version with a label.

**Perfumery percentages.** Relative % is the dilution-corrected content of a line
divided by the total non-solvent content, so the column sums to 100 and solvent
lines show a dash. Absolute % is content divided by total weight, so the total is
the concentration.

**Dilutions that behave.** A material offers only the dilutions you actually own;
100 % is not implied and any dilution can be the base. The dilution dialog keeps
the weight, keeps the percentage, or swaps the solvent, and warns when the ethanol
runs short.

**Materials.** Name, CAS, alternative names, supplier, category, stock, cost per
gram, IFRA limit, pyramid level, solvent flag, description, density and storage
location; every formula a material appears in; an optional stock ledger. A
materials library of facts can be loaded as a reference: adding a material then
fills in its CAS, category, pyramid level, IFRA limit and a few lines of odour
facts, and **Browse the library…** ticks a dozen at once.

**Sharing a formula.** **Share this version…** writes the version you are looking
at as a small JSON file another miFormulas user imports in one action, with the
material names, dilutions, weights, CAS numbers and notes, and nothing of your own
lab. **Export my inventory as a library…** does the same for the materials you
tick: your facts and your own descriptions, without stock, price or supplier.

**Also there.** Batch scaling on a factor, a target weight or a target
concentration; an IFRA check with adjustable dosage; a comparison view between
versions; an olfactive pyramid; printable weighing sheets; Excel/CSV export; Undo
to 50 steps.

**Storage.** In the browser, in a JSON file of your own (Chrome and Edge), or on
a server with a conflict check and daily snapshots: your own if you have one, or a
free Cloudflare Worker if you do not. See below.

## Getting started

1. Open the app and choose **Start with the starter set**: sixteen formulas and
   nearly two hundred materials to explore, marked "starter" so you can tell them from
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

Your own materials come in from the spreadsheet you already keep them in: save it
as a CSV and use **Import materials inventory from CSV…** on the Welcome page,
which shows your columns next to the fields of a material and lets you match them
on screen. Only the name is required; **Download a template** shows the columns
the app uses itself.

A materials library takes the place of the built-in materials database that some
apps ship: a reference file of facts that you import (**Import materials library…**
behind ⇅ in the header). With one loaded, a material you add arrives with its CAS
number, category, pyramid level, IFRA limit, alternative names and a few lines of
odour facts already filled in, all of it editable, and the materials you own are
never touched. The library published by miFormulas holds several hundred
materials under CC BY 4.0; **Get the latest library** in Settings fetches the
current one. It is not in the repository or in the ZIP: it changes more often
than the app does, so the app asks for it when you do.

## Feedback

Questions, problems and ideas: open an issue at
https://github.com/miformulas/miformulas/issues, or write to info@miformulas.com
if you would rather not use GitHub. Mention your browser, the build number shown
next to the name in the app's header (or in the Help bar, which is where a phone
shows it), and what you did.

## Three ways to keep your data

- **In the browser.** On miformulas.com the app keeps your data in the browser's
  own storage. Good for trying it out; use Backup to download a file.
- **In a file.** Download the app (one HTML file) and open it from your computer
  in Chrome or Edge. "Open data file…" then reads and writes a JSON file of your own.
  The same works on miformulas.com itself: open your data file there once and the
  site remembers it (Reopen), so an installed copy of the site keeps your own file.
- **On a server**, which is what puts the same data on your computer and your
  phone, since no browser on iOS can write to a file. Two endpoints do the same
  job. `server/worker.js` is a Cloudflare Worker with an R2 bucket: paste, bind a
  bucket as `DATA`, set a secret `TOKEN`, and you have an https endpoint on their
  free tier without a server or a domain of your own. `server/data.php` is for a
  web server with PHP: put it next to `index.html`, create a writable `data`
  folder beside them and set a token in it. Either way you give that token in
  Settings on each device. Both return the JSON with an ETag on GET and refuse a
  PUT whose `If-Match` is stale, so two devices never overwrite each other, and
  both keep daily snapshots. Section 20 of the manual walks through both.

## Privacy

Nobody but you sees your formulas. The app runs entirely in your browser and your
data lives where you put it: the browser's storage, a file on your disk, or a server
you own. It never uploads anything, sends no telemetry and loads no scripts from
elsewhere; it contacts miformulas.com only for two files you ask for yourself, the
starter set and the published materials library, and apart from those clicks it
makes no network request at all. You can check this in the code: the whole app is this one readable file, and the
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
