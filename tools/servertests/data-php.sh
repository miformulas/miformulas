#!/usr/bin/env bash
# Server test for server/data.php: the endpoint for a shared folder on a web server of your own.
# Needs php and curl, and nothing else: the script copies data.php into a temporary folder, serves it
# with php -S on localhost and walks the whole endpoint with curl. What it walks: the guard on an
# unedited token, a missing data folder, the preflight and the CORS headers, the token, ?ping=1 with
# its report on the data folder, reading, the gate in front of a write, the byte count, the conflict
# guard with a weak etag, and the daily snapshots with their trimming.
#
#     bash data-php.sh [path to data.php]
#
# Part of miFormulas, GPL v3 with additional terms, see LICENSE and NOTICE.
set -u

SRC="${1:-$(cd "$(dirname "$0")/../../server" && pwd)/data.php}"
[ -f "$SRC" ] || { echo "not found: $SRC"; exit 2; }
command -v php  >/dev/null || { echo "php is not installed"; exit 2; }
command -v curl >/dev/null || { echo "curl is not installed"; exit 2; }

TOKEN="a-long-random-token-for-the-test"
TMP="$(mktemp -d)"
OUT="$TMP/outside"          # a data folder outside the web root, for the report of ?ping=1
PHPPID=""
cleanup() { [ -n "$PHPPID" ] && kill "$PHPPID" 2>/dev/null; rm -rf "$TMP"; }
trap cleanup EXIT

mkdir -p "$TMP/web/data" "$OUT"
cp "$SRC" "$TMP/web/raw.php"                                       # untouched: its token is still the default
sed "s/^\$TOKEN    = '.*';/\$TOKEN    = '$TOKEN';/" "$SRC" > "$TMP/web/data.php"
sed "s#^\$DATA_DIR = .*#\$DATA_DIR = '$OUT';#" "$TMP/web/data.php" > "$TMP/web/outside.php"
sed "s#^\$DATA_DIR = .*#\$DATA_DIR = '$TMP/gone';#" "$TMP/web/data.php" > "$TMP/web/nodir.php"
grep -q "^\$TOKEN    = '$TOKEN';" "$TMP/web/data.php" || { echo "could not set the token in the copy"; exit 2; }

# A port can already be taken by something else, and php -S then fails to bind while the probe still
# gets an answer: the whole run would test that other server. So the probe asks for a marker only this
# copy serves, and checks that php itself is still alive.
MARKER="miformulas-servertest-$$-$TOKEN"
printf '%s' "$MARKER" > "$TMP/web/marker.txt"
PORT=""
for p in $(seq 8799 8809); do
  php -S "127.0.0.1:$p" -t "$TMP/web" >"$TMP/php.log" 2>&1 &
  PHPPID=$!
  sleep 1
  if kill -0 "$PHPPID" 2>/dev/null &&
     [ "$(curl -sS --noproxy '*' "http://127.0.0.1:$p/marker.txt" 2>/dev/null)" = "$MARKER" ]; then PORT="$p"; break; fi
  kill "$PHPPID" 2>/dev/null; PHPPID=""
done
[ -n "$PORT" ] || { echo "could not start php -S (see $TMP/php.log)"; exit 2; }
BASE="http://127.0.0.1:$PORT"
DIR="$TMP/web/data"
SNAP="$DIR/snapshots"

ok=0; fail=0
pass() { ok=$((ok+1)); echo "OK   $1"; }
flop() { fail=$((fail+1)); echo "FAIL $1${2+  <- $2}"; }
is()   { if [ "$2" = "$3" ]; then pass "$1"; else flop "$1" "expected [$2], got [$3]"; fi; }
has()  { case "$3" in *"$2"*) pass "$1";; *) flop "$1" "no [$2] in [$(echo "$3" | head -c 200)]";; esac; }
hasnt(){ case "$3" in *"$2"*) flop "$1" "found [$2]";; *) pass "$1";; esac; }

# req <method> <path> [curl args...]  ->  CODE, BODY, HEAD
req() {
  local m="$1" p="$2"; shift 2
  CODE=$(curl -sS --noproxy '*' -X "$m" -H 'Expect:' -o "$TMP/body" -D "$TMP/head" -w '%{http_code}' "$BASE$p" "$@" 2>/dev/null)
  BODY=$(cat "$TMP/body"); HEAD=$(cat "$TMP/head")
}
etag() { echo "$HEAD" | tr -d '\r' | sed -n 's/^[Ee][Tt][Aa][Gg]: //p'; }

DATA='{"materials":[{"name":"Crème"}],"formulas":[]}'              # the accent is the point: bytes are not characters
DATA2='{"materials":[{"name":"Iso E"}],"formulas":[{"name":"Test"}]}'
printf '%s' "$DATA"  > "$TMP/data.json"
printf '%s' "$DATA2" > "$TMP/data2.json"
BYTES=$(wc -c < "$TMP/data.json" | tr -d ' ')

# ---------- 1. the two setup mistakes ----------
req GET /raw.php
is   "an unedited token is refused" "500" "$CODE"
has  "and it says which line to edit" 'set $TOKEN first' "$BODY"
req GET "/nodir.php" -H "X-Token: $TOKEN"
is   "a missing data folder is 500" "500" "$CODE"
has  "and it names the folder it looked for" "data directory missing" "$BODY"

# ---------- 2. the preflight and the CORS headers ----------
req OPTIONS /data.php
is   "OPTIONS answers 204 without a token" "204" "$CODE"
has  "OPTIONS carries Allow-Origin" "Access-Control-Allow-Origin: *" "$HEAD"
has  "OPTIONS allows the methods the app uses" "Access-Control-Allow-Methods: GET, PUT, POST, OPTIONS" "$HEAD"
has  "OPTIONS allows the token header" "X-Token" "$HEAD"
has  "OPTIONS allows If-Match" "If-Match" "$HEAD"
has  "OPTIONS exposes the ETag (without it the conflict guard is off)" "Access-Control-Expose-Headers: ETag" "$HEAD"

# ---------- 3. the token ----------
req GET /data.php
is   "no token at all is 401" "401" "$CODE"
has  "and it says why" "invalid token" "$BODY"
req GET /data.php -H "X-Token: wrong"
is   "a wrong token is 401" "401" "$CODE"
hasnt "the refusal does not carry the token" "$TOKEN" "$BODY"

# ---------- 4. ?ping=1 and the data folder ----------
rm -f "$DIR/.htaccess"
req GET "/data.php?ping=1" -H "X-Token: $TOKEN"
is   "?ping=1 answers" "200" "$CODE"
has  "an empty folder reports no etag and no bytes" '"etag":null,"bytes":0' "$BODY"
has  "?ping=1 reports the .htaccess it just wrote" '"htaccess":true' "$BODY"
[ -f "$DIR/.htaccess" ] && pass "the .htaccess is really there" || flop "the .htaccess is really there"
has  "and it denies everything" "Require all denied" "$(cat "$DIR/.htaccess" 2>/dev/null)"
has  "the default folder is reported as reachable from the web" '"dataDirInWebRoot":true' "$BODY"
req GET "/outside.php?ping=1" -H "X-Token: $TOKEN"
has  "a folder outside the web root is reported as safe" '"dataDirInWebRoot":false' "$BODY"

# ---------- 5. the gate in front of a write ----------
req GET /data.php -H "X-Token: $TOKEN"
is   "reading before there is a file is 404, not a crash" "404" "$CODE"
req PUT /data.php -H "X-Token: $TOKEN" --data-binary ""
is   "an empty body is refused" "400" "$CODE"
req PUT /data.php -H "X-Token: $TOKEN" --data-binary 'not json at all'
is   "a body that is not JSON is refused" "400" "$CODE"
req PUT /data.php -H "X-Token: $TOKEN" --data-binary '{"notes":"materials and formulas belong in here"}'
is   "a JSON object that only mentions the words is refused" "400" "$CODE"
[ -f "$DIR/miformulas-data.json" ] && flop "none of the refusals made a data file" || pass "none of the refusals made a data file"

# ---------- 6. writing, reading back, and the byte count ----------
req PUT /data.php -H "X-Token: $TOKEN" --data-binary "@$TMP/data.json"
is   "a good body is written" "200" "$CODE"
has  "the answer says ok" '"ok":true' "$BODY"
TAG=$(etag)
case "$TAG" in \"*\") pass "the answer carries an ETag header";; *) flop "the answer carries an ETag header" "[$TAG]";; esac
has  "bytes is the real byte count, not the number of characters" "\"bytes\":$BYTES" "$BODY"
cmp -s "$TMP/data.json" "$DIR/miformulas-data.json" && pass "the file on disk is byte for byte what was sent" || flop "the file on disk is byte for byte what was sent"
req GET /data.php -H "X-Token: $TOKEN"
is   "reading gives it back" "200" "$CODE"
is   "with the same ETag" "$TAG" "$(etag)"
is   "and the same bytes" "$DATA" "$BODY"

# ---------- 7. the conflict guard ----------
req PUT /data.php -H "X-Token: $TOKEN" -H 'If-Match: "0000000000000000000000000000dead"' --data-binary "@$TMP/data2.json"
is   "a stale If-Match is 409" "409" "$CODE"
has  "and it hands back the etag to reload with" "$(echo "$TAG" | tr -d '\"')" "$BODY"
cmp -s "$TMP/data.json" "$DIR/miformulas-data.json" && pass "the data did not change" || flop "the data did not change"
req PUT /data.php -H "X-Token: $TOKEN" -H "If-Match: W/$TAG" --data-binary "@$TMP/data2.json"
is   "the weak form of the same etag is accepted" "200" "$CODE"
cmp -s "$TMP/data2.json" "$DIR/miformulas-data.json" && pass "and that write landed" || flop "and that write landed"

# ---------- 8. the daily snapshots ----------
rm -rf "$SNAP"
req PUT /data.php -H "X-Token: $TOKEN" --data-binary "@$TMP/data.json"
LAST=$(ls "$SNAP" 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}\.json$' | sort | tail -1)
cmp -s "$TMP/data2.json" "$SNAP/$LAST" 2>/dev/null && pass "the first write of the day keeps the previous content" || flop "the first write of the day keeps the previous content" "$LAST"
req PUT /data.php -H "X-Token: $TOKEN" --data-binary "@$TMP/data2.json"
cmp -s "$TMP/data2.json" "$SNAP/$LAST" 2>/dev/null && pass "a second write the same day leaves that snapshot alone" || flop "a second write the same day leaves that snapshot alone"

rm -f "$SNAP"/*.json
for d in $(seq -w 1 16); do printf 'old %s' "$d" > "$SNAP/2026-01-$d.json"; done
printf 'mine' > "$SNAP/my own backup.json"
req PUT /data.php -H "X-Token: $TOKEN" --data-binary "@$TMP/data.json"
N=$(ls "$SNAP" | grep -cE '^[0-9]{4}-[0-9]{2}-[0-9]{2}\.json$')
is   "trimming keeps fourteen daily files" "14" "$N"
[ -f "$SNAP/2026-01-03.json" ] && flop "the oldest three are gone" || pass "the oldest three are gone"
[ -f "$SNAP/2026-01-04.json" ] && pass "and the fourth is not" || flop "and the fourth is not"
[ -f "$SNAP/my own backup.json" ] && pass "a backup you put there by hand survives" || flop "a backup you put there by hand survives"

# ---------- 9. anything else ----------
req DELETE /data.php -H "X-Token: $TOKEN"
is   "a method the endpoint does not know is 405" "405" "$CODE"

echo ""
echo "$ok OK, $fail FAIL"
[ "$fail" = "0" ] || exit 1
