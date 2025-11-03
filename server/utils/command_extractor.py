"""
AI-Driven Command Extraction Utility
Extracts structured command JSON from AI responses
"""
import json
import re
from typing import List, Dict, Any, Optional

def extract_commands_from_response(response_text: str) -> List[Dict[str, Any]]:
    """
    Extract command JSON from AI response text.
    
    The AI is instructed to return commands in this format:
    ```json
    {
      "commands_detected": [
        {
          "command": "delete_session",
          "type": "session",
          "name": "6E",
          "id": "6E session-176197759...",
          "action": "delete"
        }
      ]
    }
    ```
    
    Args:
        response_text: The full AI response text
        
    Returns:
        List of command dictionaries, empty list if none found
    """
    commands = []
    
    # Method 1: Look for JSON code blocks (most common)
    # Try both ```json and ``` (some models don't specify json)
    json_block_patterns = [
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{.*?"commands_detected".*?\})\s*```',
        r'```\s*(\{.*?"command".*?\})\s*```'
    ]
    
    matches = []
    for pattern in json_block_patterns:
        matches.extend(re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE))
        if matches:
            break
    
    for match in matches:
        try:
            data = json.loads(match)
            if 'commands_detected' in data and isinstance(data['commands_detected'], list):
                commands.extend(data['commands_detected'])
        except json.JSONDecodeError:
            continue
    
    # Method 2: Look for inline JSON objects
    if not commands:
        # Try to find standalone JSON objects
        json_pattern = r'\{[^{}]*"commands_detected"[^{}]*\[[^\]]*\][^{}]*\}'
        matches = re.findall(json_pattern, response_text, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                if 'commands_detected' in data and isinstance(data['commands_detected'], list):
                    commands.extend(data['commands_detected'])
                    break  # Take first valid match
            except json.JSONDecodeError:
                continue
    
    # Method 3: Look for single command JSON (without commands_detected wrapper)
    if not commands:
        # Single command object: {"command": "delete_session", "type": "session", ...}
        single_command_pattern = r'\{[^{}]*"command"[^{}]*\}'
        matches = re.findall(single_command_pattern, response_text, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                if 'command' in data:
                    commands.append(data)
                    break  # Take first valid match
            except json.JSONDecodeError:
                continue
    
    return commands


def normalize_command(command_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize command dictionary to ensure consistent format.
    
    Phase 5E: Also handles commands from intent analyzer with "arguments" field.
    
    Args:
        command_dict: Raw command dictionary from AI or intent analyzer
        
    Returns:
        Normalized command dictionary
    """
    normalized = {}
    
    # Extract command name
    normalized['command'] = command_dict.get('command') or command_dict.get('command_name') or command_dict.get('action')
    
    # Extract type
    normalized['type'] = command_dict.get('type') or command_dict.get('command_type', 'unknown')
    
    # Extract action
    normalized['action'] = command_dict.get('action') or command_dict.get('operation', '')
    
    # Phase 5E: Handle "arguments" field from intent analyzer
    arguments = command_dict.get('arguments', {})
    if arguments:
        # Extract arguments into top-level fields
        normalized.update(arguments)
    
    # Extract entity-specific fields (handle both old format and new arguments format)
    if normalized['type'] == 'session':
        # For create_session, prefer symbol over name (symbol is more reliable)
        normalized['symbol'] = command_dict.get('symbol') or arguments.get('symbol') or arguments.get('name')
        normalized['session_name'] = command_dict.get('name') or command_dict.get('session_name') or arguments.get('name')
        # Filter out filler words like "called" from session_name
        if normalized.get('session_name'):
            session_name = normalized['session_name'].strip().lower()
            # Remove common filler words
            filler_words = ['called', 'the', 'a', 'an']
            words = session_name.split()
            filtered_words = [w for w in words if w not in filler_words]
            if filtered_words:
                # Use the last word (usually the symbol) or first non-filler word
                normalized['session_name'] = filtered_words[-1].upper() if filtered_words else normalized['session_name']
            # If symbol is available and different, prefer symbol
            if normalized.get('symbol') and normalized['symbol'].upper() != normalized['session_name'].upper():
                normalized['session_name'] = normalized['symbol']
        
        normalized['session_id'] = command_dict.get('id') or command_dict.get('session_id') or arguments.get('session_id')
        # Ensure symbol is set for create_session commands
        if normalized.get('command') == 'create_session' and not normalized.get('symbol'):
            normalized['symbol'] = normalized.get('session_name') or normalized.get('name')
    elif normalized['type'] == 'trade':
        normalized['trade_id'] = command_dict.get('trade_id') or command_dict.get('id') or arguments.get('trade_id')
        normalized['symbol'] = command_dict.get('symbol') or arguments.get('symbol')
    elif normalized['type'] == 'chart':
        normalized['trade_id'] = command_dict.get('trade_id') or command_dict.get('id') or arguments.get('trade_id')
        normalized['symbol'] = command_dict.get('symbol') or arguments.get('symbol')
        normalized['trade_reference'] = command_dict.get('trade_reference') or arguments.get('trade_reference')
    
    # Extract other fields
    if command_dict.get('action_hint'):
        normalized['action_hint'] = command_dict.get('action_hint')
    if command_dict.get('lesson_id') or arguments.get('lesson_id'):
        normalized['lesson_id'] = command_dict.get('lesson_id') or arguments.get('lesson_id')
    
    # Preserve any other fields not already handled
    for key, value in command_dict.items():
        if key not in normalized and key != 'arguments':
            normalized[key] = value
    
    return normalized

