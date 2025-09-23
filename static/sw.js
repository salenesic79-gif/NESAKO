// Simple Service Worker for NESAKO AI
const CACHE_NAME = 'nesako-ai-v4';
const urlsToCache = [
  '/',
  '/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// Install event
self.addEventListener('install', function(event) {
  console.log('[SW] Installing Service Worker');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('[SW] Caching app shell');
        return cache.addAll(urlsToCache);
      })
      .then(function() {
        console.log('[SW] Skip waiting on install');
        return self.skipWaiting();
      })
  );
});

// Activate event
self.addEventListener('activate', function(event) {
  console.log('[SW] Activating Service Worker');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(function() {
      console.log('[SW] Claiming clients');
      return self.clients.claim();
    })
  );
});

// Fetch event
self.addEventListener('fetch', function(event) {
  // Skip API requests and POST requests
  if (event.request.url.includes('/api/') || event.request.method === 'POST') {
    return fetch(event.request);
  }
  
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Cache hit - return response
        if (response) {
          return response;
        }
        
        // Clone the request
        var fetchRequest = event.request.clone();
        
        return fetch(fetchRequest).then(function(response) {
          // Check if valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }
          
          // Clone the response
          var responseToCache = response.clone();
          
          caches.open(CACHE_NAME)
            .then(function(cache) {
              cache.put(event.request, responseToCache);
            });
          
          return response;
        }).catch(function(error) {
          console.log('[SW] Fetch failed:', error);
          // Return offline page for HTML requests
          if (event.request.headers.get('accept').includes('text/html')) {
            return caches.match('/').then(function(cachedResponse) {
              return cachedResponse || new Response(
                '<html><body><h1>Offline</h1><p>Molim proverite internet konekciju.</p></body></html>',
                { headers: { 'Content-Type': 'text/html' } }
              );
            });
          }
        });
      })
  );
});

// Simple message handler
self.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
