/**
 * auth_handler.js — WeatherWise Auth Layer
 * Login, Register, token yönetimi ve navbar güncellemesi
 */

const API_BASE = 'http://127.0.0.1:8000';

// ══════════════════════════════════════════════
// Token / Session Utilities
// ══════════════════════════════════════════════

function getToken()    { return localStorage.getItem('ww_token'); }
function getUserName() { return localStorage.getItem('ww_user_name'); }
function isLoggedIn()  { return !!getToken(); }

function saveSession(token, name) {
    localStorage.setItem('ww_token',     token);
    localStorage.setItem('ww_user_name', name);
}

function clearSession() {
    localStorage.removeItem('ww_token');
    localStorage.removeItem('ww_user_name');
}

// ══════════════════════════════════════════════
// Navbar Güncelle
// ══════════════════════════════════════════════

function updateNavbar() {
    const navLogin   = document.getElementById('nav-login');
    const navSignup  = document.getElementById('nav-signup');
    const navUser    = document.getElementById('nav-user');
    const navSignout = document.getElementById('nav-signout');

    if (isLoggedIn()) {
        if (navLogin)   navLogin.style.display   = 'none';
        if (navSignup)  navSignup.style.display  = 'none';
        if (navUser) {
            navUser.style.display  = 'flex';
            navUser.textContent    = getUserName() || 'User';
        }
        if (navSignout) navSignout.style.display = 'flex';
    } else {
        if (navLogin)   navLogin.style.display   = '';
        if (navSignup)  navSignup.style.display  = '';
        if (navUser)    navUser.style.display    = 'none';
        if (navSignout) navSignout.style.display = 'none';
    }
}

// Sign out
function signOut() {
    clearSession();
    window.location.reload();
}

// ══════════════════════════════════════════════
// Login
// ══════════════════════════════════════════════

async function handleLogin(event) {
    if (event) event.preventDefault();

    const emailEl    = document.getElementById('email-input');
    const passEl     = document.getElementById('pass-input');
    const errorEl    = document.getElementById('login-error');
    const submitBtn  = document.getElementById('btn-submit-login');

    const email    = emailEl?.value?.trim();
    const password = passEl?.value;

    if (!email || !password) {
        _showError(errorEl, 'Please fill in all fields.');
        return;
    }

    _setLoading(submitBtn, 'Signing in...');

    try {
        const res  = await fetch(`${API_BASE}/auth/login`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ email, password }),
        });
        const data = await res.json();

        if (!res.ok) {
            _showError(errorEl, data.detail || 'Login failed.');
            return;
        }

        saveSession(data.token, data.name);
        window.location.href = 'index.html';

    } catch {
        _showError(errorEl, 'Connection error. Make sure the backend is running!');
    } finally {
        _resetLoading(submitBtn, 'Sign in');
    }
}

// ══════════════════════════════════════════════
// Register
// ══════════════════════════════════════════════

async function handleRegister(event) {
    if (event) event.preventDefault();

    const name            = document.getElementById('name-input')?.value?.trim();
    const country         = document.getElementById('country-select')?.value?.trim() || '';
    const city            = document.getElementById('city-select')?.value?.trim() || '';
    const email           = document.getElementById('email-input')?.value?.trim();
    const password        = document.getElementById('pass-input')?.value;
    const confirmPassword = document.getElementById('pass-confirm-input')?.value;
    const errorEl         = document.getElementById('signup-error');
    const submitBtn       = document.getElementById('btn-submit-signup');

    // Validasyon
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const passRegex  = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$/;

    if (!name)                        { _showError(errorEl, 'Please enter your full name.');                          return; }
    if (!emailRegex.test(email))      { _showError(errorEl, 'Please enter a valid email address.');                   return; }
    if (password !== confirmPassword) { _showError(errorEl, 'Passwords do not match!');                               return; }
    if (!passRegex.test(password))    { _showError(errorEl, 'Password must include uppercase, lowercase and a number.'); return; }

    _setLoading(submitBtn, 'Signing up...');

    try {
        const res  = await fetch(`${API_BASE}/auth/register`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ name, email, password, country, city }),
        });
        const data = await res.json();

        if (!res.ok) {
            _showError(errorEl, data.detail || 'Registration failed.');
            return;
        }

        // Kayıt başarılı → otomatik login
        saveSession(data.token, data.name);
        window.location.href = 'index.html';

    } catch {
        _showError(errorEl, 'Connection error. Make sure the backend is running!');
    } finally {
        _resetLoading(submitBtn, 'Sign up');
    }
}

// ══════════════════════════════════════════════
// Helpers
// ══════════════════════════════════════════════

function _showError(el, msg) {
    if (!el) return;
    el.textContent     = msg;
    el.style.display   = 'block';
}

function _setLoading(btn, text) {
    if (!btn) return;
    btn.disabled     = true;
    btn.textContent  = text;
}

function _resetLoading(btn, text) {
    if (!btn) return;
    btn.disabled     = false;
    btn.textContent  = text;
}

// ══════════════════════════════════════════════
// Sayfa yüklenince navbar'ı güncelle
// ══════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', updateNavbar);
