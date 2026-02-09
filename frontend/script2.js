// ================= FIREBASE IMPORTS =================
import { auth, db } from "./firebase.js";
import {
  addDoc,
  collection,
  serverTimestamp
} from "https://www.gstatic.com/firebasejs/12.4.0/firebase-firestore.js";
import {
  onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/12.4.0/firebase-auth.js";

// ================= DOM ELEMENTS =================
const resumeInput = document.getElementById("resumeUpload");
const uploadText = document.getElementById("uploadText");
const analyzeBtn = document.getElementById("analyzeBtn");

const companyInput = document.getElementById("companyInput");
const roleInput = document.getElementById("roleInput");
const descriptionInput = document.getElementById("descriptionInput");

const loadingOverlay = document.getElementById("loadingOverlay");

// ================= UI HELPERS =================
function showLoading() {
  if (loadingOverlay) loadingOverlay.classList.remove("hidden");
}

function hideLoading() {
  if (loadingOverlay) loadingOverlay.classList.add("hidden");
}

// ================= FILE NAME DISPLAY =================
if (resumeInput) {
  resumeInput.addEventListener("change", () => {
    if (resumeInput.files.length > 0) {
      uploadText.innerText = resumeInput.files[0].name;
    }
  });
}

// ================= AUTH STATE =================
let currentUser = null;
let authReady = false;

onAuthStateChanged(auth, (user) => {
  currentUser = user;
  authReady = true;
});

// ================= ANALYZE RESUME =================
if (analyzeBtn) {
  analyzeBtn.addEventListener("click", async () => {

    // Wait for Firebase to initialize
    if (!authReady) {
      alert("Please wait a moment and try again.");
      return;
    }

    // ---------- Validation ----------
    if (resumeInput.files.length === 0) {
      alert("Please upload your resume.");
      return;
    }

    if (companyInput.value.trim() === "") {
      alert("Please enter target company.");
      return;
    }

    if (roleInput.value.trim() === "") {
      alert("Please enter target job role.");
      return;
    }

    // ---------- Guest / Login Check ----------
    const isGuest = localStorage.getItem("guest") === "true";

    if (!currentUser && !isGuest) {
      alert("Please login or continue as guest.");
      return;
    }

    // ---------- UI LOCK ----------
    analyzeBtn.disabled = true;
    analyzeBtn.innerText = "Analyzing...";
    showLoading();

    // ---------- Prepare Form Data ----------
    const formData = new FormData();
    formData.append("resume", resumeInput.files[0]);
    formData.append("company", companyInput.value.trim());
    formData.append("role", roleInput.value.trim());
    formData.append("description", descriptionInput.value.trim());

    try {
      // ---------- Updated: Use Render Backend ----------
      const backendURL = "https://resume-analyser-project.onrender.com";
      const response = await fetch(`${backendURL}/analyze`, {
        method: "POST",
        body: formData
      });

      const result = await response.json();

      if (!response.ok || result.error) {
        throw new Error(result.error || "Resume analysis failed");
      }

      // ---------- SAVE TO FIRESTORE (Only if logged in) ----------
      if (currentUser) {
        await addDoc(
          collection(db, "resumeHistory", currentUser.uid, "analyses"),
          {
            company: companyInput.value.trim(),
            role: roleInput.value.trim(),
            score: Number(result.match_score) || 0,
            fullResult: result,
            createdAt: serverTimestamp()
          }
        );
      }

      // ---------- Store result ----------
      localStorage.setItem("analysisResult", JSON.stringify(result));

      // ---------- Redirect ----------
      window.location.href = "result.html";

    } catch (error) {
      console.error(error);
      alert("Server error. Please wait and try again.");
    } finally {
      hideLoading();
      analyzeBtn.disabled = false;
      analyzeBtn.innerText = "Analyse Resume";
    }
  });
}
