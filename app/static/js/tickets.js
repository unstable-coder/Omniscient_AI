async function loadTickets() {
  const response = await fetch('/api/chat/tickets');
  const tickets = await response.json();
  const body = document.getElementById('tickets-body');
  if (!body) return;
  body.innerHTML = tickets.map(ticket => `
    <tr>
      <td>${ticket.id}</td>
      <td>${ticket.equipment}</td>
      <td>${ticket.priority}</td>
      <td>${ticket.category}</td>
      <td>${ticket.problem}</td>
      <td>${ticket.assigned_team}</td>
      <td>${ticket.status}</td>
    </tr>
  `).join('');
}

document.getElementById('refresh-tickets')?.addEventListener('click', loadTickets);
loadTickets();
