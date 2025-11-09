// Phase 4B: Chart Annotation page JavaScript with Fabric.js
(function () {
  const API_BASE = '';
  let canvas = null;
  let tradeId = null;
  let trade = null;
  let currentTool = 'poi';
  let poiMarkers = [];
  let bosLines = [];
  let annotationId = null;

  const $ = (id) => document.getElementById(id);
  const loading = $('loading');
  const content = $('content');

  // Get trade_id from URL
  const urlParams = new URLSearchParams(window.location.search);
  tradeId = urlParams.get('trade_id');

  if (!tradeId) {
    loading.innerHTML = '<p style="color: #ef5350;">Error: No trade_id provided. <a href="/app/">Go back to trades</a></p>';
    return;
  }

  async function init() {
    try {
      // Load trade data
      const tradeRes = await fetch(`${API_BASE}/trades/${tradeId}`);
      if (!tradeRes.ok) throw new Error('Trade not found');
      trade = await tradeRes.json();

      // Update trade info
      $('trade-info').textContent = `${trade.symbol || 'Unknown'} - Trade ${trade.trade_id}`;
      $('trade-details').textContent = `${trade.direction || ''} ${trade.outcome || ''} | P&L: ${trade.pnl ? '$' + trade.pnl.toFixed(2) : 'N/A'} | ${trade.entry_time ? new Date(trade.entry_time).toLocaleDateString() : ''}`;

      // Load chart image
      const chartUrl = `/charts/by-trade/${tradeId}`;
      await loadChart(chartUrl);

      // Load existing annotations
      await loadAnnotations();

      // Load setups and entry methods for linking
      await loadSetupsAndEntryMethods();

      loading.style.display = 'none';
      content.style.display = 'block';
    } catch (err) {
      loading.innerHTML = `<p style="color: #ef5350;">Error: ${err.message}. <a href="/app/">Go back to trades</a></p>`;
      console.error(err);
    }
  }

  async function loadChart(chartUrl) {
    return new Promise((resolve, reject) => {
      fabric.Image.fromURL(chartUrl, (img) => {
        if (!canvas) {
          canvas = new fabric.Canvas('chart-canvas', {
            backgroundColor: '#0b0b0b',
            selection: false
          });
        }

        // Scale image to fit canvas (max width 1200px)
        const maxWidth = 1200;
        const scale = img.width > maxWidth ? maxWidth / img.width : 1;
        img.scale(scale);
        
        canvas.setWidth(img.width * scale);
        canvas.setHeight(img.height * scale);
        canvas.add(img);
        canvas.sendToBack(img);

        // Setup canvas click handler
        canvas.on('mouse:down', handleCanvasClick);

        resolve();
      }, {
        crossOrigin: 'anonymous'
      });
    });
  }

  async function loadAnnotations() {
    try {
      const res = await fetch(`${API_BASE}/annotations/trade/${tradeId}`);
      const annotations = await res.json();
      
      if (annotations.length > 0) {
        // Use the most recent annotation
        const ann = annotations[0];
        annotationId = ann.id;
        
        // Load POI markers
        if (ann.poi_locations && ann.poi_locations.length > 0) {
          ann.poi_locations.forEach(poi => {
            addPOIMarker(poi.x, poi.y, poi.price);
          });
        }

        // Load BOS lines
        if (ann.bos_locations && ann.bos_locations.length > 0) {
          ann.bos_locations.forEach(bos => {
            addBOSLine(bos.x, bos.y, bos.price);
          });
        }

        // Load notes
        if (ann.notes) {
          $('annotation-notes').value = ann.notes;
        }
      }
    } catch (err) {
      console.error('Failed to load annotations:', err);
    }
  }

  function handleCanvasClick(e) {
    if (!canvas) return;
    const pointer = canvas.getPointer(e.e);
    
    if (currentTool === 'poi') {
      // Prompt for price
      const price = prompt('Enter POI price:');
      if (price) {
        addPOIMarker(pointer.x, pointer.y, parseFloat(price));
      }
    } else if (currentTool === 'bos') {
      // For BOS, we'll create a horizontal line
      const price = prompt('Enter BOS price level:');
      if (price) {
        addBOSLine(pointer.x, pointer.y, parseFloat(price));
      }
    }
  }

  function addPOIMarker(x, y, price) {
    if (!canvas) return;
    
    const circle = new fabric.Circle({
      left: x - 5,
      top: y - 5,
      radius: 5,
      fill: '#ffd84d',
      stroke: '#fff',
      strokeWidth: 2,
      selectable: true,
      hasControls: true,
      data: { type: 'poi', price }
    });

    const text = new fabric.Text(`POI: ${price}`, {
      left: x + 10,
      top: y - 10,
      fontSize: 12,
      fill: '#ffd84d',
      selectable: false
    });

    const group = new fabric.Group([circle, text], {
      left: x,
      top: y,
      selectable: true,
      hasControls: true,
      data: { type: 'poi', price }
    });

    canvas.add(group);
    poiMarkers.push(group);
  }

  function addBOSLine(x, y, price) {
    if (!canvas) return;
    
    // Create horizontal line across canvas
    const line = new fabric.Line([0, y, canvas.width, y], {
      stroke: '#26a69a',
      strokeWidth: 2,
      selectable: true,
      hasControls: true,
      data: { type: 'bos', price }
    });

    const text = new fabric.Text(`BOS: ${price}`, {
      left: 10,
      top: y - 15,
      fontSize: 12,
      fill: '#26a69a',
      selectable: false
    });

    const group = new fabric.Group([line, text], {
      selectable: true,
      hasControls: true,
      data: { type: 'bos', price }
    });

    canvas.add(group);
    bosLines.push(group);
  }

  async function saveAnnotations() {
    if (!canvas) return;

    // Collect POI and BOS data
    const poiLocations = poiMarkers.map(marker => {
      const bounds = marker.getBoundingRect();
      return {
        x: bounds.left + bounds.width / 2,
        y: bounds.top + bounds.height / 2,
        price: marker.data?.price || 0,
        timestamp: new Date().toISOString()
      };
    });

    const bosLocations = bosLines.map(line => {
      const bounds = line.getBoundingRect();
      return {
        x: bounds.left,
        y: bounds.top,
        price: line.data?.price || 0,
        timestamp: new Date().toISOString()
      };
    });

    const data = {
      trade_id: tradeId,
      poi_locations: poiLocations,
      bos_locations: bosLocations,
      notes: $('annotation-notes').value.trim() || null,
      ai_detected: false,
      user_corrected: false
    };

    try {
      const url = annotationId ? `${API_BASE}/annotations/${annotationId}` : `${API_BASE}/annotations`;
      const method = annotationId ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to save annotation');
      }

      const result = await res.json();
      annotationId = result.id;
      alert('Annotations saved successfully!');
    } catch (err) {
      alert('Error saving annotations: ' + err.message);
      console.error(err);
    }
  }

  async function loadSetupsAndEntryMethods() {
    try {
      const [setupsRes, entryMethodsRes] = await Promise.all([
        fetch(`${API_BASE}/setups`),
        fetch(`${API_BASE}/entry-methods`)
      ]);

      const setups = await setupsRes.json();
      const entryMethods = await entryMethodsRes.json();

      const setupSelect = $('link-setup-id');
      const entryMethodSelect = $('link-entry-method-id');

      setupSelect.innerHTML = '<option value="">No setup</option>' + setups.map(s => 
        `<option value="${s.id}">${escapeHtml(s.name)}</option>`
      ).join('');

      entryMethodSelect.innerHTML = '<option value="">No entry method</option>' + entryMethods.map(em => 
        `<option value="${em.id}">${escapeHtml(em.name)}</option>`
      ).join('');

      // Load current links if any
      if (trade.setup_id) {
        setupSelect.value = trade.setup_id;
      }
      if (trade.entry_method_id) {
        entryMethodSelect.value = trade.entry_method_id;
      }
    } catch (err) {
      console.error('Failed to load setups/entry methods:', err);
    }
  }

  async function linkTradeToSetup() {
    const setupId = $('link-setup-id').value;
    const entryMethodId = $('link-entry-method-id').value;

    try {
      const params = new URLSearchParams();
      if (setupId) params.append('setup_id', setupId);
      if (entryMethodId) params.append('entry_method_id', entryMethodId);

      const res = await fetch(`${API_BASE}/trades/${tradeId}/link-setup?${params.toString()}`, {
        method: 'POST'
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to link trade');
      }

      $('link-modal').style.display = 'none';
      alert('Trade linked successfully!');
    } catch (err) {
      alert('Error linking trade: ' + err.message);
      console.error(err);
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Tool selection
  document.querySelectorAll('.tool-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTool = btn.dataset.tool;

      if (currentTool === 'delete') {
        const activeObject = canvas.getActiveObject();
        if (activeObject) {
          if (activeObject.data?.type === 'poi') {
            poiMarkers = poiMarkers.filter(m => m !== activeObject);
          } else if (activeObject.data?.type === 'bos') {
            bosLines = bosLines.filter(l => l !== activeObject);
          }
          canvas.remove(activeObject);
        } else {
          alert('Select an annotation to delete');
        }
        // Reset to POI tool after delete
        document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
        $('tool-poi').classList.add('active');
        currentTool = 'poi';
      }
    });
  });

  // Event handlers
  $('save-btn').addEventListener('click', saveAnnotations);
  $('clear-all-btn').addEventListener('click', () => {
    if (confirm('Clear all annotations?')) {
      poiMarkers.forEach(m => canvas.remove(m));
      bosLines.forEach(l => canvas.remove(l));
      poiMarkers = [];
      bosLines = [];
      $('annotation-notes').value = '';
    }
  });

  $('link-setup-btn').addEventListener('click', () => {
    $('link-modal').style.display = 'flex';
  });

  $('link-cancel-btn').addEventListener('click', () => {
    $('link-modal').style.display = 'none';
  });

  $('link-form').addEventListener('submit', (e) => {
    e.preventDefault();
    linkTradeToSetup();
  });

  // Initialize
  init();
})();

