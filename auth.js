// Import Firebase SDKs
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.4.0/firebase-app.js";
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword } 
from "https://www.gstatic.com/firebasejs/12.4.0/firebase-auth.js";

// Your Firebase config
const firebaseConfig = {
  apiKey: "AIzaSyD2g-a5Z9uvzMuAe7o0-00pXz3HK-Mupxk",
  authDomain: "login-signup-app-dd873.firebaseapp.com",
  projectId: "login-signup-app-dd873",
  storageBucket: "login-signup-app-dd873.firebasestorage.app",
  messagingSenderId: "174804431167",
  appId: "1:174804431167:web:c8f97e4676a53a79dde38a"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

console.log(" Firebase initialized successfully!");

// -------------------- SIGN UP --------------------
const signUpForm = document.querySelector('.sign-up form');
signUpForm.addEventListener('submit', (e) => {
  e.preventDefault();

  const name = signUpForm.querySelector('input[type="text"]').value;
  const email = signUpForm.querySelector('input[type="email"]').value;
  const password = signUpForm.querySelector('input[type="password"]').value;

  createUserWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
      
       console.log("User created:", userCredential.user);
    signUpForm.reset();

    // Redirect to home page after signup
    window.location.href = "home.html";
    })





    
    .catch((error) => {
      alert(" " + error.message);
      console.error(error);
    });
});

// -------------------- SIGN IN --------------------
const signInForm = document.querySelector('.sign-in form');
signInForm.addEventListener('submit', (e) => {
  e.preventDefault();

  const email = signInForm.querySelector('input[type="email"]').value;
  const password = signInForm.querySelector('input[type="password"]').value;

  signInWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
       console.log("User signed in:", userCredential.user);

    // Redirect to home page after login
    window.location.href = "home.html";
    })
    .catch((error) => {
      alert(" Login failed: " + error.message);
      console.error(error);
    });
});
