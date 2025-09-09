// Service Worker for PaperIgnition PWA
const CACHE_NAME = 'paperignition-v1.0.0';
const STATIC_CACHE = 'paperignition-static-v1';
const DYNAMIC_CACHE = 'paperignition-dynamic-v1';

// Files to cache on install
const STATIC_FILES = [
    '/',
    '/index.html',
    '/login.html',
    '/register.html',
    '/profile.html',
    '/paper.html',
    '/test.html',
    '/config.js',
    '/js/auth.js',
    '/js/main.js',
    '/manifest.json'
];

// API endpoints to cache dynamically
const API_CACHE_PATTERNS = [
    /^.*\/api\/papers\/recommendations\/.*/,
    /^.*\/api\/papers\/paper_content\/.*/,
    /^.*\/api\/users\/me.*/
];

// Install event - cache static files
self.addEventListener('install', (event) => {
    console.log('SW: Installing service worker...');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('SW: Caching static files');
                return cache.addAll(STATIC_FILES);
            })
            .then(() => {
                console.log('SW: Static files cached successfully');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('SW: Failed to cache static files:', error);
            })
    );
});

// Activate event - cleanup old caches
self.addEventListener('activate', (event) => {
    console.log('SW: Activating service worker...');
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((cacheName) => {
                            return cacheName.startsWith('paperignition-') && 
                                   cacheName !== STATIC_CACHE && 
                                   cacheName !== DYNAMIC_CACHE;
                        })
                        .map((cacheName) => {
                            console.log('SW: Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        })
                );
            })
            .then(() => {
                console.log('SW: Service worker activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - serve cached files or fetch from network
self.addEventListener('fetch', (event) => {
    const request = event.request;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Handle API requests
    if (isApiRequest(request.url)) {
        event.respondWith(handleApiRequest(request));
        return;
    }

    // Handle static file requests
    event.respondWith(handleStaticRequest(request));
});

// Check if request is for API
function isApiRequest(url) {
    return url.includes('/api/') || API_CACHE_PATTERNS.some(pattern => pattern.test(url));
}

// Handle API requests with network-first strategy
async function handleApiRequest(request) {
    try {
        // Try network first
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Cache successful API responses
            const cache = await caches.open(DYNAMIC_CACHE);
            await cache.put(request, networkResponse.clone());
            return networkResponse;
        } else {
            // If network fails, try cache
            const cachedResponse = await caches.match(request);
            return cachedResponse || networkResponse;
        }
    } catch (error) {
        console.log('SW: Network failed, trying cache for:', request.url);
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline page for failed requests
        return new Response(
            JSON.stringify({
                error: 'Offline',
                message: 'This content is not available offline'
            }),
            {
                status: 503,
                statusText: 'Service Unavailable',
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Handle static file requests with cache-first strategy
async function handleStaticRequest(request) {
    try {
        // Try cache first
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }

        // If not in cache, fetch from network
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Cache the response for next time
            const cache = await caches.open(DYNAMIC_CACHE);
            await cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.error('SW: Failed to fetch:', request.url, error);
        
        // Return offline fallback
        if (request.destination === 'document') {
            return caches.match('/index.html');
        }
        
        return new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable'
        });
    }
}

// Background sync for offline actions
self.addEventListener('sync', (event) => {
    console.log('SW: Background sync triggered:', event.tag);
    
    if (event.tag === 'bookmark-sync') {
        event.waitUntil(syncBookmarks());
    }
});

// Sync bookmarks when back online
async function syncBookmarks() {
    try {
        const bookmarks = localStorage.getItem('pendingBookmarks');
        if (bookmarks) {
            const bookmarkList = JSON.parse(bookmarks);
            // Sync bookmarks with server
            // Implementation depends on API design
            localStorage.removeItem('pendingBookmarks');
            console.log('SW: Bookmarks synced successfully');
        }
    } catch (error) {
        console.error('SW: Failed to sync bookmarks:', error);
    }
}

// Push notifications (placeholder)
self.addEventListener('push', (event) => {
    console.log('SW: Push notification received');
    
    const options = {
        body: event.data ? event.data.text() : 'New papers available!',
        icon: '/icon-192x192.png',
        badge: '/icon-96x96.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'View Papers',
                icon: '/icon-96x96.png'
            },
            {
                action: 'close',
                title: 'Close',
                icon: '/icon-96x96.png'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification('PaperIgnition', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});