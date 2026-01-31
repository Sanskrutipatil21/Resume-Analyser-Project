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

// ================= BACKEND URL =================
// LOCAL:
// const BACKEND_URL = "http://127.0.0.1:8000/analyze";

// PRODUCTION (Render):
const BACKEND_URL = "https://resume-analyser-project.onrender.com/analyze";

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
  loadingOverlay.classList.remove("hidden");
}

function hideLoading() {
  loadingOverlay.classList.add("hidden");
}

// ================= FILE NAME DISPLAY =================
resumeInput.addEventListener("change", () => {
  if (resumeInput.files.length > 0) {
    uploadText.innerText = resumeInput.files[0].name;
  }
});

// ================= AUTH STATE =================
let currentUser = null;

onAuthStateChanged(auth, (user) => {
  currentUser = user;
});

// ================= ANALYZE RESUME =================
analyzeBtn.addEventListener("click", async () => {

  // ---------- VALIDATION ----------
  if (resumeInput.files.length === 0) {
    alert("Please upload your resume.");
    return;
  }

  if (!companyInput.value.trim()) {
    alert("Please enter target company.");
    return;
  }

  if (!roleInput.value.trim()) {
    alert("Please enter target job role.");
    return;
  }

  if (!currentUser) {
    alert("You must be logged in.");
    return;
  }

  // ---------- UI LOCK ----------
  analyzeBtn.disabled = true;
  analyzeBtn.innerText = "Analyzing...";
  showLoading();

  // ---------- FORM DATA ----------
  const formData = new FormData();
  formData.append("resume", resumeInput.files[0]);
  formData.append("company", companyInput.value.trim());
  formData.append("role", roleInput.value.trim());
  formData.append("description", descriptionInput.value.trim());

  try {
    // ---------- CALL BACKEND ----------
    const response = await fetch(BACKEND_URL, {
      method: "POST",
      body: formData
    });

    const result = await response.json();

    if (!response.ok || result.error) {
      throw new Error(result.error || "Resume analysis failed");
    }

    // ---------- SAVE TO FIRESTORE (IMPORTANT FIX) ----------
    const docRef = await addDoc(
      collection(db, "resumeHistory", currentUser.uid, "analyses"),
      {
        company: result.company,
        role: result.job_role,
        score: Number(result.match_score) || 0,
        predictedCategory: result.predicted_category || "",
        analysis: result.analysis,
        createdAt: serverTimestamp()
      }
    );

    // ---------- OPTIONAL LOCAL STORAGE (PDF USE) ----------
    localStorage.setItem("analysisResult", JSON.stringify(result));

    // ---------- REDIRECT WITH DOC ID (🔥 FIX 🔥) ----------
    window.location.href = `result.html?id=${docRef.id}`;

  } catch (error) {
    console.error("Analyze Error:", error);
    alert("Server error. Please try again in a moment.");
  } finally {
    hideLoading();
    analyzeBtn.disabled = false;
    analyzeBtn.innerText = "Analyse Resume";
  }
});
