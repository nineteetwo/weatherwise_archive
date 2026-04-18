document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('btn-submit-login');
    const emailInput = document.getElementById('email-input');
    const passInput = document.getElementById('pass-input');
    const errorMsg = document.getElementById('login-error-msg');
    if (!btn || !window.WeatherwiseSession) return;

    function apiDetailMessage(payload) {
        if (!payload || typeof payload !== 'object') return 'Something went wrong';
        const d = payload.detail;
        if (typeof d === 'string') return d;
        if (Array.isArray(d)) {
            return d.map((x) => (x && x.msg) || JSON.stringify(x)).join(' ');
        }
        return 'Something went wrong';
    }

    function showError(text) {
        if (!errorMsg) return;
        errorMsg.textContent = text;
        errorMsg.classList.add('is-visible');
    }

    function hideError() {
        if (!errorMsg) return;
        errorMsg.textContent = '';
        errorMsg.classList.remove('is-visible');
    }

    btn.addEventListener('click', async () => {
        hideError();
        const email = emailInput && emailInput.value.trim();
        if (!email) {
            showError('Please enter your email.');
            return;
        }
        if (!passInput || !passInput.value) {
            showError('Please enter your password.');
            return;
        }

        btn.disabled = true;
        try {
            const res = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password: passInput.value }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                showError(apiDetailMessage(data) || 'Sign in failed');
                return;
            }

            window.WeatherwiseSession.set({
                mode: 'signed_in',
                token: data.token,
                name: data.name,
                displayName: data.name,
                email: data.email,
                country: data.country,
                city: data.city,
                at: Date.now(),
            });
            if (data.city) sessionStorage.setItem('weatherwise_last_city', data.city);
            window.location.href = 'home.html';
        } catch (err) {
            showError(err.message || 'Network error. Is the server running?');
        } finally {
            btn.disabled = false;
        }
    });
});
