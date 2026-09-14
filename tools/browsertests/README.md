# Browsertests (Playwright, Chromium)

Draaien tegen een lokale webserver met de inhoud van `public\` op poort 8765:

    cd public && python -m http.server 8765
    python demo-flow.py            # startscherm, starterset, autosave, labels, Settings, herbezoek, server, reset, opzoeklinks (42 controles)
    python migratie-en-file.py     # bestaand token zonder serverUrl -> data.php; geen token in de HTML; file:// -> bestandsmodus
    python opslagbalk.py           # balk bij niet-persistente browseropslag, tekstvarianten (Firefox, iOS, Dock-app), sluiten, sessie (21 controles)
    python formulair-import.py     # DataModel.sqlite inlezen, download vergelijken met formulair-naar-json.py (pad SQ aanpassen)
    python formulair-doorsturen.py # "Add to miFormulas" in een lege browser -> app start met 698 formules (pad SQ aanpassen)
    python merge-import.py         # Formulair-import samengevoegd met bestaande data: naam-matching, diluties, categorieën, overslaan bij tweede import, Undo, lege browser (21 controles)
    python site-reopen.py          # Open data file… op de site: onthouden, Reopen, Forget in Settings, verdwenen bestand, Install-knop, Save to a data file… (36 controles)
    python file-mode.py            # gedownloade app via file://: hint, starterset van miformulas.com (nagebootst), databestand aanmaken (44 controles, incl. herstart met Reopen en verdwenen bestand; geen webserver nodig; leest de bouwstempel uit index.html)
    python help.py                 # Help-knop: ingebedde handleiding, inhoudstafel, terug naar de vorige weergave (17 controles)
    python move-into.py            # Move into…: geïmporteerde formule als versie of bevroren variatie van een andere, Move together, "this formula", Undo (48 controles)
    python materiaallijst.py       # materials library: import, Settings, Get the latest library, + New material met feiten, Browse the library… met shift-klik, "+ Add" in de zoeklijst, Undo (50 controles)
    python undo-navigatie.py       # één undo-stap per handeling (nieuwe categorie, predilutie, Replace + dilutiewissel), Redo keert terug naar de plek van de wijziging, Copy vanuit een variatie, bench mee naar een nieuwe versie (14 controles)
    python validatie.py            # wat de app weigert: negatief gewicht, dilutie buiten 0-100, dubbele dilutie, basisdilutie die verdwijnt, tekst als getal, eigen velden met underscore; dagsnapshot, Delete version op een import, verborgen importverwijzing (21 controles)
    python namen.py                # Add line, formule-import en Delivered nemen de feiten uit de bibliotheek mee, categorie niet dubbel door hoofdletters, alias die je al bezit, hernoemen zonder dubbele namen (14 controles)
    python kost-en-ifra.py         # kost per gram zuiver (Delivered met basisdilutie, predilutie), IFRA 0 = prohibited en negatief = niet nagekeken, geen databestand openen, bibliotheek met rommel, server zonder databestand (21 controles)
    python variaties.py            # live variaties: verschillen per regel van de basisversie (materiaal + dilutie daar), marks die niet verschuiven, solventcorrectie die meeschaalt, predilutie vanuit een variatie (20 controles)
    python opslagvolgorde.py       # één schrijfactie tegelijk: wijziging tijdens een trage PUT (nagebootste server in de pagina), geen tweede PUT met dezelfde ETag, browseropslag die weigert, databestand vervangt de browserkopie (15 controles)
    python getalnotatie.py         # en-GB: duizendtalscheiding in invoervelden, parseNum, Delivered per 1000 g, IFRA-dosering per formule, Ctrl+Z onder een dialoog, Replace + Cancel, gebruiksindex na Add line (15 controles)
    python safari-hints.py         # Safari op de Mac: Add to Dock-link en dialoog, waarschuwing bij Download the app, alleen-lezen startscherm via file://, opslagbalk in tabblad en Dock-app, Import from Formulair op de Welcome-pagina, importer in de Dock-app (37 controles)
    python screenshots.py          # geen test: maakt de app-schermen voor docs/img (zie docstring)

Vereist `pip install playwright` en `playwright install chromium`. De paden bovenaan de
scripts (URL, SQ, referentiebestand) zijn die van de cloudsessie van 07/09/2026; pas ze aan.
