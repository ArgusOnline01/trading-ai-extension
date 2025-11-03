"""
Utility to detect trade references in user messages and extract trade IDs
"""
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

def extract_trade_id_from_text(text: str) -> Optional[int]:
    """Extract trade ID from text using various patterns"""
    if not text:
        return None
    
    id_patterns = [
        r'\btrade\s*#?\s*(\d+)',  # "Trade#7" or "trade 7" or "Trade #7"
        r'\bid\s*[:\s]+(\d{8,})',
        r'trade\s+(?:id\s+)?(\d{8,})',
        r'ID\s+(\d{8,})',
        r'#(\d{8,})',
        r'trade\s*[:\s]+(\d{8,})'
    ]
    
    for pattern in id_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue
    return None

def detect_trade_reference(message: str, all_trades: List[Dict[str, Any]] = None, conversation_history: List[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Detect trade reference in user message, including from conversation history.
    Returns trade object if found, None otherwise.
    
    Detection methods:
    1. Direct trade ID mention: "trade 1540306142" or "ID 1540306142"
    2. Symbol + date: "6EZ5 from 10/29" or "6EZ5 on 10/29/2025"
    3. Symbol + outcome: "that 6EZ5 loss" or "6EZ5 win"
    4. Recent trade context from conversation history (if user asks "its image", "that trade", etc.)
    5. Trade ID extraction from previous AI messages
    
    Args:
        message: User's message text
        all_trades: List of all trades (from /performance/all)
        conversation_history: Optional list of previous messages (for context)
        
    Returns:
        Trade dict if found, None otherwise
    """
    if not message:
        return None
    
    message_lower = message.lower()
    
    # Method 1: Direct trade ID
    id_patterns = [
        r'\btrade\s+(?:id\s+)?(\d{8,})',
        r'\bid\s+(\d{8,})',
        r'#(\d{8,})',
        r'trade\s*[:\s]+(\d{8,})'
    ]
    
    for pattern in id_patterns:
        match = re.search(pattern, message_lower, re.IGNORECASE)
        if match:
            trade_id = int(match.group(1))
            if all_trades:
                trade = next((t for t in all_trades if (t.get('id') == trade_id or 
                                                       t.get('trade_id') == trade_id or
                                                       str(t.get('id')) == str(trade_id))), None)
                if trade:
                    return trade
    
    # Method 2: Symbol + date
    if all_trades:
        # Extract symbol (typically 3-5 uppercase letters/numbers)
        symbol_match = re.search(r'\b([A-Z0-9]{3,6})\b', message.upper())
        if symbol_match:
            symbol = symbol_match.group(1)
            
            # Extract date patterns
            date_patterns = [
                r'(\d{1,2})/(\d{1,2})/(\d{2,4})',  # 10/29/2025 or 10/29/25
                r'(\d{1,2})/(\d{1,2})',  # 10/29
                r'(\d{4})-(\d{2})-(\d{2})',  # 2025-10-29
            ]
            
            for pattern in date_patterns:
                date_match = re.search(pattern, message)
                if date_match:
                    # Find trades matching symbol and date
                    for trade in all_trades:
                        if trade.get('symbol', '').upper() == symbol:
                            trade_date = trade.get('timestamp') or trade.get('entry_time')
                            if trade_date:
                                # Simple date matching (could be improved)
                                date_str = str(trade_date)
                                if any(d in date_str for d in date_match.groups()):
                                    return trade
    
    # Method 3: Symbol + outcome (win/loss/breakeven)
    if all_trades and symbol_match:
        symbol = symbol_match.group(1)
        outcome_keywords = {
            'win': ['win', 'won', 'profit', 'positive'],
            'loss': ['loss', 'lose', 'negative', 'red'],
            'breakeven': ['breakeven', 'even', 'zero']
        }
        
        for outcome_type, keywords in outcome_keywords.items():
            if any(kw in message_lower for kw in keywords):
                # Find most recent trade matching symbol and outcome
                matching_trades = [
                    t for t in all_trades
                    if t.get('symbol', '').upper() == symbol and
                    (t.get('outcome', '').lower() == outcome_type or
                     (outcome_type == 'win' and t.get('pnl', 0) > 0) or
                     (outcome_type == 'loss' and t.get('pnl', 0) < 0) or
                     (outcome_type == 'breakeven' and t.get('pnl', 0) == 0))
                ]
                if matching_trades:
                    # Return most recent
                    return sorted(matching_trades, 
                                 key=lambda t: t.get('timestamp') or t.get('entry_time') or '', 
                                 reverse=True)[0]
    
    # Method 4: Check conversation history for recently mentioned trades
    # (e.g., "its image", "that trade's chart", "can you see it")
    if conversation_history and all_trades:
        # Look for phrases that reference a previously mentioned trade
        reference_phrases = ['its image', 'that trade', 'this trade', 'the trade', 
                           'can you see', 'show me', 'pull up', 'that chart', 'show its chart',
                           'show chart', 'show the chart', 'show it', 'open chart', 'open image', 
                           'open the chart', 'pull up chart', 'pull up image', 'pull up the chart',
                           'display chart', 'display image', 'can you show',
                           'redo this', 'redo', 'do this', 'this one', 'do it again',
                           'lets redo', 'review this', 'teach me about this', 'open teaching for this']
        if any(phrase in message_lower for phrase in reference_phrases):
            # Search backwards through conversation history for trade mentions (most recent first)
            # Check both user and assistant messages for trade context
            for msg in reversed(conversation_history[-15:]):  # Check last 15 messages
                content = str(msg.get('content', ''))
                content_upper = content.upper()
                role = msg.get('role', '')
                
                # Priority 1: Extract trade ID from message (most reliable)
                # Also check for "Trade#7" format explicitly
                trade_id_patterns = [
                    r'\btrade\s*#?\s*(\d+)',  # "Trade#7" or "trade 7"
                    r'\btrade\s+(?:number\s+)?(\d+)',  # "trade number 7"
                ]
                trade_id = None
                for pattern in trade_id_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        try:
                            trade_id = int(match.group(1))
                            break
                        except (ValueError, IndexError):
                            continue
                
                # If no match from patterns, try extract_trade_id_from_text
                if not trade_id:
                    trade_id = extract_trade_id_from_text(content)
                
                if trade_id:
                    # For short IDs like "7", need to match against trade index or find by symbol+context
                    if trade_id < 1000:
                        # This is likely a trade number/index, not a full trade ID
                        # Try to find by matching symbol from the same message
                        symbol_match = re.search(r'\b([A-Z]{2,6}\d{0,1})\b', content_upper)
                        if symbol_match:
                            symbol = symbol_match.group(1)
                            # Find all trades with this symbol, sort by date, then get by index
                            matching_trades = [t for t in all_trades if t.get('symbol', '').upper() == symbol]
                            if matching_trades:
                                sorted_trades = sorted(matching_trades,
                                                      key=lambda t: t.get('timestamp') or t.get('entry_time') or '',
                                                      reverse=True)
                                if trade_id <= len(sorted_trades):
                                    trade = sorted_trades[trade_id - 1]  # Convert to 0-based index
                                    print(f"[TRADE_DETECTOR] Found trade #{trade_id} ({symbol}) from conversation: '{content[:100]}'")
                                    return trade
                    
                    # Try to match full trade ID
                    trade = next((t for t in all_trades if (t.get('id') == trade_id or 
                                                           t.get('trade_id') == trade_id or
                                                           str(t.get('id')) == str(trade_id))), None)
                    if trade:
                        print(f"[TRADE_DETECTOR] Found specific trade {trade_id} from conversation history: '{content[:100]}'")
                        return trade
                
                # Priority 2: Look for symbol + date combination (e.g., "6EZ5 from 10/29" or "6EZ5 on 2025-10-23")
                # This is CRITICAL to avoid matching wrong trade when multiple trades have same symbol
                symbol_match = re.search(r'\b([A-Z]{2,6}\d{0,1})\b', content_upper)
                if symbol_match:
                    symbol = symbol_match.group(1)
                    
                    # Extract date patterns from the same message
                    date_patterns = [
                        r'(\d{1,2})/(\d{1,2})/(\d{2,4})',  # 10/29/2025
                        r'(\d{1,2})/(\d{1,2})',  # 10/29
                        r'(\d{4})-(\d{2})-(\d{2})',  # 2025-10-23
                    ]
                    
                    for date_pattern in date_patterns:
                        date_match = re.search(date_pattern, content)
                        if date_match:
                            # Find trade matching BOTH symbol AND date
                            for trade in all_trades:
                                if trade.get('symbol', '').upper() == symbol:
                                    trade_date = trade.get('timestamp') or trade.get('entry_time') or trade.get('date')
                                    if trade_date:
                                        date_str = str(trade_date)
                                        # Check if date components match
                                        if any(d in date_str for d in date_match.groups()):
                                            print(f"[TRADE_DETECTOR] Found trade {symbol} with date from conversation: '{content[:100]}'")
                                            return trade
                
                # Priority 3: Look for symbol + outcome (e.g., "6EZ5 loss")
                if symbol_match:
                    symbol = symbol_match.group(1)
                    outcome_keywords = {
                        'win': ['win', 'won', 'profit', 'positive', r'\+'],
                        'loss': ['loss', 'lose', 'negative', 'red', r'-'],
                        'breakeven': ['breakeven', 'even', 'zero']
                    }
                    
                    for outcome_type, keywords in outcome_keywords.items():
                        if any(re.search(kw, content, re.IGNORECASE) for kw in keywords):
                            # Find trade matching symbol and outcome
                            matching_trades = [
                                t for t in all_trades
                                if t.get('symbol', '').upper() == symbol and
                                (t.get('outcome', '').lower() == outcome_type or
                                 (outcome_type == 'win' and t.get('pnl', 0) > 0) or
                                 (outcome_type == 'loss' and t.get('pnl', 0) < 0) or
                                 (outcome_type == 'breakeven' and t.get('pnl', 0) == 0))
                            ]
                            if matching_trades:
                                # Return most recent matching trade
                                sorted_matches = sorted(matching_trades,
                                                       key=lambda t: t.get('timestamp') or t.get('entry_time') or '',
                                                       reverse=True)
                                print(f"[TRADE_DETECTOR] Found trade {symbol} {outcome_type} from conversation: '{content[:100]}'")
                                return sorted_matches[0]
                
                # Priority 4: Look for explicit symbol mentions with context (e.g., "first trade: MNQZ5")
                # Only use this if no date was found above (to avoid wrong trade)
                symbol_patterns = [
                    r'\b([A-Z]{2,6}\d{0,1})\s*\|\s*(?:win|loss|breakeven)',  # "MNQZ5 | win"
                    r'(?:first|second|third|last|next)\s+(?:trade|one)[\s:]*([A-Z]{2,6}\d{0,1})',  # "first trade: MNQZ5"
                    r'✅\s*[^:]*:\s*([A-Z]{2,6}\d{0,1})',  # "✅ First trade: MNQZ5"
                    r'\b([A-Z]{2,6}\d{0,1})\s+win|\b([A-Z]{2,6}\d{0,1})\s+loss',  # "MNQZ5 win" or "MNQZ5 loss"
                ]
                
                for pattern in symbol_patterns:
                    matches = re.findall(pattern, content_upper)
                    for match in matches:
                        symbol = match if isinstance(match, str) else (match[0] if match[0] else match[1] if len(match) > 1 else None)
                        if symbol:
                            # Find most recent trade with this symbol (but only if no date/outcome was found)
                            matching = [t for t in all_trades if t.get('symbol', '').upper() == symbol.upper()]
                            if matching:
                                # Return most recent
                                sorted_matches = sorted(matching,
                                                       key=lambda t: t.get('timestamp') or t.get('entry_time') or '',
                                                       reverse=True)
                                print(f"[TRADE_DETECTOR] Found trade {symbol} from conversation context: '{content[:100]}'")
                                return sorted_matches[0]
                
                # Priority 5: Try symbol extraction (e.g., "SILZ5 | loss") - fallback
                if role == 'assistant':
                    symbol_match = re.search(r'\b([A-Z0-9]{3,6})\s*\|', content_upper)
                    if symbol_match:
                        symbol = symbol_match.group(1)
                        # Find most recent trade with this symbol
                        matching = [t for t in all_trades if t.get('symbol', '').upper() == symbol.upper()]
                        if matching:
                            # Return most recent
                            sorted_matches = sorted(matching,
                                                   key=lambda t: t.get('timestamp') or t.get('entry_time') or '',
                                                   reverse=True)
                            print(f"[TRADE_DETECTOR] Found trade {symbol} from assistant message")
                            return sorted_matches[0]
    
    # Method 5: Recent trade context (most recent trade if message is vague)
    if all_trades and any(kw in message_lower for kw in ['that trade', 'this trade', 'the trade', 'last trade']):
        # Return most recent trade
        sorted_trades = sorted(all_trades, 
                              key=lambda t: t.get('timestamp') or t.get('entry_time') or '', 
                              reverse=True)
        if sorted_trades:
            return sorted_trades[0]
    
    return None


def load_chart_image_for_trade(trade: Dict[str, Any]) -> Optional[str]:
    """
    Load chart image file for a trade and return as base64.
    Processes image similar to uploaded images (resize, convert to RGB, etc.)
    
    Args:
        trade: Trade dictionary
        
    Returns:
        Base64-encoded image string (JPEG), or None if not found
    """
    from pathlib import Path
    import base64
    import io
    
    # Try to import PIL for image processing
    try:
        from PIL import Image
        PIL_AVAILABLE = True
    except ImportError:
        PIL_AVAILABLE = False
    
    charts_dir = Path(__file__).parent.parent / "data" / "charts"
    
    if not charts_dir.exists():
        return None
    
    image_file_path = None
    
    # Try chart_path first
    chart_path = trade.get('chart_path')
    if chart_path:
        # Handle both absolute and relative paths
        if Path(chart_path).exists():
            image_file_path = Path(chart_path)
        else:
            # Try to extract filename
            filename = Path(chart_path).name
            candidate = charts_dir / filename
            if candidate.exists():
                image_file_path = candidate
    
    # Try pattern matching if chart_path didn't work
    if not image_file_path or not image_file_path.exists():
        trade_id = trade.get('id') or trade.get('trade_id') or trade.get('session_id')
        symbol = trade.get('symbol', '')
        
        if trade_id and symbol:
            # Try common patterns
            patterns = [
                f"{symbol}_5m_{trade_id}.png",
                f"{symbol}_15m_{trade_id}.png",
                f"chart_{trade_id}.png"
            ]
            
            for pattern in patterns:
                file_path = charts_dir / pattern
                if file_path.exists():
                    image_file_path = file_path
                    break
            
            # Try glob if exact match didn't work
            if not image_file_path or not image_file_path.exists():
                glob_pattern = f"{symbol}_5m_{trade_id}*.png"
                matches = list(charts_dir.glob(glob_pattern))
                if matches:
                    image_file_path = matches[0]
    
    # Load and process image if found
    if image_file_path and image_file_path.exists() and image_file_path.is_file():
        try:
            if PIL_AVAILABLE:
                # Full image processing with PIL (same as uploaded images)
                image = Image.open(image_file_path)
                
                # Convert to RGB if necessary (for PNG with transparency)
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Resize if too large (OpenAI has size limits)
                max_size = 2048
                if image.width > max_size or image.height > max_size:
                    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert to base64 JPEG (same as uploaded images)
                buffer = io.BytesIO()
                image.save(buffer, format='JPEG', quality=85)
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                return image_base64
            else:
                # Fallback: read raw and encode
                with open(image_file_path, 'rb') as f:
                    image_data = f.read()
                    return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            print(f"[TRADE_DETECTOR] Failed to load/process chart from {image_file_path}: {e}")
            import traceback
            traceback.print_exc()
    
    return None

