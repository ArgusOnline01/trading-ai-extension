(function () {
  const $ = (id) => document.getElementById(id);
  const tbody = document.querySelector('#trades tbody');

  let entryMethods = [];
  let currentTrades = [];
  let currentPage = 1;
  let totalPages = 1;
  let totalTrades = 0;
  const TRADES_PER_PAGE = 50;

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

  async function loadTrades(resetPage = false) {
    if (resetPage) {
      currentPage = 1;
    }
    
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
    params.append('limit', TRADES_PER_PAGE.toString());
    params.append('offset', ((currentPage - 1) * TRADES_PER_PAGE).toString());

    const res = await fetch(`/trades?${params.toString()}`);
    const data = await res.json();
    currentTrades = data.items || [];
    totalTrades = data.total || 0;
    totalPages = Math.ceil(totalTrades / TRADES_PER_PAGE) || 1;
    
    // Update total trades counter
    const totalTradesEl = $('total-trades');
    const showingTradesEl = $('showing-trades');
    if (totalTradesEl) {
      totalTradesEl.textContent = totalTrades;
    }
    if (showingTradesEl) {
      const start = totalTrades > 0 ? ((currentPage - 1) * TRADES_PER_PAGE) + 1 : 0;
      const end = Math.min(start + currentTrades.length - 1, totalTrades);
      if (totalTrades > 0) {
        showingTradesEl.textContent = `${start}-${end} of ${totalTrades}`;
      } else {
        showingTradesEl.textContent = '0';
      }
    }
    
    // Update pagination
    updatePagination();
    
    renderRows(currentTrades);
  }

  function updatePagination() {
    const currentPageEl = $('current-page');
    const totalPagesEl = $('total-pages');
    const prevBtn = $('prev-page');
    const nextBtn = $('next-page');
    
    if (currentPageEl) {
      currentPageEl.textContent = currentPage;
    }
    if (totalPagesEl) {
      totalPagesEl.textContent = totalPages;
    }
    if (prevBtn) {
      prevBtn.disabled = currentPage <= 1;
      prevBtn.style.opacity = currentPage <= 1 ? '0.5' : '1';
      prevBtn.style.cursor = currentPage <= 1 ? 'not-allowed' : 'pointer';
    }
    if (nextBtn) {
      nextBtn.disabled = currentPage >= totalPages;
      nextBtn.style.opacity = currentPage >= totalPages ? '0.5' : '1';
      nextBtn.style.cursor = currentPage >= totalPages ? 'not-allowed' : 'pointer';
    }
  }

  function goToPage(page) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    loadTrades();
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

  function getOutcome(trade) {
    // If outcome is explicitly set, use it
    if (trade.outcome) {
      return trade.outcome;
    }
    // Otherwise, calculate from PnL
    if (trade.pnl !== null && trade.pnl !== undefined) {
      if (trade.pnl > 0) return 'win';
      if (trade.pnl < 0) return 'loss';
      if (trade.pnl === 0) return 'breakeven';
    }
    // If no P&L value, assume breakeven
    return 'breakeven';
  }

  function renderRows(items) {
    tbody.innerHTML = '';
    for (const t of items) {
      const tr = document.createElement('tr');
      const entryMethodName = getEntryMethodName(t.entry_method_id);
      const outcome = getOutcome(t);
      const exitTime = t.exit_time ? fmtDate(t.exit_time) : '';
      tr.innerHTML = `
        <td>${t.trade_id}</td>
        <td>${t.symbol ?? ''}</td>
        <td>${fmtDate(t.entry_time)}</td>
        <td>${exitTime}</td>
        <td>${t.direction ?? ''}</td>
        <td>${outcome}</td>
        <td>${(t.pnl==null || t.pnl === undefined) ? '-' : ('$' + Number(t.pnl).toFixed(2))}</td>
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
    $('apply').addEventListener('click', () => loadTrades(true));
    $('export-csv').addEventListener('click', exportToCSV);
    $('prev-page').addEventListener('click', () => goToPage(currentPage - 1));
    $('next-page').addEventListener('click', () => goToPage(currentPage + 1));
    loadTrades();
  });
})();


