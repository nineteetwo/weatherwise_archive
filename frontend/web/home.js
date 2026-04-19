document.addEventListener('DOMContentLoaded', async () => {
    if (window.refreshWeatherwiseSessionFromServer) {
        await window.refreshWeatherwiseSessionFromServer();
    }
    const LAST_CITY_KEY = 'weatherwise_last_city';

    const weatherIconEl = document.getElementById('weather-icon');
    const timeTextEl = document.getElementById('time-text');
    const locationText = document.getElementById('location-text');
    const tempText = document.getElementById('temp-text');
    const dateEl = document.getElementById('home-date');
    const userNameEl = document.getElementById('home-user-name');
    const searchInput = document.getElementById('home-city-search');
    const goBtn = document.getElementById('home-city-go');
    const hourlyList = document.getElementById('home-hourly-list');
    const btnOpenChat = document.getElementById('home-open-chat');

    const hamburgerBtn = document.getElementById('hamburger-btn');
    const navRight = document.getElementById('nav-right');
    if (hamburgerBtn && navRight) {
        hamburgerBtn.addEventListener('click', () => {
            navRight.classList.toggle('active');
            hamburgerBtn.querySelector('span').textContent = navRight.classList.contains('active')
                ? 'close'
                : 'menu';
        });
    }

    let currentCityOffset = null;

    const WEATHER_ICONS = {
        clear: { day: 'clear_day', night: 'clear_night' },
        clouds: { day: 'cloud', night: 'cloud' },
        rain: { day: 'rainy', night: 'rainy' },
        'heavy-rain': { day: 'storm', night: 'storm' },
        snow: { day: 'snowing', night: 'snowing' },
        thunder: { day: 'thunderstorm', night: 'thunderstorm' },
        fog: { day: 'foggy', night: 'foggy' },
    };

    function getTimeSlot(h) {
        if (h >= 6 && h < 8) return 'sunrise';
        if (h >= 8 && h < 12) return 'morning';
        if (h >= 12 && h < 17) return 'noon';
        if (h >= 17 && h < 19) return 'sunset';
        if (h >= 19 && h < 22) return 'evening';
        return 'night';
    }

    function applyBackground(timeSlot, weatherEffect) {
        const keep = document.body.className
            .split(' ')
            .filter((c) => c && c !== 'home-page' && !c.startsWith('time-') && !c.startsWith('weather-'))
            .join(' ');
        document.body.className = `home-page ${keep} time-${timeSlot} weather-${weatherEffect}`.trim();
        const icons = WEATHER_ICONS[weatherEffect] || WEATHER_ICONS.clear;
        const isNight = timeSlot === 'night' || timeSlot === 'evening';
        if (weatherIconEl) weatherIconEl.textContent = isNight ? icons.night : icons.day;
    }

    function updateDateLine() {
        if (!dateEl) return;
        const now = new Date();
        const opts = { weekday: 'short', month: 'short', day: 'numeric' };
        let d = now;
        if (currentCityOffset !== null) {
            const utcMs = now.getTime() + now.getTimezoneOffset() * 60000;
            d = new Date(utcMs + currentCityOffset * 1000);
        }
        dateEl.textContent = d.toLocaleDateString(undefined, opts);
    }

    function updateClock() {
        if (!timeTextEl) return;
        const now = new Date();
        let cityTime;
        if (currentCityOffset !== null) {
            const utcMs = now.getTime() + now.getTimezoneOffset() * 60000;
            cityTime = new Date(utcMs + currentCityOffset * 1000);
        } else {
            cityTime = now;
        }
        const h = cityTime.getHours();
        const m = cityTime.getMinutes();
        timeTextEl.textContent = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
        const timeSlot = getTimeSlot(h);
        const weatherClass =
            document.body.className.split(' ').find((c) => c.startsWith('weather-')) || 'weather-clear';
        applyBackground(timeSlot, weatherClass.replace('weather-', ''));
        updateDateLine();
    }

    function initUserLabel() {
        const s = window.WeatherwiseSession && window.WeatherwiseSession.get();
        if (!userNameEl) return;
        if (!s) { userNameEl.textContent = 'Guest'; return; }
        if (s.mode === 'guest') { userNameEl.textContent = 'Guest'; return; }
        userNameEl.textContent = s.displayName || s.name || s.email || 'You';
    }

    function defaultCityQuery() {
        const s = window.WeatherwiseSession && window.WeatherwiseSession.get();
        if (s && s.city && String(s.city).trim()) return String(s.city).trim();
        const last = sessionStorage.getItem(LAST_CITY_KEY);
        return last ? last.trim() : '';
    }

    function renderHourly(rows) {
        if (!hourlyList) return;
        hourlyList.innerHTML = '';
        if (!rows || !rows.length) {
            hourlyList.innerHTML = '<li class="home-hourly-placeholder">No hourly data yet.</li>';
            return;
        }
        rows.slice(0, 24).forEach((row) => {
            const li = document.createElement('li');
            li.className = 'home-hourly-row';
            let timeLabel = row.time || '';
            if (timeLabel && timeLabel.includes('T')) {
                const d = new Date(timeLabel);
                if (!Number.isNaN(d.getTime())) {
                    timeLabel = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                }
            }
            const temp = row.temperature != null ? `${Math.round(row.temperature)}°C` : '—';
            const eff = row.weather_effect || '';
            li.innerHTML = `<span class="home-hourly-time">${timeLabel}</span><span class="home-hourly-temp">${temp}</span><span class="home-hourly-eff">${eff}</span>`;
            hourlyList.appendChild(li);
        });
    }

    async function fetchForCity(city) {
        city = (city || '').trim();
        if (!city) { alert('Please enter a city name.'); return; }

        const original = goBtn?.querySelector('.material-symbols-outlined')?.textContent;
        if (goBtn) {
            goBtn.disabled = true;
            const icon = goBtn.querySelector('.material-symbols-outlined');
            if (icon) icon.textContent = 'hourglass_empty';
        }

        try {
            const res = await fetch(`/recommend/?city=${encodeURIComponent(city)}`);
            if (res.status === 404) throw new Error(`City "${city}" not found.`);
            if (res.status === 503) throw new Error('Weather service temporarily unavailable.');
            if (!res.ok) throw new Error(`Server error (${res.status})`);

            const data = await res.json();
            sessionStorage.setItem(LAST_CITY_KEY, data.city || city);

            if (locationText) locationText.textContent = data.city;
            if (tempText) tempText.textContent = `${Math.round(data.temperature)}°C`;
            currentCityOffset = data.utc_offset;

            const utcMs = Date.now() + new Date().getTimezoneOffset() * 60000;
            const cityHour = new Date(utcMs + data.utc_offset * 1000).getHours();
            applyBackground(getTimeSlot(cityHour), data.weather_effect || 'clear');
            if (window.setWeatherEffect) window.setWeatherEffect(data.weather_effect || 'clear');
            updateClock();

            const c   = document.getElementById('home-ai-clothing');
            const u   = document.getElementById('home-ai-umbrella');
            const sc  = document.getElementById('home-ai-score');
            const tip = document.getElementById('home-ai-tip');
            if (c)   c.textContent  = data.clothing_recommendation || '—';
            if (u)   u.textContent  = data.umbrella_needed ? 'Yes ☂️' : 'No';
            if (sc)  sc.textContent = `${data.suitability_score}/10`;
            if (tip) tip.textContent = data.tip_text || '—';

            renderHourly(data.forecast_24h || []);
        } catch (err) {
            console.error(err);
            alert(err.message || 'Connection error. Is the backend running?');
        } finally {
            if (goBtn) {
                goBtn.disabled = false;
                const icon = goBtn.querySelector('.material-symbols-outlined');
                if (icon) icon.textContent = original || 'search';
            }
        }
    }

    initUserLabel();
    updateClock();
    setInterval(updateClock, 1000);

    const startCity = defaultCityQuery();
    if (searchInput && startCity) searchInput.value = startCity;
    if (startCity) fetchForCity(startCity);

    if (goBtn) goBtn.addEventListener('click', () => fetchForCity(searchInput && searchInput.value));
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') fetchForCity(searchInput.value);
        });
    }

    // Community comment system
    const COMMENTS_KEY = 'weatherwise_community_comments';

    function loadComments() {
        try { return JSON.parse(localStorage.getItem(COMMENTS_KEY) || '[]'); }
        catch { return []; }
    }

    function saveComments(arr) {
        localStorage.setItem(COMMENTS_KEY, JSON.stringify(arr));
    }

    function renderCommentsList(listEl, comments) {
        if (!listEl) return;
        listEl.innerHTML = '';
        if (!comments.length) {
            listEl.innerHTML = '<li class="community-comment-empty">No comments yet. Be the first!</li>';
            return;
        }
        comments.slice().reverse().forEach(c => {
            const li = document.createElement('li');
            li.className = 'community-comment-item';
            li.innerHTML = `
                <div class="community-comment-meta">
                    <span class="community-comment-author">${escapeHtml(c.author)}</span>
                    <span class="community-comment-time">${new Date(c.ts).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                </div>
                <p class="community-comment-text">${escapeHtml(c.text)}</p>
            `;
            listEl.appendChild(li);
        });
    }

    function escapeHtml(s) {
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    function refreshAllComments() {
        const comments = loadComments();
        renderCommentsList(document.getElementById('community-comments-list'), comments);
        renderCommentsList(document.getElementById('feed-comments-list'), comments);
    }

    function initCommunityUI() {
        const s = window.WeatherwiseSession && window.WeatherwiseSession.get();
        const isLoggedIn = s && s.mode !== 'guest';

        const homeForm = document.getElementById('community-comment-form');
        const homeHint = document.getElementById('community-login-hint');
        const feedForm = document.getElementById('feed-comment-form');
        const feedHint = document.getElementById('feed-login-hint');

        if (isLoggedIn) {
            if (homeForm) homeForm.style.display = '';
            if (feedForm) feedForm.style.display = '';
        } else {
            if (homeHint) homeHint.style.display = '';
            if (feedHint) feedHint.style.display = '';
        }

        refreshAllComments();

        function postComment(inputEl) {
            if (!inputEl) return;
            const text = inputEl.value.trim();
            if (!text) return;
            const author = (s && (s.displayName || s.name || s.email)) || 'Anonymous';
            const comments = loadComments();
            comments.push({ author, text, ts: Date.now() });
            if (comments.length > 100) comments.splice(0, comments.length - 100);
            saveComments(comments);
            inputEl.value = '';
            refreshAllComments();
        }

        const homeSubmit = document.getElementById('community-comment-submit');
        if (homeSubmit) homeSubmit.addEventListener('click', () => postComment(document.getElementById('community-comment-input')));

        const feedSubmit = document.getElementById('feed-comment-submit');
        if (feedSubmit) feedSubmit.addEventListener('click', () => postComment(document.getElementById('feed-comment-input')));

        [document.getElementById('community-comment-input'), document.getElementById('feed-comment-input')].forEach(inp => {
            if (inp) inp.addEventListener('keydown', e => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); postComment(inp); }
            });
        });
    }

    initCommunityUI();

    const chatStubEl = document.getElementById('chat-stub-context');

    function refreshChatStub() {
        if (!chatStubEl) return;
        const cityRaw = (locationText && locationText.textContent.trim()) || defaultCityQuery() || '';
        const city = cityRaw && cityRaw !== '—' ? cityRaw : '';
        chatStubEl.textContent = city
            ? `City: ${city}. Ask anything about the weather.`
            : 'Pick a city on Home to personalize chat context.';
    }

    const track = document.getElementById('app-track');
    const tabButtons = document.querySelectorAll('.home-bottom-nav [data-app-view]');
    const panels = [
        document.getElementById('app-panel-home'),
        document.getElementById('app-panel-chat'),
        document.getElementById('app-panel-myday'),
        document.getElementById('app-panel-feed'),
    ];
    const HASH_KEYS = ['home', 'chat', 'myday', 'feed'];
    const titles = ['PhanarAi — Home', 'PhanarAi — Chat', 'PhanarAi — My Day', 'PhanarAi — Feed'];
    let appViewIndex = -1;

    function indexFromHash() {
        let h = (location.hash || '').replace(/^#/, '').toLowerCase();
        if (!h) h = 'home';
        const i = HASH_KEYS.indexOf(h);
        return i >= 0 ? i : 0;
    }

    function setAppView(next, { replaceHash } = { replaceHash: true }) {
        if (!track || !tabButtons.length) return;
        const n = Math.max(0, Math.min(3, next));
        if (n === appViewIndex) return;
        appViewIndex = n;
        track.style.setProperty('--app-index', String(n));
        tabButtons.forEach((btn) => {
            const i = Number(btn.getAttribute('data-app-view'));
            const on = i === n;
            btn.classList.toggle('is-active', on);
            btn.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        panels.forEach((panel, i) => {
            if (!panel) return;
            panel.setAttribute('aria-hidden', i === n ? 'false' : 'true');
        });
        if (replaceHash) {
            const nextHash = `#${HASH_KEYS[n]}`;
            if (location.hash !== nextHash) {
                history.pushState(null, '', `${location.pathname}${location.search}${nextHash}`);
            }
        }
        document.title = titles[n] || titles[0];
        if (n === 1) refreshChatStub();
    }

    tabButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            const i = Number(btn.getAttribute('data-app-view'));
            setAppView(i);
        });
    });

    function syncViewFromUrl() {
        appViewIndex = -1;
        setAppView(indexFromHash(), { replaceHash: false });
    }

    window.addEventListener('hashchange', syncViewFromUrl);
    window.addEventListener('popstate', syncViewFromUrl);

    const logo = document.getElementById('home-logo');
    if (logo) {
        logo.addEventListener('click', () => {
            if (appViewIndex === 0) {
                const homeScroll = document.querySelector('#app-panel-home .home-main');
                if (homeScroll) homeScroll.scrollTo({ top: 0, behavior: 'smooth' });
                return;
            }
            setAppView(0);
        });
    }

    if (track && tabButtons.length) {
        setAppView(indexFromHash(), { replaceHash: false });
    }

    if (btnOpenChat) {
        btnOpenChat.addEventListener('click', () => {
            refreshChatStub();
            if (appViewIndex !== 1) setAppView(1);
        });
    }

    // ==========================================
    // CHAT UI — POST /chat/
    // ==========================================
    const chatMessages = document.getElementById('chat-messages');
    const chatInput    = document.getElementById('chat-input');
    const chatSendBtn  = document.getElementById('chat-send-btn');

    function addMessage(text, role = 'user') {
        if (!chatMessages) return;
        const div = document.createElement('div');
        div.className = `chat-msg chat-msg--${role}`;
        div.textContent = text;
        div.style.cssText = role === 'user'
            ? 'background:rgba(255,255,255,0.2);padding:12px 16px;border-radius:16px;border-bottom-right-radius:4px;max-width:85%;align-self:flex-end;'
            : 'background:rgba(255,255,255,0.1);padding:12px 16px;border-radius:16px;border-bottom-left-radius:4px;max-width:85%;align-self:flex-start;';
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addTyping() {
        const div = document.createElement('div');
        div.id = 'chat-typing';
        div.textContent = '...';
        div.style.cssText = 'background:rgba(255,255,255,0.1);padding:12px 16px;border-radius:16px;border-bottom-left-radius:4px;max-width:85%;align-self:flex-start;opacity:0.6;';
        chatMessages?.appendChild(div);
        if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeTyping() {
        document.getElementById('chat-typing')?.remove();
    }

    async function sendChatMessage() {
        const question = (chatInput?.value || '').trim();
        if (!question) return;

        const city = (locationText?.textContent || '').trim() || defaultCityQuery();
        if (!city || city === '—') {
            alert('Please search for a city first on the Home tab!');
            return;
        }

        chatInput.value = '';
        addMessage(question, 'user');
        addTyping();
        if (chatSendBtn) chatSendBtn.disabled = true;

        try {
            const res = await fetch('/chat/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ city, question })
            });
            if (!res.ok) throw new Error(`Server error (${res.status})`);
            const data = await res.json();
            removeTyping();
            addMessage(data.answer || 'No answer received.', 'ai');
        } catch (err) {
            removeTyping();
            addMessage(`❌ ${err.message || 'Connection error.'}`, 'ai');
        } finally {
            if (chatSendBtn) chatSendBtn.disabled = false;
            chatInput?.focus();
        }
    }

    if (chatSendBtn) chatSendBtn.addEventListener('click', sendChatMessage);
    if (chatInput) {
        chatInput.addEventListener('keypress', e => {
            if (e.key === 'Enter') sendChatMessage();
        });
    }
});