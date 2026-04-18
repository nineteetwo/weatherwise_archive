document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('btn-submit-login');
    const emailInput = document.getElementById('email-input');
    const passInput = document.getElementById('pass-input');
    if (!btn || !window.WeatherwiseSession) return;

    btn.addEventListener('click', () => {
        const email = emailInput && emailInput.value.trim();
        if (!email) {
            alert('Please enter your email.');
            return;
        }
        if (!passInput || !passInput.value) {
            alert('Please enter your password.');
            return;
        }

        window.WeatherwiseSession.set({
            mode: 'signed_in',
            email,
            at: Date.now(),
        });
        window.location.href = 'index.html';
    });
});
