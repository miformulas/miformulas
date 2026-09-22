<?php
/* miFormulas data endpoint - read/write miformulas-data.json with a conflict guard and daily snapshots.
   Part of miFormulas, GPL v3 with additional terms, see LICENSE and NOTICE.

   GET  data.php            -> JSON body, header ETag
   PUT  data.php            -> body = JSON, headers X-Token, If-Match (ETag from load); 409 on conflict
   GET  data.php?ping=1     -> {"ok":true,"etag":...}

   Setup: put this file next to index.html, create a folder "data" beside it that the web server
   may write to, and put your miformulas-data.json in it. Choose a long random token below; the app
   asks for it once per device (Settings, or when it first connects). */

$TOKEN    = 'change-me-to-a-long-random-token';
// The web server serves this folder as well: a browser that asks for data/miformulas-data.json gets the whole
// file, token or no token, because the token only guards this script. Safest is a folder OUTSIDE the web root,
// for instance dirname(__DIR__) . '/miformulas-data'; the default below keeps older setups working and is
// protected with an .htaccess (Apache only), written on the first save when none is there. ?ping=1 tells you
// which of the two you have.
$DATA_DIR = __DIR__ . '/data';
$FILE     = $DATA_DIR . '/miformulas-data.json';
$SNAPDIR  = $DATA_DIR . '/snapshots';
$KEEP_DAYS = 14;

header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
// The same CORS block as server/worker.js, so the endpoint also works on another address than the app.
// Expose-Headers matters: without the ETag the app cannot see it and its conflict guard is off.
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, PUT, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, X-Token, If-Match');
header('Access-Control-Expose-Headers: ETag');
header('Access-Control-Max-Age: 86400');

function fail($code, $msg, $extra = []) {
  http_response_code($code);
  header('Content-Type: application/json; charset=utf-8');
  echo json_encode(array_merge(['error' => $msg], $extra));
  exit;
}
function etag_of($s) { return '"' . sha1($s) . '"'; }
// A web server that compresses the response may weaken the ETag to W/"..."; the app sends that back in
// If-Match. Compare without W/ and without quotes, exactly as server/worker.js does.
function norm_tag($e) { $e = trim((string)$e); $e = preg_replace('/^W\//i', '', $e); return preg_replace('/^"|"$/', '', $e); }
function same_tag($a, $b) { return norm_tag($a) === norm_tag($b); }
function hdr($name) {
  $k = 'HTTP_' . strtoupper(str_replace('-', '_', $name));
  return isset($_SERVER[$k]) ? $_SERVER[$k] : '';
}

// A folder that a browser can fetch straight from the web is worth a lock of its own on Apache; harmless
// elsewhere, and no substitute for putting the folder outside the web root.
function guard_dir($dir) {
  $f = $dir . '/.htaccess';
  if (is_dir($dir) && !file_exists($f)) @file_put_contents($f,
    "# miFormulas: this folder holds your data file and its snapshots, and nothing here belongs on the web.\n"
    . "<IfModule mod_authz_core.c>\n  Require all denied\n</IfModule>\n"
    . "<IfModule !mod_authz_core.c>\n  Order allow,deny\n  Deny from all\n</IfModule>\n");
}
function in_web_root($dir) {
  $root = isset($_SERVER['DOCUMENT_ROOT']) ? realpath($_SERVER['DOCUMENT_ROOT']) : '';
  $d = realpath($dir);
  if ($root === '' || $root === false || $d === false) return false;
  // A bare prefix reads /var/www/html-data as "inside /var/www/html": compare on the folder boundary.
  $root = rtrim($root, '/\\');
  if ($root === '') return true;                                     // the web root is the root of the file system
  $sep = strpos($d, '\\') !== false ? '\\' : '/';
  return $d === $root || strncmp($d, $root . $sep, strlen($root) + 1) === 0;
}

$method = $_SERVER['REQUEST_METHOD'];
// The preflight of a browser carries no headers of its own, so it can never bring a token: answer it first.
if ($method === 'OPTIONS') { http_response_code(204); exit; }
// The same order as server/worker.js: the preflight first, then this guard, so the CORS headers above are
// already sent and the app can read the message from another address instead of a bare CORS error.
if ($TOKEN === 'change-me-to-a-long-random-token') fail(500, 'data.php: set $TOKEN first');
if (!hash_equals($TOKEN, hdr('X-Token'))) fail(401, 'invalid token');   // constant time, so the token cannot be guessed by the clock

if (!is_dir($DATA_DIR)) fail(500, 'data directory missing: ' . $DATA_DIR);
if (!is_writable($DATA_DIR)) fail(500, 'data directory not writable by the web server (give the "http" user read/write on the shared folder)');

if ($method === 'GET') {
  if (isset($_GET['ping'])) {
    $cur = file_exists($FILE) ? file_get_contents($FILE) : '';
    guard_dir($DATA_DIR);
    header('Content-Type: application/json; charset=utf-8');
    // the last two say whether your data folder is reachable from the web: see the note at $DATA_DIR
    echo json_encode(['ok' => true, 'etag' => $cur === '' ? null : etag_of($cur), 'bytes' => strlen($cur),
                      'dataDirInWebRoot' => in_web_root($DATA_DIR), 'htaccess' => file_exists($DATA_DIR . '/.htaccess')]);
    exit;
  }
  if (!file_exists($FILE)) fail(404, 'no data file yet');
  $cur = file_get_contents($FILE);
  header('Content-Type: application/json; charset=utf-8');
  header('ETag: ' . etag_of($cur));
  echo $cur;
  exit;
}

if ($method === 'PUT' || $method === 'POST') {
  $body = file_get_contents('php://input');
  if ($body === '' || $body === false) fail(400, 'empty body');
  $decoded = json_decode($body, true);
  if (!is_array($decoded) || !isset($decoded['materials']) || !isset($decoded['formulas'])) fail(400, 'body is not a miFormulas data file');

  guard_dir($DATA_DIR);   // the lock file below lands in that folder as well
  $fh = fopen($FILE . '.lock', 'c');
  if (!$fh || !flock($fh, LOCK_EX)) fail(500, 'could not lock');

  $cur = file_exists($FILE) ? file_get_contents($FILE) : '';
  $curTag = $cur === '' ? '' : etag_of($cur);
  $ifMatch = hdr('If-Match');
  if ($cur !== '' && $ifMatch !== '' && !same_tag($ifMatch, $curTag)) {
    flock($fh, LOCK_UN); fclose($fh);
    fail(409, 'conflict: the data changed on another device – reload before saving', ['etag' => $curTag]);
  }

  // daily snapshot of the previous content (first write of the day)
  if ($cur !== '') {
    if (!is_dir($SNAPDIR)) @mkdir($SNAPDIR, 0775, true);
    $snap = $SNAPDIR . '/' . date('Y-m-d') . '.json';
    if (!file_exists($snap)) {
      @file_put_contents($snap, $cur);
      // only the daily files count: a backup you put in this folder by hand used to eat a day, or be deleted first
      $files = array_values(array_filter((array)glob($SNAPDIR . '/*.json'),
        function ($f) { return preg_match('/^\d{4}-\d{2}-\d{2}\.json$/', basename($f)); }));
      if ($files) { sort($files); while (count($files) > $KEEP_DAYS) { @unlink(array_shift($files)); } }
    }
  }

  $tmp = $FILE . '.tmp';
  if (file_put_contents($tmp, $body) === false) { flock($fh, LOCK_UN); fclose($fh); fail(500, 'write failed'); }
  if (!rename($tmp, $FILE)) { @unlink($tmp); flock($fh, LOCK_UN); fclose($fh); fail(500, 'rename failed'); }
  flock($fh, LOCK_UN); fclose($fh);

  $newTag = etag_of($body);
  header('Content-Type: application/json; charset=utf-8');
  header('ETag: ' . $newTag);
  echo json_encode(['ok' => true, 'etag' => $newTag, 'bytes' => strlen($body), 'saved' => date('c')]);
  exit;
}

fail(405, 'method not allowed');
