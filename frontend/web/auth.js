document.addEventListener('DOMContentLoaded', () => {
    const signupBtn = document.getElementById('btn-submit-signup');
    const emailInput = document.getElementById('email-input');
    const passInput = document.getElementById('pass-input');
    const passConfirmInput = document.getElementById('pass-confirm-input');

    if (signupBtn && emailInput && passInput && passConfirmInput) {
        const errorMsg = document.createElement('p');
        errorMsg.style.color = '#ff6b6b';
        errorMsg.style.fontSize = '13px';
        errorMsg.style.fontWeight = '500';
        errorMsg.style.display = 'none';
        errorMsg.style.textAlign = 'center';
        
        signupBtn.parentNode.insertBefore(errorMsg, signupBtn);

        signupBtn.addEventListener('click', (e) => {
            const email = emailInput.value;
            const password = passInput.value;
            const confirmPassword = passConfirmInput.value;
            
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            const passRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$/;

            if (!emailRegex.test(email)) {
                e.preventDefault();
                errorMsg.textContent = "Please enter a valid email address.";
                errorMsg.style.display = 'block';
                return;
            }

            if (password !== confirmPassword) {
                e.preventDefault();
                errorMsg.textContent = "Passwords do not match!";
                errorMsg.style.display = 'block';
                return;
            }

            if (!passRegex.test(password)) {
                e.preventDefault();
                errorMsg.textContent = "Password must include uppercase, lowercase letters and a number.";
                errorMsg.style.display = 'block';
                return;
            }

            errorMsg.style.display = 'none';

            const nameInput = document.getElementById('name-input');
            const displayName = (nameInput && nameInput.value.trim()) || email.split('@')[0];

            if (window.WeatherwiseSession) {
                window.WeatherwiseSession.set({
                    mode: 'signed_in',
                    email,
                    displayName,
                    at: Date.now(),
                });
            }
            window.location.href = 'index.html';
        });
    }
});