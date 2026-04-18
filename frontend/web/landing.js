document.addEventListener('DOMContentLoaded', () => {
    const translations = {
        en: {
            tagline: 'The sky speaks. We translate.',
            signIn: 'Sign in',
            signUp: 'Sign up',
            guest: 'Continue as guest',
            privacy: 'Privacy Policy',
            cookie: 'Cookie Policy',
        },
        tr: {
            tagline: 'Gökyüzü konuşur. Biz çeviririz.',
            signIn: 'Giriş Yap',
            signUp: 'Kayıt Ol',
            guest: 'Misafir olarak devam et',
            privacy: 'Gizlilik Politikası',
            cookie: 'Çerez Politikası',
        },
        ru: {
            tagline: 'Небо говорит. Мы переводим.',
            signIn: 'Войти',
            signUp: 'Регистрация',
            guest: 'Продолжить как гость',
            privacy: 'Политика конфиденциальности',
            cookie: 'Файлы cookie',
        },
    };

    const langSelect = document.getElementById('lang-select');
    const taglineEl = document.getElementById('txt-landing-tagline');
    const signInEl = document.getElementById('btn-landing-signin');
    const signUpEl = document.getElementById('btn-landing-signup');
    const guestLabelEl = document.getElementById('txt-landing-guest');
    const privacyEl = document.getElementById('txt-privacy');
    const cookieEl = document.getElementById('txt-cookie');

    function applyTranslation(lang) {
        const t = translations[lang];
        if (!t) return;
        if (taglineEl) taglineEl.textContent = t.tagline;
        if (signInEl) signInEl.textContent = t.signIn;
        if (signUpEl) signUpEl.textContent = t.signUp;
        if (guestLabelEl) guestLabelEl.textContent = t.guest;
        if (privacyEl) privacyEl.textContent = t.privacy;
        if (cookieEl) cookieEl.textContent = t.cookie;
    }

    if (langSelect) {
        langSelect.addEventListener('change', (e) => applyTranslation(e.target.value));
        const bl = (navigator.language || 'en').substring(0, 2);
        langSelect.value = translations[bl] ? bl : 'en';
        applyTranslation(langSelect.value);
    }

    const guestLink = document.getElementById('btn-landing-guest');
    if (guestLink && window.WeatherwiseSession) {
        guestLink.addEventListener('click', () => {
            window.WeatherwiseSession.set({ mode: 'guest', at: Date.now() });
        });
    }
});
