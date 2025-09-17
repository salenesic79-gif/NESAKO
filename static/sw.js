const CACHE_NAME = 'nesako-ai-v2.0';
const STATIC_CACHE = 'nesako-static-v2.0';
const DYNAMIC_CACHE = 'nesako-dynamic-v2.0';

// Static assets to cache immediately
const STATIC_ASSETS = [
  '/',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/login/',
  '/api/chat/'
];

// Dynamic cache patterns
const CACHE_PATTERNS = [
  /^https:\/\/api\.deepseek\.com/,
  /^https:\/\/fonts\.googleapis\.com/,
  /^https:\/\/cdnjs\.cloudflare\.com/
];

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('[SW] Installing service worker...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[SW] Static assets cached');
        return self.skipWaiting();
      })
  );
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
  console.log('[SW] Activating service worker...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW] Service worker activated');
      return self.clients.claim();
    })
  );
});

// Fetch event - network first with cache fallback
self.addEventListener('fetch', event => {
  const { request } = event;
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Handle API requests with network-first strategy
  if (request.url.includes('/api/')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Clone response for caching
          const responseClone = response.clone();
          
          // Cache successful responses
          if (response.status === 200) {
            caches.open(DYNAMIC_CACHE).then(cache => {
              cache.put(request, responseClone);
            });
          }
          
          return response;
        })
        .catch(() => {
          // Fallback to cache if network fails
          return caches.match(request).then(cachedResponse => {
            if (cachedResponse) {
              return cachedResponse;
            }
            
            // Return offline page for API failures
            return new Response(JSON.stringify({
              error: 'Offline mode',
              message: 'NESAKO AI je trenutno offline. Molim pokušajte ponovo kada se povežete na internet.',
              status: 'offline'
            }), {
              status: 503,
              headers: { 'Content-Type': 'application/json' }
            });
          });
        })
    );
    return;
  }
  
  // Handle static assets with cache-first strategy
  event.respondWith(
    caches.match(request)
      .then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }
        
        // Fetch from network and cache
        return fetch(request).then(response => {
          // Don't cache non-successful responses
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }
          
          const responseClone = response.clone();
          
          caches.open(DYNAMIC_CACHE).then(cache => {
            cache.put(request, responseClone);
          });
          
          return response;
        });
      })
      .catch(() => {
        // Return offline fallback for HTML pages
        if (request.headers.get('accept').includes('text/html')) {
          return caches.match('/').then(cachedPage => {
            return cachedPage || new Response(`
              <!DOCTYPE html>
              <html>
              <head>
                <title>NESAKO AI - Offline</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                  body { 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px;
                    background: #1a1a2e;
                    color: white;
                  }
                  .offline-icon { font-size: 64px; margin-bottom: 20px; }
                  .retry-btn {
                    background: #16213e;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                    margin-top: 20px;
                  }
                </style>
              </head>
              <body>
                <div class="offline-icon">📱</div>
                <h1>NESAKO AI</h1>
                <h2>Offline Mode</h2>
                <p>Trenutno ste offline. Molim proverite internet konekciju.</p>
                <button class="retry-btn" onclick="location.reload()">Pokušaj ponovo</button>
              </body>
              </html>
            `, {
              headers: { 'Content-Type': 'text/html' }
            });
          });
        }
        
        return new Response('Offline', { status: 503 });
      })
  );
});

// Background sync for offline actions
self.addEventListener('sync', event => {
  console.log('[SW] Background sync:', event.tag);
  
  if (event.tag === 'chat-sync') {
    event.waitUntil(syncOfflineChats());
  }
});

// Push notifications
self.addEventListener('push', event => {
  console.log('[SW] Push received:', event);
  
  const options = {
    body: event.data ? event.data.text() : 'Nova poruka od NESAKO AI',
    icon: '/static/icon-192.png',
    badge: '/static/icon-192.png',
    vibrate: [200, 100, 200],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'open',
        title: 'Otvori chat',
        icon: '/static/icon-192.png'
      },
      {
        action: 'close',
        title: 'Zatvori'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('NESAKO AI', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notification click:', event);
  
  event.notification.close();
  
  if (event.action === 'open') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Sync offline chats when back online
async function syncOfflineChats() {
  try {
    const cache = await caches.open(DYNAMIC_CACHE);
    const requests = await cache.keys();
    
    for (const request of requests) {
      if (request.url.includes('/api/chat/') && request.method === 'POST') {
        try {
          await fetch(request);
          await cache.delete(request);
          console.log('[SW] Synced offline chat');
        } catch (error) {
          console.log('[SW] Failed to sync chat:', error);
        }
      }
    }
  } catch (error) {
    console.log('[SW] Sync error:', error);
  }
}

// Cache management
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => caches.delete(cacheName))
        );
      })
    );
  }
});
