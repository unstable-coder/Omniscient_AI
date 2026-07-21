const questionInput = document.getElementById('question-input');
const askButton = document.getElementById('ask-button');
const chatWindow = document.getElementById("chat-window");
const historyBox = document.getElementById('history-box');
const chatStatus = document.getElementById('chat-status');
const clearHistoryButton = document.getElementById('clear-history');
const emptyState = document.getElementById("empty-state");
function addUserMessage(text) {
    chatWindow.innerHTML += `
        <div class="message">
            <div class="avatar user">You</div>
            <div class="message-body">
                <div class="bubble user-bubble">${text}</div>
            </div>
        </div>
    `;
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function addAssistantMessage(answer, sources = []) {

    // Convert Markdown to HTML
    const renderedAnswer = marked.parse(answer);

    let html = `
        <div class="message">
            <div class="avatar ai">AI</div>
            <div class="message-body">
                <div class="bubble assistant-bubble markdown-body">
                    ${renderedAnswer}
    `;

    if (sources.length) {

        html += `
            <details class="sources">
                <summary>Sources (${sources.length})</summary>
        `;

        sources.forEach(source => {
            html += `
                <div class="source">
                    <strong>${source.citation}</strong>
                    <p>${source.text}</p>
                </div>
            `;
        });

        html += `</details>`;
    }

    html += `
                </div>
            </div>
        </div>
    `;

    chatWindow.innerHTML += html;
    chatWindow.scrollTop = chatWindow.scrollHeight;
}
function renderHistory(history) {
  if (!history.length) {
    historyBox.textContent = 'No history yet.';
    return;
  }

  historyBox.innerHTML = history
    .map(item => `
      <button class="history-item" data-id="${item.id}">
        <div class="history-question">${item.question}</div>
        <div class="history-meta">${new Date(item.timestamp).toLocaleString()}</div>
      </button>
    `)
    .join('');
}

function showHistoryItem(history) {

    chatWindow.innerHTML = "";

    addUserMessage(history.question);

    addAssistantMessage(
        history.answer,
        history.sources
    );

    chatStatus.textContent = "Loaded from history";
}

async function loadHistory() {
  try {
    const response = await fetch('/api/history');
    console.log('History response:', response);
    if (!response.ok) {
      return;
    }
    const history = await response.json();
    console.log('History data:', history);
    renderHistory(history);
  } catch {
    // ignore silently
  }
}

async function askQuestion() {
  const question = questionInput.value.trim();
  if (!question) {
    chatStatus.textContent = 'Enter a question first.';
    return;
  }

  askButton.textContent = 'Searching...';
  askButton.disabled = true;
  addUserMessage(question);
  try {
    const response = await fetch('/api/chat/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    if (!response.ok) {
      const error = await response.json();
      chatStatus.textContent = error.detail || 'Query failed';
      return;
    }

    const payload = await response.json();
    addAssistantMessage(payload.answer, payload.sources);
    chatStatus.textContent = 'Completed';
    await loadHistory();
  } catch (err) {
    chatStatus.textContent = 'Request failed';
  } finally {
    askButton.disabled = false;
  }
}

async function clearHistory() {
  try {
    const response = await fetch('/api/history', {
      method: 'DELETE',
    });
    if (!response.ok) {
      chatStatus.textContent = 'Could not clear history';
      return;
    }
    await loadHistory();
    chatWindow.innerHTML = "";
    chatStatus.textContent = 'History cleared';
  } catch {
    chatStatus.textContent = 'Could not clear history';
  }
}

historyBox.addEventListener('click', event => {
  const button = event.target.closest('.history-item');
  if (!button) {
    return;
  }

  const id = button.dataset.id;
  if (!id) {
    return;
  }

  fetch('/api/history')
    .then(response => response.ok ? response.json() : [])
    .then(history => history.find(item => item.id === id))
    .then(item => showHistoryItem(item))
    .catch(() => {
      chatStatus.textContent = 'Could not load history item';
    });
});

if (clearHistoryButton) {
  clearHistoryButton.addEventListener('click', clearHistory);
}
askButton?.addEventListener('click', askQuestion);
questionInput.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    questionInput.innerHTML = ''
    askQuestion();
    
  }
});
loadHistory();
document.getElementById("new-chat").addEventListener("click", () => {
    window.location.reload();
});
if (emptyState) {
   
}