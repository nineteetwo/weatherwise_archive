document.addEventListener('DOMContentLoaded', () => {
    const signupBtn = document.getElementById('btn-submit-signup');
    const emailInput = document.getElementById('email-input');
    const passInput = document.getElementById('pass-input');
    const passConfirmInput = document.getElementById('pass-confirm-input');

    function apiDetailMessage(payload) {
        if (!payload || typeof payload !== 'object') return 'Something went wrong';
        const d = payload.detail;
        if (typeof d === 'string') return d;
        if (Array.isArray(d)) {
            return d.map((x) => (x && x.msg) || JSON.stringify(x)).join(' ');
        }
        return 'Something went wrong';
    }

    if (signupBtn && emailInput && passInput && passConfirmInput) {
        const errorMsg = document.createElement('p');
        errorMsg.className = 'auth-form-error';
        errorMsg.setAttribute('role', 'alert');
        errorMsg.setAttribute('aria-live', 'polite');

        signupBtn.parentNode.insertBefore(errorMsg, signupBtn);

        signupBtn.addEventListener('click', async () => {
            const email = emailInput.value.trim();
            const password = passInput.value;
            const confirmPassword = passConfirmInput.value;

            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            const passRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$/;

            if (!emailRegex.test(email)) {
                errorMsg.textContent = 'Please enter a valid email address.';
                errorMsg.classList.add('is-visible');
                return;
            }

            if (password !== confirmPassword) {
                errorMsg.textContent = 'Passwords do not match!';
                errorMsg.classList.add('is-visible');
                return;
            }

            if (!passRegex.test(password)) {
                errorMsg.textContent =
                    'Password must include uppercase, lowercase letters and a number.';
                errorMsg.classList.add('is-visible');
                return;
            }

            errorMsg.textContent = '';
            errorMsg.classList.remove('is-visible');

            const nameInput = document.getElementById('name-input');
            const name = (nameInput && nameInput.value.trim()) || email.split('@')[0];
            const citySelect = document.getElementById('city-select');
            const countrySelect = document.getElementById('country-select');
            let city = '';
            let country = '';
            if (citySelect && citySelect.value) {
                const opt = citySelect.options[citySelect.selectedIndex];
                city = (opt && opt.textContent && opt.textContent.trim()) || citySelect.value;
            }
            if (countrySelect && countrySelect.value) {
                const opt = countrySelect.options[countrySelect.selectedIndex];
                country = (opt && opt.textContent && opt.textContent.trim()) || countrySelect.value;
            }

            signupBtn.disabled = true;
            try {
                var apiBase = typeof weatherwiseApiBase === 'function' ? weatherwiseApiBase() : '';
                const res = await fetch(apiBase + '/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, password, country, city }),
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    errorMsg.textContent = apiDetailMessage(data) || `Error (${res.status})`;
                    errorMsg.classList.add('is-visible');
                    return;
                }

                if (window.WeatherwiseSession) {
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
                }
                if (data.city) sessionStorage.setItem('weatherwise_last_city', data.city);
                window.location.href = 'home.html';
            } catch (err) {
                errorMsg.textContent = err.message || 'Network error. Is the server running?';
                errorMsg.classList.add('is-visible');
            } finally {
                signupBtn.disabled = false;
            }
        });
    }
});
