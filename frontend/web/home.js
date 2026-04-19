document.addEventListener('DOMContentLoaded', async () => {
    const LAST_CITY_KEY = 'weatherwise_last_city';

    const weatherIconEl = document.getElementById('weather-icon');
    const timeTextEl = document.getElementById('time-text');
    const locationText = document.getElementById('location-text');
    const tempText = document.getElementById('temp-text');
    const dateEl = document.getElementById('home-date');
    const userNameEl = document.getElementById('home-user-name');
    const searchInput = document.getElementById('home-city-search');
    const goBtn = document.getElementById('home-city-go');
    const suggestionsEl = document.getElementById('home-city-suggestions');
    const hourlyList = document.getElementById('home-hourly-list');
    const feelPanel = document.getElementById('home-feel-panel');
    const btnOpenFeel = document.getElementById('btn-open-feel');
    const feelResult = document.getElementById('home-feel-result');
    const chatPrefill = document.getElementById('home-chat-prefill');
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
    /** @type {Record<string, unknown> | null} */
    let lastRecommendPayload = null;
    let chatAutostartDone = false;
    let cityFetchAbort = null;
    let cityFetchInflight = 0;
    let placesCountries = null;
    /** @type {{ country: string, city: string, lo: string }[] | null} */
    let placesFlat = null;
    let pendingCountry = '';
    let syncingSearchInput = false;
    let suggestTimer = null;
    /** @type {{ country: string, city: string }[]} */
    let suggestionMatchList = [];
    let activeSuggestionIndex = -1;

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
        if (userNameEl) {
            if (!s) userNameEl.textContent = 'Guest';
            else if (s.mode === 'guest') userNameEl.textContent = 'Guest';
            else userNameEl.textContent = s.displayName || s.name || s.email || 'You';
        }
    }

    function apiBase() {
        return typeof window.weatherwiseApiBase === 'function' ? window.weatherwiseApiBase() : '';
    }

    function profileCityDiffersFrom(stored, resolved) {
        return (
            String(stored || '')
                .trim()
                .toLowerCase() !==
            String(resolved || '')
                .trim()
                .toLowerCase()
        );
    }

    async function saveDefaultCityToAccount(country, city) {
        const s = window.WeatherwiseSession && window.WeatherwiseSession.get();
        if (!s || s.mode !== 'signed_in' || !s.token) {
            alert('Sign in to save your city to your account.');
            return;
        }
        const c = String(city || '').trim();
        if (!c) return;
        try {
            const res = await fetch(`${apiBase()}/auth/profile`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${s.token}`,
                },
                body: JSON.stringify({ country: String(country || ''), city: c }),
            });
            const body = await res.json().catch(() => ({}));
            if (!res.ok) {
                const msg = typeof body.detail === 'string' ? body.detail : 'Could not save city to your profile.';
                alert(msg);
                return;
            }
            window.WeatherwiseSession.set({
                ...s,
                country: body.country != null ? body.country : country,
                city: body.city != null ? body.city : c,
            });
        } catch (e) {
            alert(e.message || 'Network error saving city.');
        }
    }

    async function ensurePlacesLoaded() {
        if (placesCountries) return;
        try {
            const res = await fetch('https://countriesnow.space/api/v0.1/countries');
            const json = await res.json();
            if (json.error || !Array.isArray(json.data)) return;
            placesCountries = json.data.slice().sort((a, b) => String(a.country).localeCompare(String(b.country)));
            placesFlat = [];
            for (const row of placesCountries) {
                const ctry = String(row.country || '');
                const cities = Array.isArray(row.cities) ? row.cities : [];
                for (const city of cities) {
                    const cs = String(city);
                    placesFlat.push({ country: ctry, city: cs, lo: cs.toLowerCase() });
                }
            }
        } catch (e) {
            console.warn('Places list unavailable', e);
        }
    }

    const PLACES_MATCH_MAX = 28;
    const PLACES_SCAN_BUDGET = 52000;

    /**
     * @returns {{ matches: { country: string, city: string }[], partial: boolean }}
     */
    function matchPlaces(query) {
        if (!placesCountries || !placesFlat) {
            return { matches: [], partial: false };
        }
        const q = query.trim().toLowerCase();
        if (q.length < 2) return { matches: [], partial: false };
        const out = [];
        const seen = new Set();
        let scanned = 0;
        let partial = false;

        function add(ctry, city) {
            const k = `${ctry}\0${city}`;
            if (seen.has(k)) return;
            seen.add(k);
            out.push({ country: ctry, city });
        }

        for (const row of placesFlat) {
            if (out.length >= PLACES_MATCH_MAX) break;
            scanned += 1;
            if (scanned > PLACES_SCAN_BUDGET) {
                partial = true;
                break;
            }
            if (row.lo.includes(q)) add(row.country, row.city);
        }
        if (out.length < 8) {
            for (const row of placesCountries) {
                if (out.length >= PLACES_MATCH_MAX) break;
                const ctry = String(row.country || '');
                if (!ctry.toLowerCase().includes(q)) continue;
                const cities = (Array.isArray(row.cities) ? row.cities : []).slice().sort();
                for (let i = 0; i < Math.min(18, cities.length) && out.length < PLACES_MATCH_MAX; i += 1) {
                    add(ctry, String(cities[i]));
                }
            }
        }
        return { matches: out, partial };
    }

    function syncSuggestionHighlight() {
        if (!suggestionsEl || !searchInput) return;
        const opts = suggestionsEl.querySelectorAll('li[role="option"]');
        opts.forEach((li, i) => {
            const on = i === activeSuggestionIndex;
            li.classList.toggle('is-active', on);
            li.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        if (activeSuggestionIndex >= 0 && opts[activeSuggestionIndex]) {
            searchInput.setAttribute('aria-activedescendant', opts[activeSuggestionIndex].id);
        } else {
            searchInput.removeAttribute('aria-activedescendant');
        }
    }

    function hideSuggestions() {
        if (!suggestionsEl) return;
        suggestionsEl.hidden = true;
        suggestionsEl.innerHTML = '';
        suggestionMatchList = [];
        activeSuggestionIndex = -1;
        if (searchInput) {
            searchInput.setAttribute('aria-expanded', 'false');
            searchInput.removeAttribute('aria-activedescendant');
        }
    }

    function showSuggestionStatus(text, className) {
        if (!suggestionsEl) return;
        suggestionsEl.innerHTML = '';
        suggestionMatchList = [];
        activeSuggestionIndex = -1;
        if (searchInput) searchInput.removeAttribute('aria-activedescendant');
        const li = document.createElement('li');
        li.className = className || 'home-city-suggest-status';
        li.setAttribute('role', 'status');
        li.textContent = text;
        suggestionsEl.appendChild(li);
        suggestionsEl.hidden = false;
        if (searchInput) searchInput.setAttribute('aria-expanded', 'true');
    }

    function pickSuggestionAtIndex(i) {
        const m = suggestionMatchList[i];
        if (!m) return;
        pendingCountry = m.country;
        syncingSearchInput = true;
        if (searchInput) searchInput.value = m.city;
        syncingSearchInput = false;
        hideSuggestions();
        const picked = String(m.city || '').trim();
        if (!picked) return;
        if (!commitCitySelection(picked)) return;
        void fetchForCity(picked, { askDefaultCity: true });
    }

    function showSuggestions(matches, queryTrimmed, partialScan) {
        if (!suggestionsEl) return;
        suggestionsEl.innerHTML = '';
        const qt = String(queryTrimmed || '').trim();
        suggestionMatchList = matches.slice();
        activeSuggestionIndex = -1;
        if (!matches.length) {
            if (qt.length >= 2) {
                showSuggestionStatus(
                    'No matches in the list — press Search to try this name.',
                    'home-city-suggest-status',
                );
            } else {
                hideSuggestions();
            }
            return;
        }
        matches.forEach((m, i) => {
            const li = document.createElement('li');
            li.setAttribute('role', 'option');
            li.setAttribute('aria-selected', 'false');
            li.id = `home-city-sug-${i}`;
            const line = document.createElement('span');
            line.className = 'suggestion-line';
            line.textContent = m.city;
            const sub = document.createElement('span');
            sub.className = 'suggestion-country';
            sub.textContent = m.country;
            li.appendChild(line);
            li.appendChild(sub);
            li.addEventListener('mouseenter', () => {
                activeSuggestionIndex = i;
                syncSuggestionHighlight();
            });
            li.addEventListener('mousedown', (e) => {
                e.preventDefault();
                pickSuggestionAtIndex(i);
            });
            suggestionsEl.appendChild(li);
        });
        if (partialScan) {
            const note = document.createElement('li');
            note.className = 'home-city-suggest-hint';
            note.setAttribute('role', 'presentation');
            note.textContent = 'List truncated — type more letters or press Search.';
            suggestionsEl.appendChild(note);
        }
        suggestionsEl.hidden = false;
        if (searchInput) searchInput.setAttribute('aria-expanded', 'true');
        syncSuggestionHighlight();
    }

    async function refreshSuggestionsFromInput() {
        if (!searchInput || syncingSearchInput) return;
        const raw = searchInput.value || '';
        const qt = raw.trim();
        if (!qt.length) {
            hideSuggestions();
            return;
        }
        if (qt.length === 1) {
            showSuggestionStatus(
                'Keep typing for country and city suggestions…',
                'home-city-suggest-hint',
            );
            void ensurePlacesLoaded();
            return;
        }
        if (!placesCountries) {
            showSuggestionStatus('Loading city list…', 'home-city-suggest-status');
        }
        await ensurePlacesLoaded();
        if (!placesCountries) {
            showSuggestionStatus(
                'Could not load suggestions — press Search to continue.',
                'home-city-suggest-status',
            );
            return;
        }
        const { matches, partial } = matchPlaces(raw);
        showSuggestions(matches, qt, partial);
    }

    /**
     * Persist chosen city/country in session + storage before /recommend resolves.
     * Account default city is updated only after a successful load (see fetchForCity).
     */
    function commitCitySelection(rawCity) {
        const city = (rawCity || '').trim();
        if (!city) {
            alert('Please enter a city name.');
            return false;
        }
        const countryHint = String(pendingCountry || '').trim();
        sessionStorage.setItem(LAST_CITY_KEY, city);
        if (locationText) locationText.textContent = city;
        syncingSearchInput = true;
        if (searchInput) searchInput.value = city;
        syncingSearchInput = false;

        if (window.WeatherwiseSession) {
            const s = window.WeatherwiseSession.get();
            if (s) {
                window.WeatherwiseSession.set({
                    ...s,
                    city,
                    country: countryHint || s.country || '',
                });
            }
        }
        hideSuggestions();
        pendingCountry = '';
        return true;
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
            hourlyList.innerHTML =
                '<li class="home-hourly-placeholder">No hourly data yet.</li>';
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

    async function fetchForCity(city, opts) {
        const askDefaultCity =
            opts && typeof opts === 'object' && opts.askDefaultCity === true;
        city = (city || '').trim();
        if (!city) {
            alert('Please enter a city name.');
            return;
        }

        if (cityFetchAbort) cityFetchAbort.abort();
        cityFetchAbort = new AbortController();
        const { signal } = cityFetchAbort;

        cityFetchInflight += 1;
        if (goBtn) {
            goBtn.classList.add('is-loading');
            const icon = goBtn.querySelector('.material-symbols-outlined');
            if (icon) icon.textContent = 'hourglass_empty';
        }

        try {
            const res = await fetch(`${apiBase()}/recommend/?city=${encodeURIComponent(city)}`, { signal });
            if (res.status === 404) throw new Error(`City "${city}" not found.`);
            if (res.status === 503) throw new Error('Weather service temporarily unavailable.');
            if (!res.ok) throw new Error(`Server error (${res.status})`);

            const data = await res.json();
            if (signal.aborted) return;
            const resolvedCity = data.city || city;
            sessionStorage.setItem(LAST_CITY_KEY, resolvedCity);
            syncingSearchInput = true;
            if (searchInput) searchInput.value = resolvedCity;
            syncingSearchInput = false;

            if (window.WeatherwiseSession) {
                const s = window.WeatherwiseSession.get();
                if (s) {
                    window.WeatherwiseSession.set({
                        ...s,
                        city: resolvedCity,
                        country: data.country != null ? data.country : s.country,
                    });
                }
            }

            if (locationText) locationText.textContent = resolvedCity;
            if (tempText) tempText.textContent = `${Math.round(data.temperature)}°C`;
            currentCityOffset = data.utc_offset;

            const utcMs = Date.now() + new Date().getTimezoneOffset() * 60000;
            const cityHour = new Date(utcMs + data.utc_offset * 1000).getHours();
            applyBackground(getTimeSlot(cityHour), data.weather_effect || 'clear');
            if (window.setWeatherEffect) window.setWeatherEffect(data.weather_effect || 'clear');
            updateClock();

            const c = document.getElementById('home-ai-clothing');
            const u = document.getElementById('home-ai-umbrella');
            const sc = document.getElementById('home-ai-score');
            const tip = document.getElementById('home-ai-tip');
            if (c) c.textContent = data.clothing_recommendation || '—';
            if (u) u.textContent = data.umbrella_needed ? 'Yes ☂️' : 'No';
            if (sc) sc.textContent = `${data.suitability_score}/10`;
            if (tip) tip.textContent = data.tip_text || '—';

            renderHourly(data.forecast_24h || []);
            lastRecommendPayload = data;

            const sess = window.WeatherwiseSession && window.WeatherwiseSession.get();
            if (
                askDefaultCity &&
                sess &&
                sess.mode === 'signed_in' &&
                sess.token &&
                profileCityDiffersFrom(sess.city, resolvedCity)
            ) {
                const ok = window.confirm(
                    `Set “${resolvedCity}” as your default city on your account?`,
                );
                if (ok) await saveDefaultCityToAccount(data.country, resolvedCity);
            }

            hideSuggestions();
        } catch (err) {
            if (err.name === 'AbortError') return;
            console.error(err);
            var msg = err && err.message ? err.message : 'Connection error.';
            if (msg === 'Failed to fetch') {
                msg =
                    'Could not reach the API (network error). Start uvicorn on port 8000, ' +
                    'or open the app at http://127.0.0.1:8000/home.html so the same server serves the UI.';
            }
            alert(msg);
        } finally {
            cityFetchInflight -= 1;
            if (goBtn && cityFetchInflight <= 0) {
                goBtn.classList.remove('is-loading');
                const icon = goBtn.querySelector('.material-symbols-outlined');
                if (icon) icon.textContent = 'search';
            }
        }
    }

    const cityForm = document.getElementById('home-city-form');
    if (cityForm) {
        cityForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const raw = (searchInput && searchInput.value) || '';
            if (!commitCitySelection(raw)) return;
            const cityToFetch = ((searchInput && searchInput.value) || raw).trim();
            queueMicrotask(() => {
                void fetchForCity(cityToFetch, { askDefaultCity: true });
            });
        });
    }

    if (searchInput && suggestionsEl) {
        searchInput.addEventListener('focus', () => {
            void refreshSuggestionsFromInput();
        });
        searchInput.addEventListener('input', () => {
            if (syncingSearchInput) return;
            pendingCountry = '';
            clearTimeout(suggestTimer);
            suggestTimer = setTimeout(() => {
                void refreshSuggestionsFromInput();
            }, 120);
        });
        searchInput.addEventListener('blur', () => {
            setTimeout(() => hideSuggestions(), 200);
        });
        searchInput.addEventListener('keydown', (e) => {
            const opts = suggestionsEl.querySelectorAll('li[role="option"]');
            const n = opts.length;
            const listOpen = !suggestionsEl.hidden && n > 0;

            if (e.key === 'Escape') {
                if (!suggestionsEl.hidden) {
                    e.preventDefault();
                    hideSuggestions();
                }
                return;
            }

            if (!listOpen) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                activeSuggestionIndex = activeSuggestionIndex < n - 1 ? activeSuggestionIndex + 1 : 0;
                syncSuggestionHighlight();
                opts[activeSuggestionIndex].scrollIntoView({ block: 'nearest' });
                return;
            }
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeSuggestionIndex = activeSuggestionIndex > 0 ? activeSuggestionIndex - 1 : n - 1;
                syncSuggestionHighlight();
                opts[activeSuggestionIndex].scrollIntoView({ block: 'nearest' });
                return;
            }
            if (e.key === 'Enter' && activeSuggestionIndex >= 0) {
                e.preventDefault();
                pickSuggestionAtIndex(activeSuggestionIndex);
            }
        });
    }

    updateClock();
    setInterval(updateClock, 1000);

    try {
        if (window.refreshWeatherwiseSessionFromServer) {
            await window.refreshWeatherwiseSessionFromServer();
        }
    } catch (err) {
        console.warn('Session refresh failed', err);
    }
    initUserLabel();

    const startCity = defaultCityQuery();
    syncingSearchInput = true;
    if (searchInput && startCity) searchInput.value = startCity;
    if (locationText && startCity) locationText.textContent = startCity;
    syncingSearchInput = false;
    if (startCity) fetchForCity(startCity);

    if (btnOpenFeel && feelPanel) {
        btnOpenFeel.addEventListener('click', () => {
            feelPanel.hidden = !feelPanel.hidden;
            feelResult.textContent = '';
        });
    }

    function feelLoginCtaHtml(lead) {
        const prefix = lead || 'Please';
        return `${prefix} <a href="login.html" style="font-weight:700;color:inherit;">log in</a> to leave community reports.`;
    }

    function currentReportCity() {
        const loc = locationText && locationText.textContent.trim();
        if (loc && loc !== '—') return loc;
        const fromSearch = searchInput && searchInput.value.trim();
        if (fromSearch) return fromSearch;
        return defaultCityQuery();
    }

    function setFeelButtonsDisabled(disabled) {
        document.querySelectorAll('.home-feel-btns [data-feel]').forEach((b) => {
            b.disabled = disabled;
        });
    }

    let feelSubmitting = false;

    document.querySelectorAll('.home-feel-btns [data-feel]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            if (!feelResult) return;
            const s = window.WeatherwiseSession && window.WeatherwiseSession.get();
            if (!s || s.mode === 'guest' || !s.token) {
                feelResult.innerHTML = feelLoginCtaHtml('Please');
                return;
            }
            const rating = btn.getAttribute('data-feel');
            if (!rating) return;
            const city = currentReportCity().trim();
            if (!city) {
                feelResult.textContent = 'Load a city first, then share how it feels.';
                return;
            }
            if (feelSubmitting) return;
            feelSubmitting = true;
            setFeelButtonsDisabled(true);
            feelResult.textContent = 'Sending…';
            try {
                const res = await fetch(`${apiBase()}/report`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${s.token}`,
                    },
                    body: JSON.stringify({ city, rating }),
                });
                let body = {};
                try {
                    body = await res.json();
                } catch (_) {
                    body = {};
                }
                if (res.status === 401) {
                    feelResult.innerHTML = feelLoginCtaHtml('Session expired — please');
                    return;
                }
                if (!res.ok) {
                    let msg = typeof body.detail === 'string' ? body.detail : '';
                    if (!msg && Array.isArray(body.detail)) {
                        msg = body.detail
                            .map((x) => (x && (x.msg || x.message)) || '')
                            .filter(Boolean)
                            .join(' ');
                    }
                    feelResult.textContent = msg || `Could not save report (${res.status}).`;
                    return;
                }
                feelResult.textContent = 'Thanks — your report was saved and helps tune advice for others.';
            } catch (err) {
                let msg = err && err.message ? err.message : 'Connection error.';
                if (msg === 'Failed to fetch') {
                    msg =
                        'Could not reach the API (network error). Start the backend on port 8000, ' +
                        'or open the app from the same host as the API.';
                }
                feelResult.textContent = msg;
            } finally {
                feelSubmitting = false;
                setFeelButtonsDisabled(false);
            }
        });
    });

    const chatStubEl = document.getElementById('chat-stub-context');

    function refreshChatStub() {
        if (!chatStubEl) return;
        const params = new URLSearchParams(location.search);
        const qFromUrl = (params.get('q') || params.get('question') || '').trim();
        const cityFromUrl = (params.get('city') || '').trim();
        const q =
            qFromUrl ||
            (chatPrefill && chatPrefill.value.trim()) ||
            '';
        const cityRaw =
            cityFromUrl ||
            (locationText && locationText.textContent.trim()) ||
            defaultCityQuery() ||
            '';
        const city = cityRaw && cityRaw !== '—' ? cityRaw : '';
        chatStubEl.textContent = city
            ? `City: ${city}. ${q ? `Question: “${q}”.` : 'Ask anything about the weather.'}`
            : 'Pick a city on Home to personalize chat context.';
    }

    const chatTranscript = document.getElementById('home-chat-transcript');
    const chatEmpty = document.getElementById('home-chat-empty');
    const chatTyping = document.getElementById('home-chat-typing');
    const chatForm = document.getElementById('home-chat-form');
    const homeChatInputEl = document.getElementById('home-chat-input');
    const homeChatSendBtn = document.getElementById('home-chat-send');
    const feedList = document.getElementById('home-feed-list');
    const feedStatus = document.getElementById('home-feed-status');

    function hideChatEmpty() {
        if (chatEmpty) chatEmpty.hidden = true;
    }

    function appendChatBubble(text, role) {
        if (!chatTranscript) return;
        hideChatEmpty();
        const div = document.createElement('div');
        div.className = `home-chat-bubble home-chat-bubble--${role}`;
        div.textContent = text;
        chatTranscript.appendChild(div);
        chatTranscript.scrollTop = chatTranscript.scrollHeight;
    }

    function setChatTyping(on) {
        if (chatTyping) chatTyping.hidden = !on;
    }

    async function sendChatMessage() {
        const question = (homeChatInputEl && homeChatInputEl.value) ? homeChatInputEl.value.trim() : '';
        if (!question) return;

        const city = (locationText && locationText.textContent.trim()) || defaultCityQuery() || '';
        if (!city || city === '—') {
            alert('Please search for a city first on the Home tab!');
            return;
        }

        if (homeChatInputEl) homeChatInputEl.value = '';
        appendChatBubble(question, 'user');
        setChatTyping(true);
        if (homeChatSendBtn) homeChatSendBtn.disabled = true;

        try {
            const res = await fetch(`${apiBase()}/chat/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ city, question }),
            });
            if (!res.ok) throw new Error(`Server error (${res.status})`);
            const data = await res.json();
            appendChatBubble(data.answer || 'No answer received.', 'ai');
        } catch (err) {
            appendChatBubble(`❌ ${err.message || 'Connection error.'}`, 'ai');
        } finally {
            setChatTyping(false);
            if (homeChatSendBtn) homeChatSendBtn.disabled = false;
            if (homeChatInputEl) homeChatInputEl.focus();
        }
    }

    function maybeAutostartChatFromUrl() {
        if (chatAutostartDone || !homeChatInputEl) return;
        const params = new URLSearchParams(location.search);
        if (params.get('autostart') !== '1') return;
        const q = (params.get('q') || params.get('question') || '').trim();
        if (!q) return;
        chatAutostartDone = true;
        homeChatInputEl.value = q;
        void sendChatMessage();
    }

    function renderFeedFromCache() {
        if (!feedList) return;
        if (!lastRecommendPayload) {
            if (feedStatus) feedStatus.textContent = 'Load a city on Home to see hourly data here.';
            feedList.innerHTML = '';
            return;
        }
        if (feedStatus) feedStatus.textContent = '';
        const rows = lastRecommendPayload.forecast_24h || [];
        feedList.innerHTML = '';
        if (!rows.length) {
            feedList.innerHTML = '<li class="home-hourly-placeholder">No hourly rows yet.</li>';
            return;
        }
        rows.slice(0, 24).forEach((row) => {
            const li = document.createElement('li');
            li.className = 'home-feed-row';
            let timeLabel = row.time || '';
            if (timeLabel && timeLabel.includes('T')) {
                const d = new Date(timeLabel);
                if (!Number.isNaN(d.getTime())) {
                    timeLabel = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                }
            }
            const temp = row.temperature != null ? `${Math.round(row.temperature)}°C` : '—';
            const eff = row.weather_effect || '';
            li.textContent = `${timeLabel}  ${temp}  ${eff}`;
            feedList.appendChild(li);
        });
    }

    document.querySelectorAll('.home-chat-chip').forEach((btn) => {
        btn.addEventListener('click', () => {
            const fill = btn.getAttribute('data-chat-fill');
            const send = btn.getAttribute('data-chat-send');
            if (fill && homeChatInputEl) {
                homeChatInputEl.value = fill;
                homeChatInputEl.focus();
            } else if (send && homeChatInputEl) {
                homeChatInputEl.value = send;
                void sendChatMessage();
            }
        });
    });

    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            void sendChatMessage();
        });
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
        if (n === 1) {
            refreshChatStub();
            maybeAutostartChatFromUrl();
        }
        if (n === 3) renderFeedFromCache();
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
});
