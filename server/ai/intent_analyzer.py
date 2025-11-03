"""
Intent Analyzer - Model-Mediated Command Layer (Phase 5E)
LLM-based intent detection that replaces regex/keyword matching
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from utils.command_schema import validate_command_schema

# Lazy initialization of OpenAI client with dual-SDK support
_client = None
_client_type = None  # 'new' or 'legacy'
_api_key = None

def get_client():
    """
    Get or create OpenAI client (lazy initialization with dual-SDK support)
    Supports both new SDK (openai.OpenAI()) and legacy SDK (openai.api_key)
    """
    global _client, _client_type, _api_key
    
    if _client is None:
        import openai
        
        API_KEY = os.getenv('OPENAI_API_KEY')
        if not API_KEY:
            raise Exception("OPENAI_API_KEY not found in environment variables")
        
        _api_key = API_KEY
        
        # Try new SDK first (v1.x+)
        try:
            if hasattr(openai, 'OpenAI'):
                _client = openai.OpenAI(api_key=API_KEY)
                _client_type = 'new'
                print("[INTENT_ANALYZER] Using new OpenAI SDK (v1.x+)")
            else:
                raise AttributeError("OpenAI class not available")
        except (AttributeError, Exception) as e:
            # Fallback to legacy SDK
            try:
                openai.api_key = API_KEY
                _client = openai  # Use module itself as client
                _client_type = 'legacy'
                print(f"[INTENT_ANALYZER] Using legacy OpenAI SDK (fallback: {e})")
            except Exception as legacy_error:
                raise Exception(f"Failed to initialize OpenAI client (new: {e}, legacy: {legacy_error})")
    
    return _client, _client_type

# Path to intent prompt
INTENT_PROMPT_PATH = Path(__file__).parent.parent / "config" / "intent_prompt.txt"

# Initialize on module load
print("[INTENT_ANALYZER] Analyzer initialized successfully")


def load_intent_prompt() -> str:
    """Load the intent analysis system prompt from file"""
    if not INTENT_PROMPT_PATH.exists():
        raise FileNotFoundError(f"Intent prompt not found at {INTENT_PROMPT_PATH}")
    
    with open(INTENT_PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def analyze_intent(
    user_text: str, 
    conversation: List[Dict[str, Any]] = None, 
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Analyze whether the user_text is a command or normal conversation.
    
    Args:
        user_text: User's message text
        conversation: Optional conversation history for context
        model: OpenAI model to use (default: gpt-4o-mini - FASTEST for this use case)
        
    Returns:
        {
            "is_command": bool,
            "confidence": float (0.0-1.0),
            "commands_detected": [ {...}, {...} ],
            "error": str (if error occurred)
        }
    """
    if not user_text or not user_text.strip():
        return {
            "is_command": False,
            "confidence": 0.0,
            "commands_detected": []
        }
    
    print(f"[INTENT_ANALYZER] Analyzing: '{user_text[:100]}'")
    
    try:
        system_prompt = load_intent_prompt()
        
        # Build messages with conversation context (limit to last 3 for speed)
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history for context (last 3 messages only for speed)
        if conversation:
            for msg in conversation[-3:]:
                if isinstance(msg, dict):
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    if content:
                        messages.append({"role": role, "content": content})
        
        # Add current user message
        messages.append({"role": "user", "content": user_text})
        
        # Call OpenAI API with JSON mode (dual-SDK support)
        client, client_type = get_client()
        
        print(f"[INTENT_ANALYZER] SDK Type: {client_type}, Calling OpenAI API with model {model}...")
        
        if client_type == 'new':
            # New SDK (v1.x+)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent results
                max_tokens=500  # Limit tokens for speed
            )
            result_text = response.choices[0].message.content
        else:
            # Legacy SDK
            try:
                response = client.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=500
                )
                result_text = response.choices[0].message.content
            except TypeError:
                # Legacy SDK doesn't support response_format - inject JSON instructions
                system_prompt_with_json = system_prompt + "\n\nIMPORTANT: You MUST respond with ONLY valid JSON. No other text."
                messages[0]["content"] = system_prompt_with_json
                response = client.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=500
                )
                result_text = response.choices[0].message.content
        
        print(f"[INTENT_ANALYZER] Received response from OpenAI (length: {len(result_text)})")
        
        # Parse JSON response
        data = json.loads(result_text)
        
        # Validate command schema if commands detected
        if data.get("is_command") and "commands_detected" in data:
            validated_commands = []
            for cmd in data["commands_detected"]:
                if validate_command_schema(cmd):
                    validated_commands.append(cmd)
                else:
                    print(f"[INTENT_ANALYZER] Invalid command schema: {cmd}")
            
            data["commands_detected"] = validated_commands
            
            # If all commands were invalid, mark as non-command
            if not validated_commands:
                data["is_command"] = False
                data["confidence"] = 0.0
        
        # Enhanced logging with confidence and command details
        confidence = data.get('confidence', 0.0)
        is_command = data.get('is_command', False)
        commands_detected = data.get('commands_detected', [])
        
        print(f"[INTENT_ANALYZER] Analysis result: is_command={is_command}, confidence={confidence:.2f}, commands={len(commands_detected)}")
        
        if is_command and commands_detected:
            print(f"[INTENT_ANALYZER] confidence: {confidence:.2f} | detected command: {commands_detected[0].get('command', 'unknown')}")
            if commands_detected[0].get('arguments'):
                args_str = str(commands_detected[0]['arguments'])
                print(f"[INTENT_ANALYZER] args: {args_str[:200]}")  # Limit length for readability
            
            # Full command details
            print(f"[INTENT_ANALYZER] Commands detected: {json.dumps(commands_detected, indent=2)}")
        
        return data
        
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON response: {str(e)}"
        print(f"[INTENT_ANALYZER] JSON decode error: {e}")
        print(f"[INTENT_ANALYZER] error: {error_msg}")
        # Fallback: try to parse as conversation
        return {
            "is_command": False,
            "confidence": 0.0,
            "commands_detected": [],
            "error": error_msg
        }
    except Exception as e:
        error_msg = str(e)
        import traceback
        print(f"[INTENT_ANALYZER] Error: {error_msg}")
        print(f"[INTENT_ANALYZER] error: {error_msg}")
        print(f"[INTENT_ANALYZER] Traceback: {traceback.format_exc()[:500]}")  # Limit traceback length
        return {
            "is_command": False,
            "confidence": 0.0,
            "commands_detected": [],
            "error": error_msg
        }

