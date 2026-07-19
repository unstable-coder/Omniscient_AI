const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const selectFilesButton = document.getElementById("select-files");
const uploadFilesButton = document.getElementById("upload-files");
const fileList = document.getElementById("file-list");
const documentsBody = document.getElementById("documents-body");
const refreshButton = document.getElementById("refresh-documents");
const connectionStatus = document.getElementById("connection-status");
let selectedFiles = [];

function updateUploadState() {
  uploadFilesButton.disabled = selectedFiles.length === 0;
  fileList.innerHTML = selectedFiles.map(file => `<div class="file-item"><span>${file.name}</span><span>${(file.size / 1024).toFixed(1)} KB</span></div>`).join("");
}

function setConnectionStatus(text, success = true) {
  connectionStatus.textContent = text;
  connectionStatus.style.backgroundColor = success ? "rgba(56, 189, 248, 0.18)" : "rgba(248, 81, 73, 0.16)";
}

selectFilesButton.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  selectedFiles = Array.from(fileInput.files || []);
  updateUploadState();
});

["dragenter", "dragover"].forEach(eventName => {
  dropZone.addEventListener(eventName, event => {
    event.preventDefault();
    event.stopPropagation();
    dropZone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach(eventName => {
  dropZone.addEventListener(eventName, event => {
    event.preventDefault();
    event.stopPropagation();
    dropZone.classList.remove("dragover");
  });
});

dropZone.addEventListener("drop", event => {
  selectedFiles = Array.from(event.dataTransfer.files || []);
  updateUploadState();
});

dropZone.addEventListener("click", () => fileInput.click());

uploadFilesButton.addEventListener("click", async () => {
  if (!selectedFiles.length) return;
  const form = new FormData();
  selectedFiles.forEach(file => form.append("files", file));
  uploadFilesButton.disabled = true;
  setConnectionStatus("Uploading...", true);
  try {
    const response = await fetch("/api/admin/documents/upload", {
      method: "POST",
      body: form,
    });
    if (!response.ok) {
      const error = await response.json();
      setConnectionStatus(error.detail || "Upload failed", false);
    } else {
      setConnectionStatus("Upload queued", true);
      selectedFiles = [];
      updateUploadState();
      await loadDocuments();
    }
  } catch (err) {
    setConnectionStatus("Upload failed", false);
  } finally {
    uploadFilesButton.disabled = false;
  }
});

async function loadDocuments() {
  try {
    const response = await fetch("/api/admin/documents");
    const payload = await response.json();
    documentsBody.innerHTML = payload.documents.map(doc => {
      return `<tr>
        <td>${doc.original_filename}</td>
        <td>${doc.file_type}</td>
        <td>${(doc.size / 1024).toFixed(1)} KB</td>
        <td>${new Date(doc.uploaded_at).toLocaleString()}</td>
        <td><span class="status-chip ${doc.status}">${doc.status}</span></td>
        <td>${doc.chunk_count}</td>
        <td>${doc.error || "-"}</td>
        <td>
          <button class="action-button" onclick="retryDocument('${doc.document_id}')">Retry</button>
          <button class="action-button" onclick="deleteDocument('${doc.document_id}')">Delete</button>
        </td>
      </tr>`;
    }).join("");
  } catch (err) {
    console.error(err);
  }
}

window.retryDocument = async function(documentId) {
  await fetch(`/api/admin/documents/${documentId}/retry`, { method: "POST" });
  await loadDocuments();
};

window.deleteDocument = async function(documentId) {
  await fetch(`/api/admin/documents/${documentId}`, { method: "DELETE" });
  await loadDocuments();
};

refreshButton.addEventListener("click", loadDocuments);

async function checkHealth() {
  try {
    const response = await fetch("/api/admin/qdrant-health");
    const payload = await response.json();
    if (payload.status === "ok") {
      setConnectionStatus(`Qdrant OK (${payload.collection})`, true);
    } else {
      setConnectionStatus(`Qdrant error`, false);
    }
  } catch {
    setConnectionStatus("Qdrant connection failed", false);
  }
}

setInterval(loadDocuments, 5000);
setInterval(checkHealth, 10000);
loadDocuments();
checkHealth();
