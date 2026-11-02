// Service worker: lets the installed app open offline, while always fetching the newest version when online.
// The game page is network-first (updates show on the next launch); assets and libraries are cached after first use.
const CACHE = 'curve-kings-v1';

self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const isPage = req.mode === 'navigate' || req.url.endsWith('/index.html');
  if (isPage) {
    e.respondWith(
      fetch(req).then(res => { caches.open(CACHE).then(c => c.put(req, res.clone())); return res; })
        .catch(() => caches.match(req).then(r => r || caches.match('./')))
    );
    return;
  }
  e.respondWith(
    caches.match(req).then(hit => {
      const net = fetch(req).then(res => {
        if (res.ok || res.type === 'opaque') caches.open(CACHE).then(c => c.put(req, res.clone()));
        return res;
      });
      return hit || net; // cached copy instantly; refresh it in the background
    })
  );
});
