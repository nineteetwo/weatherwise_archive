document.addEventListener('DOMContentLoaded', () => {

    // ==========================================
    // 1. TRANSLATIONS
    // ==========================================
    const translations = {
        en: {
            placeholder: "How can I help you today?",
            privacy: "Privacy Policy", cookie: "Cookie Policy",
            createImage: "Create Image", navLogin: "Sign in", navSignup: "Sign up"
        },
        tr: {
            placeholder: "Bugün size nasıl yardımcı olabilirim?",
            privacy: "Gizlilik Politikası", cookie: "Çerez Politikası",
            createImage: "Görsel Oluştur", navLogin: "Giriş Yap", navSignup: "Kayıt Ol"
        },
        ru: {
            placeholder: "Чем я могу вам помочь сегодня?",
            privacy: "Политика конфиденциальности", cookie: "Файлы cookie",
            createImage: "Создать изобр.", navLogin: "Войти", navSignup: "Регистрация"
        }
    };

    const langSelect     = document.getElementById('lang-select');
    const searchInput    = document.getElementById('search-input');
    const txtPrivacy     = document.getElementById('txt-privacy');
    const txtCookie      = document.getElementById('txt-cookie');
    const txtCreateImage = document.getElementById('txt-create-image');
    const navLogin       = document.getElementById('nav-login');
    const navSignup      = document.getElementById('nav-signup');
    const hamburgerBtn   = document.getElementById('hamburger-btn');
    const navRight       = document.getElementById('nav-right');

    if (hamburgerBtn && navRight) {
        hamburgerBtn.addEventListener('click', () => {
            navRight.classList.toggle('active');
            hamburgerBtn.querySelector('span').textContent =
                navRight.classList.contains('active') ? 'close' : 'menu';
        });
    }

    function applyTranslation(lang) {
        const t = translations[lang];
        if (!t) return;
        if (searchInput)    searchInput.placeholder    = t.placeholder;
        if (txtPrivacy)     txtPrivacy.textContent     = t.privacy;
        if (txtCookie)      txtCookie.textContent      = t.cookie;
        if (txtCreateImage) txtCreateImage.textContent = t.createImage;
        if (navLogin)       navLogin.textContent       = t.navLogin;
        if (navSignup)      navSignup.textContent      = t.navSignup;
    }

    if (langSelect) {
        langSelect.addEventListener('change', e => applyTranslation(e.target.value));
        const bl = (navigator.language || 'en').substring(0, 2);
        langSelect.value = translations[bl] ? bl : 'en';
        applyTranslation(langSelect.value);
    }

    // ==========================================
    // 2. CLOCK & BACKGROUND
    // ==========================================
    const weatherIconEl = document.getElementById('weather-icon');
    const timeTextEl    = document.getElementById('time-text');
    const locationText  = document.getElementById('location-text');
    const tempText      = document.getElementById('temp-text');
    const enterBtn      = document.querySelector('.enter-btn');
    const aiResultsCard = document.getElementById('ai-results');
    const aiAdviceEl    = document.getElementById('ai-advice-text');

    let currentCityOffset = null;

    const WEATHER_ICONS = {
        'clear':      { day: 'clear_day',   night: 'clear_night'  },
        'clouds':     { day: 'cloud',        night: 'cloud'        },
        'rain':       { day: 'rainy',        night: 'rainy'        },
        'heavy-rain': { day: 'storm',        night: 'storm'        },
        'snow':       { day: 'snowing',      night: 'snowing'      },
        'thunder':    { day: 'thunderstorm', night: 'thunderstorm' },
        'fog':        { day: 'foggy',        night: 'foggy'        }
    };

    function getTimeSlot(h) {
        if (h >= 6  && h < 8)  return 'sunrise';
        if (h >= 8  && h < 12) return 'morning';
        if (h >= 12 && h < 17) return 'noon';
        if (h >= 17 && h < 19) return 'sunset';
        if (h >= 19 && h < 22) return 'evening';
        return 'night';
    }

    function applyBackground(timeSlot, weatherEffect) {
        const keep = document.body.className
            .split(' ')
            .filter(c => !c.startsWith('time-') && !c.startsWith('weather-'))
            .join(' ');
        document.body.className = `${keep} time-${timeSlot} weather-${weatherEffect}`.trim();
        const icons   = WEATHER_ICONS[weatherEffect] || WEATHER_ICONS['clear'];
        const isNight = timeSlot === 'night' || timeSlot === 'evening';
        if (weatherIconEl) weatherIconEl.textContent = isNight ? icons.night : icons.day;
    }

    function updateClock() {
        if (!timeTextEl) return;
        const now = new Date();
        let cityTime;
        if (currentCityOffset !== null) {
            const utcMs = now.getTime() + now.getTimezoneOffset() * 60000;
            cityTime    = new Date(utcMs + currentCityOffset * 1000);
        } else {
            cityTime = now;
        }
        const h = cityTime.getHours();
        const m = cityTime.getMinutes();
        timeTextEl.textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
        const timeSlot     = getTimeSlot(h);
        const weatherClass = document.body.className.split(' ')
            .find(c => c.startsWith('weather-')) || 'weather-clear';
        applyBackground(timeSlot, weatherClass.replace('weather-', ''));
    }

    updateClock();
    setInterval(updateClock, 1000);

    // ==========================================
    // 3. FETCH & UPDATE UI
    // ==========================================
    const API_BASE = 'http://127.0.0.1:8000';

    async function fetchWeatherWiseData(city) {
        city = (city || '').trim();
        if (!city) { alert("Please enter a city name!"); return; }

        const originalIcon = enterBtn?.textContent;
        if (enterBtn) {
            enterBtn.textContent         = 'hourglass_empty';
            enterBtn.style.pointerEvents = 'none';
        }

        try {
            const res = await fetch(`${API_BASE}/recommend/?city=${encodeURIComponent(city)}`);
            if (res.status === 404) throw new Error(`City "${city}" not found.`);
            if (res.status === 503) throw new Error('Weather service temporarily unavailable.');
            if (!res.ok)            throw new Error(`Server error (${res.status})`);

            const data = await res.json();

            // ✅ Location & temp — البنية الجديدة flat
            if (locationText) locationText.textContent = data.city;
            if (tempText)     tempText.textContent     = `${Math.round(data.temperature)}°C`;
            currentCityOffset = data.utc_offset;

            // ✅ خلفية + ساعة
            const utcMs    = Date.now() + new Date().getTimezoneOffset() * 60000;
            const cityHour = new Date(utcMs + data.utc_offset * 1000).getHours();
            applyBackground(getTimeSlot(cityHour), data.weather_effect || 'clear');
            if (window.setWeatherEffect) window.setWeatherEffect(data.weather_effect || 'clear');
            updateClock();

            // ✅ AI results
            if (aiResultsCard) aiResultsCard.style.display = 'block';

            const elClothing = document.getElementById('ai-clothing');
            const elUmbrella = document.getElementById('ai-umbrella');
            const elScore    = document.getElementById('ai-score');
            const elDecision = document.getElementById('ai-decision');

            if (elClothing) elClothing.textContent = data.clothing_recommendation;
            if (elUmbrella) elUmbrella.textContent = data.umbrella_needed ? "Yes ☂️" : "No 🌤️";
            if (elScore)    elScore.textContent    = `${data.suitability_score}/10`;

            if (elDecision) {
                const go = data.go_or_no;
                elDecision.textContent      = go ? "GO ✅" : "STAY ❌";
                elDecision.style.background = go ? "rgba(46,204,113,0.2)" : "rgba(231,76,60,0.2)";
                elDecision.style.color      = go ? "#2ecc71" : "#ff6b6b";
            }

            // ✅ AI Tip من Yandex أو rule-based
            if (aiAdviceEl) {
                aiAdviceEl.textContent = data.tip_text || '';
            }

        } catch (err) {
            console.error('Fetch error:', err);
            alert(`❌ ${err.message || 'Connection error. Make sure the backend is running!'}`);
        } finally {
            if (enterBtn) {
                enterBtn.textContent         = originalIcon;
                enterBtn.style.pointerEvents = 'auto';
            }
        }
    }

    if (enterBtn)    enterBtn.addEventListener('click', () => fetchWeatherWiseData(searchInput?.value));
    if (searchInput) searchInput.addEventListener('keypress', e => {
        if (e.key === 'Enter') fetchWeatherWiseData(searchInput.value);
    });
});