# Browsertests (Playwright, Chromium)

Draaien tegen een lokale webserver met de inhoud van `public\` op poort 8765:

    cd public && python -m http.server 8765
    python demo-flow.py            # startscherm, starterset, autosave, labels, Settings, herbezoek, server, reset (27 controles)
    python migratie-en-file.py     # bestaand token zonder serverUrl -> data.php; geen token in de HTML; file:// -> bestandsmodus
    python opslagbalk.py           # balk bij niet-persistente browseropslag, tekstvarianten, sluiten, sessie
    python formulair-import.py     # DataModel.sqlite inlezen, download vergelijken met formulair-naar-json.py (pad SQ aanpassen)
    python formulair-doorsturen.py # "Open in miFormulas in this browser" -> app start met 698 formules
    python file-mode.py            # gedownloade app via file://: hint, starterset van miformulas.com (nagebootst), databestand aanmaken (29 controles; geen webserver nodig)

Vereist `pip install playwright` en `playwright install chromium`. De paden bovenaan de
scripts (URL, SQ, referentiebestand) zijn die van de cloudsessie van 07/09/2026; pas ze aan.
