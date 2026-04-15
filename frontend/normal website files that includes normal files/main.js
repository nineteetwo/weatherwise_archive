document.addEventListener('DOMContentLoaded', () => {
    const translations = {
        en: { 
            placeholder: "How can I help you today?", privacy: "Privacy Policy", cookie: "Cookie Policy", createImage: "Create Image",
            navLogin: "Sign in", navSignup: "Sign up", authTitleIn: "Sign in", authTitleUp: "Sign up",
            nameLabel: "Full Name", emailLabel: "Email Address", passLabel: "Password",
            noAccount: "Don't have an account?", hasAccount: "Already have an account?"
        },
        tr: { 
            placeholder: "Bugün size nasıl yardımcı olabilirim?", privacy: "Gizlilik Politikası", cookie: "Çerez Politikası", createImage: "Görsel Oluştur",
            navLogin: "Giriş Yap", navSignup: "Kayıt Ol", authTitleIn: "Giriş Yap", authTitleUp: "Kayıt Ol",
            nameLabel: "Ad Soyad", emailLabel: "E-posta Adresi", passLabel: "Şifre",
            noAccount: "Hesabın yok mu?", hasAccount: "Zaten hesabın var mı?"
        },
        ru: { 
            placeholder: "Чем я могу вам помочь сегодня?", privacy: "Политика конфиденциальности", cookie: "Файлы cookie", createImage: "Создать изобр.",
            navLogin: "Войти", navSignup: "Регистрация", authTitleIn: "Вход", authTitleUp: "Регистрация",
            nameLabel: "Полное имя", emailLabel: "Адрес эл. почты", passLabel: "Пароль",
            noAccount: "Нет аккаунта?", hasAccount: "Уже есть аккаунт?"
        }
    };

    const langSelect = document.getElementById('lang-select');
    const searchInput = document.getElementById('search-input');
    const txtPrivacy = document.getElementById('txt-privacy');
    const txtCookie = document.getElementById('txt-cookie');
    const txtCreateImage = document.getElementById('txt-create-image');
    const navLogin = document.getElementById('nav-login');
    const navSignup = document.getElementById('nav-signup');
    const authTitleIn = document.getElementById('txt-auth-title');
    const authTitleUp = document.getElementById('txt-auth-title-up');
    const nameLabel = document.getElementById('txt-name-label');
    const emailLabel = document.getElementById('txt-email-label');
    const passLabel = document.getElementById('txt-pass-label');
    const btnSubmitLogin = document.getElementById('btn-submit-login');
    const btnSubmitSignup = document.getElementById('btn-submit-signup');
    const txtNoAccount = document.getElementById('txt-no-account');
    const txtHasAccount = document.getElementById('txt-has-account');
    const linkSignup = document.getElementById('link-signup');
    const linkSignin = document.getElementById('link-signin');
    const hamburgerBtn = document.getElementById('hamburger-btn');
    const navRight = document.getElementById('nav-right');

    if (hamburgerBtn && navRight) {
        hamburgerBtn.addEventListener('click', () => {
            navRight.classList.toggle('active');
            const icon = hamburgerBtn.querySelector('span');
            if (navRight.classList.contains('active')) {
                icon.textContent = 'close';
            } else {
                icon.textContent = 'menu';
            }
        });
    }

    function applyTranslation(lang) {
        const t = translations[lang];
        if (!t) return;
        if (searchInput) searchInput.placeholder = t.placeholder;
        if (txtPrivacy) txtPrivacy.textContent = t.privacy;
        if (txtCookie) txtCookie.textContent = t.cookie;
        if (txtCreateImage) txtCreateImage.textContent = t.createImage;
        if (navLogin) navLogin.textContent = t.navLogin;
        if (navSignup) navSignup.textContent = t.navSignup;
        if (authTitleIn) authTitleIn.textContent = t.authTitleIn;
        if (authTitleUp) authTitleUp.textContent = t.authTitleUp;
        if (nameLabel) nameLabel.textContent = t.nameLabel;
        if (emailLabel) emailLabel.textContent = t.emailLabel;
        if (passLabel) passLabel.textContent = t.passLabel;
        if (btnSubmitLogin) btnSubmitLogin.textContent = t.authTitleIn;
        if (btnSubmitSignup) btnSubmitSignup.textContent = t.authTitleUp;
        if (txtNoAccount) txtNoAccount.textContent = t.noAccount;
        if (txtHasAccount) txtHasAccount.textContent = t.hasAccount;
        if (linkSignup) linkSignup.textContent = t.navSignup;
        if (linkSignin) linkSignin.textContent = t.navLogin;
    }

    langSelect.addEventListener('change', (e) => applyTranslation(e.target.value));

    const browserLang = (navigator.language || navigator.userLanguage).substring(0, 2);
    if (translations[browserLang]) {
        langSelect.value = browserLang;
    } else {
        langSelect.value = 'en';
    }
    applyTranslation(langSelect.value);

    const weatherIconElement = document.getElementById('weather-icon');
    const timeTextElement = document.getElementById('time-text');

    function updateClock() {
        if (!timeTextElement) return; 
        const now = new Date();
        timeTextElement.textContent = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    }
    
    updateClock();
    setInterval(updateClock, 1000);

    function getSystemTimeOfDay() {
        const h = new Date().getHours();
        if (h >= 6 && h < 8) return 'sunrise';
        if (h >= 8 && h < 12) return 'morning';
        if (h >= 12 && h < 17) return 'noon';
        if (h >= 17 && h < 19) return 'sunset';
        if (h >= 19 && h < 22) return 'evening';
        return 'night';
    }

    function updateWidgetIcon(weather, time) {
        if (!weatherIconElement) return;
        let iconName = 'clear_day';
        if (weather === 'clear') iconName = (time === 'night' || time === 'evening') ? 'clear_night' : 'clear_day';
        else if (weather === 'clouds') iconName = 'cloud';
        else if (weather === 'rain') iconName = 'rainy';
        else if (weather === 'heavy-rain') iconName = 'storm';
        else if (weather === 'snow') iconName = 'snowing';
        else if (weather === 'thunder') iconName = 'thunderstorm';
        else if (weather === 'fog') iconName = 'foggy';
        weatherIconElement.textContent = iconName;
    }

    function updateEnvironment() {
        const time = getSystemTimeOfDay();
        const weather = 'clear';
        document.body.className = `time-${time} weather-${weather}`;
        updateWidgetIcon(weather, time);
        if (window.setWeatherEffect) window.setWeatherEffect(weather);
    }

    updateEnvironment();
});