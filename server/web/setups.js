// Phase 4B: Setups page JavaScript
(function () {
  const API_BASE = '';
  let editingId = null;

  const $ = (id) => document.getElementById(id);
  const modal = $('setup-modal');
  const form = $('setup-form');
  const list = $('setups-list');

  async function loadSetups() {
    try {
      const res = await fetch(`${API_BASE}/setups`);
      const setups = await res.json();
      renderSetups(setups);
    } catch (err) {
      console.error('Failed to load setups:', err);
      list.innerHTML = '<p style="color: #ef5350;">Failed to load setups. Check console for details.</p>';
    }
  }

  function renderSetups(setups) {
    if (setups.length === 0) {
      list.innerHTML = '<p style="color: var(--muted);">No setups yet. Create your first setup!</p>';
      return;
    }

    list.innerHTML = setups.map(s => `
      <div style="background: var(--panel); padding: 16px; border: 1px solid #1f1f1f; border-radius: 6px;">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
          <div>
            <h3 style="margin: 0; color: var(--accent); font-size: 18px;">${escapeHtml(s.name)}</h3>
            ${s.setup_type ? `<span style="display: inline-block; margin-top: 4px; padding: 2px 8px; background: ${s.setup_type === 'bullish' ? '#26a69a' : '#ef5350'}; color: #fff; border-radius: 4px; font-size: 12px; text-transform: uppercase;">${s.setup_type}</span>` : ''}
          </div>
          <div style="display: flex; gap: 8px;">
            <button onclick="editSetup(${s.id})" style="padding: 4px 8px; background: #222; color: var(--text); border: 1px solid #333; border-radius: 4px; cursor: pointer; font-size: 12px;">Edit</button>
            <button onclick="deleteSetup(${s.id})" style="padding: 4px 8px; background: #ef5350; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Delete</button>
          </div>
        </div>
        ${s.description ? `<p style="margin: 8px 0 0; color: var(--muted); font-size: 14px;">${escapeHtml(s.description)}</p>` : ''}
        <p style="margin: 8px 0 0; color: var(--muted); font-size: 12px;">Created: ${new Date(s.created_at).toLocaleDateString()}</p>
      </div>
    `).join('');
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function openModal(isEdit = false, setup = null) {
    editingId = isEdit ? setup.id : null;
    $('modal-title').textContent = isEdit ? 'Edit Setup' : 'Create Setup';
    $('setup-id').value = setup?.id || '';
    $('setup-name').value = setup?.name || '';
    $('setup-type').value = setup?.setup_type || '';
    $('setup-description').value = setup?.description || '';
    modal.style.display = 'flex';
  }

  function closeModal() {
    modal.style.display = 'none';
    form.reset();
    editingId = null;
  }

  async function saveSetup(e) {
    e.preventDefault();
    const data = {
      name: $('setup-name').value.trim(),
      setup_type: $('setup-type').value || null,
      description: $('setup-description').value.trim() || null
    };

    try {
      const url = editingId ? `${API_BASE}/setups/${editingId}` : `${API_BASE}/setups`;
      const method = editingId ? 'PUT' : 'POST';
      
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to save setup');
      }

      closeModal();
      loadSetups();
    } catch (err) {
      alert('Error: ' + err.message);
      console.error(err);
    }
  }

  async function deleteSetup(id) {
    if (!confirm('Are you sure you want to delete this setup?')) return;

    try {
      const res = await fetch(`${API_BASE}/setups/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to delete setup');
      }
      loadSetups();
    } catch (err) {
      alert('Error: ' + err.message);
      console.error(err);
    }
  }

  window.editSetup = (id) => {
    fetch(`${API_BASE}/setups/${id}`)
      .then(r => r.json())
      .then(setup => openModal(true, setup))
      .catch(err => {
        alert('Failed to load setup: ' + err.message);
        console.error(err);
      });
  };

  window.deleteSetup = deleteSetup;

  document.addEventListener('DOMContentLoaded', () => {
    $('create-setup-btn').addEventListener('click', () => openModal(false));
    $('cancel-btn').addEventListener('click', closeModal);
    form.addEventListener('submit', saveSetup);
    loadSetups();
  });
})();

