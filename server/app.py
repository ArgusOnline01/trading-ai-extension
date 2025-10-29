from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import io
import json
import os
from dotenv import load_dotenv
from decision import analyze_chart_with_gpt4v, get_base_prompt
from openai_client import get_client, get_budget_status, resolve_model, list_available_models, sync_model_aliases

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

# Sync model aliases at startup to auto-detect GPT-5
@app.on_event("startup")
async def startup_event():
    """Run model alias sync on server startup"""
    try:
        print("Syncing model aliases with OpenAI API...")
        sync_model_aliases()
    except Exception as e:
        print(f"Warning: Could not sync model aliases: {e}")
        print("Continuing with default aliases...")

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
    image: UploadFile = File(...),
    question: str = Form(...),
    model: str = Form(None),
    messages: str = Form(None)
):
    """
    Ask a natural language question about a trading chart (Phase 3A: With conversation memory)
    
    Args:
        image: Trading chart image file
        question: Natural language question about the chart
        model: Optional model selection (aliases: "fast", "balanced", "advanced" or direct model names)
        messages: Optional JSON string of previous conversation messages for context
        
    Returns:
        AskResponse with model name and conversational answer
    """
    try:
        # Validate file type
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Resolve the model to use
        selected_model = resolve_model(model)
        
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
        
        # Parse conversation history if provided
        conversation_history = []
        if messages:
            try:
                parsed_messages = json.loads(messages)
                # Take last 5 messages for context (to avoid token limits)
                conversation_history = parsed_messages[-5:]
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse messages: {e}")
                # Continue without history if parsing fails
        
        # Get OpenAI client and create response with selected model and conversation context
        client = get_client()
        response = await client.create_response(
            question, 
            image_base64, 
            model=selected_model,
            conversation_history=conversation_history
        )
        
        return AskResponse(
            model=response["model"],
            answer=response["answer"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
