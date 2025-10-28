from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import base64
import io
import json
import os
from dotenv import load_dotenv
from decision import analyze_chart_with_gpt4v, get_base_prompt

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

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Visual Trade Copilot API is running", "status": "healthy"}

@app.post("/analyze")
async def analyze_chart(file: UploadFile = File(...)):
    """
    Analyze a trading chart image using GPT-4 Vision API
    
    Args:
        file: Image file (PNG, JPEG, etc.) containing the trading chart
        
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
        
        # Analyze the chart using GPT-4 Vision
        analysis_result = await analyze_chart_with_gpt4v(image_base64, api_key)
        
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
