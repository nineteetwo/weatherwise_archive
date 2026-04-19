document.addEventListener('DOMContentLoaded', () => {
    function setupSessionNav() {
        const session = window.WeatherwiseSession && window.WeatherwiseSession.get();
        const navLogin = document.getElementById('nav-login');
        const navSignup = document.getElementById('nav-signup');
        const navRight = document.getElementById('nav-right');
        const langSelect = document.getElementById('lang-select');

        if (!session || !navLogin || !navSignup || !navRight) return;

        navLogin.style.display = 'none';
        navSignup.style.display = 'none';

        const existing = navRight.querySelector('[data-weatherwise-session-out]');
        if (existing) existing.remove();

        const outBtn = document.createElement('button');
        outBtn.type = 'button';
        outBtn.className = 'glass-btn login-btn';
        outBtn.setAttribute('data-weatherwise-session-out', '1');
        if (session.mode === 'guest') {
            outBtn.textContent = 'Guest · Sign out';
        } else {
            const label = session.email || session.displayName || session.name || 'Account';
            const short = label.length > 18 ? label.slice(0, 16) + '…' : label;
            outBtn.textContent = short + ' · Sign out';
            outBtn.title = 'Sign out and return to welcome';
        }

        outBtn.addEventListener('click', () => {
            window.WeatherwiseSession.clear();
            window.location.href = 'landing.html';
        });

        if (langSelect && langSelect.parentNode === navRight) {
            langSelect.after(outBtn);
        } else {
            navRight.appendChild(outBtn);
        }
    }

    if (window.refreshWeatherwiseSessionFromServer) {
        void window.refreshWeatherwiseSessionFromServer().finally(() => setupSessionNav());
    } else {
        setupSessionNav();
    }
});
