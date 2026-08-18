// Drag-and-drop support on the upload page
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const label = document.getElementById("dropzone-label");

if (dropzone && fileInput) {
  ["dragenter", "dragover"].forEach(evt =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    })
  );

  ["dragleave", "drop"].forEach(evt =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    })
  );

  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      label.textContent = e.dataTransfer.files[0].name;
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) {
      label.textContent = fileInput.files[0].name;
    }
  });
}

// Copy-to-clipboard on the download/share page
const copyBtn = document.getElementById("copy-btn");
if (copyBtn) {
  copyBtn.addEventListener("click", async () => {
    const input = document.getElementById("share-url");
    input.select();
    try {
      await navigator.clipboard.writeText(input.value);
      copyBtn.textContent = "Copied!";
      setTimeout(() => (copyBtn.textContent = "Copy"), 1500);
    } catch (err) {
      document.execCommand("copy");
    }
  });
}
