const questionInput = document.getElementById('question-input');
const askButton = document.getElementById('ask-button');
const answerBox = document.getElementById('answer-box');
const sourcesBox = document.getElementById('sources-box');
const historyBox = document.getElementById('history-box');
const chatStatus = document.getElementById('chat-status');
const clearHistoryButton = document.getElementById('clear-history');

function renderSources(sources) {
  if (!sources.length) {
    sourcesBox.textContent = 'No supporting chunks found.';
    return;
  }

  sourcesBox.innerHTML = sources
    .map(source => `
      <div class="source-item">
        <strong>${source.citation}</strong>
        <p>${source.text}</p>
      </div>
    `)
    .join('');
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
  if (!history) {
    return;
  }

  questionInput.value = history.question;
  answerBox.textContent = history.answer;
  renderSources(history.sources);
  chatStatus.textContent = 'Loaded from history';
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

  chatStatus.textContent = 'Thinking...';
  askButton.disabled = true;
  answerBox.textContent = '';
  sourcesBox.textContent = '';
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
    answerBox.textContent = payload.answer;
    renderSources(payload.sources);
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
    answerBox.textContent = '';
    sourcesBox.textContent = 'No sources yet.';
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
askButton.addEventListener('click', askQuestion);
questionInput.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    askQuestion();
  }
});

loadHistory();
