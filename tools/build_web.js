// Packages the game as an installable web app in dist/ (ready for any static host, e.g. GitHub Pages).
// Usage: node tools/build_web.js
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..'), dist = path.join(root, 'dist');
fs.rmSync(dist, { recursive: true, force: true });
fs.mkdirSync(path.join(dist, 'assets'), { recursive: true });

const game = fs.readFileSync(path.join(root, 'curve-kings.html'), 'utf8');
const head = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#0b1324">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Curve Kings">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon-192.png">
<link rel="apple-touch-icon" href="icon-192.png">
<style>:root{padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)}</style>
`;
const tail = `
<script>
if ('serviceWorker' in navigator) addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
</script>
</body>
</html>
`;
// the game file starts with its own <title>/<style>; everything after the first <canvas> is body content
const split = game.indexOf('<canvas id="game">');
const html = head + game.slice(0, split) + '</head>\n<body>\n' + game.slice(split) + tail;
fs.writeFileSync(path.join(dist, 'index.html'), html);

for (const f of ['manifest.webmanifest', 'sw.js', 'icon-192.png', 'icon-512.png']) fs.copyFileSync(path.join(root, 'app', f), path.join(dist, f));
for (const f of fs.readdirSync(path.join(root, 'assets'))) fs.copyFileSync(path.join(root, 'assets', f), path.join(dist, 'assets', f));
// tell GitHub Pages not to run Jekyll on the files
fs.writeFileSync(path.join(dist, '.nojekyll'), '');
const size = fs.readdirSync(dist, { recursive: true }).reduce((s, f) => { const p = path.join(dist, f); return s + (fs.statSync(p).isFile() ? fs.statSync(p).size : 0); }, 0);
console.log(`dist/ ready (${(size / 1e6).toFixed(2)} MB)`);
