from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import base64
import io
import json
import os
from dotenv import load_dotenv
from decision import analyze_chart_with_gpt4v, get_base_prompt
from openai_client import get_client, get_budget_status, resolve_model, list_available_models, sync_model_aliases
from performance.routes import router as performance_router
from performance.dashboard import router as dashboard_router
from performance.learning import learning_router
from memory.routes import memory_router
from memory.utils import initialize_default_files, get_memory_status
from trades_import.routes import router as trades_import_router
from chart_reconstruction.routes import router as chart_reconstruction_router
from trades_merge.routes import router as trades_merge_router
from amn_teaching.routes import router as amn_teaching_router
from copilot_bridge.routes import router as copilot_router
from performance.learning import generate_learning_profile

# Try to import PIL, but make it optional for now
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL/Pillow not available. Using pypng for basic image processing.")

# Try to import pypng as fallback
try:
    import png
    PYPNG_AVAILABLE = True
except ImportError:
    PYPNG_AVAILABLE = False
    print("Warning: pypng not available. Image processing will be very limited.")

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Visual Trade Copilot API",
    description="Backend API for analyzing trading charts using GPT-4 Vision",
    version="1.0.0"
)

# Add CORS middleware to allow browser extension to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount performance tracking router (Phase 4A)
app.include_router(performance_router)
app.include_router(dashboard_router)

# Mount learning router (Phase 4C)
app.include_router(learning_router)

# Mount memory router (Phase 4C.1)
app.include_router(memory_router)

# Mount trades import router (Phase 4D.0)
app.include_router(trades_import_router)

# Mount chart reconstruction router (Phase 4D.1)
app.include_router(chart_reconstruction_router)

# Mount trades merge router (Phase 4D.2)
app.include_router(trades_merge_router)

# Mount AMN teaching router (Phase 4D.2)
app.include_router(amn_teaching_router)

# Mount static files for dashboard (Phase 4B.1)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount chart images (Phase 5A: Teach Copilot)
from pathlib import Path
charts_dir = Path(__file__).parent / "data" / "charts"
if charts_dir.exists():
    app.mount("/charts", StaticFiles(directory=str(charts_dir)), name="charts")

# Mount copilot bridge router (Phase 4D.2.1)
app.include_router(copilot_router)

# Phase 4C.1: Startup initialization with persistent memory
@app.on_event("startup")
async def startup_event():
    """Initialize system on server startup"""
    print("=" * 60)
    print("[BOOT] Visual Trade Copilot v4.6.0")
    print("=" * 60)
    
    # Initialize memory system
    try:
        print("[MEMORY] Checking data directory...")
        initialize_default_files()
        
        status = get_memory_status()
        print(f"[MEMORY] Loaded persistent memory:")
        print(f"         - {status['total_trades']} trades")
        print(f"         - {status['active_sessions']} sessions")
        print(f"         - {status['conversation_messages']} conversation messages")
        
        if status['total_trades'] > 0:
            print(f"         - Win rate: {status['win_rate']*100:.1f}%")
            print(f"         - Avg R: {status['avg_rr']:+.2f}")
    except Exception as e:
        print(f"[MEMORY] Warning: Could not load memory: {e}")
    
    # Sync model aliases
    try:
        print("[SYSTEM] Syncing model aliases with OpenAI API...")
        sync_model_aliases()
    except Exception as e:
        print(f"[SYSTEM] Warning: Could not sync model aliases: {e}")
        print("[SYSTEM] Continuing with default aliases...")
    
    # Phase 4D.3: Regenerate learning profile from unified logs on startup
    try:
        print("[LEARNING] Regenerating performance profile...")
        generate_learning_profile()
    except Exception as e:
        print(f"[LEARNING] Warning: Could not regenerate profile: {e}")
    
    print("[SYSTEM] Awareness layer initialized")
    print("[SYSTEM] Commands registered: stats, delete, clear, model, sessions, help")
    print("=" * 60)

# Pydantic models
class AskResponse(BaseModel):
    model: str
    answer: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Visual Trade Copilot API is running", "status": "healthy"}

@app.post("/analyze")
async def analyze_chart(
    file: UploadFile = File(...),
    model: str = Form(None)
):
    """
    Analyze a trading chart image using GPT-4 Vision API
    
    Args:
        file: Image file (PNG, JPEG, etc.) containing the trading chart
        model: Optional model selection (aliases: "fast", "balanced", "advanced" or direct model names)
        
    Returns:
        JSON response with analysis results including bias, signals, and verdict
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and process the image
        image_data = await file.read()
        
        if PIL_AVAILABLE:
            # Full image processing with PIL
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary (for PNG with transparency)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large (OpenAI has size limits)
            max_size = 2048
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Convert to base64 for OpenAI API
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        elif PYPNG_AVAILABLE:
            # Basic processing with pypng - limited but functional
            try:
                # Try to read PNG data with pypng
                reader = png.Reader(bytes=image_data)
                width, height, pixels, metadata = reader.read()
                
                # Convert to RGB if needed
                if metadata.get('alpha'):
                    # Handle RGBA -> RGB conversion
                    rgb_pixels = []
                    for row in pixels:
                        rgb_row = []
                        for i in range(0, len(row), 4):
                            r, g, b, a = row[i:i+4]
                            # Simple alpha blending with white background
                            alpha = a / 255.0
                            rgb_row.extend([
                                int(r * alpha + 255 * (1 - alpha)),
                                int(g * alpha + 255 * (1 - alpha)),
                                int(b * alpha + 255 * (1 - alpha))
                            ])
                        rgb_pixels.append(rgb_row)
                    pixels = rgb_pixels
                
                # Basic resize if too large (simple downsampling)
                max_size = 2048
                if width > max_size or height > max_size:
                    scale = min(max_size / width, max_size / height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    
                    # Simple downsampling
                    new_pixels = []
                    for y in range(0, height, int(1/scale)):
                        if len(new_pixels) >= new_height:
                            break
                        row = []
                        for x in range(0, width, int(1/scale)):
                            if len(row) >= new_width * 3:
                                break
                            pixel_idx = int(x * 3)
                            if pixel_idx < len(pixels[int(y)]):
                                row.extend(pixels[int(y)][pixel_idx:pixel_idx+3])
                        new_pixels.append(row)
                    pixels = new_pixels
                    width, height = new_width, new_height
                
                # Convert back to PNG bytes
                buffer = io.BytesIO()
                writer = png.Writer(width=width, height=height, **{k: v for k, v in metadata.items() if k != 'alpha'})
                writer.write(buffer, pixels)
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            except Exception as e:
                print(f"pypng processing failed: {e}, falling back to raw data")
                # Fallback to raw data
                image_base64 = base64.b64encode(image_data).decode('utf-8')
        else:
            # Basic processing without any image library - just convert to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Check if OpenAI API key is configured
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise HTTPException(
                status_code=500, 
                detail="OpenAI API key not configured. Please set OPENAI_API_KEY in your .env file"
            )
        
        # Resolve the model to use
        selected_model = resolve_model(model)
        
        # Analyze the chart using GPT-4 Vision with selected model
        analysis_result = await analyze_chart_with_gpt4v(image_base64, api_key, model=selected_model)
        
        # Prepare response
        response = {
            "success": True,
            "analysis": analysis_result
        }
        
        if PIL_AVAILABLE:
            response["image_info"] = {
                "width": image.width,
                "height": image.height,
                "format": "JPEG",
                "processor": "PIL/Pillow"
            }
        elif PYPNG_AVAILABLE:
            response["image_info"] = {
                "width": width if 'width' in locals() else "unknown",
                "height": height if 'height' in locals() else "unknown",
                "format": "PNG",
                "processor": "pypng"
            }
        else:
            response["image_info"] = {
                "width": "unknown",
                "height": "unknown", 
                "format": "raw",
                "processor": "none"
            }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/prompt")
async def get_prompt():
    """Get the current analysis prompt for debugging"""
    return {"prompt": get_base_prompt()}

@app.post("/ask", response_model=AskResponse)
async def ask_about_chart(
    image: UploadFile = File(None),  # Phase 3B.1: Optional for text-only mode
    question: str = Form(...),
    model: str = Form(None),
    messages: str = Form(None),
    context: str = Form(None)
):
    """
    Ask a natural language question about a trading chart (Phase 3B: With session context)
    
    Args:
        image: Trading chart image file
        question: Natural language question about the chart
        model: Optional model selection (aliases: "fast", "balanced", "advanced" or direct model names)
        messages: Optional JSON string of previous conversation messages for context
        context: Optional JSON string of session context (price, bias, POIs, etc.)
        
    Returns:
        AskResponse with model name and conversational answer
    """
    try:
        # Phase 3B.1: Handle optional image (text-only mode)
        image_base64 = None
        if image is not None:
            # Validate file type
            if not image.content_type or not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            # Read and process the image (reuse existing logic)
            image_data = await image.read()
            
            if PIL_AVAILABLE:
                # Full image processing with PIL
                image_obj = Image.open(io.BytesIO(image_data))
                
                # Convert to RGB if necessary
                if image_obj.mode != 'RGB':
                    image_obj = image_obj.convert('RGB')
                
                # Resize if too large
                max_size = 2048
                if image_obj.width > max_size or image_obj.height > max_size:
                    image_obj.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert to base64
                buffer = io.BytesIO()
                image_obj.save(buffer, format='JPEG', quality=85)
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            else:
                # Fallback to raw data
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            print(f"[INFO] Image mode: Image processed ({len(image_base64)} chars base64)")
        else:
            print("[INFO] Text-only mode: No image provided")
        
        # Resolve the model to use
        selected_model = resolve_model(model)
        print(f"[MODEL] Request model: '{model}' -> Resolved to: '{selected_model}'")
        
        # Parse conversation history if provided (Phase 3B: take last 50 messages)
        conversation_history = []
        if messages:
            try:
                parsed_messages = json.loads(messages)
                # Take last 50 messages for full context (Phase 3B upgrade from 5)
                conversation_history = parsed_messages[-50:]
                print(f"[OK] Received {len(conversation_history)} messages for context")
                print(f"[DEBUG] First message: {conversation_history[0] if conversation_history else 'None'}")
            except json.JSONDecodeError as e:
                print(f"[WARNING] Failed to parse messages: {e}")
                # Continue without history if parsing fails
        else:
            print("[INFO] No messages field in request - first message in conversation")
        
        # Parse session context if provided (Phase 3B)
        session_context = {}
        if context:
            try:
                session_context = json.loads(context)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse context: {e}")
        
        # Get OpenAI client and create response with selected model, conversation context, and session state
        client = get_client()
        response = await client.create_response(
            question, 
            image_base64, 
            model=selected_model,
            conversation_history=conversation_history,
            session_context=session_context
        )
        
        return AskResponse(
            model=response["model"],
            answer=response["answer"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print("[ERROR] Exception in /ask endpoint:")
        print(error_details)
        raise HTTPException(status_code=500, detail=f"Ask failed: {str(e)}")

@app.get("/budget")
async def get_budget():
    """Get current budget status"""
    return get_budget_status()

@app.get("/models")
async def get_models():
    """
    List all OpenAI models available to the current API key.
    Detects GPT-5 variants and provides diagnostic information.
    
    Returns:
        JSON with model list, counts, GPT-5 detection, and current aliases
    """
    try:
        return list_available_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")

# ========== Phase 3B: Session Management Endpoints ==========

# In-memory session storage (Phase 3B: Server-side session tracking)
# In Phase 3C, this will be migrated to a proper database
sessions_storage = {}

class SessionCreate(BaseModel):
    symbol: str
    title: str = None

class SessionUpdate(BaseModel):
    title: str = None
    context: dict = None

@app.get("/sessions")
async def list_sessions():
    """
    List all sessions (Phase 3B: Server-side session management)
    
    Returns:
        List of session metadata
    """
    return {
        "sessions": list(sessions_storage.values()),
        "count": len(sessions_storage)
    }

@app.post("/sessions")
async def create_session(session: SessionCreate):
    """
    Create a new trading session (Phase 3B)
    
    Args:
        session: SessionCreate with symbol and optional title
        
    Returns:
        Created session object
    """
    import time
    session_id = f"{session.symbol}-{int(time.time() * 1000)}"
    
    new_session = {
        "sessionId": session_id,
        "symbol": session.symbol.upper(),
        "title": session.title or f"{session.symbol.upper()} Session",
        "created_at": int(time.time() * 1000),
        "last_updated": int(time.time() * 1000),
        "context": {
            "latest_price": None,
            "bias": None,
            "last_poi": None,
            "timeframe": None,
            "notes": []
        }
    }
    
    sessions_storage[session_id] = new_session
    return new_session

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """
    Get a specific session by ID (Phase 3B)
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session object or 404
    """
    if session_id not in sessions_storage:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return sessions_storage[session_id]

@app.put("/sessions/{session_id}")
async def update_session(session_id: str, update: SessionUpdate):
    """
    Update session metadata or context (Phase 3B)
    
    Args:
        session_id: Session identifier
        update: SessionUpdate with optional title and/or context
        
    Returns:
        Updated session object
    """
    if session_id not in sessions_storage:
        raise HTTPException(status_code=404, detail="Session not found")
    
    import time
    session = sessions_storage[session_id]
    
    if update.title:
        session["title"] = update.title
    
    if update.context:
        # Merge context (don't overwrite, update fields)
        session["context"].update(update.context)
    
    session["last_updated"] = int(time.time() * 1000)
    
    sessions_storage[session_id] = session
    return session

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session (Phase 3B)
    
    Args:
        session_id: Session identifier
        
    Returns:
        Success message
    """
    if session_id not in sessions_storage:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del sessions_storage[session_id]
    return {"message": "Session deleted", "sessionId": session_id}

@app.get("/sessions/{session_id}/memory")
async def get_session_memory(session_id: str):
    """
    Get session context/memory (Phase 3B)
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session context object
    """
    if session_id not in sessions_storage:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return sessions_storage[session_id]["context"]

@app.put("/sessions/{session_id}/memory")
async def update_session_memory(session_id: str, context: dict):
    """
    Update session context/memory (Phase 3B)
    
    Args:
        session_id: Session identifier
        context: New context data to merge
        
    Returns:
        Updated context object
    """
    if session_id not in sessions_storage:
        raise HTTPException(status_code=404, detail="Session not found")
    
    import time
    session = sessions_storage[session_id]
    session["context"].update(context)
    session["last_updated"] = int(time.time() * 1000)
    
    sessions_storage[session_id] = session
    return session["context"]

# ========== Phase 3C: Hybrid Reasoning System ==========

from hybrid_pipeline import hybrid_reasoning, clear_session_cache

class HybridResponse(BaseModel):
    model: str
    answer: str
    hybrid_mode: bool
    vision_model: str
    reasoning_model: str
    cache_hit: bool

@app.post("/hybrid", response_model=HybridResponse)
async def hybrid_endpoint(
    image: UploadFile = File(...),
    question: str = Form(...),
    model: str = Form("gpt-5-mini"),
    session_id: str = Form("default"),
    messages: str = Form(None),
    force_refresh: bool = Form(False)
):
    """
    Hybrid Vision → Reasoning Endpoint (Phase 3C)
    
    Enables GPT-5 Mini/Search to "see" charts via GPT-4o summaries.
    Caches vision summaries per session for cost efficiency.
    
    Args:
        image: Trading chart image
        question: User's question
        model: Reasoning model (gpt-5-mini, gpt-5-search-api, etc.)
        session_id: Session identifier for caching
        messages: JSON string of conversation history
        force_refresh: Force new vision analysis (ignore cache)
        
    Returns:
        HybridResponse with answer, model info, and cache status
    """
    try:
        # Parse conversation history
        conversation_history = []
        if messages:
            try:
                parsed_messages = json.loads(messages)
                conversation_history = parsed_messages[-10:]  # Last 10 for reasoning context
                print(f"[HYBRID] Using {len(conversation_history)} messages for context")
            except json.JSONDecodeError as e:
                print(f"[WARNING] Failed to parse messages: {e}")
        
        # Run hybrid pipeline
        result = await hybrid_reasoning(
            image=image,
            question=question,
            reasoning_model=model,
            session_id=session_id,
            conversation_history=conversation_history,
            force_refresh=force_refresh
        )
        
        # Log results
        cache_status = "CACHED" if result["cache_hit"] else "NEW"
        print(f"[HYBRID] {cache_status} | Vision: {result['vision_model']} -> Reasoning: {result['reasoning_model']}")
        
        return HybridResponse(
            model=result["model"],
            answer=result["answer"],
            hybrid_mode=result["hybrid_mode"],
            vision_model=result["vision_model"],
            reasoning_model=result["reasoning_model"],
            cache_hit=result["cache_hit"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print("[ERROR] Exception in /hybrid endpoint:")
        print(error_details)
        raise HTTPException(status_code=500, detail=f"Hybrid reasoning failed: {str(e)}")

@app.delete("/hybrid/cache/{session_id}")
async def clear_hybrid_cache(session_id: str):
    """
    Clear cached vision summaries for a session (Phase 3C)
    
    Call this when user uploads a new chart or changes symbol.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Status message
    """
    try:
        result = await clear_session_cache(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
