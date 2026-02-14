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
    botDiv.innerText = data.response;
  } catch (error) {
    botDiv.innerText = "Error: " + error;
  }

  // Auto-scroll to bottom
  history.scrollTop = history.scrollHeight;
}
