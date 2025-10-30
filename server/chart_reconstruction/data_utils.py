"""
Data Utilities - Fetch Historical Price Data
Uses yfinance to get 5-minute OHLCV data with retry logic
"""

import time
from datetime import timedelta
from random import uniform
import pandas as pd

# Try to import yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("[WARN] yfinance not installed. Run: pip install yfinance")


def fetch_price_data(symbol, entry_time, window_hours=36, retries=3, delay=5):
    """
    Fetch 5-minute historical data centered on trade entry time
    Args:
        symbol: Trading symbol
        entry_time: Entry timestamp (str or datetime)
        window_hours: Hours before and after entry (default: 36)
        retries: retry logic
        delay: seconds
    Returns: DataFrame of OHLCV or empty
    """
    if not YFINANCE_AVAILABLE:
        print("[ERROR] yfinance not installed. Cannot fetch data.")
        return pd.DataFrame()
    interval = "5m"
    try:
        entry_dt = pd.to_datetime(entry_time)
    except Exception as e:
        print(f"[ERROR] Invalid entry_time format: {entry_time} - {e}")
        return pd.DataFrame()
    
    start = entry_dt - timedelta(hours=window_hours)
    end = entry_dt + timedelta(hours=window_hours)
    yf_symbol = convert_symbol_to_yfinance(symbol)
    for attempt in range(1, retries + 1):
        try:
            print(f"[FETCH] {symbol} ({yf_symbol}) attempt {attempt}/{retries} ({interval})")
            df = yf.download(
                yf_symbol,
                interval=interval,
                start=start,
                end=end,
                progress=False
            )
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                print(f"[SUCCESS] Fetched {len(df)} candles for {symbol}")
                return df
            else:
                print(f"[WARN] No data for {symbol} between {start} and {end}")
        except Exception as e:
            print(f"[ERROR] {symbol} fetch failed: {e}")
        if attempt < retries:
            wait_time = delay + uniform(0.5, 1.5)
            print(f"[RETRY] Waiting {wait_time:.1f}s before attempt {attempt + 1}...")
            time.sleep(wait_time)
    print(f"[FAIL] Giving up on {symbol} after {retries} attempts")
    return pd.DataFrame()


def convert_symbol_to_yfinance(symbol):
    """
    Convert Topstep symbol to yfinance format
    
    Examples:
        6EZ5 -> 6E=F (Euro FX Futures)
        MNQZ5 -> MNQ=F (Micro E-mini Nasdaq-100)
        CLZ5 -> CL=F (Crude Oil)
        MCLZ5 -> MCL=F (Micro Crude Oil)
        MGCZ5 -> MGC=F (Micro Gold)
        SILZ5 -> SI=F (Silver)
    """
    # Remove month/year code (e.g., Z5, H5, M5)
    base_symbol = symbol[:-2] if len(symbol) > 2 else symbol
    
    # Map to yfinance continuous contract format
    symbol_map = {
        "6E": "6E=F",      # Euro FX
        "MNQ": "MNQ=F",    # Micro E-mini Nasdaq
        "NQ": "NQ=F",      # E-mini Nasdaq
        "ES": "ES=F",      # E-mini S&P 500
        "CL": "CL=F",      # Crude Oil
        "MCL": "MCL=F",    # Micro Crude Oil
        "MGC": "MGC=F",    # Micro Gold
        "GC": "GC=F",      # Gold
        "SI": "SI=F",      # Silver
        "SIL": "SI=F",     # Silver (alternate)
        "YM": "YM=F",      # E-mini Dow
        "RTY": "RTY=F",    # E-mini Russell 2000
        "ZN": "ZN=F",      # 10-Year T-Note
    }
    
    yf_symbol = symbol_map.get(base_symbol, f"{base_symbol}=F")
    
    return yf_symbol


def get_available_symbols():
    """
    Get list of supported symbols for chart reconstruction
    
    Returns:
        dict mapping Topstep symbols to yfinance symbols
    """
    return {
        "6E": "6E=F (Euro FX Futures)",
        "MNQ": "MNQ=F (Micro E-mini Nasdaq-100)",
        "NQ": "NQ=F (E-mini Nasdaq-100)",
        "ES": "ES=F (E-mini S&P 500)",
        "CL": "CL=F (Crude Oil Futures)",
        "MCL": "MCL=F (Micro Crude Oil)",
        "MGC": "MGC=F (Micro Gold)",
        "GC": "GC=F (Gold Futures)",
        "SI": "SI=F (Silver Futures)",
        "YM": "YM=F (E-mini Dow)",
        "RTY": "RTY=F (E-mini Russell 2000)",
        "ZN": "ZN=F (10-Year T-Note)",
    }

