# What’s new in miFormulas

What changed in the app, newest first. The manual describes every function in full; the technical release notes are on GitHub.

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

> **Do you have the latest version?** When using the app on miformulas.com, in a browser or installed from there as an app, you always do: just reopen it.  
> A copy of miFormulas.html on your own computer does not change by itself: go to **Settings › Check for updates**. No such button in your Settings? Then your copy is v2.2 or older. Open miformulas.com in Chrome or Edge, go to **Settings › Download the app** and put the new miFormulas.html in place of the old one (same folder, same name). Your data file is not touched, and the app offers to reopen it.

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
