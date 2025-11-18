// Phase 4B: Chart Annotation page JavaScript with Fabric.js
// Redesigned with sidebar menu and proper drawing tools
// Version 2: Fixed background, two-click drawing
(function () {
  const API_BASE = '';
  let canvas = null;
  let tradeId = null;
  let trade = null;
  let currentTool = 'cursor'; // Start with cursor (selection mode)
  let currentColor = 'bullish'; // Default to bullish (blue)
  let poiMarkers = [];
  let bosLines = [];
  let circles = [];
  let annotationId = null;
  let hudEl = null;
  let defaultZoom = 1.0; // Store default zoom level
  let defaultViewportTransform = null; // Store default viewport transform
  let chartScale = 1; // Store the scale factor for coordinate conversion (same as teach page)
  
  // Helper: convert viewport coordinates to unzoomed canvas coords, then to original-image units
  // This matches teach.js to ensure coordinate consistency between pages
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
  
  // Drawing state
  let isDrawing = false;
  let startPoint = null;
  let endPoint = null;
  let currentRect = null;
  let currentLine = null;
  let currentCircle = null;
  let previewRect = null;
  let previewLine = null;
  let previewCircle = null;
  let clickCount = 0; // Track clicks for two-click drawing
  
  // Voice input
  let recognition = null;
  let isRecording = false;

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
      // Call loadTradeSelector without await since we're not in async context
      loadTradeSelector().catch(err => {
        console.error('[ANNOTATE] Failed to load trade selector:', err);
        loading.innerHTML = `<p style="color: #ef5350;">Error loading trades. <a href="/app/">Go back to trades</a></p>`;
      });
    }
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

      // Setup tool buttons
      setupToolButtons();

      // Setup save/export buttons
      $('save-btn').addEventListener('click', saveAnnotations);
      $('export-png-btn').addEventListener('click', exportPNG);
      
      // Setup link button
      $('link-setup-btn').addEventListener('click', () => {
        $('link-modal').style.display = 'flex';
      });
      
      $('link-cancel-btn').addEventListener('click', () => {
        $('link-modal').style.display = 'none';
      });
      
      $('link-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await linkTradeToSetup();
      });
      
      // Setup unlink button
      $('unlink-btn').addEventListener('click', () => {
        unlinkTrade();
      });

      // Setup clear all button
      $('clear-all-btn').addEventListener('click', () => {
        if (confirm('Clear all annotations?')) {
          clearAllAnnotations();
        }
      });
      
      // Setup reset zoom button
      $('reset-zoom-btn').addEventListener('click', resetZoom);

      loading.style.display = 'none';
      content.style.display = 'block';

      // Create HUD (coordinate overlay)
      hudEl = document.createElement('div');
      hudEl.className = 'coords-hud-panel';
      hudEl.innerHTML = '<strong>Coordinates</strong><br/>coords: -';
      document.body.appendChild(hudEl);
    } catch (err) {
      loading.innerHTML = `<p style="color: #ef5350;">Error: ${err.message}. <a href="/app/">Go back to trades</a></p>`;
      console.error(err);
    }
  }

  function setupToolButtons() {
    const tools = ['cursor', 'poi', 'ifvg', 'bos', 'circle', 'delete'];
    tools.forEach(tool => {
      const btn = $(`tool-${tool}`);
      if (btn) {
        btn.addEventListener('click', () => {
          setTool(tool);
        });
      }
    });
    
    // Color selection buttons
    $('color-bullish').addEventListener('click', () => {
      setColor('bullish');
    });
    $('color-bearish').addEventListener('click', () => {
      setColor('bearish');
    });
    
    // Voice input button
    $('voice-input-btn').addEventListener('click', toggleVoiceInput);
    
    // Initialize voice recognition if available
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';
      
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        const notesField = $('annotation-notes');
        notesField.value += (notesField.value ? ' ' : '') + transcript;
        updateVoiceStatus('✅ Voice input added', 'success');
      };
      
      recognition.onerror = (event) => {
        updateVoiceStatus('❌ Error: ' + event.error, 'error');
      };
      
      recognition.onend = () => {
        isRecording = false;
        $('voice-input-btn').textContent = '🎤 Voice Input';
        $('voice-input-btn').style.background = '#222';
      };
    } else {
      $('voice-input-btn').style.display = 'none';
    }
  }
  
  function setColor(color) {
    currentColor = color;
    document.querySelectorAll('[data-color]').forEach(btn => {
      btn.style.border = '2px solid #333';
    });
    $(`color-${color}`).style.border = '2px solid var(--accent)';
  }
  
  function toggleVoiceInput() {
    if (!recognition) {
      updateVoiceStatus('❌ Voice recognition not available', 'error');
      return;
    }
    
    if (isRecording) {
      recognition.stop();
      isRecording = false;
      $('voice-input-btn').textContent = '🎤 Voice Input';
      $('voice-input-btn').style.background = '#222';
      updateVoiceStatus('', '');
    } else {
      recognition.start();
      isRecording = true;
      $('voice-input-btn').textContent = '⏹ Stop Recording';
      $('voice-input-btn').style.background = '#ef5350';
      updateVoiceStatus('🎤 Listening...', 'recording');
    }
  }
  
  function updateVoiceStatus(message, type) {
    const status = $('voice-status');
    status.textContent = message;
    status.style.display = message ? 'block' : 'none';
    status.style.color = type === 'error' ? '#ef5350' : type === 'success' ? '#26a69a' : 'var(--muted)';
  }
  
  function getColorForTool() {
    return currentColor === 'bullish' ? '#2962FF' : '#F23645';
  }

  function setTool(tool) {
    currentTool = tool;
    
    // Reset click count when switching tools
    clickCount = 0;
    startPoint = null;
    endPoint = null;
    
    // Remove preview objects
    if (canvas) {
      if (previewRect) {
        canvas.remove(previewRect);
        previewRect = null;
      }
      if (previewLine) {
        canvas.remove(previewLine);
        previewLine = null;
      }
      if (previewCircle) {
        canvas.remove(previewCircle);
        previewCircle = null;
      }
      canvas.renderAll();
    }
    
    // Update button states
    document.querySelectorAll('.tool-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    
    const activeBtn = $(`tool-${tool}`);
    if (activeBtn) {
      activeBtn.classList.add('active');
    }
    
    // Update canvas selection mode
    if (canvas) {
      if (tool === 'cursor') {
        canvas.selection = true;
        canvas.defaultCursor = 'default';
        // Enable object selection and moving
        canvas.forEachObject(obj => {
          if (obj !== canvas.chartImage) {
            obj.selectable = true;
            obj.evented = true;
          }
        });
      } else {
        // Drawing tools: disable selection and moving
        canvas.selection = false;
        canvas.defaultCursor = 'crosshair';
        // Disable object selection/moving when drawing tools are active
        canvas.forEachObject(obj => {
          if (obj !== canvas.chartImage) {
            obj.selectable = false;
            obj.evented = false; // Prevent interaction with existing objects
          }
        });
        // Deselect any currently selected objects
        canvas.discardActiveObject();
      }
      canvas.renderAll();
    }
  }

  async function loadChart(chartUrl) {
    return new Promise((resolve, reject) => {
      // Use full URL to avoid CORS issues
      const fullUrl = chartUrl.startsWith('http') ? chartUrl : `${window.location.origin}${chartUrl}`;
      
      // Load chart as Fabric.js image object (non-selectable, non-movable, in background)
      fabric.Image.fromURL(fullUrl, (img) => {
        if (!canvas) {
          canvas = new fabric.Canvas('chart-canvas', {
            backgroundColor: '#0b0b0b',
            selection: true,
            preserveObjectStacking: true
          });
        }

        // Scale image to fit canvas (max width 1200px)
        const maxWidth = 1200;
        // Store original dimensions BEFORE scaling
        const originalWidth = img.width;
        const originalHeight = img.height;
        
        chartScale = originalWidth > maxWidth ? maxWidth / originalWidth : 1;
        img.scale(chartScale);
        
        canvas.setWidth(originalWidth * chartScale);
        canvas.setHeight(originalHeight * chartScale);
        
        // Store scale and original dimensions on canvas for coordinate conversion
        canvas.chartScale = chartScale;
        canvas.originalImageWidth = originalWidth;
        canvas.originalImageHeight = originalHeight;
        
        // Make chart image non-selectable and non-movable (background layer)
        img.selectable = false;
        img.evented = false;  // Cannot be clicked/moved
        img.hoverCursor = 'default';
        img.moveCursor = 'default';
        img.set('zIndex', 0);  // Background layer
        
        // Add image to canvas and send to back
        canvas.add(img);
        canvas.sendToBack(img);
        
        // Store reference to chart image for later use
        canvas.chartImage = img;

        // Store default zoom and viewport for reset
        defaultZoom = 1.0;
        defaultViewportTransform = canvas.viewportTransform.slice(); // Copy array

        // Setup canvas event handlers
        setupCanvasHandlers();
        setupDeleteHandlers();
        setupZoomHandlers();

        console.log('[ANNOTATE] Chart loaded successfully');
        canvas.renderAll();
        resolve();
      }, {
        crossOrigin: 'anonymous'
      });
    });
  }
  
  function setupZoomHandlers() {
    // Mouse wheel zoom
    canvas.on('mouse:wheel', (opt) => {
      const delta = opt.e.deltaY;
      let zoom = canvas.getZoom();
      
      // Zoom in/out based on scroll direction
      zoom *= 0.999 ** delta;
      
      // Limit zoom range (0.1x to 5x)
      zoom = Math.max(0.1, Math.min(5, zoom));
      
      // Get mouse position relative to canvas
      const pointer = canvas.getPointer(opt.e);
      
      // Zoom at mouse position
      canvas.zoomToPoint(pointer, zoom);
      
      opt.e.preventDefault();
      opt.e.stopPropagation();
    });
  }
  
  function resetZoom() {
    if (!canvas) return;
    
    // Reset zoom to default
    canvas.setZoom(defaultZoom);
    
    // Reset viewport transform to default
    if (defaultViewportTransform) {
      canvas.setViewportTransform(defaultViewportTransform);
    } else {
      // Fallback: center the chart
      canvas.viewportTransform = [1, 0, 0, 1, 0, 0];
    }
    
    canvas.renderAll();
    console.log('[ANNOTATE] Zoom reset to default');
  }

  function setupCanvasHandlers() {
    if (!canvas) return;
    canvas.on('object:moving', updateHUD);
    canvas.on('object:scaling', updateHUD);
    canvas.on('object:modified', updateHUD);
    canvas.on('selection:created', updateHUD);
    canvas.on('selection:updated', updateHUD);
    canvas.on('selection:cleared', () => { if (hudEl) hudEl.innerHTML = '<strong>Coordinates</strong><br/>coords: -'; });

    // Drawing interactions
    canvas.on('mouse:down', handleMouseDown);
    canvas.on('mouse:move', handleMouseMove);
    canvas.on('mouse:up', handleMouseUp);
  }
  
  function updateHUD() {
    if (!hudEl) return;
    const objs = canvas.getActiveObjects();
    if (!objs || objs.length === 0) { hudEl.innerHTML = '<strong>Coordinates</strong><br/>coords: -'; return; }
    const obj = objs[0];
    // Determine logical type
    const dataType = (obj.data && obj.data.type) || obj.get('annotationType');
    const type = dataType || obj.type;
    let text = `type=${type}`;
    if (type === 'circle' || obj.type === 'circle') {
      const center = obj.getCenterPoint();
      const ou = toOriginalUnits(center.x, center.y);
      const current = {
        x: ou.x.toFixed(1),
        y: ou.y.toFixed(1),
        r: ((obj.radius * (obj.scaleX || 1)) / (canvas.chartScale || 1)).toFixed(1)
      };
      text += ` | current x=${current.x} y=${current.y} r=${current.r}`;
    } else if (type === 'poi') {
      // POI is a group: use its bounding rect and remove viewport transform
      const bounds = obj.getBoundingRect(true);
      const p1 = toOriginalUnits(bounds.left, bounds.top);
      const p2 = toOriginalUnits(bounds.left + bounds.width, bounds.top + bounds.height);
      const w = (p2.x - p1.x);
      const h = (p2.y - p1.y);
      text += ` | current left=${p1.x.toFixed(1)} top=${p1.y.toFixed(1)} w=${w.toFixed(1)} h=${h.toFixed(1)}`;
    } else if (type === 'bos') {
      // BOS is a group containing a line. Compute endpoints and remove viewport transform (zoom/pan)
      const lineObj = obj.getObjects().find(o => o.type === 'line');
      if (lineObj) {
        const p1 = new fabric.Point(lineObj.x1||0, lineObj.y1||0);
        const p2 = new fabric.Point(lineObj.x2||0, lineObj.y2||0);
        const m = obj.calcTransformMatrix();
        const a1 = fabric.util.transformPoint(p1, m);
        const a2 = fabric.util.transformPoint(p2, m);
        const ou1 = toOriginalUnits(a1.x, a1.y);
        const ou2 = toOriginalUnits(a2.x, a2.y);
        text += ` | current x1=${ou1.x.toFixed(1)} y1=${ou1.y.toFixed(1)} x2=${ou2.x.toFixed(1)} y2=${ou2.y.toFixed(1)}`;
      } else if (obj.data && obj.data.originalX1 !== undefined) {
        // Fallback: use stored original coords (but still account for viewport if needed)
        const ou1 = toOriginalUnits(obj.data.originalX1, obj.data.originalY1);
        const ou2 = toOriginalUnits(obj.data.originalX2, obj.data.originalY2);
        text += ` | current x1=${ou1.x.toFixed(1)} y1=${ou1.y.toFixed(1)} x2=${ou2.x.toFixed(1)} y2=${ou2.y.toFixed(1)}`;
      }
    } else if (obj.type === 'rect') {
      const br = obj.getBoundingRect(true);
      const p1 = toOriginalUnits(br.left, br.top);
      const p2 = toOriginalUnits(br.left + br.width, br.top + br.height);
      const w = (p2.x - p1.x);
      const h = (p2.y - p1.y);
      text += ` | current left=${p1.x.toFixed(1)} top=${p1.y.toFixed(1)} w=${w.toFixed(1)} h=${h.toFixed(1)}`;
    } else if (obj.type === 'line') {
      const p1 = new fabric.Point(obj.x1||0, obj.y1||0);
      const p2 = new fabric.Point(obj.x2||0, obj.y2||0);
      const m = obj.calcTransformMatrix();
      const a1 = fabric.util.transformPoint(p1, m);
      const a2 = fabric.util.transformPoint(p2, m);
      const ou1 = toOriginalUnits(a1.x, a1.y);
      const ou2 = toOriginalUnits(a2.x, a2.y);
      text += ` | current x1=${ou1.x.toFixed(1)} y1=${ou1.y.toFixed(1)} x2=${ou2.x.toFixed(1)} y2=${ou2.y.toFixed(1)}`;
    }
    hudEl.innerHTML = `<strong>Coordinates</strong><br/>${text}`;
  }

  function getPointer(opt) {
    const e = opt ? opt.e : null;
    return canvas.getPointer(e);
  }

  function handleMouseDown(opt) {
    if (!canvas) return;
    if (currentTool === 'cursor' || currentTool === 'delete') return;
    const pointer = getPointer(opt);
    isDrawing = true;
    startPoint = { x: pointer.x, y: pointer.y };
    endPoint = { x: pointer.x, y: pointer.y };
    const color = getColorForTool();
    if (currentTool === 'poi' || currentTool === 'ifvg') {
      // Create preview rect
      previewRect = new fabric.Rect({
        left: startPoint.x, top: startPoint.y, width: 1, height: 1,
        fill: color === '#2962FF' ? 'rgba(41,98,255,0.1)' : 'rgba(242,54,69,0.1)',
        stroke: color, strokeWidth: 1, selectable: false, evented: false
      });
      canvas.add(previewRect);
    } else if (currentTool === 'bos') {
      previewLine = new fabric.Line([startPoint.x, startPoint.y, startPoint.x, startPoint.y], {
        stroke: color, strokeWidth: 1, selectable: false, evented: false
      });
      canvas.add(previewLine);
    } else if (currentTool === 'circle') {
      previewCircle = new fabric.Circle({
        left: startPoint.x, top: startPoint.y, radius: 1,
        fill: color === '#2962FF' ? 'rgba(41,98,255,0.1)' : 'rgba(242,54,69,0.1)',
        stroke: color, strokeWidth: 1, originX: 'center', originY: 'center', selectable: false, evented: false
      });
      canvas.add(previewCircle);
    }
  }

  function handleMouseMove(opt) {
    if (!isDrawing || !canvas) return;
    const pointer = getPointer(opt);
    endPoint = { x: pointer.x, y: pointer.y };
    if ((currentTool === 'poi' || currentTool === 'ifvg') && previewRect) {
      const left = Math.min(startPoint.x, endPoint.x);
      const top = Math.min(startPoint.y, endPoint.y);
      const width = Math.abs(endPoint.x - startPoint.x);
      const height = Math.abs(endPoint.y - startPoint.y);
      previewRect.set({ left, top, width, height });
      canvas.renderAll();
    } else if (currentTool === 'bos' && previewLine) {
      previewLine.set({ x1: startPoint.x, y1: startPoint.y, x2: endPoint.x, y2: endPoint.y });
      canvas.renderAll();
    } else if (currentTool === 'circle' && previewCircle) {
      const dx = endPoint.x - startPoint.x;
      const dy = endPoint.y - startPoint.y;
      const r = Math.sqrt(dx*dx + dy*dy);
      previewCircle.set({ left: startPoint.x, top: startPoint.y, radius: r });
      canvas.renderAll();
    }
  }

  function handleMouseUp(opt) {
    if (!isDrawing || !canvas) return;
    isDrawing = false;
    const color = getColorForTool();
    // Finalize creation
    if (currentTool === 'poi' || currentTool === 'ifvg') {
      if (previewRect) {
        const rect = previewRect;
        previewRect = null;
        const end = { x: rect.left + rect.width, y: rect.top + rect.height };
        createPOIBox({ x: rect.left, y: rect.top }, end, color, currentTool);
        canvas.remove(rect);
      }
    } else if (currentTool === 'bos') {
      if (previewLine) {
        const line = previewLine;
        previewLine = null;
        createBOSLine({ x: line.x1, y: line.y1 }, { x: line.x2, y: line.y2 }, color);
        canvas.remove(line);
      }
    } else if (currentTool === 'circle') {
      if (previewCircle) {
        const circ = previewCircle; const center = { x: circ.left, y: circ.top }; const r = circ.radius;
        previewCircle = null;
        createCircle(center, r, color);
        canvas.remove(circ);
      }
    }
    canvas.renderAll();
  }
  
  function createPOIBox(start, end, color, labelType = 'poi') {
    // Create rectangle from two corner points
    const left = Math.min(start.x, end.x);
    const top = Math.min(start.y, end.y);
    const width = Math.abs(end.x - start.x);
    const height = Math.abs(end.y - start.y);
    
    if (width < 10 || height < 10) {
      // Too small, don't create
      return;
    }
    
    const fillColor = color === '#2962FF' 
      ? 'rgba(41, 98, 255, 0.1)' 
      : 'rgba(242, 54, 69, 0.1)';
    
    const rect = new fabric.Rect({
      left: left,
      top: top,
      width: width,
      height: height,
      fill: fillColor,
      stroke: color,
      strokeWidth: 2,
      selectable: true,
      hasControls: true,
      data: { type: labelType, price: 0, color: color }
    });
    
    const text = new fabric.Text(labelType.toUpperCase(), {
      left: left + width / 2,
      top: top + height / 2,
      fontSize: 12,
      fill: color,
      textAlign: 'center',
      originX: 'center',
      originY: 'center',
      textBaseline: 'alphabetic', // Fix: use 'alphabetic' not 'alphabetical'
      selectable: false,
      evented: false
    });
    
    const group = new fabric.Group([rect, text], {
      left: left,
      top: top,
      selectable: true, // Always selectable (will be disabled by setTool if needed)
      evented: true, // Always interactive (will be disabled by setTool if needed)
      hasControls: true,
      data: { type: 'poi', price: 0, color: color }
    });
    
    canvas.add(group);
    canvas.bringToFront(group);
    poiMarkers.push(group);
    
    // Double-click to edit price
    group.on('mousedblclick', () => {
      const newPrice = prompt('Enter POI price:', group.data.price || '');
      if (newPrice !== null) {
        group.data.price = parseFloat(newPrice) || 0;
        const textObj = group.getObjects().find(obj => obj.type === 'text');
        if (textObj) {
          textObj.set('text', `POI: ${group.data.price}`);
        }
        canvas.renderAll();
      }
    });
    
    canvas.renderAll();
  }
  
  function createBOSLine(start, end, color) {
    // Create line from start to end point
    // Store original absolute coordinates for accurate saving
    const line = new fabric.Line([start.x, start.y, end.x, end.y], {
      stroke: color,
      strokeWidth: 2,
      selectable: true,
      hasControls: true,
      data: { 
        type: 'bos', 
        price: 0, 
        color: color,
        // Store original absolute coordinates before grouping
        originalX1: start.x,
        originalY1: start.y,
        originalX2: end.x,
        originalY2: end.y
      }
    });
    
    const text = new fabric.Text('BOS', {
      left: (start.x + end.x) / 2,
      top: (start.y + end.y) / 2 - 15,
      fontSize: 12,
      fill: color,
      textBaseline: 'alphabetic', // Fix: use 'alphabetic' not 'alphabetical'
      selectable: false,
      evented: false
    });
    
    const group = new fabric.Group([line, text], {
      selectable: true, // Always selectable (will be disabled by setTool if needed)
      evented: true, // Always interactive (will be disabled by setTool if needed)
      hasControls: true,
      data: { 
        type: 'bos', 
        price: 0, 
        color: color,
        // Store original absolute coordinates in group data too
        originalX1: start.x,
        originalY1: start.y,
        originalX2: end.x,
        originalY2: end.y
      }
    });
    
    canvas.add(group);
    canvas.bringToFront(group);
    bosLines.push(group);
    
    // Update stored coordinates when group is modified (moved/resized)
    // This ensures we always have accurate original coordinates for saving
    group.on('modified', () => {
      // After modification, update the stored original coordinates
      // Get the line object from the group
      const lineObj = group.getObjects().find(obj => obj.type === 'line');
      if (lineObj) {
        // Get relative coordinates
        const relX1 = lineObj.x1 || 0;
        const relY1 = lineObj.y1 || 0;
        const relX2 = lineObj.x2 || 0;
        const relY2 = lineObj.y2 || 0;
        
        // Transform to absolute coordinates
        const point1 = new fabric.Point(relX1, relY1);
        const point2 = new fabric.Point(relX2, relY2);
        const transform = group.calcTransformMatrix();
        const absPoint1 = fabric.util.transformPoint(point1, transform);
        const absPoint2 = fabric.util.transformPoint(point2, transform);
        
        // Update stored coordinates
        group.data.originalX1 = absPoint1.x;
        group.data.originalY1 = absPoint1.y;
        group.data.originalX2 = absPoint2.x;
        group.data.originalY2 = absPoint2.y;
      }
    });
    
    // Double-click to edit price
    group.on('mousedblclick', () => {
      const newPrice = prompt('Enter BOS price level:', group.data.price || '');
      if (newPrice !== null) {
        group.data.price = parseFloat(newPrice) || 0;
        const textObj = group.getObjects().find(obj => obj.type === 'text');
        if (textObj) {
          textObj.set('text', `BOS: ${group.data.price}`);
        }
        canvas.renderAll();
      }
    });
    
    canvas.renderAll();
  }
  
  function createCircle(center, radius, color) {
    if (radius < 5) {
      // Too small, don't create
      return;
    }
    
    const fillColor = color === '#2962FF' 
      ? 'rgba(41, 98, 255, 0.1)' 
      : 'rgba(242, 54, 69, 0.1)';
    
    const circle = new fabric.Circle({
      left: center.x,
      top: center.y,
      radius: radius,
      fill: fillColor,
      stroke: color,
      strokeWidth: 2,
      selectable: true, // Always selectable (will be disabled by setTool if needed)
      evented: true, // Always interactive (will be disabled by setTool if needed)
      hasControls: true,
      originX: 'center',
      originY: 'center',
      data: { type: 'circle', color: color }
    });
    
    canvas.add(circle);
    canvas.bringToFront(circle);
    circles.push(circle);
    
    canvas.renderAll();
  }

  function setupDeleteHandlers() {
    // Delete key handler
    canvas.on('key:down', (e) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        const activeObjects = canvas.getActiveObjects();
        if (activeObjects.length > 0) {
          activeObjects.forEach(obj => {
            canvas.remove(obj);
            poiMarkers = poiMarkers.filter(m => m !== obj);
            bosLines = bosLines.filter(l => l !== obj);
          });
          canvas.discardActiveObject();
          canvas.renderAll();
        }
      }
    });
    
    // Delete button handler
    $('tool-delete').addEventListener('click', () => {
      const activeObjects = canvas.getActiveObjects();
      if (activeObjects.length > 0) {
        activeObjects.forEach(obj => {
          canvas.remove(obj);
          poiMarkers = poiMarkers.filter(m => m !== obj);
          bosLines = bosLines.filter(l => l !== obj);
          circles = circles.filter(c => c !== obj);
        });
        canvas.discardActiveObject();
        canvas.renderAll();
      }
    });
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
          window.location.href = `/app/annotate.html?trade_id=${selectedTradeId}`;
        } else {
          alert('Please select a trade');
        }
      });
    } catch (err) {
      console.error('[ANNOTATE] Failed to load trade selector:', err);
      const select = $('trade-select');
      if (select) {
        select.innerHTML = '<option value="">Error loading trades</option>';
      }
    }
  }

  async function loadAnnotations() {
    try {
      const res = await fetch(`${API_BASE}/annotations/trade/${tradeId}`);
      const annotations = await res.json();
      
      if (annotations.length > 0) {
        const ann = annotations[0];
        annotationId = ann.id;
        
        // Clear any existing annotations before loading persisted ones
        clearAllAnnotations();

        // Load POI markers (rectangles)
        if (ann.poi_locations && ann.poi_locations.length > 0) {
          ann.poi_locations.forEach(poi => {
            addPOIFromData(poi);
          });
        }
        
        // Load BOS lines
        if (ann.bos_locations && ann.bos_locations.length > 0) {
          ann.bos_locations.forEach((bos, idx) => {
            addBOSFromData(bos, idx);
          });
        }
        
        // Load circles
        if (ann.circle_locations && ann.circle_locations.length > 0) {
          ann.circle_locations.forEach(circle => {
            addCircleFromData(circle);
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

  function addPOIFromData(poi) {
    // Recreate POI box from saved data - use actual bounds if available
    // Saved coordinates are in original image coordinates, convert to scaled canvas
    const scale = canvas.chartScale || 1;
    const color = poi.color || '#2962FF';
    const fillColor = color === '#2962FF' 
      ? 'rgba(41, 98, 255, 0.1)' 
      : 'rgba(242, 54, 69, 0.1)';
    
    // Use saved bounds if available (in original image coords), convert to canvas coords
    const left = (poi.left !== undefined ? poi.left : (poi.x !== undefined ? poi.x - 50 : 0)) * scale;
    const top = (poi.top !== undefined ? poi.top : (poi.y !== undefined ? poi.y - 30 : 0)) * scale;
    const width = (poi.width !== undefined ? poi.width : 100) * scale;
    const height = (poi.height !== undefined ? poi.height : 60) * scale;
    const centerX = (poi.x !== undefined ? poi.x : (poi.left !== undefined ? poi.left + (poi.width || 100) / 2 : left / scale + width / 2 / scale)) * scale;
    const centerY = (poi.y !== undefined ? poi.y : (poi.top !== undefined ? poi.top + (poi.height || 60) / 2 : top / scale + height / 2 / scale)) * scale;
    
    const rect = new fabric.Rect({
      left: left,
      top: top,
      width: width,
      height: height,
      fill: fillColor,
      stroke: color,
      strokeWidth: 2,
      selectable: false,
      evented: false,
      data: { type: 'poi', price: poi.price || 0, color: color }
    });
    
    const text = new fabric.Text(`POI${poi.price ? ': ' + poi.price : ''}`, {
      left: centerX,
      top: centerY,
      fontSize: 12,
      fill: color,
      textAlign: 'center',
      originX: 'center',
      originY: 'center',
      textBaseline: 'alphabetic', // Fix: use 'alphabetic' not 'alphabetical'
      selectable: false,
      evented: false
    });
    
    const group = new fabric.Group([rect, text], {
      left: left,
      top: top,
      selectable: true,
      hasControls: true,
      data: { type: 'poi', price: poi.price || 0, color: color }
    });
    
    canvas.add(group);
    canvas.bringToFront(group);
    poiMarkers.push(group);
    
    group.on('mousedblclick', () => {
      const newPrice = prompt('Enter POI price:', group.data.price || '');
      if (newPrice !== null) {
        group.data.price = parseFloat(newPrice) || 0;
        const textObj = group.getObjects().find(obj => obj.type === 'text');
        if (textObj) {
          textObj.set('text', `POI: ${group.data.price}`);
        }
        canvas.renderAll();
      }
    });
  }

  function addBOSFromData(bos, idx) {
    // Recreate BOS line from saved data - use actual coordinates if available
    // Saved coordinates are in original image coordinates, convert to scaled canvas
    // IMPORTANT: Match the exact way createBOSLine works - use absolute coordinates and let Fabric.js group it
    const scale = canvas.chartScale || 1;
    const color = bos.color || '#2962FF';
    
    // Use saved coordinates if available (these are in original image coordinates)
    let x1, y1, x2, y2;
    if (bos.x1 !== undefined && bos.y1 !== undefined && bos.x2 !== undefined && bos.y2 !== undefined) {
      // Convert from original image coordinates to scaled canvas coordinates
      x1 = bos.x1 * scale;
      y1 = bos.y1 * scale;
      x2 = bos.x2 * scale;
      y2 = bos.y2 * scale;
      
      console.log(`[LOAD BOS ${idx}]`, {
        saved: { x1: bos.x1, y1: bos.y1, x2: bos.x2, y2: bos.y2 },
        scale,
        canvas: { x1, y1, x2, y2 }
      });
    } else if (bos.y !== undefined) {
      // Backward compatibility: horizontal line
      x1 = 0;
      y1 = bos.y * scale;
      x2 = canvas.width;
      y2 = bos.y * scale;
    } else {
      // Fallback
      x1 = 0;
      y1 = 100;
      x2 = canvas.width;
      y2 = 100;
    }
    
    // Create line with ABSOLUTE coordinates (same as createBOSLine)
    // This matches how we create it initially, so Fabric.js will group it the same way
    const line = new fabric.Line([x1, y1, x2, y2], {
      stroke: color,
      strokeWidth: 2,
      selectable: true,
      hasControls: true,
      data: { 
        type: 'bos', 
        price: bos.price || 0, 
        color: color,
        // Store original absolute coordinates (same as createBOSLine)
        originalX1: x1,
        originalY1: y1,
        originalX2: x2,
        originalY2: y2
      }
    });
    
    const text = new fabric.Text(`BOS${bos.price ? ': ' + bos.price : ''}`, {
      left: (x1 + x2) / 2,
      top: (y1 + y2) / 2 - 15,
      fontSize: 12,
      fill: color,
      textBaseline: 'alphabetic', // Fix: use 'alphabetic' not 'alphabetical'
      selectable: false,
      evented: false
    });
    
    // Create group - Fabric.js will automatically position it based on the objects
    // This matches how createBOSLine works
    const group = new fabric.Group([line, text], {
      selectable: true,
      hasControls: true,
      data: { 
        type: 'bos', 
        price: bos.price || 0, 
        color: color,
        // Store original absolute coordinates (in scaled canvas coordinates)
        originalX1: x1,
        originalY1: y1,
        originalX2: x2,
        originalY2: y2
      }
    });
    
    canvas.add(group);
    canvas.bringToFront(group);
    bosLines.push(group);
    
    // Debug: Log the actual group position after Fabric.js calculates it
    console.log(`[LOAD BOS ${idx}] Group created:`, {
      expected: { x1, y1, x2, y2 },
      groupPosition: { left: group.left, top: group.top },
      groupBounds: group.getBoundingRect(),
      lineInGroup: {
        x1: line.x1,
        y1: line.y1,
        x2: line.x2,
        y2: line.y2
      }
    });
    
    group.on('mousedblclick', () => {
      const newPrice = prompt('Enter BOS price level:', group.data.price || '');
      if (newPrice !== null) {
        group.data.price = parseFloat(newPrice) || 0;
        const textObj = group.getObjects().find(obj => obj.type === 'text');
        if (textObj) {
          textObj.set('text', `BOS: ${group.data.price}`);
        }
        canvas.renderAll();
      }
    });
  }
  
  function addCircleFromData(circle) {
    // Recreate circle from saved data
    // Saved coordinates are in original image coordinates, convert to scaled canvas
    const scale = canvas.chartScale || 1;
    const color = circle.color || '#2962FF';
    const fillColor = color === '#2962FF' 
      ? 'rgba(41, 98, 255, 0.1)' 
      : 'rgba(242, 54, 69, 0.1)';
    
    console.log(`[LOAD CIRCLE]`, {
      saved: { x: circle.x, y: circle.y, radius: circle.radius },
      scale,
      canvas: { x: (circle.x || 0) * scale, y: (circle.y || 0) * scale, radius: (circle.radius || 20) * scale }
    });
    
    const circleObj = new fabric.Circle({
      left: (circle.x || 0) * scale,
      top: (circle.y || 0) * scale,
      radius: (circle.radius || 20) * scale,
      fill: fillColor,
      stroke: color,
      strokeWidth: 2,
      selectable: true, // Always selectable (will be disabled by setTool if needed)
      evented: true, // Always interactive (will be disabled by setTool if needed)
      hasControls: true,
      originX: 'center',
      originY: 'center',
      data: { type: 'circle', color: color }
    });
    
    canvas.add(circleObj);
    canvas.bringToFront(circleObj);
    circles.push(circleObj);
    
    // Update object state based on current tool
    if (currentTool !== 'cursor') {
      circleObj.selectable = false;
      circleObj.evented = false;
    }
  }

  function clearAllAnnotations() {
    poiMarkers.forEach(marker => canvas.remove(marker));
    bosLines.forEach(line => canvas.remove(line));
    circles.forEach(circle => canvas.remove(circle));
    poiMarkers = [];
    bosLines = [];
    circles = [];
    canvas.renderAll();
  }

  async function saveAnnotations() {
    if (!canvas) return;

    // Collect POI and BOS data - save in ORIGINAL IMAGE coordinates (not scaled canvas)
    // This ensures annotations work correctly on both annotate and teach pages
    const scale = canvas.chartScale || 1;
    
    const imgW = canvas.originalImageWidth || 1;
    const imgH = canvas.originalImageHeight || 1;

    const clamp = (val, min, max) => Math.max(min, Math.min(max, val));

    const poiLocations = poiMarkers.map(marker => {
      // Use bounding rect and remove viewport transform (zoom/pan) - matches teach.js
      const bounds = marker.getBoundingRect(true);
      const p1 = toOriginalUnits(bounds.left, bounds.top);
      const p2 = toOriginalUnits(bounds.left + bounds.width, bounds.top + bounds.height);
      const left = clamp(p1.x, 0, imgW);
      const top = clamp(p1.y, 0, imgH);
      const right = clamp(p2.x, 0, imgW);
      const bottom = clamp(p2.y, 0, imgH);
      return {
        left,
        top,
        width: right - left,
        height: bottom - top,
        type: marker.data?.type || 'poi',
        price: marker.data?.price || 0,
        color: marker.data?.color || '#2962FF',
        timestamp: new Date().toISOString()
      };
    });

    const bosLocations = bosLines.map((line, idx) => {
      // Use bounding box approach (same as teach.js) to avoid coordinate skew
      const bounds = line.getBoundingRect(true);
      
      // For a line, extract endpoints from the bounding box
      const isHorizontal = Math.abs(bounds.width) > Math.abs(bounds.height);
      
      let canvasX1, canvasY1, canvasX2, canvasY2;
      if (isHorizontal) {
        // Horizontal line: endpoints at left/right edges, vertically centered
        canvasX1 = bounds.left;
        canvasY1 = bounds.top + bounds.height / 2;
        canvasX2 = bounds.left + bounds.width;
        canvasY2 = bounds.top + bounds.height / 2;
      } else {
        // Vertical line: endpoints at top/bottom edges, horizontally centered
        canvasX1 = bounds.left + bounds.width / 2;
        canvasY1 = bounds.top;
        canvasX2 = bounds.left + bounds.width / 2;
        canvasY2 = bounds.top + bounds.height;
      }
      
      // Convert to original image coordinates
      const ou1 = toOriginalUnits(canvasX1, canvasY1);
      const ou2 = toOriginalUnits(canvasX2, canvasY2);
      
      // Clamp to image bounds
      const clamped = {
        x1: clamp(ou1.x, 0, imgW),
        y1: clamp(ou1.y, 0, imgH),
        x2: clamp(ou2.x, 0, imgW),
        y2: clamp(ou2.y, 0, imgH)
      };
      
      const saved = {
        x1: clamped.x1,
        y1: clamped.y1,
        x2: clamped.x2,
        y2: clamped.y2,
        price: line.data?.price || 0,
        color: line.data?.color || '#2962FF',
        timestamp: new Date().toISOString()
      };
      
      console.log(`[SAVE BOS ${idx}] Bounding box method:`, {
        bounds: { left: bounds.left, top: bounds.top, width: bounds.width, height: bounds.height },
        isHorizontal,
        canvasCoords: { x1: canvasX1, y1: canvasY1, x2: canvasX2, y2: canvasY2 },
        originalUnits: { x1: ou1.x, y1: ou1.y, x2: ou2.x, y2: ou2.y },
        clamped,
        scale: canvas.chartScale || 1,
        img: { w: imgW, h: imgH }
      });
      
      return saved;
    });
    
    const circleLocations = circles.map((circle, idx) => {
      // Convert from canvas coordinates (accounting for viewport transform) to original image coordinates
      const center = circle.getCenterPoint();
      const ou = toOriginalUnits(center.x, center.y);
      const rCanvas = (circle.radius * (circle.scaleX || 1));
      const scale = canvas.chartScale || 1;
      const cx = clamp(ou.x, 0, imgW);
      const cy = clamp(ou.y, 0, imgH);
      const saved = {
        x: cx,
        y: cy,
        radius: rCanvas / scale,
        color: circle.data?.color || '#2962FF',
        timestamp: new Date().toISOString()
      };
      
      console.log(`[SAVE CIRCLE ${idx}]`, {
        canvas: { centerX: center.x, centerY: center.y, radius: rCanvas },
        original: saved,
        scale,
        img: { w: canvas.originalImageWidth, h: canvas.originalImageHeight }
      });
      
      return saved;
    });

    const data = {
      trade_id: tradeId,
      poi_locations: poiLocations,
      bos_locations: bosLocations,
      circle_locations: circleLocations,
      image_width: canvas.originalImageWidth || null,
      image_height: canvas.originalImageHeight || null,
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
        // Try to parse JSON error, fallback to text if not JSON
        let errorMessage = 'Failed to save annotation';
        try {
          const error = await res.json();
          errorMessage = error.detail || errorMessage;
        } catch (e) {
          // Response is not JSON (probably HTML error page)
          const text = await res.text();
          errorMessage = `Server error (${res.status}): ${text.substring(0, 100)}`;
        }
        throw new Error(errorMessage);
      }

      const result = await res.json();
      annotationId = result.id;
      alert('Annotations saved successfully!');
    } catch (err) {
      alert('Error saving annotations: ' + err.message);
      console.error('Save error:', err);
    }
  }

  function exportPNG() {
    if (!canvas) return;
    const dataUrl = canvas.toDataURL({ format: 'png', multiplier: 1 });
    const link = document.createElement('a');
    link.download = `trade-${tradeId || 'annotated'}.png`;
    link.href = dataUrl;
    link.click();
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
      // Always send both parameters, even if empty (to allow unlinking)
      params.append('setup_id', setupId || '');
      params.append('entry_method_id', entryMethodId || '');

      const res = await fetch(`${API_BASE}/trades/${tradeId}/link-setup?${params.toString()}`, {
        method: 'POST'
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to link trade');
      }

      $('link-modal').style.display = 'none';
      alert('Trade linked successfully!');
      // Reload trade data to show updated links
      await init();
    } catch (err) {
      alert('Error linking trade: ' + err.message);
      console.error(err);
    }
  }

  async function unlinkTrade() {
    if (!confirm('Are you sure you want to unlink this trade from all setups and entry methods?')) {
      return;
    }

    try {
      const params = new URLSearchParams();
      params.append('setup_id', '');
      params.append('entry_method_id', '');

      const res = await fetch(`${API_BASE}/trades/${tradeId}/link-setup?${params.toString()}`, {
        method: 'POST'
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to unlink trade');
      }

      alert('Trade unlinked successfully!');
      // Reload trade data to show updated links
      await init();
    } catch (err) {
      alert('Error unlinking trade: ' + err.message);
      console.error(err);
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
