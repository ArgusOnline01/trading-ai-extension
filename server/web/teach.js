// Phase 4D.1: Teaching page JavaScript
// Allows AI to analyze charts and user to correct AI annotations
(async function () {
  const API_BASE = '';
  let canvas = null;
  let tradeId = null;
  let trade = null;
  let aiAnnotations = {
    poi: [],
    bos: [],
    circles: []
  };
  let aiAnnotationObjects = []; // Fabric.js objects for AI annotations
  let userCorrections = {
    poi: [],
    bos: [],
    circles: []
  };
  let similarTrades = [];
  let aiReasoning = '';
  let chartScale = 1; // Store the scale factor for coordinate conversion
  let userAnnotations = null; // Store user's original annotations
  let userAnnotationObjects = []; // Fabric.js objects for user annotations
  let annotationId = null;
  let hudEl = null;

  // Helper: convert viewport coordinates to unzoomed canvas coords, then to original-image units
  function toOriginalUnits(x, y) {
    const scale = canvas?.chartScale || 1;
    const vt = canvas?.viewportTransform || [1,0,0,1,0,0];
    const zoomX = vt[0] || 1; // scaleX
    const zoomY = vt[3] || 1; // scaleY
    const panX = vt[4] || 0;  // translateX
    const panY = vt[5] || 0;  // translateY
    const cx = (x - panX) / zoomX; // canvas-space (no viewport)
    const cy = (y - panY) / zoomY;
    return { x: cx / scale, y: cy / scale };
  }

  const $ = (id) => document.getElementById(id);
  const loading = $('loading');
  const content = $('content');

  // Get trade_id from URL
  const urlParams = new URLSearchParams(window.location.search);
  tradeId = urlParams.get('trade_id');

  if (!tradeId) {
    // Show trade selector instead of error
    loading.style.display = 'none';
    const tradeSelector = $('trade-selector');
    if (tradeSelector) {
      tradeSelector.style.display = 'block';
      await loadTradeSelector();
    }
    return;
  }

  async function loadTradeSelector() {
    try {
      // Load list of trades - use absolute path like app.js does
      const response = await fetch('/trades?limit=100&sort_by=entry_time&sort_dir=desc');
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to load trades: ${response.status} ${response.statusText} - ${errorText}`);
      }
      
      const data = await response.json();
      const select = $('trade-select');
      select.innerHTML = '<option value="">Select a trade...</option>';
      
      // Check if data has trades array (response format from trades API)
      // The API returns { items: [...], total: ... } format
      const trades = data.items || data.trades || [];
      
      if (trades.length === 0) {
        select.innerHTML = '<option value="">No trades found</option>';
        return;
      }
      
      trades.forEach(t => {
        const option = document.createElement('option');
        option.value = t.trade_id;
        const symbol = t.symbol || 'Unknown';
        const direction = t.direction || '';
        const outcome = t.outcome || '';
        const pnl = t.pnl !== null ? `$${t.pnl.toFixed(2)}` : 'N/A';
        option.textContent = `${symbol} ${direction} ${outcome} (${pnl}) - ${t.trade_id}`;
        select.appendChild(option);
      });
      
      // Setup load button
      $('load-trade-btn').addEventListener('click', () => {
        const selectedTradeId = select.value;
        if (selectedTradeId) {
          window.location.href = `/app/teach.html?trade_id=${selectedTradeId}`;
        } else {
          alert('Please select a trade');
        }
      });
    } catch (err) {
      console.error('[TEACH] Error loading trade selector:', err);
      const errorMsg = err.message || 'Unknown error';
      $('trade-select').innerHTML = `<option value="">Error: ${errorMsg}</option>`;
    }
  }

  async function init() {
    try {
      // Load trade data - use absolute path
      const tradeRes = await fetch(`/trades/${tradeId}`);
      if (!tradeRes.ok) throw new Error('Trade not found');
      trade = await tradeRes.json();

      // Update trade info
      $('trade-info').textContent = `${trade.symbol || 'Unknown'} - Trade ${trade.trade_id}`;
      $('trade-details').textContent = `${trade.direction || ''} ${trade.outcome || ''} | P&L: ${trade.pnl ? '$' + trade.pnl.toFixed(2) : 'N/A'} | ${trade.entry_time ? new Date(trade.entry_time).toLocaleDateString() : ''}`;

      // Load chart image
      const chartUrl = `/charts/by-trade/${tradeId}`;
      await loadChart(chartUrl);

      // Analyze chart with AI
      await analyzeChart();

      // Load user's original annotations (if any)
      await loadUserAnnotations();

      // Setup event listeners
      $('analyze-btn').addEventListener('click', analyzeChart);
      $('show-ai-annotations').addEventListener('change', toggleAIAnnotations);
      $('show-user-annotations').addEventListener('change', toggleUserAnnotations);
      $('save-corrections-btn').addEventListener('click', saveCorrections);
      $('reset-zoom-btn').addEventListener('click', resetZoom);

      loading.style.display = 'none';
      content.style.display = 'block';

      // Create HUD
      hudEl = document.createElement('div');
      hudEl.className = 'coords-hud-panel';
      hudEl.innerHTML = '<strong>Coordinates</strong><br/>coords: -';
      document.body.appendChild(hudEl);
    } catch (err) {
      loading.innerHTML = `<p style="color: #ef5350;">Error: ${err.message}. <a href="/app/">Go back to trades</a></p>`;
      console.error(err);
    }
  }

  async function loadChart(chartUrl) {
    return new Promise((resolve, reject) => {
      const fullUrl = chartUrl.startsWith('http') ? chartUrl : `${window.location.origin}${chartUrl}`;
      
      fabric.Image.fromURL(fullUrl, (img) => {
        if (!canvas) {
          canvas = new fabric.Canvas('chart-canvas', {
            backgroundColor: '#0b0b0b',
            selection: true,
            preserveObjectStacking: true
          });
        }

        const maxWidth = 1200;
        // Store original dimensions BEFORE scaling
        const originalWidth = img.width;
        const originalHeight = img.height;
        
        chartScale = originalWidth > maxWidth ? maxWidth / originalWidth : 1;
        img.scale(chartScale);
        
        canvas.setWidth(originalWidth * chartScale);
        canvas.setHeight(originalHeight * chartScale);
        
        img.selectable = false;
        img.evented = false;
        img.set('zIndex', 0);
        
        canvas.add(img);
        canvas.sendToBack(img);
        canvas.chartImage = img;
        canvas.chartScale = chartScale; // Store scale for later use
        canvas.originalImageWidth = originalWidth; // Store original image dimensions
        canvas.originalImageHeight = originalHeight;
        console.log('[TEACH] Image dims:', { originalWidth, originalHeight, chartScale });

        // Setup zoom handlers
        canvas.on('mouse:wheel', (opt) => {
          const delta = opt.e.deltaY;
          let zoom = canvas.getZoom();
          zoom *= 0.999 ** delta;
          zoom = Math.max(0.1, Math.min(5, zoom));
          const pointer = canvas.getPointer(opt.e);
          canvas.zoomToPoint(pointer, zoom);
          opt.e.preventDefault();
          opt.e.stopPropagation();
        });

        console.log('[TEACH] Chart loaded successfully');
        // Enable selection/move events for HUD updates
        setupCanvasHandlers();
        canvas.renderAll();
        resolve();
      }, {
        crossOrigin: 'anonymous'
      });
    });
  }

  async function analyzeChart() {
    try {
      $('analyze-btn').disabled = true;
      $('analyze-btn').textContent = '⏳ Analyzing...';

      // Call AI analyze-chart endpoint
      const formData = new FormData();
      formData.append('trade_id', tradeId);

      const response = await fetch('/ai/analyze-chart', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`AI analysis failed: ${response.statusText}`);
      }

      const result = await response.json();

      if (!result.success) {
        throw new Error('AI analysis returned unsuccessful result');
      }

      // Store AI annotations
      aiAnnotations = result.annotations || { poi: [], bos: [], circles: [] };
      similarTrades = result.similar_trades || [];
      aiReasoning = result.reasoning || '';

      // Display AI annotations on chart
      displayAIAnnotations();

      // Display similar trades
      displaySimilarTrades();

      // Display AI reasoning
      displayReasoning();

      $('analyze-btn').disabled = false;
      $('analyze-btn').textContent = '🔄 Re-analyze Chart';
    } catch (err) {
      console.error('[TEACH] Error analyzing chart:', err);
      alert(`Error analyzing chart: ${err.message}`);
      $('analyze-btn').disabled = false;
      $('analyze-btn').textContent = '🔄 Re-analyze Chart';
    }
  }

  async function loadUserAnnotations() {
    try {
      const res = await fetch(`/annotations/trade/${tradeId}`);
      if (!res.ok) return;
      
      const annotations = await res.json();
      if (annotations.length > 0) {
        userAnnotations = annotations[0];
        // Cache saved image dimensions if provided
        userAnnotations._image_width = userAnnotations.image_width || userAnnotations.img_width || null;
        userAnnotations._image_height = userAnnotations.image_height || userAnnotations.img_height || null;
        console.log('[TEACH] Loaded user annotations:', userAnnotations);
        
        // Display user's notes if available
        if (userAnnotations.notes) {
          const notesSection = document.getElementById('user-notes-section');
          const notesDiv = document.getElementById('user-notes');
          if (notesSection && notesDiv) {
            notesDiv.textContent = userAnnotations.notes;
            notesSection.style.display = 'block';
          }
        }
        // Re-draw AI annotations so the ghost BOS (from user annotations) renders on top
        if (document.getElementById('show-ai-annotations')?.checked) {
          displayAIAnnotations();
        }
      }
    } catch (err) {
      console.error('[TEACH] Failed to load user annotations:', err);
    }
  }

  function displayUserAnnotations() {
    // Clear existing user annotations
    userAnnotationObjects.forEach(obj => {
      canvas.remove(obj);
    });
    userAnnotationObjects = [];

    if (!$('show-user-annotations').checked || !userAnnotations) {
      return;
    }

    const scale = canvas.chartScale || 1;

    // Display user's POI (solid, not dashed)
    // User annotations are saved in original image coordinates, convert to scaled canvas
    if (userAnnotations.poi_locations && userAnnotations.poi_locations.length > 0) {
      userAnnotations.poi_locations.forEach(poi => {
        // Saved coordinates are in original image coordinates
        const left = (poi.left || 0) * scale;
        const top = (poi.top || 0) * scale;
        const width = (poi.width || 50) * scale;
        const height = (poi.height || 30) * scale;
        const color = poi.color || '#2962FF';
        const centerX = left + width / 2;
        const centerY = top + height / 2;
        
        const rect = new fabric.Rect({
          left: left,
          top: top,
          width: width,
          height: height,
          fill: color === '#2962FF' ? 'rgba(41, 98, 255, 0.1)' : 'rgba(239, 83, 80, 0.1)',
          stroke: color,
          strokeWidth: 2,
          strokeDashArray: [], // Solid line for user annotations
          selectable: false,
          evented: false,
          hasControls: false,
          hasBorders: false
        });
        rect.set('userAnnotation', true);
        canvas.add(rect);
        userAnnotationObjects.push(rect);
        
        // Add POI text label
        const text = new fabric.Text(`POI${poi.price ? ': ' + poi.price : ''}`, {
          left: centerX,
          top: centerY,
          fontSize: 12,
          fill: color,
          textAlign: 'center',
          originX: 'center',
          originY: 'center',
          textBaseline: 'alphabetic',
          selectable: false,
          evented: false
        });
        text.set('userAnnotation', true);
        canvas.add(text);
        userAnnotationObjects.push(text);
      });
    }

    // Display user's BOS (solid)
    if (userAnnotations.bos_locations && userAnnotations.bos_locations.length > 0) {
      userAnnotations.bos_locations.forEach(bos => {
        const x1 = (bos.x1 || 0) * scale;
        const y1 = (bos.y1 || 0) * scale;
        const x2 = (bos.x2 || 100) * scale;
        const y2 = (bos.y2 || 0) * scale;
        const color = bos.color || '#2962FF';
        const centerX = (x1 + x2) / 2;
        const centerY = (y1 + y2) / 2;
        
        const line = new fabric.Line([x1, y1, x2, y2], {
          stroke: color,
          strokeWidth: 2,
          strokeDashArray: [], // Solid line
          selectable: false,
          evented: false,
          hasControls: false,
          hasBorders: false
        });
        line.set('userAnnotation', true);
        canvas.add(line);
        userAnnotationObjects.push(line);
        
        // Add BOS text label
        const text = new fabric.Text(`BOS${bos.price ? ': ' + bos.price : ''}`, {
          left: centerX,
          top: centerY - 15,
          fontSize: 12,
          fill: color,
          textAlign: 'center',
          originX: 'center',
          originY: 'center',
          textBaseline: 'alphabetic',
          selectable: false,
          evented: false
        });
        text.set('userAnnotation', true);
        canvas.add(text);
        userAnnotationObjects.push(text);
      });
    }

    // Display user's circles (solid)
    if (userAnnotations.circle_locations && userAnnotations.circle_locations.length > 0) {
      userAnnotations.circle_locations.forEach(circle => {
        const left = (circle.x || 0) * scale;
        const top = (circle.y || 0) * scale;
        const radius = (circle.radius || 20) * scale;
        const color = circle.color || '#2962FF';
        
        const circ = new fabric.Circle({
          left: left,
          top: top,
          radius: radius,
          fill: color === '#2962FF' ? 'rgba(41, 98, 255, 0.1)' : 'rgba(239, 83, 80, 0.1)',
          stroke: color,
          strokeWidth: 2,
          strokeDashArray: [], // Solid line
          selectable: false,
          evented: false,
          hasControls: false,
          hasBorders: false,
          originX: 'center',
          originY: 'center'
        });
        circ.set('userAnnotation', true);
        canvas.add(circ);
        userAnnotationObjects.push(circ);
      });
    }

    canvas.renderAll();
  }

  function toggleUserAnnotations() {
    displayUserAnnotations();
  }

  function displayAIAnnotations() {
    // Clear existing AI annotations
    aiAnnotationObjects.forEach(obj => {
      canvas.remove(obj);
    });
    aiAnnotationObjects = [];

    if (!$('show-ai-annotations').checked) {
      return;
    }

    // Get scale factor and original image dimensions
    const scale = canvas.chartScale || 1;
    const origWidth = canvas.originalImageWidth || canvas.width / scale;
    const origHeight = canvas.originalImageHeight || canvas.height / scale;
    
    console.log('[TEACH] Displaying AI annotations:', {
      scale,
      origWidth,
      origHeight,
      canvasWidth: canvas.width,
      canvasHeight: canvas.height,
      aiAnnotations
    });
    
    // Display POI boxes (blue dashed)
    // AI coordinates are relative to original image, need to scale to canvas
    if (aiAnnotations.poi && aiAnnotations.poi.length > 0) {
      aiAnnotations.poi.forEach((poi, idx) => {
        // Scale coordinates from original image size to canvas size
        const left = (poi.left || 0) * scale;
        const top = (poi.top || 0) * scale;
        const width = (poi.width || 50) * scale;
        const height = (poi.height || 30) * scale;
        
        console.log(`[TEACH] POI ${idx}:`, { original: poi, scaled: { left, top, width, height } });
        
        const rect = new fabric.Rect({
          left: left,
          top: top,
          width: width,
          height: height,
          fill: 'rgba(41, 98, 255, 0.1)',
          stroke: '#2962FF',
          strokeWidth: 2,
          strokeDashArray: [5, 5],
          selectable: true,
          evented: true,
          hasControls: true,
          hasBorders: true,
          lockRotation: true,
          lockScalingFlip: true
        });
        rect.set('aiAnnotation', true);
        rect.set('annotationType', 'poi');
        rect.set('originalData', poi);
        canvas.add(rect);
        aiAnnotationObjects.push(rect);
      });
    }

    // Display BOS lines (blue dashed)
    if (aiAnnotations.bos && aiAnnotations.bos.length > 0) {
      aiAnnotations.bos.forEach((bos, idx) => {
        // Scale coordinates from original image size to canvas size
        const x1 = (bos.x1 || 0) * scale;
        const y1 = (bos.y1 || 0) * scale;
        const x2 = (bos.x2 || 100) * scale;
        const y2 = (bos.y2 || 0) * scale;
        
        console.log(`[TEACH] BOS ${idx}:`, { original: bos, scaled: { x1, y1, x2, y2 } });
        
        const line = new fabric.Line([
          x1, y1, x2, y2
        ], {
          stroke: '#2962FF',
          strokeWidth: 2,
          strokeDashArray: [5, 5],
          selectable: true,
          evented: true,
          hasControls: true,
          hasBorders: true,
          // Keep rotation locked but allow endpoint scaling via controls
          lockRotation: true,
          lockScalingFlip: true,
          perPixelTargetFind: true,
          strokeUniform: true,
          // Allow line to be rotated by dragging endpoints
          cornerStyle: 'circle',
          cornerSize: 10,
          transparentCorners: false
        });
        line.set('aiAnnotation', true);
        line.set('annotationType', 'bos');
        line.set('originalData', bos);
        canvas.add(line);
        aiAnnotationObjects.push(line);

        // No extra handles for now to avoid runtime instability
      });
    }

    // Display circles (blue dashed)
    if (aiAnnotations.circles && aiAnnotations.circles.length > 0) {
      aiAnnotations.circles.forEach(circle => {
        // Scale coordinates from original image size to canvas size
        const left = (circle.x || 0) * scale;
        const top = (circle.y || 0) * scale;
        const radius = (circle.radius || 20) * scale;
        
        const circ = new fabric.Circle({
          left: left,
          top: top,
          radius: radius,
          fill: 'rgba(41, 98, 255, 0.1)',
          stroke: '#2962FF',
          strokeWidth: 2,
          strokeDashArray: [5, 5],
          selectable: true,
          evented: true,
          hasControls: true,
          hasBorders: true,
          originX: 'center',
          originY: 'center'
        });
        circ.set('aiAnnotation', true);
        circ.set('annotationType', 'circle');
        circ.set('originalData', circle);
        canvas.add(circ);
        aiAnnotationObjects.push(circ);
      });
    }

    // Draw user's BOS as a faint ghost reference (always visible to compare)
    if (userAnnotations && userAnnotations.bos_locations && userAnnotations.bos_locations.length > 0) {
      const srcW = userAnnotations._image_width || (canvas.originalImageWidth || 1);
      const srcH = userAnnotations._image_height || (canvas.originalImageHeight || 1);
      const dstW = canvas.originalImageWidth || 1;
      const dstH = canvas.originalImageHeight || 1;
      const rx = dstW / srcW;
      const ry = dstH / srcH;
      userAnnotations.bos_locations.forEach(bos => {
        const gx1 = ((bos.x1 || 0) * rx) * scale;
        const gy1 = ((bos.y1 || 0) * ry) * scale;
        const gx2 = ((bos.x2 || 0) * rx) * scale;
        const gy2 = ((bos.y2 || 0) * ry) * scale;
        const ghost = new fabric.Line([gx1, gy1, gx2, gy2], {
          stroke: '#9e9e9e',
          strokeWidth: 1,
          strokeDashArray: [3, 3],
          opacity: 0.8,
          selectable: false,
          evented: false
        });
        canvas.add(ghost);
        canvas.bringToFront(ghost);
        aiAnnotationObjects.push(ghost);
      });
    }

    canvas.renderAll();
  }

  function toggleAIAnnotations() {
    displayAIAnnotations();
  }

  function resetZoom() {
    if (!canvas) return;
    canvas.setZoom(1);
    canvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
    canvas.renderAll();
  }

  function displaySimilarTrades() {
    const container = $('similar-trades-list');
    const section = $('similar-trades-section');

    if (!similarTrades || similarTrades.length === 0) {
      section.style.display = 'none';
      return;
    }

    section.style.display = 'block';
    container.innerHTML = '';

    similarTrades.forEach(trade => {
      const item = document.createElement('div');
      item.className = 'similar-trade-item';
      item.innerHTML = `
        <strong>${trade.symbol || 'Unknown'}</strong> - ${trade.direction || ''} ${trade.outcome || ''}
        ${trade.distance !== undefined ? `<span style="color: var(--muted);">(similarity: ${(1 - trade.distance).toFixed(2)})</span>` : ''}
        ${trade.has_annotations ? '<span style="color: #4caf50;">✓ Annotated</span>' : ''}
      `;
      container.appendChild(item);
    });
  }

  function displayReasoning() {
    const section = $('reasoning-section');
    const text = $('ai-reasoning');

    if (!aiReasoning) {
      section.style.display = 'none';
      return;
    }

    section.style.display = 'block';
    text.textContent = aiReasoning;
  }

  async function saveCorrections() {
    try {
      // Get corrected reasoning if provided
      const correctedReasoningEl = $('corrected-reasoning');
      const correctedReasoning = correctedReasoningEl ? correctedReasoningEl.value.trim() : null;
      
      // Collect corrected annotations
      const corrections = {
        poi: [],
        bos: [],
        circles: []
      };

      // Convert corrected coordinates from scaled canvas to original image coordinates
      const scale = canvas.chartScale || 1;

      aiAnnotationObjects.forEach(obj => {
        if (!obj.aiAnnotation) return;

        const type = obj.get('annotationType');
        const original = obj.get('originalData');

        if (type === 'poi') {
          corrections.poi.push({
            original: original,
            corrected: {
              // Use bounding rect and invert viewport transform
              ...(() => {
                const br = obj.getBoundingRect(true);
                const p1 = toOriginalUnits(br.left, br.top);
                const p2 = toOriginalUnits(br.left + br.width, br.top + br.height);
                return { left: p1.x, top: p1.y, width: p2.x - p1.x, height: p2.y - p1.y };
              })()
            }
          });
        } else if (type === 'bos') {
          // Absolute endpoints via transform matrix, then remove viewport transform
          const p1 = new fabric.Point(obj.x1||0, obj.y1||0);
          const p2 = new fabric.Point(obj.x2||0, obj.y2||0);
          const m = obj.calcTransformMatrix();
          const a1 = fabric.util.transformPoint(p1, m);
          const a2 = fabric.util.transformPoint(p2, m);
          const ou1 = toOriginalUnits(a1.x, a1.y);
          const ou2 = toOriginalUnits(a2.x, a2.y);
          console.log('[TEACH][SAVE BOS] raw->norm', { raw: { x1: a1.x, y1: a1.y, x2: a2.x, y2: a2.y }, norm: { x1: ou1.x, y1: ou1.y, x2: ou2.x, y2: ou2.y }, scale, img: { w: canvas.originalImageWidth, h: canvas.originalImageHeight } });
          corrections.bos.push({
            original: original,
            corrected: {
              x1: ou1.x,
              y1: ou1.y,
              x2: ou2.x,
              y2: ou2.y
            }
          });
        } else if (type === 'circle') {
          corrections.circles.push({
            original: original,
            corrected: {
              ...(() => {
                const center = obj.getCenterPoint();
                const ou = toOriginalUnits(center.x, center.y);
                return { x: ou.x, y: ou.y, radius: (obj.radius * (obj.scaleX || 1)) / scale };
              })()
            }
          });
        }
      });

      // Save corrections to backend
        const response = await fetch('/ai/lessons', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          trade_id: tradeId,
          ai_annotations: aiAnnotations,
          corrected_annotations: corrections,
          corrected_reasoning: correctedReasoning || null
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to save corrections: ${response.statusText}`);
      }

      alert('✅ Corrections saved! AI will learn from these changes.');
    } catch (err) {
      console.error('[TEACH] Error saving corrections:', err);
      alert(`Error saving corrections: ${err.message}`);
    }
  }

  function setupCanvasHandlers() {
    if (!canvas) return;
    canvas.on('object:moving', updateHUD);
    canvas.on('object:scaling', updateHUD);
    canvas.on('object:modified', updateHUD);
    canvas.on('selection:created', updateHUD);
    canvas.on('selection:updated', updateHUD);
    canvas.on('selection:cleared', () => { if (hudEl) hudEl.innerHTML = '<strong>Coordinates</strong><br/>coords: -'; });
  }

  function updateHUD() {
    if (!hudEl) return;
    const objs = canvas.getActiveObjects();
    const scale = canvas.chartScale || 1;
    if (!objs || objs.length === 0) { hudEl.innerHTML = '<strong>Coordinates</strong><br/>coords: -'; return; }
    const obj = objs[0];
    let text = `scale=${scale.toFixed(6)} | img=${(canvas.originalImageWidth||0)}x${(canvas.originalImageHeight||0)}`;
    const type = obj.get('annotationType') || obj.type;
    text += ` | type=${type}`;
    if (type === 'circle') {
      const center = obj.getCenterPoint();
      const ou = toOriginalUnits(center.x, center.y);
      const rCanvas = (obj.radius * (obj.scaleX || 1));
      const r = rCanvas / scale;
      text += ` | x=${ou.x.toFixed(1)} y=${ou.y.toFixed(1)} r=${r.toFixed(1)}`;
    } else if (type === 'poi' || obj.type === 'rect') {
      // Use bounding rect and remove viewport transform
      const br = obj.getBoundingRect(true);
      const p1 = toOriginalUnits(br.left, br.top);
      const p2 = toOriginalUnits(br.left + br.width, br.top + br.height);
      const w = (p2.x - p1.x);
      const h = (p2.y - p1.y);
      text += ` | left=${p1.x.toFixed(1)} top=${p1.y.toFixed(1)} w=${w.toFixed(1)} h=${h.toFixed(1)}`;
    } else if (type === 'bos' || obj.type === 'line') {
      // Compute endpoints and remove viewport transform (zoom/pan)
      const p1 = new fabric.Point(obj.x1||0, obj.y1||0);
      const p2 = new fabric.Point(obj.x2||0, obj.y2||0);
      const m = obj.calcTransformMatrix();
      const a1 = fabric.util.transformPoint(p1, m);
      const a2 = fabric.util.transformPoint(p2, m);
      const ou1 = toOriginalUnits(a1.x, a1.y);
      const ou2 = toOriginalUnits(a2.x, a2.y);
      text += ` | x1=${ou1.x.toFixed(1)} y1=${ou1.y.toFixed(1)} x2=${ou2.x.toFixed(1)} y2=${ou2.y.toFixed(1)}`;
      // Percent readout relative to image dims
      const px1 = (ou1.x / (canvas.originalImageWidth||1));
      const px2 = (ou2.x / (canvas.originalImageWidth||1));
      text += ` | x%=(${px1.toFixed(4)},${px2.toFixed(4)})`;
      text += ` | raw=(${a1.x.toFixed(1)},${a1.y.toFixed(1)})→(${a2.x.toFixed(1)},${a2.y.toFixed(1)})`;
      // If user's BOS exists, show its percent for comparison
      if (userAnnotations && userAnnotations.bos_locations && userAnnotations.bos_locations.length > 0) {
        const ub = userAnnotations.bos_locations[0];
        const srcW = userAnnotations._image_width || (canvas.originalImageWidth || 1);
        const up1 = (ub.x1 || 0) / srcW;
        const up2 = (ub.x2 || 0) / srcW;
        text += ` | user x%=(${up1.toFixed(4)},${up2.toFixed(4)})`;
      }
    }
    // If AI original is attached
    const original = obj.get('originalData');
    if (original) {
      let otext = '';
      if (type === 'circle') { otext = ` | AI x=${original.x} y=${original.y} r=${original.radius}`; }
      else if (type === 'bos') { otext = ` | AI x1=${original.x1} y1=${original.y1} x2=${original.x2} y2=${original.y2}`; }
      else if (type === 'poi') { otext = ` | AI left=${original.left} top=${original.top} w=${original.width} h=${original.height}`; }
      text += otext;
    }
    hudEl.innerHTML = `<strong>Coordinates</strong><br/>${text}`;
  }

  // Initialize on page load
  init();
})();

