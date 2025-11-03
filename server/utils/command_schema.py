"""
Command Schema Validation
Centralized schema definition for command validation
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, ValidationError


class CommandModel(BaseModel):
    """Pydantic model for command validation"""
    command: str
    type: str
    action: str
    arguments: dict = {}
    
    class Config:
        extra = "allow"  # Allow additional fields for flexibility


def validate_command_schema(cmd: Dict[str, Any]) -> bool:
    """
    Validate command against schema using Pydantic.
    
    Args:
        cmd: Command dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        CommandModel(**cmd)
        return True
    except ValidationError as e:
        print(f"[COMMAND_SCHEMA] Validation failed: {e}")
        return False


# Schema definition for reference
COMMAND_SCHEMA = {
    "command": str,
    "type": str,
    "action": str,
    "arguments": dict
}

