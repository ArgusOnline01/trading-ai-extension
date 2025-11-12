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
  let aiQuestions = []; // Phase 4D.2: AI-generated questions
  let userAnswers = {}; // Phase 4D.2: User's answers to questions
  let chartScale = 1; // Store the scale factor for coordinate conversion
  let userAnnotations = null; // Store user's original annotations
  let userAnnotationObjects = []; // Fabric.js objects for user annotations
  let annotationId = null;
  let hudEl = null;
  
  // Drawing state
  let currentTool = null; // 'poi', 'bos', 'circle', or null
  let isDrawing = false;
  let startPoint = null;
  let endPoint = null;
  let previewRect = null;
  let previewLine = null;
  let previewCircle = null;
  let deletedAIAnnotations = []; // Track which AI annotations were deleted
  let addedAnnotations = { poi: [], bos: [], circles: [] }; // Track user-added annotations

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
      
      // Tool buttons
      $('tool-poi').addEventListener('click', () => selectTool('poi'));
      $('tool-bos').addEventListener('click', () => selectTool('bos'));
      $('tool-circle').addEventListener('click', () => selectTool('circle'));
      $('tool-select').addEventListener('click', () => selectTool(null));
      $('delete-selected-btn').addEventListener('click', deleteSelected);

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
      aiQuestions = result.questions || []; // Phase 4D.2: Store questions

      // Display AI annotations on chart
      displayAIAnnotations();

      // Display similar trades
      displaySimilarTrades();

      // Display AI reasoning
      displayReasoning();

      // Phase 4D.2: Display teaching questions
      displayQuestions();

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
        
        console.log(`[TEACH] BOS ${idx} - Creating line:`, { 
          original: bos, 
          scale,
          scaled: { x1, y1, x2, y2 },
          imgSize: { w: canvas.originalImageWidth, h: canvas.originalImageHeight },
          canvasSize: { w: canvas.width, h: canvas.height }
        });
        
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
          perPixelTargetFind: false, // Make entire bounding box clickable, not just stroke pixels
          strokeUniform: true,
          // Allow line to be rotated by dragging endpoints
          cornerStyle: 'circle',
          cornerSize: 10,
          transparentCorners: false,
          // Add padding to increase hit area around the line
          padding: 10
        });
        line.set('aiAnnotation', true);
        line.set('annotationType', 'bos');
        line.set('originalData', bos);
        canvas.add(line);
        aiAnnotationObjects.push(line);
        
        // Debug: Log what Fabric.js actually stored after creation
        console.log(`[TEACH] BOS ${idx} - After creation:`, {
          stored: { x1: line.x1, y1: line.y1, x2: line.x2, y2: line.y2 },
          position: { left: line.left, top: line.top },
          scale: { scaleX: line.scaleX, scaleY: line.scaleY },
          origin: { originX: line.originX, originY: line.originY },
          width: line.width,
          height: line.height
        });

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

    // Ghost BOS line removed - user can see their annotations via "Show My Annotations" checkbox

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

  // Phase 4D.2: Display interactive teaching questions
  function displayQuestions() {
    const section = $('teaching-questions-section');
    const container = $('questions-container');

    if (!aiQuestions || aiQuestions.length === 0) {
      section.style.display = 'none';
      return;
    }

    section.style.display = 'block';
    container.innerHTML = '';

    // Create question cards
    aiQuestions.forEach((question, index) => {
      const questionCard = document.createElement('div');
      questionCard.style.cssText = 'margin-bottom: 16px; padding: 12px; background: var(--panel); border-radius: 6px; border: 1px solid #1f1f1f;';

      const questionText = document.createElement('div');
      questionText.style.cssText = 'color: var(--text); font-size: 14px; margin-bottom: 8px; font-weight: 500;';
      questionText.textContent = `Q${index + 1}: ${question.text}`;

      const answerTextarea = document.createElement('textarea');
      answerTextarea.id = `answer-${question.id}`;
      answerTextarea.rows = 3;
      answerTextarea.placeholder = 'Your answer (optional)...';
      answerTextarea.style.cssText = 'width: 100%; padding: 8px; background: var(--bg); color: var(--text); border: 1px solid #333; border-radius: 4px; font-size: 13px; font-family: inherit;';

      // Restore previous answer if available
      if (userAnswers[question.id]) {
        answerTextarea.value = userAnswers[question.id];
      }

      // Save answer on input
      answerTextarea.addEventListener('input', () => {
        userAnswers[question.id] = answerTextarea.value.trim();
      });

      questionCard.appendChild(questionText);
      questionCard.appendChild(answerTextarea);
      container.appendChild(questionCard);
    });
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
          // Use bounding box approach (like POI) to get absolute canvas coordinates
          // This avoids issues with calcTransformMatrix double-applying transforms
          const bounds = obj.getBoundingRect(true);
          
          // For a line, the bounding box gives us the rectangular area it occupies
          // We need to extract the actual line endpoints from this
          // Assume horizontal or near-horizontal lines (BOS typically are)
          const isHorizontal = Math.abs(bounds.width) > Math.abs(bounds.height);
          
          let canvasX1, canvasY1, canvasX2, canvasY2;
          if (isHorizontal) {
            // Horizontal line: endpoints are at left and right edges, vertically centered
            canvasX1 = bounds.left;
            canvasY1 = bounds.top + bounds.height / 2;
            canvasX2 = bounds.left + bounds.width;
            canvasY2 = bounds.top + bounds.height / 2;
          } else {
            // Vertical line: endpoints are at top and bottom edges, horizontally centered
            canvasX1 = bounds.left + bounds.width / 2;
            canvasY1 = bounds.top;
            canvasX2 = bounds.left + bounds.width / 2;
            canvasY2 = bounds.top + bounds.height;
          }

          // Convert from canvas coordinates to original image coordinates
          const ou1 = toOriginalUnits(canvasX1, canvasY1);
          const ou2 = toOriginalUnits(canvasX2, canvasY2);

          // Clamp coordinates to image bounds
          const imgW = canvas.originalImageWidth || 1;
          const imgH = canvas.originalImageHeight || 1;
          const clampedX1 = Math.max(0, Math.min(imgW, ou1.x));
          const clampedY1 = Math.max(0, Math.min(imgH, ou1.y));
          const clampedX2 = Math.max(0, Math.min(imgW, ou2.x));
          const clampedY2 = Math.max(0, Math.min(imgH, ou2.y));

          console.log('[TEACH][SAVE BOS] Bounding box method:', {
            bounds: { left: bounds.left, top: bounds.top, width: bounds.width, height: bounds.height },
            isHorizontal,
            canvasCoords: { x1: canvasX1, y1: canvasY1, x2: canvasX2, y2: canvasY2 },
            originalUnits: { x1: ou1.x, y1: ou1.y, x2: ou2.x, y2: ou2.y },
            clamped: { x1: clampedX1, y1: clampedY1, x2: clampedX2, y2: clampedY2 },
            chartScale: canvas.chartScale || 1,
            img: { w: imgW, h: imgH }
          });

          corrections.bos.push({
            original: original,
            corrected: {
              x1: clampedX1,
              y1: clampedY1,
              x2: clampedX2,
              y2: clampedY2
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

      // Add user-added annotations to corrections
      addedAnnotations.poi.forEach(poi => {
        const bounds = poi.getBoundingRect(true);
        const p1 = toOriginalUnits(bounds.left, bounds.top);
        const p2 = toOriginalUnits(bounds.left + bounds.width, bounds.top + bounds.height);
        const imgW = canvas.originalImageWidth || 1;
        const imgH = canvas.originalImageHeight || 1;
        corrections.poi.push({
          original: null, // No original AI annotation
          corrected: {
            left: Math.max(0, Math.min(imgW, p1.x)),
            top: Math.max(0, Math.min(imgH, p1.y)),
            width: p2.x - p1.x,
            height: p2.y - p1.y
          },
          added: true
        });
      });
      
      addedAnnotations.bos.forEach(bos => {
        const bounds = bos.getBoundingRect(true);
        const isHorizontal = Math.abs(bounds.width) > Math.abs(bounds.height);
        let canvasX1, canvasY1, canvasX2, canvasY2;
        if (isHorizontal) {
          canvasX1 = bounds.left;
          canvasY1 = bounds.top + bounds.height / 2;
          canvasX2 = bounds.left + bounds.width;
          canvasY2 = bounds.top + bounds.height / 2;
        } else {
          canvasX1 = bounds.left + bounds.width / 2;
          canvasY1 = bounds.top;
          canvasX2 = bounds.left + bounds.width / 2;
          canvasY2 = bounds.top + bounds.height;
        }
        const ou1 = toOriginalUnits(canvasX1, canvasY1);
        const ou2 = toOriginalUnits(canvasX2, canvasY2);
        const imgW = canvas.originalImageWidth || 1;
        const imgH = canvas.originalImageHeight || 1;
        corrections.bos.push({
          original: null,
          corrected: {
            x1: Math.max(0, Math.min(imgW, ou1.x)),
            y1: Math.max(0, Math.min(imgH, ou1.y)),
            x2: Math.max(0, Math.min(imgW, ou2.x)),
            y2: Math.max(0, Math.min(imgH, ou2.y))
          },
          added: true
        });
      });
      
      addedAnnotations.circles.forEach(circle => {
        const center = circle.getCenterPoint();
        const ou = toOriginalUnits(center.x, center.y);
        const rCanvas = (circle.radius * (circle.scaleX || 1));
        const r = rCanvas / scale;
        const imgW = canvas.originalImageWidth || 1;
        const imgH = canvas.originalImageHeight || 1;
        corrections.circles.push({
          original: null,
          corrected: {
            x: Math.max(0, Math.min(imgW, ou.x)),
            y: Math.max(0, Math.min(imgH, ou.y)),
            radius: r
          },
          added: true
        });
      });

      // Phase 4D.2: Collect answers to teaching questions
      const answersArray = aiQuestions.map(q => ({
        question_id: q.id,
        question_text: q.text,
        answer: userAnswers[q.id] || '',
        context: q.context || ''
      })).filter(a => a.answer.trim() !== ''); // Only include answered questions

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
          corrected_reasoning: correctedReasoning || null,
          deleted_annotations: deletedAIAnnotations,
          questions: aiQuestions.length > 0 ? aiQuestions : null, // Phase 4D.2
          answers: answersArray.length > 0 ? answersArray : null // Phase 4D.2
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

  // ===== DRAWING & DELETION FUNCTIONS =====
  
  function selectTool(tool) {
    currentTool = tool;
    
    // Update button styles
    document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
    if (tool === 'poi') $('tool-poi').classList.add('active');
    else if (tool === 'bos') $('tool-bos').classList.add('active');
    else if (tool === 'circle') $('tool-circle').classList.add('active');
    else $('tool-select').classList.add('active');
    
    // Update canvas selection mode
    if (canvas) {
      canvas.selection = (tool === null);
      canvas.isDrawingMode = false;
      
      // Set all objects to be selectable/evented based on tool
      canvas.forEachObject(obj => {
        if (tool === null) {
          // Select mode: make everything selectable
          obj.selectable = true;
          obj.evented = true;
        } else {
          // Drawing mode: make things non-selectable
          obj.selectable = false;
          obj.evented = false;
        }
      });
      
      canvas.discardActiveObject();
      canvas.requestRenderAll();
    }
  }
  
  function deleteSelected() {
    if (!canvas) return;
    const active = canvas.getActiveObject();
    if (!active) {
      alert('No annotation selected. Click on an annotation first, then click Delete.');
      return;
    }
    
    const annotationType = active.get('annotationType');
    const isAIAnnotation = active.get('isAIAnnotation');
    
    if (isAIAnnotation) {
      // Track deleted AI annotation for learning
      const originalData = active.get('originalData');
      if (originalData) {
        deletedAIAnnotations.push({
          type: annotationType,
          data: originalData
        });
      }
      
      // Remove from AI annotations tracking
      aiAnnotationObjects = aiAnnotationObjects.filter(obj => obj !== active);
    } else {
      // If it's a user-added annotation, remove from addedAnnotations
      const idx = addedAnnotations[annotationType]?.indexOf(active);
      if (idx !== undefined && idx >= 0) {
        addedAnnotations[annotationType].splice(idx, 1);
      }
    }
    
    canvas.remove(active);
    canvas.discardActiveObject();
    canvas.requestRenderAll();
    updateDeleteButtonVisibility();
  }
  
  function updateDeleteButtonVisibility() {
    const active = canvas?.getActiveObject();
    const deleteBtn = $('delete-selected-btn');
    if (deleteBtn) {
      deleteBtn.style.display = active ? 'block' : 'none';
    }
  }
  
  function getPointer(opt) {
    return canvas.getPointer(opt.e);
  }
  
  function handleMouseDown(opt) {
    if (!currentTool || !canvas) return;
    isDrawing = true;
    const pointer = getPointer(opt);
    startPoint = { x: pointer.x, y: pointer.y };
    
    // Create preview shape
    if (currentTool === 'poi') {
      previewRect = new fabric.Rect({
        left: startPoint.x,
        top: startPoint.y,
        width: 0,
        height: 0,
        fill: 'rgba(76, 175, 80, 0.1)',
        stroke: '#4caf50',
        strokeWidth: 2,
        selectable: false,
        evented: false
      });
      canvas.add(previewRect);
    } else if (currentTool === 'bos') {
      previewLine = new fabric.Line([startPoint.x, startPoint.y, startPoint.x, startPoint.y], {
        stroke: '#4caf50',
        strokeWidth: 2,
        selectable: false,
        evented: false
      });
      canvas.add(previewLine);
    } else if (currentTool === 'circle') {
      previewCircle = new fabric.Circle({
        left: startPoint.x,
        top: startPoint.y,
        radius: 0,
        fill: 'rgba(76, 175, 80, 0.1)',
        stroke: '#4caf50',
        strokeWidth: 2,
        originX: 'center',
        originY: 'center',
        selectable: false,
        evented: false
      });
      canvas.add(previewCircle);
    }
  }
  
  function handleMouseMove(opt) {
    if (!isDrawing || !canvas || !currentTool) return;
    const pointer = getPointer(opt);
    endPoint = { x: pointer.x, y: pointer.y };
    
    if (currentTool === 'poi' && previewRect) {
      const left = Math.min(startPoint.x, endPoint.x);
      const top = Math.min(startPoint.y, endPoint.y);
      const width = Math.abs(endPoint.x - startPoint.x);
      const height = Math.abs(endPoint.y - startPoint.y);
      previewRect.set({ left, top, width, height });
      canvas.renderAll();
    } else if (currentTool === 'bos' && previewLine) {
      previewLine.set({ x2: endPoint.x, y2: endPoint.y });
      canvas.renderAll();
    } else if (currentTool === 'circle' && previewCircle) {
      const dx = endPoint.x - startPoint.x;
      const dy = endPoint.y - startPoint.y;
      const r = Math.sqrt(dx * dx + dy * dy);
      previewCircle.set({ radius: r });
      canvas.renderAll();
    }
  }
  
  function handleMouseUp(opt) {
    if (!isDrawing || !canvas || !currentTool) return;
    isDrawing = false;
    
    // Finalize creation
    if (currentTool === 'poi' && previewRect) {
      const rect = previewRect;
      previewRect = null;
      if (rect.width > 10 && rect.height > 10) {
        createAddedPOI(rect.left, rect.top, rect.width, rect.height);
      }
      canvas.remove(rect);
    } else if (currentTool === 'bos' && previewLine) {
      const line = previewLine;
      previewLine = null;
      const length = Math.sqrt(Math.pow(line.x2 - line.x1, 2) + Math.pow(line.y2 - line.y1, 2));
      if (length > 20) {
        createAddedBOS(line.x1, line.y1, line.x2, line.y2);
      }
      canvas.remove(line);
    } else if (currentTool === 'circle' && previewCircle) {
      const circ = previewCircle;
      previewCircle = null;
      if (circ.radius > 5) {
        createAddedCircle(circ.left, circ.top, circ.radius);
      }
      canvas.remove(circ);
    }
    
    canvas.renderAll();
  }
  
  function createAddedPOI(left, top, width, height) {
    const poi = new fabric.Rect({
      left,
      top,
      width,
      height,
      fill: 'rgba(76, 175, 80, 0.1)',
      stroke: '#4caf50',
      strokeWidth: 2,
      selectable: true,
      hasControls: true,
      annotationType: 'poi',
      isAIAnnotation: false,
      isAddedAnnotation: true
    });
    
    canvas.add(poi);
    addedAnnotations.poi.push(poi);
    selectTool(null); // Switch back to select mode
  }
  
  function createAddedBOS(x1, y1, x2, y2) {
    const bos = new fabric.Line([x1, y1, x2, y2], {
      stroke: '#4caf50',
      strokeWidth: 2,
      selectable: true,
      hasControls: true,
      lockScalingY: true,
      lockRotation: true,
      annotationType: 'bos',
      isAIAnnotation: false,
      isAddedAnnotation: true
    });
    
    canvas.add(bos);
    addedAnnotations.bos.push(bos);
    selectTool(null); // Switch back to select mode
  }
  
  function createAddedCircle(centerX, centerY, radius) {
    const circle = new fabric.Circle({
      left: centerX,
      top: centerY,
      radius,
      fill: 'rgba(76, 175, 80, 0.1)',
      stroke: '#4caf50',
      strokeWidth: 2,
      originX: 'center',
      originY: 'center',
      selectable: true,
      hasControls: true,
      annotationType: 'circle',
      isAIAnnotation: false,
      isAddedAnnotation: true
    });
    
    canvas.add(circle);
    addedAnnotations.circles.push(circle);
    selectTool(null); // Switch back to select mode
  }

  function setupCanvasHandlers() {
    if (!canvas) return;
    canvas.on('object:moving', updateHUD);
    canvas.on('object:scaling', updateHUD);
    canvas.on('object:modified', updateHUD);
    canvas.on('selection:created', () => {
      updateHUD();
      updateDeleteButtonVisibility();
    });
    canvas.on('selection:updated', () => {
      updateHUD();
      updateDeleteButtonVisibility();
    });
    canvas.on('selection:cleared', () => {
      if (hudEl) hudEl.innerHTML = '<strong>Coordinates</strong><br/>coords: -';
      updateDeleteButtonVisibility();
    });
    
    // Drawing handlers
    canvas.on('mouse:down', handleMouseDown);
    canvas.on('mouse:move', handleMouseMove);
    canvas.on('mouse:up', handleMouseUp);
    
    // Keyboard handler for delete key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        const active = canvas.getActiveObject();
        if (active && document.activeElement.tagName !== 'TEXTAREA' && document.activeElement.tagName !== 'INPUT') {
          e.preventDefault();
          deleteSelected();
        }
      }
    });
  }

  function updateHUD() {
    if (!hudEl) return;
    const objs = canvas.getActiveObjects();
    if (!objs || objs.length === 0) { hudEl.innerHTML = '<strong>Coordinates</strong><br/>coords: -'; return; }
    const obj = objs[0];
    const type = obj.get('annotationType') || obj.type;
    let text = `type=${type}`;
    if (type === 'circle') {
      const center = obj.getCenterPoint();
      const ou = toOriginalUnits(center.x, center.y);
      const current = {
        x: ou.x.toFixed(1),
        y: ou.y.toFixed(1),
        r: ((obj.radius * (obj.scaleX || 1)) / (canvas.chartScale || 1)).toFixed(1)
      };
      text += ` | current x=${current.x} y=${current.y} r=${current.r}`;
    } else if (type === 'poi' || obj.type === 'rect') {
      const br = obj.getBoundingRect(true);
      const p1 = toOriginalUnits(br.left, br.top);
      const p2 = toOriginalUnits(br.left + br.width, br.top + br.height);
      const current = {
        left: p1.x.toFixed(1),
        top: p1.y.toFixed(1),
        w: (p2.x - p1.x).toFixed(1),
        h: (p2.y - p1.y).toFixed(1)
      };
      text += ` | current left=${current.left} top=${current.top} w=${current.w} h=${current.h}`;
    } else if (type === 'bos' || obj.type === 'line') {
      const centerX = obj.left || 0;
      const centerY = obj.top || 0;
      const scaleX = obj.scaleX || 1;
      const scaleY = obj.scaleY || 1;

      // Compute absolute canvas coordinates by adding center position to scaled relative endpoints
      const absX1 = centerX + (obj.x1 || 0) * scaleX;
      const absY1 = centerY + (obj.y1 || 0) * scaleY;
      const absX2 = centerX + (obj.x2 || 0) * scaleX;
      const absY2 = centerY + (obj.y2 || 0) * scaleY;

      // Convert from canvas coordinates to original image coordinates
      const ou1 = toOriginalUnits(absX1, absY1);
      const ou2 = toOriginalUnits(absX2, absY2);

      // Clamp to image bounds for display (same as what will be saved)
      const imgW = canvas.originalImageWidth || 1;
      const imgH = canvas.originalImageHeight || 1;
      const current = {
        x1: Math.max(0, Math.min(imgW, ou1.x)).toFixed(1),
        y1: Math.max(0, Math.min(imgH, ou1.y)).toFixed(1),
        x2: Math.max(0, Math.min(imgW, ou2.x)).toFixed(1),
        y2: Math.max(0, Math.min(imgH, ou2.y)).toFixed(1)
      };
      text += ` | current x1=${current.x1} y1=${current.y1} x2=${current.x2} y2=${current.y2}`;
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

