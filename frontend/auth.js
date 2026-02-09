import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  updateProfile
} from "https://www.gstatic.com/firebasejs/12.4.0/firebase-auth.js";

import { auth } from "./firebase.js";

// -------- SIGN UP --------
const signUpForm = document.querySelector(".sign-up form");

if (signUpForm) {
  signUpForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = document.getElementById("signupName").value.trim();
    const email = document.getElementById("signupEmail").value.trim();
    const password = document.getElementById("signupPassword").value.trim();

    if (!name || !email || !password) {
      alert("Fill all fields");
      return;
    }

    try {
      const userCred = await createUserWithEmailAndPassword(auth, email, password);
      await updateProfile(userCred.user, { displayName: name });

      // Remove guest mode after login/signup
      localStorage.removeItem("guest");

      window.location.href = "home.html";
    } catch (err) {
      alert(err.message);
    }
  });
}

// -------- SIGN IN --------
const loginForm = document.getElementById("loginForm");

if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value.trim();

    try {
      await signInWithEmailAndPassword(auth, email, password);

      // Remove guest mode after login
      localStorage.removeItem("guest");

      window.location.href = "home.html";
    } catch (error) {
      alert(error.message);
    }
  });
}

// -------- LOGOUT --------
window.logoutUser = async () => {
  await signOut(auth);

  // Optional: clear guest too
  localStorage.removeItem("guest");

  window.location.href = "index.html";
};

onAuthStateChanged(auth, (user) => {
  const userNameEl = document.getElementById("userName");
  if (!userNameEl) return;

  // Check guest mode
  const isGuest = localStorage.getItem("guest") === "true";

  if (isGuest) {
    userNameEl.innerText = "Guest";
    return;
  }

  // Normal user
  if (user) {
    userNameEl.innerText =
      user.displayName || user.email.split("@")[0];
  } else {
    userNameEl.innerText = "Guest";
  }
});

