(function () {
  const $ = (id) => document.getElementById(id);
  const tbody = document.querySelector('#trades tbody');

  let entryMethods = [];
  let currentTrades = [];

  function q(v) { return encodeURIComponent(v ?? ''); }

  async function loadEntryMethods() {
    try {
      const res = await fetch('/entry-methods');
      entryMethods = await res.json();
      const select = $('entry_method');
      select.innerHTML = '<option value="">Any entry method</option>' + entryMethods.map(em => 
        `<option value="${em.id}">${escapeHtml(em.name)}</option>`
      ).join('');
    } catch (err) {
      console.error('Failed to load entry methods:', err);
    }
  }

  async function loadTrades() {
    const params = new URLSearchParams();
    const symbol = $('symbol').value.trim();
    const outcome = $('outcome').value;
    const direction = $('direction').value;
    const session = $('session').value;
    const entryMethodId = $('entry_method').value;
    const hasEntryMethod = $('has_entry_method').value;
    const start = $('start_time').value;
    const end = $('end_time').value;
    const sort_by = $('sort_by').value;
    const sort_dir = $('sort_dir').value;

    if (symbol) params.append('symbol', symbol);
    if (outcome) params.append('outcome', outcome);
    if (direction) params.append('direction', direction);
    if (session) params.append('session', session);
    if (entryMethodId) params.append('entry_method_id', entryMethodId);
    if (hasEntryMethod) params.append('has_entry_method', hasEntryMethod === 'true');
    if (start) params.append('start_time', start);
    if (end) params.append('end_time', end);
    if (sort_by) params.append('sort_by', sort_by);
    if (sort_dir) params.append('sort_dir', sort_dir);
    params.append('limit', '100');

    const res = await fetch(`/trades?${params.toString()}`);
    const data = await res.json();
    currentTrades = data.items || [];
    renderRows(currentTrades);
  }

  function fmtDate(s) {
    if (!s) return '';
    try { return new Date(s).toLocaleString(); } catch (e) { return s; }
  }

  function getEntryMethodName(entryMethodId) {
    if (!entryMethodId) return '-';
    const em = entryMethods.find(e => e.id === entryMethodId);
    return em ? em.name : '-';
  }

  function renderRows(items) {
    tbody.innerHTML = '';
    for (const t of items) {
      const tr = document.createElement('tr');
      const entryMethodName = getEntryMethodName(t.entry_method_id);
      tr.innerHTML = `
        <td>${t.trade_id}</td>
        <td>${t.symbol ?? ''}</td>
        <td>${fmtDate(t.entry_time)}</td>
        <td>${fmtDate(t.exit_time)}</td>
        <td>${t.direction ?? ''}</td>
        <td>${t.outcome ?? ''}</td>
        <td>${(t.pnl==null)?'':('$' + Number(t.pnl).toFixed(2))}</td>
        <td>${t.r_multiple ?? '-'}</td>
        <td>${entryMethodName}</td>
        <td>
          <a class="btn" target="_blank" href="/charts/by-trade/${t.trade_id}" style="margin-right: 8px;">View Chart</a>
          <a class="btn" href="/app/annotate.html?trade_id=${t.trade_id}" style="background: #26a69a;">Annotate</a>
        </td>
      `;
      tbody.appendChild(tr);
    }
  }

  function exportToCSV() {
    if (currentTrades.length === 0) {
      alert('No trades to export');
      return;
    }

    const headers = ['Trade ID', 'Symbol', 'Entry Time', 'Exit Time', 'Direction', 'Outcome', 'PnL', 'R Multiple', 'Entry Method'];
    const rows = currentTrades.map(t => [
      t.trade_id,
      t.symbol || '',
      t.entry_time || '',
      t.exit_time || '',
      t.direction || '',
      t.outcome || '',
      t.pnl || '',
      t.r_multiple || '',
      getEntryMethodName(t.entry_method_id)
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trades_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadEntryMethods();
    $('apply').addEventListener('click', loadTrades);
    $('export-csv').addEventListener('click', exportToCSV);
    loadTrades();
  });
})();


