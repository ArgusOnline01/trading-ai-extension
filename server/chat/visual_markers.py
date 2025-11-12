"""
Phase 4E: Visual Markers Generation
Generates overlay coordinates for entry and stop loss markers on charts
"""
from typing import Dict, Any, Optional, Tuple
import base64
import io
from PIL import Image, ImageDraw, ImageFont
import json


def price_to_pixel_y(
    price: float,
    chart_min_price: float,
    chart_max_price: float,
    image_height: int,
    margin_top: int = 50,
    margin_bottom: int = 50
) -> int:
    """
    Convert price to Y pixel coordinate on chart
    
    Args:
        price: Price level
        chart_min_price: Minimum price visible on chart
        chart_max_price: Maximum price visible on chart
        image_height: Total image height in pixels
        margin_top: Top margin (price labels area)
        margin_bottom: Bottom margin
    
    Returns:
        Y pixel coordinate
    """
    if chart_max_price == chart_min_price:
        return image_height // 2
    
    # Calculate usable height (excluding margins)
    usable_height = image_height - margin_top - margin_bottom
    
    # Normalize price to 0-1 range
    price_normalized = (price - chart_min_price) / (chart_max_price - chart_min_price)
    
    # Convert to pixel (Y=0 is top, so we invert)
    y_pixel = margin_top + (1 - price_normalized) * usable_height
    
    return int(y_pixel)


def generate_overlay_image(
    image_base64: str,
    entry_price: Optional[float] = None,
    stop_loss_price: Optional[float] = None,
    chart_min_price: Optional[float] = None,
    chart_max_price: Optional[float] = None
) -> str:
    """
    Generate overlay image with entry and stop loss markers
    
    Args:
        image_base64: Base64 encoded chart image
        entry_price: Entry price level
        stop_loss_price: Stop loss price level
        chart_min_price: Minimum price on chart (if known)
        chart_max_price: Maximum price on chart (if known)
    
    Returns:
        Base64 encoded overlay image
    """
    # Decode base64 image
    image_data = base64.b64decode(image_base64)
    image = Image.open(io.BytesIO(image_data))
    
    # Create overlay (same size, transparent)
    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    width, height = image.size
    
    # Try to detect price range from image if not provided
    # This is a simplified approach - in production, you'd parse chart labels
    if chart_min_price is None or chart_max_price is None:
        # Estimate: assume price labels are in margins
        # For now, use middle 80% of image as chart area
        margin_top = int(height * 0.1)
        margin_bottom = int(height * 0.1)
    else:
        margin_top = 50
        margin_bottom = 50
    
    # Draw entry line
    if entry_price and chart_min_price and chart_max_price:
        entry_y = price_to_pixel_y(
            entry_price,
            chart_min_price,
            chart_max_price,
            height,
            margin_top,
            margin_bottom
        )
        
        # Draw horizontal line across chart
        draw.line([(0, entry_y), (width, entry_y)], fill=(0, 255, 0, 200), width=2)
        
        # Draw label
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        label_text = f"ENTRY: {entry_price:.5f}"
        bbox = draw.textbbox((0, 0), label_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Background for label
        draw.rectangle(
            [(10, entry_y - text_height - 5), (10 + text_width + 10, entry_y + 5)],
            fill=(0, 0, 0, 180)
        )
        draw.text((15, entry_y - text_height), label_text, fill=(0, 255, 0, 255), font=font)
    
    # Draw stop loss line
    if stop_loss_price and chart_min_price and chart_max_price:
        stop_y = price_to_pixel_y(
            stop_loss_price,
            chart_min_price,
            chart_max_price,
            height,
            margin_top,
            margin_bottom
        )
        
        # Draw horizontal line across chart
        draw.line([(0, stop_y), (width, stop_y)], fill=(255, 0, 0, 200), width=2)
        
        # Draw label
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        label_text = f"STOP: {stop_loss_price:.5f}"
        bbox = draw.textbbox((0, 0), label_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Background for label
        draw.rectangle(
            [(10, stop_y - text_height - 5), (10 + text_width + 10, stop_y + 5)],
            fill=(0, 0, 0, 180)
        )
        draw.text((15, stop_y - text_height), label_text, fill=(255, 0, 0, 255), font=font)
    
    # Composite overlay onto original image
    result = Image.alpha_composite(image.convert('RGBA'), overlay)
    
    # Convert back to base64
    buffer = io.BytesIO()
    result.save(buffer, format='PNG')
    overlay_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return overlay_base64


def get_overlay_coordinates(
    entry_price: Optional[float],
    stop_loss_price: Optional[float],
    chart_min_price: Optional[float],
    chart_max_price: Optional[float],
    image_width: int,
    image_height: int,
    margin_top: int = 50,
    margin_bottom: int = 50
) -> Dict[str, Any]:
    """
    Get overlay coordinates for frontend rendering (without generating image)
    
    Returns coordinates that frontend can use to draw overlays
    """
    coordinates = {
        "entry": None,
        "stop_loss": None
    }
    
    if entry_price and chart_min_price and chart_max_price:
        entry_y = price_to_pixel_y(
            entry_price,
            chart_min_price,
            chart_max_price,
            image_height,
            margin_top,
            margin_bottom
        )
        coordinates["entry"] = {
            "price": entry_price,
            "y": entry_y,
            "x1": 0,
            "x2": image_width,
            "color": "#00ff00",
            "label": f"ENTRY: {entry_price:.5f}"
        }
    
    if stop_loss_price and chart_min_price and chart_max_price:
        stop_y = price_to_pixel_y(
            stop_loss_price,
            chart_min_price,
            chart_max_price,
            image_height,
            margin_top,
            margin_bottom
        )
        coordinates["stop_loss"] = {
            "price": stop_loss_price,
            "y": stop_y,
            "x1": 0,
            "x2": image_width,
            "color": "#ff0000",
            "label": f"STOP: {stop_loss_price:.5f}"
        }
    
    return coordinates

