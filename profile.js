import { auth, db } from "./firebase.js";
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/12.4.0/firebase-auth.js";
import {
  collection,
  getDocs,
  query,
  orderBy
} from "https://www.gstatic.com/firebasejs/12.4.0/firebase-firestore.js";

// DOM elements
const historyList = document.getElementById("historyList");
const profileName = document.getElementById("profileName");

// Auth check
onAuthStateChanged(auth, async (user) => {
  if (!user) {
    window.location.href = "index.html";
    return;
  }

  profileName.innerText =
    user.displayName || user.email.split("@")[0];

  loadResumeHistory(user.uid);
});

// Load resume history
async function loadResumeHistory(uid) {
  historyList.innerHTML = `<p style="opacity:0.7">Loading resume history...</p>`;

  try {
    const q = query(
      collection(db, "resumeHistory", uid, "analyses"),
      orderBy("createdAt", "desc")
    );

    const snapshot = await getDocs(q);

    if (snapshot.empty) {
      historyList.innerHTML =
        `<p style="opacity:0.7">No resume analysis done yet.</p>`;
      return;
    }

    historyList.innerHTML = "";

    snapshot.forEach((docSnap) => {
      const data = docSnap.data();

      const company = data.company || "Resume Analysis";
      const role = data.role || "General Profile";
      const score = data.score ?? "--";
      const date =
        data.createdAt?.toDate().toDateString() || "N/A";

      historyList.innerHTML += `
        <div class="history-card" onclick="openResult('${docSnap.id}')">
          <div class="row">
            <div>
              <strong>${company}</strong><br />
              <span>${role}</span>
            </div>
            <div class="score">${score}%</div>
          </div>
          <span>Analyzed on: ${date}</span>
        </div>
      `;
    });

  } catch (err) {
    console.error(err);
    historyList.innerHTML =
      `<p style="color:red">Failed to load history.</p>`;
  }
}


window.openResult = function (docId) {
  window.location.href = `result.html?id=${docId}`;
};
