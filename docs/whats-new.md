# What’s new in miFormulas

What changed in the app, newest first. The manual describes every function in full; the technical release notes are on GitHub.

## On miformulas.com since 19 October

These changes are on the site and in the app installed from it. If you run miFormulas.html from your own computer, you get them with the next version.

### Finding the materials library

The materials library, which fills in CAS, category, pyramid level, IFRA limit and alternative names when you type a name, has to be fetched once, and the only place to do that was Settings. Now **+ New material…** says so while no library is loaded, with **Get the latest library** right there, so the facts arrive for the material you are typing. Don’t want a library? The ✕ next to it stops the reminder for good; Settings keeps the button.

*Manual, section [3](manual.html#s3-materials)*

### The material page, rearranged

The page of a material follows the formula page: the name at the top with Add to order list and the menu **⋯** (Delete material); under it the CAS number, the category, the alternative names and the look-up links; the fields in two columns, what the material is on the left and what you have of it on the right; and the four panels, Dilutions, Stock, Description and Usage in formulas, two by two under them. The Alternative names field now says how to enter several: separated by semicolons.

*Manual, section [3](manual.html#s3-materials)*

### The formula page, rearranged

The page of a formula shows less at once. Its head has two rows: the name and the version, with what you do with versions, and under them, smaller, the category, the date and the order of the lines. Rename, copy, move and delete are in the menu **⋯** at the end of the first row, next to Bench view.

The bar with the colour marks, Lower, Higher and Create premix… appears only once you tick a line. It says how many you ticked and stays at the bottom of the window while you scroll through a long formula.

Under the table, **Print / export** holds Print full formula, Excel export and Share this version; **Print weighing sheet** stays a button of its own, and **Batch scaling** opens a strip under the table. The four panels below it, Notes, Trial log, Pyramid & categories and IFRA check, stand two by two. The pyramid, which stood in the head, is now in the panel with the categories.

*Manual, sections [4](manual.html#s4-formulas-and-versions), [5](manual.html#s5-editing-a-formula), [10](manual.html#s10-bench-view-and-printing) and [12](manual.html#s12-ifra-check-and-category-panel)*

> **Do you have the latest version?** When using the app on miformulas.com, in a browser or installed from there as an app, you always do: just reopen it.  
> A copy of miFormulas.html on your own computer does not change by itself: go to **Settings › Check for updates**. No such button in your Settings? Then your copy is v2.2 or older. Open miformulas.com in Chrome or Edge, go to **Settings › Download the app** and put the new miFormulas.html in place of the old one (same folder, same name). Your data file is not touched, and the app offers to reopen it.

## On miformulas.com since 18 October

These changes are on the site and in the app installed from it. If you run miFormulas.html from your own computer, you get them with the next version.

### Starting empty on your own computer

The downloaded app (miFormulas.html on your own computer) now has **Start empty** on its start screen, next to **Start with the starter set**. It creates your data file next to the app with nothing in it yet, and it does so without going online: the starter set has to be fetched from miformulas.com once, an empty file does not. With a data file in place, the app needs no internet connection at all.

*Manual, sections [14](manual.html#s14-where-your-data-lives-and-the-other-ways-in) and [21](manual.html#s21-privacy-who-can-see-your-formulas)*

### Import & export

The Import & export window (⇅ in the header) is grouped under headings, as Settings is: what comes in on the left, what goes out and the ways back to an earlier state on the right, with what each button does under it. The two buttons that replace all your data, Restore a Backup… and Restore daily snapshot, are red.

*Manual, section [16](manual.html#s16-import-export-and-sharing)*

### A purchase starts the stock ledger

On a material whose stock you do not track yet, **Purchase › Add** in the Stock panel now starts the ledger at once, with a stocktake of 0 g before the purchase, instead of noting a purchase that counted nowhere. **Delivered…** on the order list has a tick box **Track stock**, on by default, which does the same, also for a material it creates.

*Manual, section [13](manual.html#s13-stock-orders-and-deliveries)*

## On miformulas.com since 16 October

These changes are on the site and in the app installed from it. If you run miFormulas.html from your own computer, you get them with the next version.

### Removing the starter set

If you decided to have your formulas and materials “move in” to miFormulas, you may find that the starter set is in the way. **Settings › Starter set** now has two buttons: **Remove the starter formulas** and **Remove the starter set materials**. They are separate on purpose: if you added stock, prices or notes to the starter materials, you can remove the formulas only and keep the materials.

If you want to remove both formulas and materials, it is best to start with **Remove the starter formulas**. Materials used in the remaining formulas will not be removed with **Remove the starter set materials.** This button removes every starter material, also the ones you already edited; there is an alert before you can confirm the removal. Each button asks first, and one Undo takes everything back.

With nothing of your own yet, Delete the data kept in this browser and Start empty come to the same thing.

*Manual, section [19](manual.html#s19-settings-theme-and-keyboard-shortcuts)*

### Settings

The Settings window is grouped under headings: General, Materials library, Starter set, Where your data lives and This app. The buttons that delete something are red.

*Manual, section [19](manual.html#s19-settings-theme-and-keyboard-shortcuts)*

## v2.3 – 16 October 2026

### Search

The search finds the words of a name in any order: “gamma decalactone” finds Decalactone gamma. While you search, the list shows one list by name instead of the categories. When a material was found by an alternative name, its CAS number or its supplier, that is shown in grey beside it, and a match in the description comes last.

*Manual, section [2](manual.html#s2-the-screen)*

### Classifying several items at once

**Classify several…**, above the search box of the Materials list, gives many materials a category in one go, and a pyramid level if you want. In its window the search field narrows the list and shift-click ticks a range. The ticks stay when you search again, so you can gather the materials over several searches. Then choose a category, a level or both, and apply. One Undo takes the whole batch back. Handy when your inventory came in from a spreadsheet and still has to be sorted.

The same button sits above the Formulas list, for categories.

*Manual, sections [3](manual.html#s3-materials) and [4](manual.html#s4-formulas-and-versions)*

### The category of a formula

A formula’s category is now chosen on its page, above the version list, with + New category beside it, as on a material page. Change category… is gone.

*Manual, section [4](manual.html#s4-formulas-and-versions)*

### Materials from a spreadsheet

**Import materials inventory from CSV…** (on the Welcome page, or in Import & export, ⇅ in the header) now turns a stock column into a stocktake dated today, and keeps a description that runs over several lines in one cell, also after a round trip through Excel. Two rows with the same name become two materials; only a name you already have in your inventory is skipped. A large sheet goes much faster than before.

*Manual, section [16](manual.html#s16-import-export-and-sharing)*

### Materials library

The library grew from 654 to 1,248 materials. Every material has a category, nearly all a pyramid level and a few odour words.

The library and your inventory are easy to mix up. Your inventory is the Materials tab: the materials you own, with your dilutions, descriptions and stock. The library is a reference list the app looks things up in. Fetching a new library never touches your inventory: nothing is added, nothing is overwritten. Library materials only show up when you look for them: type a name in the Materials search (they appear under “Also in the materials library”, with + Add), or open Browse the library… in + New material.

To get the latest library: **Settings › Get the latest library**. The app does not fetch it on its own; once fetched, it is saved with your data.

*Manual, sections [3](manual.html#s3-materials) and [16](manual.html#s16-import-export-and-sharing)*

### TGSC and Olfactorian

The TGSC and Olfactorian buttons on a material page open that material’s own page on those sites whenever the library has a link for it, instead of a search.

*Manual, section [3](manual.html#s3-materials)*

### Updating your own copy

A copy of miFormulas.html on your own computer now has an update button: **Settings › Check for updates**. It compares your copy with the one on miformulas.com and replaces it when there is a newer one. Copies from v2.2 or older do not have the button yet; see the box above.

*Manual, section [14](manual.html#s14-where-your-data-lives-and-the-other-ways-in)*

### Your first five minutes

A new short guide, Your first five minutes, takes one small task from start to finish: a material from the library, a formula of four lines, and a second version compared with the first.

*[Your first five minutes](first-five-minutes.html)*

### Smaller changes

- Opening a material from a long list is several times faster.

- Settings fits on a laptop screen without scrolling.

- The tooltip of ⚠ on a formula line explains how to move the line to a dilution you have.

- The bench view no longer shows the category and the version list above it.

- A save window only offers files ending in .html or .json.

- Download the app is no longer offered on a phone or tablet: the downloaded app is meant for Chrome or Edge on a computer.

*Manual, sections [3](manual.html#s3-materials), [10](manual.html#s10-bench-view-and-printing) and [19](manual.html#s19-settings-theme-and-keyboard-shortcuts)*
