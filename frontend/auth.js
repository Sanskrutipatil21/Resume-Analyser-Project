import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  updateProfile
} from "https://www.gstatic.com/firebasejs/12.4.0/firebase-auth.js";

import { auth } from "./firebase.js";

/* =========================
   SIGN UP
========================= */
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

      // user is no longer guest
      localStorage.removeItem("authMode");

      window.location.href = "home.html";
    } catch (err) {
      alert(err.message);
    }
  });
}

/* =========================
   SIGN IN
========================= */
const loginForm = document.getElementById("loginForm");

if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value.trim();

    try {
      await signInWithEmailAndPassword(auth, email, password);

      // user is no longer guest
      localStorage.removeItem("authMode");

      window.location.href = "home.html";
    } catch (error) {
      alert(error.message);
    }
  });
}

/* =========================
   STAY LOGGED OUT (GUEST)
========================= */
const guestBtn = document.getElementById("guestBtn");

if (guestBtn) {
  guestBtn.addEventListener("click", async () => {
    // force Firebase logout
    await signOut(auth);

    // enable guest mode
    localStorage.setItem("authMode", "guest");

    window.location.href = "home.html";
  });
}

/* =========================
   LOGOUT
========================= */
window.logoutUser = async () => {
  await signOut(auth);
  localStorage.clear(); // removes guest mode too
  window.location.href = "index.html";
};

/* =========================
   USER NAME HANDLING
========================= */
onAuthStateChanged(auth, (user) => {
  const userNameEl = document.getElementById("userName");
  if (!userNameEl) return;

  const authMode = localStorage.getItem("authMode");

  // Guest mode always wins
  if (authMode === "guest") {
    userNameEl.innerText = "Guest";
    return;
  }

  // Firebase user
  if (user) {
    userNameEl.innerText =
      user.displayName || user.email.split("@")[0];
  } else {
    userNameEl.innerText = "Guest";
  }
});
