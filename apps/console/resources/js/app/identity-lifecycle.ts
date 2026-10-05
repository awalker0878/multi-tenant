import { router } from '@inertiajs/vue3';

// Carry only an invalidation signal between tabs: no actor, tenant or credentials.
const signalKey = 'workload-mobility:identity-invalidated';
let channel: BroadcastChannel | undefined;
try {
  if ('BroadcastChannel' in window) channel = new BroadcastChannel(signalKey);
} catch {
  // Storage events remain available when channel creation is restricted.
}
let leaving = false;
let signingOut = false;

function discardPage(destination?: string): void {
  if (leaving) return;
  leaving = true;
  router.cancelAll();
  router.flushAll();
  router.clearHistory();
  const root = document.getElementById('app');
  if (root) root.hidden = true;
  if (destination) window.location.replace(destination);
  else window.location.reload();
}

channel?.addEventListener('message', event => {
  if (event.data === 'signed-out') discardPage('/login');
});
window.addEventListener('storage', event => {
  if (event.key === signalKey && event.newValue !== null) discardPage('/login');
});
window.addEventListener('pageshow', event => {
  if (event.persisted && /^\/(account|setup|password|tenants)(\/|$)/.test(window.location.pathname)) discardPage();
});

router.on('start', event => {
  signingOut = event.detail.visit.method === 'post' && event.detail.visit.url.pathname === '/logout';
});
router.on('success', event => {
  if (!signingOut || event.detail.page.component !== 'identity/Login') return;
  try { channel?.postMessage('signed-out'); }
  catch { /* Storage events also carry the invalidation signal. */ }
  try {
    localStorage.setItem(signalKey, crypto.randomUUID());
    localStorage.removeItem(signalKey);
  } catch {
    // The server still reauthorizes every request if browser storage is disabled.
  }
});
router.on('finish', () => { signingOut = false; });
