# Browsertests (Playwright, Chromium)

Draaien tegen een lokale webserver met de inhoud van de repo (`public\` in de OneDrive-map) op poort 8765:

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
    python move-into.py            # Move into…: geïmporteerde formule als versie van een andere, Move together, "this formula", Undo (37 controles)
    python materiaallijst.py       # materials library: import, Settings, Get the latest library, + New material met feiten, Browse the library… met shift-klik, "+ Add" in de zoeklijst naast en zonder eigen treffers, Undo (54 controles)
    python deel-formule.py        # Share this version…: wat er in het bestand komt en wat er niet in komt, en de rondgang bij een ontvanger die het materiaal en de formule niet heeft (26 controles)
    python export-bibliotheek.py   # Export my inventory as a library…: alles vooraf aangevinkt, shift-klik, wat er wel en niet in het bestand komt, en de rondgang terug via import (40 controles)
    python opruiming.py            # staart van de review: zoeken op "starter", bevestiging bij ✕, ellipsis op de openers, aliassen in de keuzelijst, attributie in Settings, alleen-lezen op een telefoon (33 controles)
    python undo-navigatie.py       # één undo-stap per handeling (nieuwe categorie, predilutie, Replace + dilutiewissel, ook door de dilutiedialoog), Redo keert terug naar de plek van de wijziging, Copy vanuit een oudere versie, bench mee naar een nieuwe versie (18 controles)
    python validatie.py            # wat de app weigert: negatief gewicht, dilutie buiten 0-100, dubbele dilutie, basisdilutie die verdwijnt, tekst als getal, eigen velden met underscore, negatief doelgewicht, basisdilutie boven 100 in + New material, Set EtOH zonder ethanol; dagsnapshot, Delete version op een import, verborgen importverwijzing (25 controles)
    python namen.py                # Add line, formule-import en Delivered nemen de feiten uit de bibliotheek mee, categorie niet dubbel door hoofdletters, alias die je al bezit, hernoemen zonder dubbele namen (14 controles)
    python kost-en-ifra.py         # kost per gram zuiver (Delivered met basisdilutie, predilutie met hoeveelheid en IFRA-veld), IFRA 0 = prohibited en negatief = niet nagekeken, geen databestand openen, bibliotheek met rommel, server zonder databestand (22 controles)
    python geen-variaties.py       # sinds 260915b geen variaties meer: een oud bestand met variaties laadt met één waarschuwing en houdt het veld, formulepagina, Move into…, Copy, Compare, Welcome-tegel, export en lijstteller kennen alleen versies (15 controles)
    python opslagvolgorde.py       # één schrijfactie tegelijk: wijziging tijdens een trage PUT (nagebootste server in de pagina), geen tweede PUT met dezelfde ETag, browseropslag die weigert, databestand vervangt de browserkopie; dagsnapshot bij onbereikbare server wordt niet over de serverdata geschreven, mislukte eerste schrijfactie naar een bestand (28 controles)
    python getalnotatie.py         # en-GB: duizendtalscheiding in invoervelden, parseNum, Delivered per 1000 g, IFRA-dosering per formule, Ctrl+Z onder een dialoog, Replace + Cancel, gebruiksindex na Add line; de getalvelden van de materiaalpagina en het veldrooster (21 controles)
    python uiterlijk.py           # uitvoer en uiterlijk: CSV met het scheidingsteken en de decimaal van de taal, cellen die met = beginnen, bestandsnaam met een schuine streep, witte achtergrond bij afdrukken, zachte rode kleur in beide thema's, koptekst op één regel bij 1280 px, labels aan hun veld, lijstregels met het toetsenbord, koptekst op 850 px, de kop van een formule (26 controles)
    python safari-hints.py         # Safari op de Mac: Add to Dock-link en dialoog, waarschuwing bij Download the app, alleen-lezen startscherm via file://, opslagbalk in tabblad en Dock-app, Import from Formulair op de Welcome-pagina, importer in de Dock-app (37 controles)
    python screenshots.py          # geen test: maakt de app-schermen voor docs/img (zie docstring)

Vereist `pip install playwright` en `playwright install chromium`. De paden bovenaan de
scripts (URL, SQ, referentiebestand) zijn die van de cloudsessie van 07/09/2026; pas ze aan.
