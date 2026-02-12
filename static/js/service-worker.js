/**
 * MUFRA FASHIONS - Service Worker
 * Enables offline functionality, caching, and PWA features
 */

const CACHE_NAME = 'mufra-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/script.js',
  '/static/images/logo.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap'
];

const DYNAMIC_CACHE = 'mufra-dynamic-v1';
const OFFLINE_PAGE = '/';

// Install service worker and cache static assets
self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Caching static assets');
        // Cache only critical assets to avoid bloat
        return cache.addAll([
          '/',
          '/static/css/style.css',
          '/static/js/script.js',
          '/static/images/logo.png'
        ]).catch((err) => {
          console.log('Error caching static assets:', err);
        });
      })
      .then(() => self.skipWaiting())
  );
});

// Activate service worker and cleanup old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== DYNAMIC_CACHE) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Don't cache API calls, form submissions, or external requests
  if (request.method !== 'GET' || url.hostname !== location.hostname) {
    return;
  }
  
  // Strategy: Cache first for assets, Network first for pages
  if (request.url.includes('/static/') || request.url.includes('.css') || request.url.includes('.js')) {
    // Cache first strategy for static assets
    event.respondWith(
      caches.match(request)
        .then((response) => {
          if (response) {
            return response;
          }
          return fetch(request)
            .then((response) => {
              // Clone and cache successful responses
              if (!response || response.status !== 200 || response.type === 'error') {
                return response;
              }
              const responseToCache = response.clone();
              caches.open(DYNAMIC_CACHE)
                .then((cache) => {
                  cache.put(request, responseToCache);
                });
              return response;
            })
            .catch(() => {
              // Return offline page if fetch fails
              return caches.match(OFFLINE_PAGE)
                .then((response) => response || new Response('Offline'));
            });
        })
    );
  } else {
    // Network first strategy for pages and dynamic content
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Clone and cache successful responses
          if (response && response.status === 200) {
            const responseToCache = response.clone();
            caches.open(DYNAMIC_CACHE)
              .then((cache) => {
                cache.put(request, responseToCache);
              });
          }
          return response;
        })
        .catch(() => {
          // Return cached version or offline page
          return caches.match(request)
            .then((response) => {
              return response || caches.match(OFFLINE_PAGE);
            });
        })
    );
  }
});

// Handle push notifications (for future feature)
self.addEventListener('push', (event) => {
  const options = {
    body: event.data ? event.data.text() : 'New update from MUFRA FASHIONS',
    icon: '/static/images/logo.png',
    badge: '/static/images/logo.png',
    tag: 'mufra-notification',
    requireInteraction: false
  };
  
  event.waitUntil(
    self.registration.showNotification('MUFRA FASHIONS', options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window' })
      .then((clientList) => {
        // Check if app is already open
        for (let i = 0; i < clientList.length; i++) {
          const client = clientList[i];
          if (client.url === '/' && 'focus' in client) {
            return client.focus();
          }
        }
        // Open new window if app is not running
        if (clients.openWindow) {
          return clients.openWindow('/');
        }
      })
  );
});

// Background sync for offline actions (cart updates, etc.)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-cart') {
    event.waitUntil(
      // Sync cart data when back online
      fetch('/sync-cart', { method: 'POST' })
        .catch(() => {
          console.log('Cart sync failed, will retry when online');
        })
    );
  }
});

console.log('Service Worker loaded successfully');
