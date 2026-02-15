// --- Configuration & State ---
const API = {
  chat: "/chat",
  ingest: "/ingest",
  reset: "/reset",
  documents: "/documents",
};

const dom = {
  domainSelector: document.getElementById("domainSelector"),
  currentDomainTitle: document.getElementById("currentDomainTitle"),
  chatHistory: document.getElementById("chatHistory"),
  userMessage: document.getElementById("userMessage"),
  pdfUpload: document.getElementById("pdfUpload"),
  uploadStatus: document.getElementById("uploadStatus"),
  docList: document.getElementById("docList"),
};

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
  loadDocuments();
  setupEventListeners();
});

function setupEventListeners() {
  // Domain Switcher
  dom.domainSelector.addEventListener("change", (e) => {
    const domainMap = {
      hr: "Management Support",
      tech: "Technical Support",
    };
    dom.currentDomainTitle.textContent =
      domainMap[e.target.value] || "SOP Assistant";

    // Optional: clear chat on domain switch?
    // For now, we keep history but user might want a visual separator.
    appendSystemMessage(`Switched to ${domainMap[e.target.value]} mode.`);
  });
}

// --- Chat Functions ---
async function sendMessage() {
  const message = dom.userMessage.value.trim();
  if (!message) return;

  // 1. Append User Message
  appendMessage(message, "user");
  dom.userMessage.value = "";

  // Auto-scroll
  scrollToBottom();

  // 2. Show Typing Indicator
  const typingId = showTypingIndicator();

  try {
    const domain = dom.domainSelector.value;
    const response = await fetch(API.chat, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, domain }),
    });
    const data = await response.json();

    // Remove Typing Indicator
    removeTypingIndicator(typingId);

    // 3. Format Response (Markdown + Sources)
    let replyHtml = marked.parse(data.response || "");

    // Append Sources if any
    if (data.sources && data.sources.length > 0) {
      replyHtml += `<div class="sources-section"><strong>Sources:</strong><ul>`;
      data.sources.forEach((src) => {
        replyHtml += `<li>📄 ${src.file} (Page ${src.page}) <span style="opacity:0.7">[Score: ${src.score.toFixed(2)}]</span></li>`;
      });
      replyHtml += `</ul></div>`;
    }

    appendMessage(replyHtml, "bot", true); // true = isHTML
  } catch (error) {
    removeTypingIndicator(typingId);
    appendSystemMessage("Error: Could not reach the agent.");
    console.error(error);
  }

  scrollToBottom();
}

function appendMessage(content, sender, isHtml = false) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${sender}-message`;

  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";

  if (isHtml) {
    contentDiv.innerHTML = content;
  } else {
    contentDiv.textContent = content;
  }

  msgDiv.appendChild(contentDiv);
  dom.chatHistory.appendChild(msgDiv);
}

function appendSystemMessage(text) {
  const msgDiv = document.createElement("div");
  msgDiv.className = "message system-message";
  msgDiv.style.justifyContent = "center";
  msgDiv.style.opacity = "0.7";
  msgDiv.style.fontSize = "0.8rem";
  msgDiv.textContent = text;
  dom.chatHistory.appendChild(msgDiv);
}

function showTypingIndicator() {
  const id = "typing-" + Date.now();
  const msgDiv = document.createElement("div");
  msgDiv.className = "message bot-message";
  msgDiv.id = id;
  msgDiv.innerHTML = `<div class="message-content">Thinking...</div>`;
  dom.chatHistory.appendChild(msgDiv);
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function scrollToBottom() {
  dom.chatHistory.scrollTop = dom.chatHistory.scrollHeight;
}

async function clearChat() {
  try {
    await fetch(API.reset, { method: "POST" });
    dom.chatHistory.innerHTML = "";
    appendMessage("Chat history cleared. Ready for new questions.", "bot");
  } catch (e) {
    alert("Failed to reset chat.");
  }
}

// --- Document Functions ---
async function uploadFile() {
  const file = dom.pdfUpload.files[0];
  if (!file) return alert("Select a PDF first.");

  dom.uploadStatus.textContent = "Uploading & Ingesting...";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(API.ingest, { method: "POST", body: formData });
    const data = await res.json();

    if (data.status === "success") {
      dom.uploadStatus.textContent = `Success! (${data.chunks} chunks)`;
      loadDocuments(); // Refresh list
    } else {
      dom.uploadStatus.textContent = "Error: " + data.message;
    }
  } catch (e) {
    dom.uploadStatus.textContent = "Upload failed.";
  }
}

async function loadDocuments() {
  dom.docList.innerHTML = "<p class='empty-state'>Refreshing...</p>";
  try {
    const res = await fetch(API.documents);
    const data = await res.json();

    if (data.documents && data.documents.length > 0) {
      dom.docList.innerHTML = ""; // Clear
      data.documents.forEach((doc) => {
        const item = document.createElement("div");
        item.className = "doc-item";
        item.innerHTML = `
                    <span class="doc-name" title="${doc}">${doc}</span>
                    <button onclick="deleteDocument('${doc}')" class="btn btn-danger btn-icon">×</button>
                `;
        dom.docList.appendChild(item);
      });
    } else {
      dom.docList.innerHTML = "<p class='empty-state'>No documents.</p>";
    }
  } catch (e) {
    dom.docList.innerHTML =
      "<p class='empty-state' style='color:red'>Error.</p>";
  }
}

async function deleteDocument(filename) {
  if (!confirm(`Delete ${filename}?`)) return;

  await fetch(`/documents/${encodeURIComponent(filename)}`, {
    method: "DELETE",
  });
  loadDocuments();
}
