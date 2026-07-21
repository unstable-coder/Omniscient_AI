const metricsGrid = document.getElementById('metrics-grid');
const refreshIndicator = document.getElementById('refresh-indicator');

const statusChart = new Chart(document.getElementById('statusChart'), {
  type: 'doughnut',
  data: {
    labels: ['Indexed', 'Processing', 'Failed'],
    datasets: [{
      data: [0, 0, 0],
      backgroundColor: ['#4f8cff', '#facc15', '#f87171'],
      borderWidth: 0,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' } }
  }
});

const metricsChart = new Chart(document.getElementById('metricsChart'), {
  type: 'bar',
  data: {
    labels: ['Embedding', 'Graph', 'Vector', 'Response'],
    datasets: [{
      label: 'Latency (ms)',
      data: [0, 0, 0, 0],
      backgroundColor: ['#2dd4bf', '#a78bfa', '#4f8cff', '#facc15'],
      borderRadius: 8,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    scales: { y: { beginAtZero: true } }
  }
});

const cards = [
  { key: 'documents_indexed', title: 'Documents Indexed', icon: '📄', subtitle: 'Indexed successfully' },
  { key: 'documents_processing', title: 'Documents Processing', icon: '⚙️', subtitle: 'Currently processing' },
  { key: 'documents_failed', title: 'Documents Failed', icon: '❌', subtitle: 'Failed ingestion' },
  { key: 'chunks_created', title: 'Chunks Created', icon: '🧩', subtitle: 'Text chunks stored' },
  { key: 'vectors_stored', title: 'Vectors Stored', icon: '🧠', subtitle: 'Qdrant points' },
  { key: 'graph_nodes', title: 'Knowledge Graph Nodes', icon: '🕸️', subtitle: 'Neo4j nodes' },
  { key: 'graph_relationships', title: 'Graph Relationships', icon: '🔗', subtitle: 'Neo4j edges' },
  { key: 'average_response_time_ms', title: 'Average Response Time', icon: '⏱️', subtitle: 'Chat response latency' },
  { key: 'average_retrieval_time_ms', title: 'Average Retrieval Time', icon: '🔍', subtitle: 'Hybrid retrieval' },
  { key: 'average_embedding_time_ms', title: 'Embedding Time', icon: '🧪', subtitle: 'Embedding latency' },
  { key: 'average_graph_query_time_ms', title: 'Graph Query Time', icon: '📈', subtitle: 'Neo4j latency' },
  { key: 'average_vector_query_time_ms', title: 'Vector Query Time', icon: '⚡', subtitle: 'Qdrant search latency' },
];

function renderCards(stats) {
  metricsGrid.innerHTML = cards.map(card => {
    const value = stats[card.key] ?? 0;
    return `
      <article class="metric-card">
        <div class="metric-top">
          <div class="metric-title">${card.title}</div>
          <div class="metric-icon">${card.icon}</div>
        </div>
        <div class="metric-value">${formatValue(value)}</div>
        <div class="metric-subtitle">${card.subtitle}</div>
      </article>
    `;
  }).join('');
}

function formatValue(value) {
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
  }
  return value;
}

async function loadStats() {
  try {
    const response = await fetch('/api/dashboard/stats');
    const stats = await response.json();
    renderCards(stats);

    statusChart.data.datasets[0].data = [
      stats.documents_indexed,
      stats.documents_processing,
      stats.documents_failed,
    ];
    statusChart.update();

    metricsChart.data.datasets[0].data = [
      stats.average_embedding_time_ms,
      stats.average_graph_query_time_ms,
      stats.average_vector_query_time_ms,
      stats.average_response_time_ms,
    ];
    metricsChart.update();

    refreshIndicator.textContent = 'Updated at ' + new Date().toLocaleTimeString();
  } catch (error) {
    console.error(error);
    refreshIndicator.textContent = 'Refresh unavailable';
  }
}

loadStats();
