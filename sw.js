// Service Worker 비활성화 - 캐시 없이 항상 최신 버전 로드
self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => {
  self.clients.claim();
  // 모든 캐시 삭제
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k)))));
});
self.addEventListener('fetch', e => {
  // 캐시 없이 항상 네트워크에서 직접 가져옴
  e.respondWith(fetch(e.request));
});
// 2026년  3월 29일 일요일 16시 19분 47초 KST
