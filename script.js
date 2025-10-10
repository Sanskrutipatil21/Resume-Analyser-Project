// Select container and toggle buttons
const container = document.querySelector('.container');
const signupBtn = document.querySelector('.signup-btn'); // Button in toggle panel for Sign Up
const loginBtn = document.querySelector('.login-btn');   // Button in toggle panel for Login

// Show signup form when clicking "Sign Up"
signupBtn.addEventListener('click', () => {
    container.classList.add('active');  // Activate container (CSS will show signup)
});

// Show login form when clicking "Login"
loginBtn.addEventListener('click', () => {
    container.classList.remove('active');  // Remove active (CSS will show login)
});
