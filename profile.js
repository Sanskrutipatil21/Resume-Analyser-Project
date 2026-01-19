// ---------------- FIREBASE IMPORTS ----------------
import { auth, db } from "./firebase.js";
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/12.4.0/firebase-auth.js";
import {
  collection,
  getDocs,
  query,
  orderBy
} from "https://www.gstatic.com/firebasejs/12.4.0/firebase-firestore.js";

// ---------------- ELEMENTS ----------------
const historyList = document.getElementById("historyList");
const profileName = document.getElementById("profileName");

// ---------------- AUTH STATE ----------------
onAuthStateChanged(auth, async (user) => {
  if (!user) {
    window.location.href = "index.html";
    return;
  }

  // Show user name
  profileName.innerText =
    user.displayName || user.email.split("@")[0];

  // Load resume history
  loadResumeHistory(user.uid);
});

// ---------------- LOAD HISTORY ----------------
async function loadResumeHistory(uid) {
  historyList.innerHTML = "<p>Loading history...</p>";

  try {
    const q = query(
      collection(db, "resumeHistory", uid, "analyses"),
      orderBy("createdAt", "desc")
    );

    const snapshot = await getDocs(q);

    if (snapshot.empty) {
      historyList.innerHTML =
        "<p>No resume analysis found yet.</p>";
      return;
    }

    historyList.innerHTML = "";

    snapshot.forEach((doc) => {
      const data = doc.data();
      const date = data.createdAt?.toDate().toDateString() || "N/A";

      historyList.innerHTML += `
        <div class="history-card">
          <div class="row">
            <div>
              <strong>${data.company}</strong><br>
              <span>${data.role}</span>
            </div>
            <div class="score">${data.score}%</div>
          </div>
          <span>Analyzed on: ${date}</span>
        </div>
      `;
    });

  } catch (error) {
    console.error(error);
    historyList.innerHTML =
      "<p>Error loading resume history.</p>";
  }
}
