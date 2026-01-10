const resumeInput = document.getElementById("resumeUpload");
const uploadText = document.getElementById("uploadText");
const analyzeBtn = document.getElementById("analyzeBtn");

const companyInput = document.getElementById("companyInput");
const roleInput = document.getElementById("roleInput");
const descriptionInput = document.getElementById("descriptionInput");

/* Show selected file name */
resumeInput.addEventListener("change", () => {
  if (resumeInput.files.length > 0) {
    uploadText.innerText = resumeInput.files[0].name;
  }
});

/* Analyze Resume */
analyzeBtn.addEventListener("click", async () => {

  // Validation
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

  // Prepare form data (must match backend)
  const formData = new FormData();
  formData.append("resume", resumeInput.files[0]);
  formData.append("company", companyInput.value.trim());
  formData.append("role", roleInput.value.trim());
  formData.append("description", descriptionInput.value.trim());

  analyzeBtn.disabled = true;
  analyzeBtn.innerText = "Analyzing...";

  try {
    const response = await fetch("http://127.0.0.1:8000/analyze", {
      method: "POST",
      body: formData
    });

    const result = await response.json();

    // Handle backend errors
    if (!response.ok || result.error) {
      alert(result.error || "Resume analysis failed.");
      analyzeBtn.disabled = false;
      analyzeBtn.innerText = "Analyse Resume";
      return;
    }

    // Store result for result.html
    localStorage.setItem("analysisResult", JSON.stringify(result));

    // Redirect
    window.location.href = "result.html";

  } catch (error) {
    console.error(error);
    alert("Server error. Make sure backend is running.");
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.innerText = "Analyse Resume";
  }
});
