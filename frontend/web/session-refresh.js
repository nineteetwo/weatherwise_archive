(function (global) {
    var inFlight = null;

    /**
     * If the user is signed in with a JWT, checks it against GET /auth/me.
     * Merges fresh profile fields on success; clears session on 401/403/404 only.
     * Does not attach the token to other API routes (e.g. /recommend/).
     * Concurrent callers share one request.
     */
    global.refreshWeatherwiseSessionFromServer = async function refreshWeatherwiseSessionFromServer() {
        if (inFlight) return inFlight;
        inFlight = (async function doRefresh() {
            const W = global.WeatherwiseSession;
            if (!W) return;
            const s = W.get();
            if (!s || s.mode !== 'signed_in' || !s.token) return;
            try {
                const res = await fetch('/auth/me', {
                    headers: { Authorization: 'Bearer ' + s.token },
                });
                if (res.ok) {
                    const u = await res.json();
                    W.set({
                        ...s,
                        name: u.name,
                        displayName: u.name,
                        email: u.email,
                        country: u.country,
                        city: u.city,
                        at: Date.now(),
                    });
                    return;
                }
                if (res.status === 401 || res.status === 403 || res.status === 404) {
                    W.clear();
                }
            } catch (_) {
                /* keep session on network failure */
            }
        })().finally(function () {
            inFlight = null;
        });
        return inFlight;
    };
})(typeof window !== 'undefined' ? window : this);
