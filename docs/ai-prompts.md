# miFormulas and your own AI assistant

miFormulas itself never talks to an AI, and that is deliberate: a built-in AI would need a paid API key and would send your formulas to a third party, and neither fits an app that keeps everything on your own computer. But several chores around it are exactly what an AI assistant that can read images and files (ChatGPT, Claude, Gemini, Copilot and others) does well, with your files, on your account. This page collects ready-made prompts for four of them. Copy the text between the lines into the chat, attach what the prompt asks for, and check the answer before you use it: an assistant can misread a handwritten 7 as a 1 and it can state a wrong IFRA limit with full confidence.

Attachments: ChatGPT, Claude and Gemini accept photos, PDFs and CSV files as attachments. Some free Copilot versions do not; paste the text of the file into the chat instead (for the materials export, the Name column is usually enough).

## 1. Photo, PDF or spreadsheet to import file

miFormulas imports formulas from a small JSON file (type `miformulas-import`). An assistant produces it from a photo of a handwritten sheet, a scan, a PDF or a spreadsheet. Save the answer as a `.json` file, then in miFormulas go to the Welcome page, click **Import formula…**, choose the file, check the preview and confirm.

Tip: attach the file **All materials (Excel)** from the Welcome page as well. The assistant then uses the exact names of your own library, and every line lands on the right material. Without it the assistant keeps the names as written, and materials that are not in your library are created as "to order" for you to merge or rename.

---

You are converting a perfume formula into an import file for the miFormulas app. Attached is the formula as a photo, scan, PDF or spreadsheet, and possibly a CSV export of my materials library.

Do this:

1. Transcribe the formula exactly, line by line: material name, dilution in percent, weight in grams. Copy names verbatim, including brand or supplier tags such as (Giv), (IFF), (Firm). If a line shows no dilution, use 100. If the source gives only percentages or parts, convert them to grams on a 100 g batch and say so in "notes". Transcribe numbers exactly; decimal commas become decimal points in the JSON.
2. If a materials library (CSV) is attached, use its exact spelling of the material name in "material" whenever a line clearly matches a library entry. When you are not sure, keep the transcribed name in "material" and add your best guess in "comment" ("possibly: …"). Never silently substitute one material for another.
3. Do not convert dilutions or weights to what the library stocks. Keep them exactly as printed; the app flags unknown dilutions and I convert them myself.
4. Use the formula name written on the sheet. If there is none, ask me instead of inventing one. Never invent version labels.
5. Answer with the JSON only, in this shape:

{
 "type": "miformulas-import",
 "name": "<formula name as written>",
 "category": "<category if I named one, else omit this line>",
 "source": "<photo, PDF or spreadsheet, and the origin or author if known>",
 "notes": "<batch conversion, illegible lines, other remarks; omit if none>",
 "lines": [
  {"material": "Hedione", "dilutionPct": 100, "weightG": 17.5},
  {"material": "Iso E Super", "dilutionPct": 10, "weightG": 2, "comment": "possibly: Iso E Super (IFF)"}
 ]
}

6. After the JSON, tell me in a few lines: the total weight (and whether it is a round number such as 100 or 1000, which suggests a complete transcription), how many lines matched the library and how many are new, and every line you could not read or were unsure about, as questions.

One formula per file. If the source shows several formulas, ask which one you should convert first.

---

The optional fields `targetFormula` (the exact name of an existing formula; the import then becomes a new version of it instead of a new formula), `versionName`, `materialId` and `cas` are described in the data model in the repository. The app matches materials by name, so `materialId` is not needed. Save the answer as UTF-8 text with the extension `.json`, for instance `260908 import Roos akkoord.json`; if the assistant wrapped it in a code block, remove the backticks.

## 2. Checking and completing your materials

The export **All materials (Excel)** on the Welcome page is a CSV with one row per material: Name, CAS, Category, Supplier, Amount purchased, Purchase date, Cost EUR/g, IFRA limit %, Pyramid, Solvent, storage, Density, Stock, Dilutions and Description. An assistant can propose the missing CAS numbers, IFRA limits, pyramid levels, categories and one-line odour descriptions, and point out likely duplicates. The app has no materials import, so you enter what you accept by hand on the material pages; do it for the materials you added recently rather than for the whole library at once.

The IFRA figures deserve the most scepticism. The source that counts is the standards library on ifrafragrance.org; the prompt asks the assistant to name the amendment it took a limit from and to say "unknown" rather than guess, and you look up every value you enter. In the app, 99 means "checked, no restriction" and an empty field means "not yet checked".

---

Attached is a CSV export of my perfume materials library from the miFormulas app (columns: Name, CAS, Category, Supplier, Amount purchased, Purchase date, Cost EUR/g, IFRA limit %, Pyramid, Solvent, Cupboard, Fridge, Freezer, Density g/ml, Stock g, Dilutions %, Description). Help me check and complete it. Do not rename anything; I enter your proposals by hand.

Give me a table with one row per material that has something missing or doubtful, with these columns:

- Name, exactly as in the file.
- CAS: the existing value, or a proposal when it is empty, or a correction when the existing value does not belong to that material. Mark proposals and corrections as such.
- IFRA limit: the IFRA Standards limit for Category 4 (fine fragrance) in percent of the finished product, with the amendment number you took it from. Write "no restriction" when the material is not restricted under the current standards, "specification" when the standard is a purity specification rather than a limit, and "unknown" when you are not certain. Never guess a number.
- Pyramid: Top, Top-heart, Heart, Heart-base or Base.
- Category: a proposal from the categories already used in the file, or a new one if none fits.
- Odour: one line, for the description field.
- Remarks: anything else, for instance a name that looks like a typo or a dilution that seems odd.

Below the table, list the likely duplicates: pairs of rows with the same CAS number or nearly identical names. Say for each pair whether they are really the same material or legitimately different products with the same CAS (a vetiver oil from Java and one from Haiti share a CAS number and must stay separate). Do not propose merging on the CAS number alone.

Keep the table plain (no merged cells) so that I can copy it into a spreadsheet. Skip materials where everything is present and plausible.

---

## 3. Grouping formulas that came from Formulair

The Formulair importer keeps every Formulair formula as a separate frozen formula, because Formulair is flat: "Aura v04" and "Aura v05" are two formulas there. In miFormulas they belong together as versions of one formula, and "Aura v05 20%" is a variation of it. An assistant can propose that grouping from the names, for you to review; a helper inside the app for the same job is planned. Give it the names: the export **All formulas (Excel)** on the Welcome page has them in the first column, or copy them from the list on the left.

Applying the proposal is still done by hand in the app: **Copy to new formula** turns a frozen import into v1 of a new formula, **+ New version** adds the next one (the lines of an imported version can be copied by opening it and creating the new version from it), and **+ New variation** makes the presentations. Frozen imports stay as they are, so nothing is lost while you regroup.

---

Below is a list of perfume formula names that were imported from another program, where every trial was a separate formula. Propose how to group them into formulas with a version history and variations. Do not rename anything beyond splitting a name into its parts, and do not merge names that only look similar.

Rules:

- A stem followed by a version number ("Aura v04", "Aura V4", "Aura v.4", "Aura versie 4", "Aura 4") is a version of the formula "Aura". The version number is the number in the name.
- A name with a suffix that describes a presentation rather than a new trial ("20%", "EDT", "soap", "44gr", "10 ml", "candle") is a variation of the version it is based on, with that suffix as its label. If the base version is not named, note which version it most likely belongs to and mark it as a question.
- Different stems stay separate formulas, even when they share words. A date in a name is not a version number; keep it as a remark.
- When a name fits more than one reading, list it under "questions" with the readings, instead of choosing.

Answer with a table with the columns: Original name | Formula | Version | Variation label | Confidence (high, medium, low) | Remark. Sort by formula, then version. After the table, list the questions, and the names you left as separate single-version formulas.

Here are the names:

(paste the names here, one per line)

---

## 4. Setting up your own server

Section 19 of the manual describes the server mode: the app and `server/data.php` on a web server with PHP, a writable `data` folder next to them, a token, and the app connecting to it. An assistant can turn that into step-by-step instructions for your own device, if you give it the two files it needs and tell it what you have. Never give it your token; you choose that yourself and type it into `data.php` and into the app.

---

I want to run the miFormulas app on my own web server so that all my devices share one data file. Attached are the server endpoint `data.php` from the miFormulas repository and the section "Your own server" of its manual. Read both first.

My situation: (describe your device and what you know, for example: a Synology DS220+ with DSM 7.2, Web Station is installed but I have never used it; or: a Raspberry Pi 4 with Raspberry Pi OS; or: shared hosting at provider X with PHP 8.2 and FTP access. Say whether you can already reach the device by name or address in a browser, and whether you want to reach it from outside your home.)

Guide me step by step. Ask me what you need to know before each step rather than assuming. For every step, tell me exactly where to click or what to type, and how I can check that it worked. Cover: installing PHP and the web service if needed, placing `index.html`, `data.php` and the `data` folder, giving the web server's user write access to `data`, setting a token in `data.php` (I will choose the token myself and will not tell you what it is), putting my `miformulas-data.json` in the `data` folder, opening the app in the browser and entering the token, and, if I want access from outside, the safe way to do that (a VPN such as Tailscale, with https). When something can go wrong in a way that costs data, warn me before that step.

---
