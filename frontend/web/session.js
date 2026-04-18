(function (global) {
    var KEY = 'weatherwise_session';

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
