(function () {
  const $ = (id) => document.getElementById(id);
  const tbody = document.querySelector('#trades tbody');

  function q(v) { return encodeURIComponent(v ?? ''); }

  async function loadTrades() {
    const params = new URLSearchParams();
    const symbol = $('symbol').value.trim();
    const outcome = $('outcome').value;
    const direction = $('direction').value;
    const start = $('start_time').value;
    const end = $('end_time').value;
    const sort_by = $('sort_by').value;
    const sort_dir = $('sort_dir').value;

    if (symbol) params.append('symbol', symbol);
    if (outcome) params.append('outcome', outcome);
    if (direction) params.append('direction', direction);
    if (start) params.append('start_time', start);
    if (end) params.append('end_time', end);
    if (sort_by) params.append('sort_by', sort_by);
    if (sort_dir) params.append('sort_dir', sort_dir);
    params.append('limit', '100');

    const res = await fetch(`/trades?${params.toString()}`);
    const data = await res.json();
    renderRows(data.items || []);
  }

  function fmtDate(s) {
    if (!s) return '';
    try { return new Date(s).toLocaleString(); } catch (e) { return s; }
  }

  function renderRows(items) {
    tbody.innerHTML = '';
    for (const t of items) {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${t.trade_id}</td>
        <td>${t.symbol ?? ''}</td>
        <td>${fmtDate(t.entry_time)}</td>
        <td>${fmtDate(t.exit_time)}</td>
        <td>${t.direction ?? ''}</td>
        <td>${t.outcome ?? ''}</td>
        <td>${(t.pnl==null)?'':('$' + Number(t.pnl).toFixed(2))}</td>
        <td>${t.r_multiple ?? '-'}</td>
        <td>
          <a class="btn" target="_blank" href="/charts/by-trade/${t.trade_id}" style="margin-right: 8px;">View Chart</a>
          <a class="btn" href="/app/annotate.html?trade_id=${t.trade_id}" style="background: #26a69a;">Annotate</a>
        </td>
      `;
      tbody.appendChild(tr);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    $('apply').addEventListener('click', loadTrades);
    loadTrades();
  });
})();


