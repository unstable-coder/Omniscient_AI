const questionInput = document.getElementById('question-input');
const askButton = document.getElementById('ask-button');
const answerBox = document.getElementById('answer-box');
const sourcesBox = document.getElementById('sources-box');
const chatStatus = document.getElementById('chat-status');

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

    if (!payload.sources.length) {
      sourcesBox.textContent = 'No supporting chunks found.';
      chatStatus.textContent = 'Completed';
      return;
    }

    sourcesBox.innerHTML = payload.sources
      .map(source => `
        <div class="source-item">
          <strong>${source.citation}</strong>
          <p>${source.text}</p>
        </div>
      `)
      .join('');

    chatStatus.textContent = 'Completed';
  } catch (err) {
    chatStatus.textContent = 'Request failed';
  } finally {
    askButton.disabled = false;
  }
}

askButton.addEventListener('click', askQuestion);
questionInput.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    askQuestion();
  }
});
