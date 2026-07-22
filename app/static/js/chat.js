const questionInput = document.getElementById('question-input');
const askButton = document.getElementById('ask-button');
const chatWindow = document.getElementById("chat-window");
const historyBox = document.getElementById('history-box');
const chatStatus = document.getElementById('chat-status');
const clearHistoryButton = document.getElementById('clear-history');
const emptyState = document.getElementById("empty-state");
const enterpriseModal = document.getElementById('enterprise-modal');
const closeModalButton = document.getElementById('close-modal');
const ticketForm = document.getElementById('ticket-form');
let pendingTicket = null;
let pendingCompliance = null;

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

function addAssistantMessage(answer, sources = [], enterpriseActions = {}) {

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

    if (Object.keys(enterpriseActions).length) {
        html += `
            <div class="enterprise-actions">
                <h4>Suggested Enterprise Actions</h4>
        `;
        if (enterpriseActions.ticket) {
            html += `<button class="ticket-action" data-ticket='${JSON.stringify(enterpriseActions.ticket).replace(/'/g, '&#39;')}'>Create Ticket</button>`;
        }
        if (enterpriseActions.compliance) {
            html += `<button class="compliance-action" data-compliance='${JSON.stringify(enterpriseActions.compliance).replace(/'/g, '&#39;')}'>Check Compliance</button>`;
        }
        html += `</div>`;
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
        history.sources,
        history.enterprise_actions || {}
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
  emptyState.remove()
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
    addAssistantMessage(payload.answer, payload.sources, payload.enterprise_actions || {});
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

chatWindow.addEventListener('click', event => {
  const ticketButton = event.target.closest('.ticket-action');
  if (ticketButton) {
    pendingTicket = JSON.parse(ticketButton.dataset.ticket);
    document.getElementById('ticket-equipment').value = pendingTicket.equipment || '';
    document.getElementById('ticket-priority').value = pendingTicket.priority || 'Medium';
    document.getElementById('ticket-category').value = pendingTicket.category || 'Maintenance';
    document.getElementById('ticket-problem').value = pendingTicket.problem || '';
    document.getElementById('ticket-recommendation').value = pendingTicket.recommendation || '';
    document.getElementById('ticket-team').value = pendingTicket.assigned_team || 'Maintenance Operations';
    document.getElementById('ticket-status').value = pendingTicket.status || 'Open';
    enterpriseModal.classList.remove('hidden');
    enterpriseModal.setAttribute('aria-hidden', 'false');
    return;
  }

  const complianceButton = event.target.closest('.compliance-action');
  if (complianceButton) {
    const compliance = JSON.parse(complianceButton.dataset.compliance || '{}');
    const compliancePanel = document.createElement('div');
    compliancePanel.className = 'enterprise-actions';
    compliancePanel.innerHTML = `
      <h4>Compliance Summary</h4>
      <p><strong>Compliance Score:</strong> ${compliance.score || 0}%</p>
      <p><strong>Status:</strong> ${compliance.status || 'FAIL'}</p>
      <p><strong>Passed Checks:</strong> ${(compliance.passed_checks || []).join(', ') || 'None'}</p>
      <p><strong>Missing Checks:</strong> ${(compliance.missing_checks || []).join(', ') || 'None'}</p>
      <ul>${(compliance.suggested_improvements || []).map(item => `<li>${item}</li>`).join('')}</ul>
    `;
    chatWindow.appendChild(compliancePanel);
    chatStatus.textContent = 'Compliance checklist reviewed';
  }
});

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

closeModalButton?.addEventListener('click', () => {
  enterpriseModal.classList.add('hidden');
  enterpriseModal.setAttribute('aria-hidden', 'true');
});

ticketForm?.addEventListener('submit', async event => {
  event.preventDefault();
  const payload = {
    equipment: document.getElementById('ticket-equipment').value,
    priority: document.getElementById('ticket-priority').value,
    category: document.getElementById('ticket-category').value,
    problem: document.getElementById('ticket-problem').value,
    recommendation: document.getElementById('ticket-recommendation').value,
    assigned_team: document.getElementById('ticket-team').value,
    status: document.getElementById('ticket-status').value,
  };

  const response = await fetch('/api/chat/tickets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (response.ok) {
    chatStatus.textContent = 'Ticket saved locally';
    enterpriseModal.classList.add('hidden');
    enterpriseModal.setAttribute('aria-hidden', 'true');
  } else {
    chatStatus.textContent = 'Ticket could not be saved';
  }
});

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
const micButton = document.getElementById("voice-button");
const input = document.getElementById("question-input");

const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {

    const recognition = new SpeechRecognition();

    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    micButton.addEventListener("click", () => {
        recognition.start();
    });

    recognition.onresult = (event) => {
        input.value = event.results[0][0].transcript;
    };

    recognition.onerror = (event) => {
        console.log(event.error);
    };

} else {
    alert("Speech recognition is not supported in this browser.");
}
