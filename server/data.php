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
if ($TOKEN === 'change-me-to-a-long-random-token') { http_response_code(500); header('Content-Type: text/plain'); echo 'data.php: set $TOKEN first'; exit; }
$DATA_DIR = __DIR__ . '/data';
$FILE     = $DATA_DIR . '/miformulas-data.json';
$SNAPDIR  = $DATA_DIR . '/snapshots';
$KEEP_DAYS = 14;

header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

function fail($code, $msg, $extra = []) {
  http_response_code($code);
  header('Content-Type: application/json; charset=utf-8');
  echo json_encode(array_merge(['error' => $msg], $extra));
  exit;
}
function etag_of($s) { return '"' . sha1($s) . '"'; }
function hdr($name) {
  $k = 'HTTP_' . strtoupper(str_replace('-', '_', $name));
  return isset($_SERVER[$k]) ? $_SERVER[$k] : '';
}

$method = $_SERVER['REQUEST_METHOD'];
if (hdr('X-Token') !== $TOKEN) fail(401, 'invalid token');

if (!is_dir($DATA_DIR)) fail(500, 'data directory missing: ' . $DATA_DIR);
if (!is_writable($DATA_DIR)) fail(500, 'data directory not writable by the web server (give the "http" user read/write on the shared folder)');

if ($method === 'GET') {
  if (isset($_GET['ping'])) {
    $cur = file_exists($FILE) ? file_get_contents($FILE) : '';
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['ok' => true, 'etag' => $cur === '' ? null : etag_of($cur), 'bytes' => strlen($cur)]);
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

  $fh = fopen($FILE . '.lock', 'c');
  if (!$fh || !flock($fh, LOCK_EX)) fail(500, 'could not lock');

  $cur = file_exists($FILE) ? file_get_contents($FILE) : '';
  $curTag = $cur === '' ? '' : etag_of($cur);
  $ifMatch = hdr('If-Match');
  if ($cur !== '' && $ifMatch !== '' && $ifMatch !== $curTag) {
    flock($fh, LOCK_UN); fclose($fh);
    fail(409, 'conflict: the data changed on another device — reload before saving', ['etag' => $curTag]);
  }

  // daily snapshot of the previous content (first write of the day)
  if ($cur !== '') {
    if (!is_dir($SNAPDIR)) @mkdir($SNAPDIR, 0775, true);
    $snap = $SNAPDIR . '/' . date('Y-m-d') . '.json';
    if (!file_exists($snap)) {
      @file_put_contents($snap, $cur);
      $files = glob($SNAPDIR . '/*.json');
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
