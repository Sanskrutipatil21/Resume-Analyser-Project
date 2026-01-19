// firebase.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.4.0/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/12.4.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyD2g-a5Z9uvzMuAe7o0-00pXz3HK-Mupxk",
  authDomain: "login-signup-app-dd873.firebaseapp.com",
  projectId: "login-signup-app-dd873",
  storageBucket: "login-signup-app-dd873.firebasestorage.app",
  messagingSenderId: "174804431167",
  appId: "1:174804431167:web:c8f97e4676a53a79dde38a"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
