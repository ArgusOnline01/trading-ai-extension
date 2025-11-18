// Phase 4B: Entry Methods page JavaScript
(function () {
  const API_BASE = '';
  let editingId = null;
  let setups = [];

  const $ = (id) => document.getElementById(id);
  const modal = $('entry-method-modal');
  const form = $('entry-method-form');
  const list = $('entry-methods-list');
  const setupSelect = $('entry-method-setup-id');

  async function loadSetups() {
    try {
      const res = await fetch(`${API_BASE}/setups`);
      setups = await res.json();
      setupSelect.innerHTML = '<option value="">No setup</option>' + setups.map(s => 
        `<option value="${s.id}">${escapeHtml(s.name)}</option>`
      ).join('');
    } catch (err) {
      console.error('Failed to load setups:', err);
    }
  }

  async function loadEntryMethods() {
    try {
      const res = await fetch(`${API_BASE}/entry-methods`);
      const entryMethods = await res.json();
      renderEntryMethods(entryMethods);
    } catch (err) {
      console.error('Failed to load entry methods:', err);
      list.innerHTML = '<p style="color: #ef5350;">Failed to load entry methods. Check console for details.</p>';
    }
  }

  function renderEntryMethods(entryMethods) {
    if (entryMethods.length === 0) {
      list.innerHTML = '<p style="color: var(--muted);">No entry methods yet. Create your first entry method!</p>';
      return;
    }

    list.innerHTML = entryMethods.map(em => {
      const setup = setups.find(s => s.id === em.setup_id);
      return `
        <div style="background: var(--panel); padding: 16px; border: 1px solid #1f1f1f; border-radius: 6px;">
          <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
            <div>
              <h3 style="margin: 0; color: var(--accent); font-size: 18px;">${escapeHtml(em.name)}</h3>
              ${setup ? `<span style="display: inline-block; margin-top: 4px; padding: 2px 8px; background: #222; color: var(--muted); border-radius: 4px; font-size: 12px;">${escapeHtml(setup.name)}</span>` : ''}
            </div>
            <div style="display: flex; gap: 8px;">
              <button onclick="editEntryMethod(${em.id})" style="padding: 4px 8px; background: #222; color: var(--text); border: 1px solid #333; border-radius: 4px; cursor: pointer; font-size: 12px;">Edit</button>
              <button onclick="deleteEntryMethod(${em.id})" style="padding: 4px 8px; background: #ef5350; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Delete</button>
            </div>
          </div>
          ${em.description ? `<p style="margin: 8px 0 0; color: var(--muted); font-size: 14px;">${escapeHtml(em.description)}</p>` : ''}
          <p style="margin: 8px 0 0; color: var(--muted); font-size: 12px;">Created: ${new Date(em.created_at).toLocaleDateString()}</p>
        </div>
      `;
    }).join('');
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function openModal(isEdit = false, entryMethod = null) {
    editingId = isEdit ? entryMethod.id : null;
    $('modal-title').textContent = isEdit ? 'Edit Entry Method' : 'Create Entry Method';
    $('entry-method-id').value = entryMethod?.id || '';
    $('entry-method-name').value = entryMethod?.name || '';
    $('entry-method-description').value = entryMethod?.description || '';
    setupSelect.value = entryMethod?.setup_id || '';
    modal.style.display = 'flex';
  }

  function closeModal() {
    modal.style.display = 'none';
    form.reset();
    editingId = null;
  }

  async function saveEntryMethod(e) {
    e.preventDefault();
    const data = {
      name: $('entry-method-name').value.trim(),
      description: $('entry-method-description').value.trim() || null,
      setup_id: setupSelect.value ? parseInt(setupSelect.value) : null
    };

    try {
      const url = editingId ? `${API_BASE}/entry-methods/${editingId}` : `${API_BASE}/entry-methods`;
      const method = editingId ? 'PUT' : 'POST';
      
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to save entry method');
      }

      closeModal();
      loadEntryMethods();
    } catch (err) {
      alert('Error: ' + err.message);
      console.error(err);
    }
  }

  async function deleteEntryMethod(id) {
    if (!confirm('Are you sure you want to delete this entry method?')) return;

    try {
      const res = await fetch(`${API_BASE}/entry-methods/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to delete entry method');
      }
      loadEntryMethods();
    } catch (err) {
      alert('Error: ' + err.message);
      console.error(err);
    }
  }

  window.editEntryMethod = (id) => {
    fetch(`${API_BASE}/entry-methods/${id}`)
      .then(r => r.json())
      .then(entryMethod => openModal(true, entryMethod))
      .catch(err => {
        alert('Failed to load entry method: ' + err.message);
        console.error(err);
      });
  };

  window.deleteEntryMethod = deleteEntryMethod;

  document.addEventListener('DOMContentLoaded', () => {
    $('create-entry-method-btn').addEventListener('click', () => openModal(false));
    $('cancel-btn').addEventListener('click', closeModal);
    form.addEventListener('submit', saveEntryMethod);
    loadSetups();
    loadEntryMethods();
  });
})();

