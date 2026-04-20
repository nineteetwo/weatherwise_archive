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
    const mydayHourlyList = document.getElementById('myday-hourly-list');
    const mydayLead = document.getElementById('myday-lead');
    const feelPanel = document.getElementById('home-feel-panel');
    const btnOpenFeel = document.getElementById('btn-open-feel');
    const feelResult = document.getElementById('home-feel-result');
    const feelNote = document.getElementById('home-feel-note');
    const feelPostBtn = document.getElementById('home-feel-post-btn');
    const feelOptionButtons = Array.from(document.querySelectorAll('.home-feel-btns [data-feel]'));
    const chatPrefill = document.getElementById('home-chat-prefill');
    const btnOpenChat = document.getElementById('home-open-chat');
    const feedCityInput = document.getElementById('feed-city-input');
    const feedRefreshBtn = document.getElementById('feed-refresh-btn');
    const feedReportList = document.getElementById('feed-report-list');
    const feedStatus = document.getElementById('feed-status');

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
    let selectedFeel = '';

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

    function getSessionToken() {
        const s = window.WeatherwiseSession && window.WeatherwiseSession.get();
        if (!s || s.mode === 'guest' || !s.token) return '';
        return String(s.token);
    }

    function hourlyEffectMeta(effectRaw) {
        const effect = String(effectRaw || '').toLowerCase();
        if (effect.includes('thunder')) return { icon: '⛈️', label: 'Thunder' };
        if (effect.includes('heavy-rain')) return { icon: '🌧️', label: 'Heavy rain' };
        if (effect.includes('rain')) return { icon: '🌦️', label: 'Rain' };
        if (effect.includes('snow')) return { icon: '❄️', label: 'Snow' };
        if (effect.includes('fog') || effect.includes('mist')) return { icon: '🌫️', label: 'Fog' };
        if (effect.includes('cloud')) return { icon: '☁️', label: 'Cloudy' };
        if (effect.includes('clear') || !effect) return { icon: '☀️', label: 'Clear' };
        return { icon: '🌤️', label: effect.replace(/[-_]+/g, ' ') || 'Weather' };
    }

    function renderHourly(rows, listEl) {
        if (!listEl) return;
        listEl.innerHTML = '';
        if (!rows || !rows.length) {
            listEl.innerHTML = '<li class="home-hourly-placeholder">No hourly data yet.</li>';
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
            const eff = hourlyEffectMeta(row.weather_effect);
            li.innerHTML = `<span class="home-hourly-time">${timeLabel}</span><span class="home-hourly-temp">${temp}</span><span class="home-hourly-eff home-hourly-cond"><span class="home-hourly-icon" aria-hidden="true">${eff.icon}</span><span>${eff.label}</span></span>`;
            listEl.appendChild(li);
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
            if (feedCityInput && (data.city || city)) feedCityInput.value = data.city || city;

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

            const rows = data.forecast_24h || [];
            renderHourly(rows, hourlyList);
            renderHourly(rows, mydayHourlyList);
            if (mydayLead) {
                mydayLead.textContent = rows.length
                    ? `24h timeline for ${data.city || city}.`
                    : `No hourly timeline available for ${data.city || city}.`;
            }
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

    function renderFeed(items) {
        if (!feedReportList) return;
        feedReportList.innerHTML = '';
        if (!items || !items.length) {
            feedReportList.innerHTML = '<li class="home-hourly-placeholder">No reports yet for this city.</li>';
            return;
        }
        items.forEach((item) => {
            const li = document.createElement('li');
            li.className = 'feed-report-item';
            const created = item.created_at
                ? new Date(String(item.created_at).replace(' ', 'T')).toLocaleString()
                : '';
            const author = item.user_name || 'User';
            const note = (item.note || '').trim();
            const top = document.createElement('div');
            top.className = 'feed-report-top';
            const feelEl = document.createElement('span');
            const feelValue = String(item.feel || 'report').toLowerCase();
            feelEl.className = `feed-report-feel feel-${feelValue}`;
            feelEl.textContent = feelValue;
            const metaEl = document.createElement('span');
            metaEl.textContent = `${author}${created ? ` • ${created}` : ''}`;
            top.appendChild(feelEl);
            top.appendChild(metaEl);

            const noteEl = document.createElement('p');
            noteEl.className = 'feed-report-note';
            if (note) {
                noteEl.textContent = note;
            } else {
                noteEl.textContent = 'No note attached.';
                noteEl.style.opacity = '0.75';
            }

            li.appendChild(top);
            li.appendChild(noteEl);
            feedReportList.appendChild(li);
        });
    }

    async function loadFeed(cityArg) {
        if (!feedStatus) return;
        const cityRaw = (cityArg || (feedCityInput && feedCityInput.value) || defaultCityQuery() || '').trim();
        if (!cityRaw) {
            feedStatus.textContent = 'Pick a city on Home or type one here to load reports.';
            renderFeed([]);
            return;
        }
        feedStatus.textContent = `Loading reports for ${cityRaw}...`;
        try {
            const res = await fetch(`/community/reports?city=${encodeURIComponent(cityRaw)}&limit=30`);
            const payload = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(payload.detail || `Server error (${res.status})`);
            if (feedCityInput) feedCityInput.value = cityRaw;
            renderFeed(payload.items || []);
            feedStatus.textContent = `Showing ${payload.count || 0} report(s) for ${cityRaw}.`;
        } catch (err) {
            renderFeed([]);
            feedStatus.textContent = err.message || 'Could not load reports right now.';
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

    if (btnOpenFeel && feelPanel) {
        btnOpenFeel.addEventListener('click', () => {
            feelPanel.hidden = !feelPanel.hidden;
            feelResult.textContent = '';
        });
    }

    function updateFeelSelectionUI() {
        feelOptionButtons.forEach((btn) => {
            const isSelected = (btn.getAttribute('data-feel') || '') === selectedFeel;
            btn.classList.toggle('is-selected', isSelected);
            btn.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
        });
    }

    feelOptionButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            selectedFeel = btn.getAttribute('data-feel') || '';
            updateFeelSelectionUI();
            if (feelResult) feelResult.textContent = 'Selection saved. Press "Post report" to submit.';
        });
    });

    if (feelPostBtn) {
        feelPostBtn.addEventListener('click', async () => {
            const s = window.WeatherwiseSession && window.WeatherwiseSession.get();
            if (!feelResult) return;
            if (!s || s.mode === 'guest') {
                feelResult.innerHTML = 'Please <a href="login.html" style="font-weight:700;color:inherit;">log in</a> to leave community reports.';
                return;
            }
            if (!selectedFeel) {
                feelResult.textContent = 'Please select how it feels first, then press Post report.';
                return;
            }

            const token = getSessionToken();
            if (!token) {
                feelResult.textContent = 'Your session expired. Please sign in again.';
                return;
            }

            const city = ((locationText && locationText.textContent) || defaultCityQuery() || '').trim();
            if (!city || city === '—') {
                feelResult.textContent = 'Please search for a city first so your report is city-specific.';
                return;
            }

            const note = (feelNote && feelNote.value ? feelNote.value : '').trim();
            feelPostBtn.disabled = true;
            feelOptionButtons.forEach((btn) => { btn.disabled = true; });
            try {
                const res = await fetch('/community/reports', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({ city, feel: selectedFeel, note }),
                });
                const payload = await res.json().catch(() => ({}));
                if (!res.ok) throw new Error(payload.detail || `Server error (${res.status})`);
                feelResult.textContent = 'Thanks — your report helps us give better advice!';
                if (feelNote) feelNote.value = '';
                selectedFeel = '';
                updateFeelSelectionUI();
                if (feedCityInput && !feedCityInput.value.trim()) feedCityInput.value = city;
                loadFeed(city);
            } catch (err) {
                feelResult.textContent = err.message || 'Could not submit your report right now.';
            } finally {
                feelPostBtn.disabled = false;
                feelOptionButtons.forEach((btn) => { btn.disabled = false; });
            }
        });
    }

    if (feedRefreshBtn) {
        feedRefreshBtn.addEventListener('click', () => loadFeed());
    }
    if (feedCityInput) {
        if (!feedCityInput.value.trim()) {
            const defaultCity = defaultCityQuery();
            if (defaultCity) feedCityInput.value = defaultCity;
        }
        feedCityInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') loadFeed();
        });
    }

    const chatStubEl = document.getElementById('chat-stub-context');

    function refreshChatStub() {
        if (!chatStubEl) return;
        const params = new URLSearchParams(location.search);
        const qFromUrl = (params.get('q') || '').trim();
        const cityFromUrl = (params.get('city') || '').trim();
        const q = qFromUrl || (chatPrefill && chatPrefill.value.trim()) || '';
        const cityRaw = cityFromUrl || (locationText && locationText.textContent.trim()) || defaultCityQuery() || '';
        const city = cityRaw && cityRaw !== '—' ? cityRaw : '';
        chatStubEl.textContent = city
            ? `City: ${city}. ${q ? `Question: "${q}".` : 'Ask anything about the weather.'}`
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
        if (n === 3) loadFeed();
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