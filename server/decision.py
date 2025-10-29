import json
import re
from typing import Dict, Any, Optional
import openai

def get_base_prompt() -> str:
    """
    Returns the base prompt for GPT-4 Vision analysis of trading charts.
    This prompt is designed for Smart Money Concepts (SMC) and supply/demand analysis.
    """
    return """You are a professional market structure trader using Smart Money Concepts (SMC) and supply/demand analysis.

Analyze the provided trading chart image and return a JSON response with the following fields:

{
  "bias": "bullish" | "bearish" | "neutral",
  "inPOI": true | false,
  "hasSweep": true | false,
  "hasDisplacement": true | false,
  "hasFVG": true | false,
  "fiftyPctMitigation": true | false,
  "verdict": "enter" | "wait" | "invalid",
  "rationale": "Brief explanation of the analysis and reasoning"
}

Analysis Guidelines:

1. BIAS: Determine the overall market bias based on:
   - Higher highs and higher lows (bullish)
   - Lower highs and lower lows (bearish)
   - Sideways or unclear structure (neutral)

2. INPOI: Check if price is currently in or near a Point of Interest (POI):
   - Supply zones (resistance areas)
   - Demand zones (support areas)
   - Previous structure levels
   - Fair Value Gaps (FVG)

3. HASSWEEP: Look for liquidity sweeps:
   - False breakouts above/below key levels
   - Wicks that extend beyond previous highs/lows
   - Quick moves that trap retail traders

4. HASDISPLACEMENT: Identify displacement moves:
   - Strong impulsive candles
   - Clear break of structure
   - Momentum shifts with volume

5. HASFVG: Check for Fair Value Gaps:
   - Gaps between candle bodies
   - Imbalances in price action
   - Areas where price may return to fill

6. FIFTYPCTMITIGATION: Look for 50% retracements:
   - Price returning to 50% of a recent move
   - First touch of a 50% level
   - Confluence with other levels

7. VERDICT: Based on the analysis:
   - "enter": Strong setup with clear signals
   - "wait": Setup forming but not complete
   - "invalid": No clear setup or conflicting signals

8. RATIONALE: Provide a brief explanation of your analysis and why you reached this conclusion.

Focus on:
- Market structure and order flow
- Supply and demand zones
- Liquidity concepts
- Fair Value Gaps
- 50% retracement levels
- Displacement and momentum

Return ONLY the JSON response, no additional text."""

def validate_analysis_result(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply rule-based validation to the LLM analysis result.
    This helps reduce hallucinations and ensures consistency with trading rules.
    
    Args:
        analysis: Raw analysis result from GPT-4 Vision
        
    Returns:
        Validated and potentially modified analysis result
    """
    # Ensure required fields exist
    required_fields = ["bias", "inPOI", "hasSweep", "hasDisplacement", "hasFVG", "fiftyPctMitigation", "verdict", "rationale"]
    for field in required_fields:
        if field not in analysis:
            analysis[field] = None
    
    # Validate bias values
    if analysis["bias"] not in ["bullish", "bearish", "neutral"]:
        analysis["bias"] = "neutral"
    
    # Validate boolean fields
    boolean_fields = ["inPOI", "hasSweep", "hasDisplacement", "hasFVG", "fiftyPctMitigation"]
    for field in boolean_fields:
        if not isinstance(analysis[field], bool):
            analysis[field] = False
    
    # Apply trading rules for verdict validation
    verdict = analysis.get("verdict", "wait")
    
    # Rule 1: If "enter", must have strong signals
    if verdict == "enter":
        strong_signals = (
            (analysis.get("hasSweep", False) and analysis.get("hasDisplacement", False)) or
            (analysis.get("fiftyPctMitigation", False) and analysis.get("hasDisplacement", False))
        )
        
        if not strong_signals:
            analysis["verdict"] = "wait"
            analysis["rationale"] += " [Modified: Enter signal requires sweep+displacement or 50% mitigation+displacement]"
    
    # Rule 2: If "enter", should be in or near a POI
    if verdict == "enter" and not analysis.get("inPOI", False):
        analysis["verdict"] = "wait"
        analysis["rationale"] += " [Modified: Enter signal should be near a Point of Interest]"
    
    # Rule 3: Ensure verdict is valid
    if analysis["verdict"] not in ["enter", "wait", "invalid"]:
        analysis["verdict"] = "wait"
    
    return analysis

async def analyze_chart_with_gpt4v(image_base64: str, api_key: str, model: str = "gpt-4o") -> Dict[str, Any]:
    """
    Send the chart image to GPT-4 Vision API for analysis.
    
    Args:
        image_base64: Base64 encoded image data
        api_key: OpenAI API key
        model: OpenAI model to use (default: gpt-4o)
        
    Returns:
        Validated analysis result
    """
    # Set the API key for the older OpenAI client
    openai.api_key = api_key
    
    try:
        # Use the current OpenAI API format
        # GPT-5 uses max_completion_tokens instead of max_tokens
        api_params = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": get_base_prompt()
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
        }
        
        # GPT-5 models use max_completion_tokens, older models use max_tokens
        # GPT-5 also doesn't support custom temperature (only default of 1)
        if 'gpt-5' in model.lower() or 'o1' in model.lower() or 'o3' in model.lower():
            api_params["max_completion_tokens"] = 500
            # GPT-5 only supports temperature=1 (default), so we don't set it
        else:
            api_params["max_tokens"] = 500
            api_params["temperature"] = 0.1  # Low temperature for consistent analysis
        
        response = await openai.ChatCompletion.acreate(**api_params)
        
        # Extract and parse the JSON response
        content = response['choices'][0]['message']['content'].strip()
        
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            analysis = json.loads(json_str)
        else:
            # Fallback if no JSON found
            analysis = {
                "bias": "neutral",
                "inPOI": False,
                "hasSweep": False,
                "hasDisplacement": False,
                "hasFVG": False,
                "fiftyPctMitigation": False,
                "verdict": "wait",
                "rationale": "Unable to parse analysis from GPT-4 response"
            }
        
        # Apply rule-based validation
        validated_analysis = validate_analysis_result(analysis)
        
        return validated_analysis
        
    except json.JSONDecodeError as e:
        return {
            "bias": "neutral",
            "inPOI": False,
            "hasSweep": False,
            "hasDisplacement": False,
            "hasFVG": False,
            "fiftyPctMitigation": False,
            "verdict": "wait",
            "rationale": f"JSON parsing error: {str(e)}"
        }
    except Exception as e:
        return {
            "bias": "neutral",
            "inPOI": False,
            "hasSweep": False,
            "hasDisplacement": False,
            "hasFVG": False,
            "fiftyPctMitigation": False,
            "verdict": "wait",
            "rationale": f"Analysis error: {str(e)}"
        }

def get_trading_rules() -> Dict[str, str]:
    """
    Returns the trading rules used for validation.
    Useful for debugging and understanding the decision logic.
    """
    return {
        "enter_requirements": "Must have either: (1) sweep + displacement, or (2) 50% mitigation + displacement",
        "poi_requirement": "Enter signals should be in or near a Point of Interest",
        "bias_validation": "Bias must be bullish, bearish, or neutral",
        "signal_validation": "All signal fields must be boolean values"
    }
