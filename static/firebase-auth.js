/* ═══════════════════════════════════════════════════
   unlockED — Shared Firebase Auth plumbing
   Loaded after firebase-app-compat.js, firebase-auth-compat.js,
   and firebase-config.js on every authenticated page.
   ═══════════════════════════════════════════════════ */

firebase.initializeApp(FIREBASE_CONFIG);

function syntheticEmail(username) {
  return `${username}@unlocked.local`;
}

// Resolves once the FIRST onAuthStateChanged fires — currentUser is
// synchronously null right after SDK init until this resolves, so any
// redirect-if-unauthenticated check must wait for it (avoids a flash-redirect
// on a hard refresh of an already-authenticated page).
const authReady = new Promise((resolve) => {
  const unsubscribe = firebase.auth().onAuthStateChanged((user) => {
    unsubscribe();
    resolve(user);
  });
});

// Wrap fetch to attach a freshly-fetched ID token (tokens expire hourly;
// getIdToken() auto-refreshes under the hood, so always call it fresh rather
// than caching one token for the page's lifetime) to same-origin API calls.
const originalFetch = window.fetch;
window.fetch = async function (...args) {
  const user = firebase.auth().currentUser;
  if (user) {
    const token = await user.getIdToken();
    const [resource, config = {}] = args;
    config.headers = { ...(config.headers || {}), Authorization: `Bearer ${token}` };
    args = [resource, config];
  }
  const response = await originalFetch(...args);
  if (response.status === 401) {
    window.location.href = '/static/login.html';
  }
  return response;
};

let currentUserRole = null;
let currentUserStudentId = null;

async function checkUserSession() {
  const user = await authReady;
  if (!user) {
    window.location.href = '/static/login.html';
    return false;
  }
  try {
    const res = await fetch('/api/user_session');
    const data = await res.json();
    if (!data.authenticated) {
      window.location.href = '/static/login.html';
      return false;
    }
    currentUserRole = data.role;
    currentUserStudentId = data.student_id;

    const counselorLink = document.getElementById('counselor-view-link');
    if (counselorLink && currentUserRole !== 'counselor') {
      counselorLink.style.display = 'none';
    }

    return true;
  } catch (err) {
    console.error(err);
    window.location.href = '/static/login.html';
    return false;
  }
}

async function logout() {
  try {
    await firebase.auth().signOut();
  } finally {
    window.location.href = '/static/login.html';
  }
}
window.logout = logout;
