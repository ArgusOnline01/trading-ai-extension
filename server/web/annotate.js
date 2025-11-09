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
  let defaultZoom = 1.0; // Store default zoom level
  let defaultViewportTransform = null; // Store default viewport transform
  
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

      // Setup tool buttons
      setupToolButtons();

      // Setup save button
      $('save-btn').addEventListener('click', saveAnnotations);
      
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
    } catch (err) {
      loading.innerHTML = `<p style="color: #ef5350;">Error: ${err.message}. <a href="/app/">Go back to trades</a></p>`;
      console.error(err);
    }
  }

  function setupToolButtons() {
    const tools = ['cursor', 'poi', 'bos', 'circle', 'delete'];
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
        const scale = img.width > maxWidth ? maxWidth / img.width : 1;
        img.scale(scale);
        
        canvas.setWidth(img.width * scale);
        canvas.setHeight(img.height * scale);
        
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
    // Mouse down - handle two-click drawing (like TradingView)
    canvas.on('mouse:down', (e) => {
      if (currentTool === 'cursor' || currentTool === 'delete') {
        return; // Let Fabric.js handle selection/deletion
      }
      
      // When drawing tools are active, prevent selection/moving of existing objects
      // Only allow drawing - ignore clicks on existing annotations
      if (e.target && e.target !== canvas.chartImage && e.target.type !== 'image') {
        // Clicked on existing annotation - prevent selection, allow drawing at that point
        // Don't return - continue to drawing logic below
        // This allows drawing on top of existing annotations
      }
      
      // Prevent Fabric.js from selecting objects when drawing tools are active
      if (e.target && e.target !== canvas.chartImage && e.target.type !== 'image') {
        // Deselect any selected objects
        canvas.discardActiveObject();
        canvas.renderAll();
      }
      
      const pointer = canvas.getPointer(e.e);
      const color = getColorForTool();
      
      if (currentTool === 'poi') {
        // POI Box: First click = corner 1, Second click = corner 2
        if (clickCount === 0) {
          // First click - set start point and show preview
          startPoint = pointer;
          clickCount = 1;
          
          // Create preview rectangle
          previewRect = new fabric.Rect({
            left: pointer.x,
            top: pointer.y,
            width: 0,
            height: 0,
            fill: `rgba(${currentColor === 'bullish' ? '41, 98, 255' : '242, 54, 69'}, 0.2)`,
            stroke: color,
            strokeWidth: 2,
            strokeDashArray: [5, 5],
            selectable: false,
            evented: false
          });
          canvas.add(previewRect);
          canvas.renderAll();
        } else if (clickCount === 1) {
          // Second click - create box
          endPoint = pointer;
          if (previewRect) canvas.remove(previewRect);
          createPOIBox(startPoint, endPoint, color);
          clickCount = 0;
          startPoint = null;
          endPoint = null;
          previewRect = null;
        }
      } else if (currentTool === 'bos') {
        // BOS Line: First click = start point, Second click = end point
        if (clickCount === 0) {
          // First click - set start point and show preview
          startPoint = pointer;
          clickCount = 1;
          
          // Create preview line
          previewLine = new fabric.Line([pointer.x, pointer.y, pointer.x, pointer.y], {
            stroke: color,
            strokeWidth: 2,
            strokeDashArray: [5, 5],
            selectable: false,
            evented: false
          });
          canvas.add(previewLine);
          canvas.renderAll();
        } else if (clickCount === 1) {
          // Second click - create line
          endPoint = pointer;
          if (previewLine) canvas.remove(previewLine);
          createBOSLine(startPoint, endPoint, color);
          clickCount = 0;
          startPoint = null;
          endPoint = null;
          previewLine = null;
        }
      } else if (currentTool === 'circle') {
        // Circle: First click = center, Second click = edge (radius)
        if (clickCount === 0) {
          // First click - set center and show preview
          startPoint = pointer;
          clickCount = 1;
          
          // Create preview circle
          previewCircle = new fabric.Circle({
            left: pointer.x,
            top: pointer.y,
            radius: 0,
            fill: `rgba(${currentColor === 'bullish' ? '41, 98, 255' : '242, 54, 69'}, 0.2)`,
            stroke: color,
            strokeWidth: 2,
            strokeDashArray: [5, 5],
            selectable: false,
            evented: false,
            originX: 'center',
            originY: 'center'
          });
          canvas.add(previewCircle);
          canvas.renderAll();
        } else if (clickCount === 1) {
          // Second click - create circle
          endPoint = pointer;
          const radius = Math.sqrt(Math.pow(endPoint.x - startPoint.x, 2) + Math.pow(endPoint.y - startPoint.y, 2));
          if (previewCircle) canvas.remove(previewCircle);
          createCircle(startPoint, radius, color);
          clickCount = 0;
          startPoint = null;
          endPoint = null;
          previewCircle = null;
        }
      }
    });
    
    // Mouse move - update preview
    canvas.on('mouse:move', (e) => {
      if (clickCount === 0) return;
      
      const pointer = canvas.getPointer(e.e);
      const color = getColorForTool();
      
      if (currentTool === 'poi' && previewRect && startPoint) {
        const width = pointer.x - startPoint.x;
        const height = pointer.y - startPoint.y;
        previewRect.set({
          width: Math.abs(width),
          height: Math.abs(height),
          left: width < 0 ? pointer.x : startPoint.x,
          top: height < 0 ? pointer.y : startPoint.y
        });
        canvas.renderAll();
      } else if (currentTool === 'bos' && previewLine && startPoint) {
        previewLine.set({
          x2: pointer.x,
          y2: pointer.y
        });
        canvas.renderAll();
      } else if (currentTool === 'circle' && previewCircle && startPoint) {
        const radius = Math.sqrt(Math.pow(pointer.x - startPoint.x, 2) + Math.pow(pointer.y - startPoint.y, 2));
        previewCircle.set({
          radius: radius
        });
        canvas.renderAll();
      }
    });
    
    // Cancel drawing on right-click or escape
    canvas.on('mouse:down:before', (e) => {
      if (e.e.button === 2 || e.e.key === 'Escape') {
        clickCount = 0;
        startPoint = null;
        endPoint = null;
        // Remove preview objects
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
    });
  }
  
  function createPOIBox(start, end, color) {
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
      data: { type: 'poi', price: 0, color: color }
    });
    
    const text = new fabric.Text('POI', {
      left: left + width / 2,
      top: top + height / 2,
      fontSize: 12,
      fill: color,
      textAlign: 'center',
      originX: 'center',
      originY: 'center',
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
    const line = new fabric.Line([start.x, start.y, end.x, end.y], {
      stroke: color,
      strokeWidth: 2,
      selectable: true,
      hasControls: true,
      data: { type: 'bos', price: 0, color: color }
    });
    
    const text = new fabric.Text('BOS', {
      left: (start.x + end.x) / 2,
      top: (start.y + end.y) / 2 - 15,
      fontSize: 12,
      fill: color,
      selectable: false,
      evented: false
    });
    
    const group = new fabric.Group([line, text], {
      selectable: true, // Always selectable (will be disabled by setTool if needed)
      evented: true, // Always interactive (will be disabled by setTool if needed)
      hasControls: true,
      data: { type: 'bos', price: 0, color: color }
    });
    
    canvas.add(group);
    canvas.bringToFront(group);
    bosLines.push(group);
    
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

  async function loadAnnotations() {
    try {
      const res = await fetch(`${API_BASE}/annotations/trade/${tradeId}`);
      const annotations = await res.json();
      
      if (annotations.length > 0) {
        const ann = annotations[0];
        annotationId = ann.id;
        
        // Load POI markers (rectangles)
        if (ann.poi_locations && ann.poi_locations.length > 0) {
          ann.poi_locations.forEach(poi => {
            addPOIFromData(poi);
          });
        }
        
        // Load BOS lines
        if (ann.bos_locations && ann.bos_locations.length > 0) {
          ann.bos_locations.forEach(bos => {
            addBOSFromData(bos);
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
    const color = poi.color || '#2962FF';
    const fillColor = color === '#2962FF' 
      ? 'rgba(41, 98, 255, 0.1)' 
      : 'rgba(242, 54, 69, 0.1)';
    
    // Use saved bounds if available, otherwise use center point (backward compatibility)
    const left = poi.left !== undefined ? poi.left : (poi.x !== undefined ? poi.x - 50 : 0);
    const top = poi.top !== undefined ? poi.top : (poi.y !== undefined ? poi.y - 30 : 0);
    const width = poi.width !== undefined ? poi.width : 100;
    const height = poi.height !== undefined ? poi.height : 60;
    const centerX = poi.x !== undefined ? poi.x : (left + width / 2);
    const centerY = poi.y !== undefined ? poi.y : (top + height / 2);
    
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

  function addBOSFromData(bos) {
    // Recreate BOS line from saved data - use actual coordinates if available
    const color = bos.color || '#2962FF';
    
    // Use saved coordinates if available, otherwise use horizontal line (backward compatibility)
    let x1, y1, x2, y2;
    if (bos.x1 !== undefined && bos.y1 !== undefined && bos.x2 !== undefined && bos.y2 !== undefined) {
      x1 = bos.x1;
      y1 = bos.y1;
      x2 = bos.x2;
      y2 = bos.y2;
    } else if (bos.y !== undefined) {
      // Backward compatibility: horizontal line
      x1 = 0;
      y1 = bos.y;
      x2 = canvas.width;
      y2 = bos.y;
    } else {
      // Fallback
      x1 = 0;
      y1 = 100;
      x2 = canvas.width;
      y2 = 100;
    }
    
    const line = new fabric.Line([x1, y1, x2, y2], {
      stroke: color,
      strokeWidth: 2,
      selectable: false,
      evented: false,
      data: { type: 'bos', price: bos.price || 0, color: color }
    });
    
    const text = new fabric.Text(`BOS${bos.price ? ': ' + bos.price : ''}`, {
      left: (x1 + x2) / 2,
      top: (y1 + y2) / 2 - 15,
      fontSize: 12,
      fill: color,
      selectable: false,
      evented: false
    });
    
    const group = new fabric.Group([line, text], {
      selectable: true,
      hasControls: true,
      data: { type: 'bos', price: bos.price || 0, color: color }
    });
    
    canvas.add(group);
    canvas.bringToFront(group);
    bosLines.push(group);
    
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
    const color = circle.color || '#2962FF';
    const fillColor = color === '#2962FF' 
      ? 'rgba(41, 98, 255, 0.1)' 
      : 'rgba(242, 54, 69, 0.1)';
    
    const circleObj = new fabric.Circle({
      left: circle.x,
      top: circle.y,
      radius: circle.radius || 20,
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

    // Collect POI and BOS data - save actual bounds for accurate restoration
    const poiLocations = poiMarkers.map(marker => {
      const bounds = marker.getBoundingRect();
      return {
        left: bounds.left,
        top: bounds.top,
        width: bounds.width,
        height: bounds.height,
        price: marker.data?.price || 0,
        color: marker.data?.color || '#2962FF',
        timestamp: new Date().toISOString()
      };
    });

    const bosLocations = bosLines.map(line => {
      // Get actual line coordinates (start and end points)
      const lineObj = line.getObjects().find(obj => obj.type === 'line');
      if (lineObj) {
        return {
          x1: lineObj.x1,
          y1: lineObj.y1,
          x2: lineObj.x2,
          y2: lineObj.y2,
          price: line.data?.price || 0,
          color: line.data?.color || '#2962FF',
          timestamp: new Date().toISOString()
        };
      }
      // Fallback to bounds if line object not found
      const bounds = line.getBoundingRect();
      return {
        x1: bounds.left,
        y1: bounds.top,
        x2: bounds.left + bounds.width,
        y2: bounds.top + bounds.height,
        price: line.data?.price || 0,
        color: line.data?.color || '#2962FF',
        timestamp: new Date().toISOString()
      };
    });
    
    const circleLocations = circles.map(circle => {
      return {
        x: circle.left,
        y: circle.top,
        radius: circle.radius,
        color: circle.data?.color || '#2962FF',
        timestamp: new Date().toISOString()
      };
    });

    const data = {
      trade_id: tradeId,
      poi_locations: poiLocations,
      bos_locations: bosLocations,
      circle_locations: circleLocations,
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

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
