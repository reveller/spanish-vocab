// Service worker for offline study support.
//
// Strategy: keep the app fresh when online, fully usable for studying when
// offline (read-only). The user logs in once on connectivity (StarLink); the
// session cookie persists in the browser, so offline navigations are served the
// cached app shell and lessons load from the cached /api/lessons response — no
// server round-trip needed.
//
// Note: if the Flask session cookie expires while offline, re-login requires
// connectivity. Acceptable for this use case.

const CACHE = 'vocab-v1';
const SHELL = ['/'];

const FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// Network-first: try the network, cache the fresh response, fall back to cache.
async function networkFirst(request, fallbackKey) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response && response.ok) {
      cache.put(fallbackKey || request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await cache.match(fallbackKey || request);
    if (cached) return cached;
    throw err;
  }
}

// Cache-first: serve from cache, otherwise fetch and store (for immutable fonts).
async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response && (response.ok || response.type === 'opaque')) {
    cache.put(request, response.clone());
  }
  return response;
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // App shell: serve cached '/' when the network is unreachable.
  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, '/'));
    return;
  }

  // Lesson data: fresh online, last-known copy offline.
  if (request.method === 'GET' && url.pathname === '/api/lessons') {
    event.respondWith(networkFirst(request));
    return;
  }

  // Google Fonts (CSS + font files) are immutable — cache once, reuse forever.
  if (FONT_HOSTS.includes(url.hostname)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Writes (progress, add/delete): pass through, but resolve with a clear
  // offline signal instead of throwing so the UI can degrade gracefully.
  if (request.method !== 'GET') {
    event.respondWith(
      fetch(request).catch(() => new Response(
        JSON.stringify({ offline: true }),
        { status: 503, headers: { 'Content-Type': 'application/json' } }
      ))
    );
    return;
  }

  // Everything else: network, falling back to any cached copy.
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});
