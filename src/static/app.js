async function uploadFile() {
  const fileInput = document.getElementById("pdfUpload");
  const file = fileInput.files[0];

  if (!file) {
    alert("Please select a file first.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const statusDiv = document.getElementById("chatHistory");
    const processingMsg = document.createElement("div");
    processingMsg.className = "message bot";
    processingMsg.innerText = "Ingesting document... please wait.";
    statusDiv.appendChild(processingMsg);

    const response = await fetch("/ingest", {
      method: "POST",
      body: formData,
    });
    const result = await response.json();

    processingMsg.remove();

    if (result.status === "success") {
      alert(`Ingestion Successful! Processed ${result.chunks} chunks.`);
    } else {
      alert("Ingestion Failed: " + result.message);
    }
  } catch (error) {
    alert("Error uploading file: " + error);
  }
}

async function sendMessage() {
  const input = document.getElementById("userMessage");
  const history = document.getElementById("chatHistory");
  const message = input.value;

  if (!message) return;

  // Add user message
  const userDiv = document.createElement("div");
  userDiv.className = "message user";
  userDiv.innerText = message;
  history.appendChild(userDiv);

  input.value = "";

  // Typing indicator
  const botDiv = document.createElement("div");
  botDiv.className = "message bot";
  botDiv.innerText = "Thinking...";
  history.appendChild(botDiv);

  // Auto-scroll to bottom
  history.scrollTop = history.scrollHeight;

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: message, domain: "hr" }),
    });
    const data = await response.json();

    let replyText = data.response;
    if (data.sources && data.sources.length > 0) {
      replyText += "\n\nSources:";
      data.sources.forEach((source) => {
        replyText += `\n• ${source.file} (Page ${source.page})`;
      });
    }

    botDiv.innerText = replyText;
  } catch (error) {
    botDiv.innerText = "Error: " + error;
  }

  // Auto-scroll to bottom
  history.scrollTop = history.scrollHeight;
}

async function clearChat() {
  try {
    const response = await fetch("/reset", { method: "POST" });
    const result = await response.json();

    if (result.status === "success") {
      const history = document.getElementById("chatHistory");
      history.innerHTML = "";

      // Add system welcome message
      const welcome = document.createElement("div");
      welcome.className = "message bot";
      welcome.innerText =
        "Chat history cleared. How can I help you regarding the SOPs?";
      history.appendChild(welcome);
    } else {
      alert("Failed to clear chat: " + result.message);
    }
  } catch (error) {
    alert("Error: " + error);
  }
}

async function loadDocuments() {
  const listDiv = document.getElementById("docList");
  try {
    listDiv.innerHTML = "<p>Loading...</p>";
    const response = await fetch("/documents");
    const result = await response.json();

    if (result.documents && result.documents.length > 0) {
      let html = "<ul>";
      result.documents.forEach((doc) => {
        html += `
                <li style="margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center;">
                    <span>📄 ${doc}</span>
                    <button onclick="deleteDocument('${doc}')" style="background-color: #dc3545; padding: 5px 10px; font-size: 0.8rem;">Delete</button>
                </li>`;
      });
      html += "</ul>";
      listDiv.innerHTML = html;
    } else {
      listDiv.innerHTML = "<p>No documents found.</p>";
    }
  } catch (error) {
    listDiv.innerHTML = '<p style="color:red">Error loading documents.</p>';
  }
}

async function deleteDocument(filename) {
  if (!confirm(`Are you sure you want to delete ${filename}?`)) return;

  try {
    const response = await fetch(`/documents/${encodeURIComponent(filename)}`, {
      method: "DELETE",
    });
    const result = await response.json();

    if (result.status === "success") {
      alert("Document deleted!");
      loadDocuments(); // Refresh list
    } else {
      alert("Failed to delete: " + result.detail);
    }
  } catch (error) {
    alert("Error deleting: " + error);
  }
}

// Load documents on page load
document.addEventListener("DOMContentLoaded", () => {
  loadDocuments();
});
