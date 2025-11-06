const fileInput = document.getElementById('resumeUpload');

// Create a text element to show file name
const fileName = document.createElement('div');
fileName.className = 'file-name';
fileName.style.marginTop = '15px';
fileName.style.fontSize = '16px';
fileName.style.color = '#333';
fileName.textContent = 'No file selected';

// Add that text under subbox
document.querySelector('.subbox1').appendChild(fileName);

// When file is selected
fileInput.addEventListener('change', function() {
  if (this.files.length > 0) {
    const file = this.files[0];
    fileName.textContent = ` ${file.name}`;
    fileName.style.color = '#4caf50';
    document.querySelector('.subbox1').style.borderColor = '#4caf50';
    document.querySelector('.subbox1').style.boxShadow = '0 0 20px rgba(76,175,80,0.3)';
  } else {
    fileName.textContent = 'No file selected';
    fileName.style.color = '#333';
    document.querySelector('.subbox1').style.borderColor = 'rgb(216,211,211)';
    document.querySelector('.subbox1').style.boxShadow = 'none';
  }
});

// script2.js

document.addEventListener("DOMContentLoaded", () => {
  const analyseBtn = document.querySelector('.submit input[type="submit"]');
  const resumeInput = document.getElementById("resumeUpload");
  const companyInput = document.querySelector(".target-company input");
  const roleInput = document.querySelector(".target-role input");

  analyseBtn.addEventListener("click", () => {
    // Check required inputs
    if (!resumeInput.files.length) {
      alert("⚠️ Please upload your resume before analysing!");
      resumeInput.scrollIntoView({ behavior: "smooth", block: "center" });
      resumeInput.style.outline = "2px solid red";
      return;
    }

    if (companyInput.value.trim() === "") {
      alert("⚠️ Please enter your target company!");
      companyInput.focus();
      companyInput.style.border = "2px solid red";
      return;
    }

    if (roleInput.value.trim() === "") {
      alert("⚠️ Please enter your target role!");
      roleInput.focus();
      roleInput.style.border = "2px solid red";
      return;
    }

    // If all fields filled — perform action
    alert("✅ Resume analysis started!\n\nCompany: " + companyInput.value + "\nRole: " + roleInput.value);
    
    // You can later replace alert with:
    // window.location.href = "analysis_result.html"; 
    // or send data to backend using fetch()
  });

  // Remove red border when user types
  [companyInput, roleInput].forEach(input => {
    input.addEventListener("input", () => {
      input.style.border = "2px solid #683dbfff";
    });
  });
});

