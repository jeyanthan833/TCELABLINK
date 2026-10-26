/**
 * TCELABLINK Client Application JavaScript
 * Prototype v2 - Design Thinking Project
 */

// Student Portal: Live Filter Cards by Name, ID, or Category
function filterCards() {
  const searchInput = document.getElementById('search');
  if (!searchInput) return;

  const query = (searchInput.value || '').trim().toLowerCase();
  const cards = document.querySelectorAll('.grid .eq');
  let visibleCount = 0;

  cards.forEach(card => {
    const cardData = (card.dataset.name || '').toLowerCase();
    const isMatch = !query || cardData.includes(query);
    card.style.display = isMatch ? 'block' : 'none';
    if (isMatch) visibleCount++;
  });

  // Update item count badge
  const counter = document.getElementById('search-counter');
  if (counter) {
    counter.textContent = `${visibleCount} item${visibleCount === 1 ? '' : 's'}`;
  }

  // Toggle empty-state card
  const emptyState = document.getElementById('no-search-results');
  if (emptyState) {
    emptyState.style.display = visibleCount === 0 ? 'block' : 'none';
  }
}

// Staff Admin Dashboard: Live Table Search and Status Dropdown Filtering
function filterAdminTable() {
  const searchInput = document.getElementById('admin-search');
  const statusSelect = document.getElementById('admin-status-filter');
  const rows = document.querySelectorAll('#admin-table tbody .admin-eq-row');
  const emptyRow = document.getElementById('admin-empty-row');

  const query = searchInput ? (searchInput.value || '').trim().toLowerCase() : '';
  const selectedStatus = statusSelect ? (statusSelect.value || 'all').trim().toLowerCase() : 'all';

  let visibleCount = 0;

  rows.forEach(row => {
    const rowName = (row.dataset.name || '').toLowerCase();
    const rowId = (row.dataset.id || '').toLowerCase();
    const rowStatus = (row.dataset.status || '').toLowerCase();

    const matchesQuery = !query || rowName.includes(query) || rowId.includes(query);
    const matchesStatus = selectedStatus === 'all' || rowStatus === selectedStatus;

    if (matchesQuery && matchesStatus) {
      row.style.display = '';
      visibleCount++;
    } else {
      row.style.display = 'none';
    }
  });

  if (emptyRow) {
    emptyRow.style.display = visibleCount === 0 ? '' : 'none';
  }
}
