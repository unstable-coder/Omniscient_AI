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

const ROWS_PER_PAGE = 10;
let allDocuments = [];
let currentPage = 1;

async function loadDocuments() {
  try {
    const response = await fetch("/api/admin/documents");
    const payload = await response.json();

    // Reverse order (latest first)
    allDocuments = [...payload.documents].sort((a, b) => {
      return new Date(b.uploaded_at) - new Date(a.uploaded_at);
    });

    currentPage = 1;
    renderTable();
  } catch (err) {
    console.error(err);
  }
}

function renderTable() {
  const totalPages = Math.ceil(allDocuments.length / ROWS_PER_PAGE);

  if (currentPage > totalPages && totalPages > 0) {
    currentPage = totalPages;
  }

  const start = (currentPage - 1) * ROWS_PER_PAGE;
  const end = start + ROWS_PER_PAGE;

  const docs = allDocuments.slice(start, end);

  documentsBody.innerHTML = docs.map(doc => `
      <tr>
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
      </tr>
  `).join("");

  renderPagination(totalPages);
}

function renderPagination(totalPages) {
  let pagination = document.getElementById("pagination");

  if (!pagination) {
    pagination = document.createElement("div");
    pagination.id = "pagination";
    pagination.style.marginTop = "20px";
    pagination.style.display = "flex";
    pagination.style.justifyContent = "center";
    pagination.style.alignItems = "center";
    pagination.style.gap = "10px";

    document.querySelector("table").after(pagination);
  }

  pagination.innerHTML = `
      <button ${currentPage === 1 ? "disabled" : ""} id="prev-page">
          Previous
      </button>

      <span>Page ${totalPages === 0 ? 0 : currentPage} of ${totalPages}</span>

      <button ${currentPage === totalPages || totalPages === 0 ? "disabled" : ""} id="next-page">
          Next
      </button>
  `;

  document.getElementById("prev-page")?.addEventListener("click", () => {
    currentPage--;
    renderTable();
  });

  document.getElementById("next-page")?.addEventListener("click", () => {
    currentPage++;
    renderTable();
  });
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
    console.log('Health response:', response);
    const payload = await response.json();
    console.log('Health payload:', payload);
    if (payload.status === "ok") {
      setConnectionStatus(`Connected`, true);
    } 
  } catch {
    setConnectionStatus("Qdrant connection failed", false);
  }
}

setInterval(loadDocuments, 5000);
setInterval(checkHealth, 10000);
loadDocuments();
checkHealth();

