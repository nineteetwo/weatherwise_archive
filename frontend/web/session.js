(function (global) {
    var KEY = 'weatherwise_session';

    /**
     * When pages are opened as file://, relative /auth and /recommend URLs do not reach uvicorn.
     * Same-origin loads (http://127.0.0.1:8000/...) use '' so paths stay relative.
     */
    global.weatherwiseApiBase = function weatherwiseApiBase() {
        try {
            if (typeof location === 'undefined') return '';
            if (location.protocol === 'file:') {
                return 'http://127.0.0.1:8000';
            }
            var host = location.hostname;
            var loopback = host === '127.0.0.1' || host === 'localhost' || host === '[::1]';
            if (!loopback) return '';
            var port = location.port;   
            /* Live Server / static dev on loopback with explicit port — API is uvicorn :8000. */
            if (port && port !== '8000') {
                return 'http://127.0.0.1:8000';
            }
        } catch (e) {}
        return '';
    };

    global.WeatherwiseSession = {
        get: function () {
            try {
                var raw = sessionStorage.getItem(KEY);
                return raw ? JSON.parse(raw) : null;
            } catch (e) {
                return null;
            }
        },
        set: function (data) {
            sessionStorage.setItem(KEY, JSON.stringify(data));
        },
        clear: function () {
            sessionStorage.removeItem(KEY);
        },
    };
})(typeof window !== 'undefined' ? window : this);
