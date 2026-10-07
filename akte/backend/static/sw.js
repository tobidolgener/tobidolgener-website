/* Service Worker: Push anzeigen, Klick oeffnet die passende Seite. Kein Offline-Cache (Daten immer frisch). */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('push', (e) => {
  let d = { titel: 'AKTE', text: '', url: '/' };
  try { d = Object.assign(d, e.data.json()); } catch (_) { d.text = e.data ? e.data.text() : ''; }
  e.waitUntil(self.registration.showNotification(d.titel, { body: d.text, icon: '/static/icon-192.png', badge: '/static/icon-192.png', data: { url: d.url } }));
});
self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || '/';
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((liste) => {
    for (const c of liste) { if ('focus' in c) { c.navigate(url); return c.focus(); } }
    return self.clients.openWindow(url);
  }));
});
