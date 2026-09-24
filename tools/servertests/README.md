# Servertests

De twee data-endpoints van `server\` krijgen hun eigen tests, want de browsertests draaien tegen een
nagebootste server in de pagina en raken de echte code nooit. Geen netwerk, geen Cloudflare-account
en geen webserver nodig: beide tests zetten hun eigen omgeving op en breken ze weer af.

    node worker.mjs        # server\worker.js met een nagemaakte R2-bak (53 controles)
    bash data-php.sh       # server\data.php achter php -S, met curl (67 controles)

`worker.mjs` bootst R2 na met echte etag- en uploadtijdsemantiek en stuurt de geëxporteerde
`fetch()` rechtstreeks aan: de preflight, de twee opzetfouten (geen TOKEN, geen DATA), het token,
`?ping=1`, lezen, de sluis voor een schrijfactie, het bytegetal, de conflictwacht met een zwakke
etag, de wedloop die een voorwaardelijke schrijfactie moet overleven, en de dagsnapshots met hun
opruiming, en de ene publieke route (de bibliotheek zonder token).

`data-php.sh` kopieert `data.php` naar een tijdelijke map, zet het token, bedient het met `php -S` op
localhost en loopt het endpoint af met curl: de wacht op een onaangepast token (ook na Vervang alles
in een editor, en een leeg token), een ontbrekende datamap, de preflight en de CORS-koppen, het token,
`?ping=1` met zijn verslag over de datamap (`dataDirInWebRoot`, `htaccess`, ook voor een koppeling
naar een map elders), lezen, de sluis, het bytegetal, de conflictwacht, de snapshots, een databestand
dat een koppeling is, en een dagsnapshot die niet past: een tweede `php -S` met `ulimit -f` staat voor
een volle schijf, zodat daar geen root voor nodig is.

Vereist `node` (22 of hoger) voor de eerste, `php` en `curl` voor de tweede. Beide geven exitcode 1
bij een fout, dus ze kunnen zonder meer in een reeks. Een pad als argument test een andere kopie:

    node worker.mjs ../../deploy/worker.js
    bash data-php.sh /pad/naar/data.php
