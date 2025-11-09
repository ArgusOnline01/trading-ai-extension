"""
Check Data Quality - Inspect fetched price data for issues
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chart_reconstruction.data_utils import fetch_price_data
import pandas as pd

def check_data_quality(symbol, entry_time):
    """Check data quality for a specific trade"""
    print(f"\n{'='*60}")
    print(f"Checking data quality for {symbol} at {entry_time}")
    print(f"{'='*60}\n")
    
    df = fetch_price_data(symbol, entry_time)
    
    if df.empty:
        print("❌ No data fetched!")
        return
    
    print(f"✅ Total candles: {len(df)}")
    print(f"📅 Date range: {df.index[0]} to {df.index[-1]}")
    print(f"⏱️  Time span: {(df.index[-1] - df.index[0]).total_seconds() / 3600:.1f} hours")
    
    # Check for duplicates
    duplicates = df.index.duplicated().sum()
    print(f"\n🔍 Duplicate timestamps: {duplicates}")
    if duplicates > 0:
        print("   ⚠️  Found duplicate timestamps!")
        dup_times = df.index[df.index.duplicated(keep=False)]
        print(f"   Sample duplicates: {dup_times[:5].tolist()}")
    
    # Check for NaN values
    nan_counts = df.isna().sum()
    print(f"\n🔍 NaN values:")
    for col, count in nan_counts.items():
        if count > 0:
            print(f"   ⚠️  {col}: {count} NaN values")
    
    # Check for invalid OHLC relationships
    invalid_high_low = (df['High'] < df['Low']).sum()
    invalid_high_open = (df['High'] < df['Open']).sum()
    invalid_high_close = (df['High'] < df['Close']).sum()
    invalid_low_open = (df['Low'] > df['Open']).sum()
    invalid_low_close = (df['Low'] > df['Close']).sum()
    
    print(f"\n🔍 Invalid OHLC relationships:")
    if invalid_high_low > 0:
        print(f"   ⚠️  High < Low: {invalid_high_low} rows")
    if invalid_high_open > 0:
        print(f"   ⚠️  High < Open: {invalid_high_open} rows")
    if invalid_high_close > 0:
        print(f"   ⚠️  High < Close: {invalid_high_close} rows")
    if invalid_low_open > 0:
        print(f"   ⚠️  Low > Open: {invalid_low_open} rows")
    if invalid_low_close > 0:
        print(f"   ⚠️  Low > Close: {invalid_low_close} rows")
    
    # Check for extreme price movements (potential data corruption)
    if 'Close' in df.columns:
        price_changes = df['Close'].pct_change().abs()
        extreme_moves = (price_changes > 0.1).sum()  # >10% move in 5 minutes
        print(f"\n🔍 Extreme price movements (>10% in 5min): {extreme_moves}")
        if extreme_moves > 0:
            extreme_dates = df[price_changes > 0.1].index[:5]
            print(f"   ⚠️  Sample extreme moves at: {extreme_dates.tolist()}")
    
    # Check data around Oct 16-17 for CLZ5
    if symbol == 'CLZ5':
        print(f"\n🔍 Checking data around Oct 16-17 (where jaggedness starts):")
        oct_16_17 = df.loc['2025-10-16':'2025-10-17']
        if not oct_16_17.empty:
            print(f"   📊 Candles in Oct 16-17: {len(oct_16_17)}")
            print(f"   📅 Range: {oct_16_17.index[0]} to {oct_16_17.index[-1]}")
            print(f"   📈 Price range: {oct_16_17['Low'].min():.2f} to {oct_16_17['High'].max():.2f}")
            
            # Check for data gaps
            time_diffs = oct_16_17.index.to_series().diff()
            large_gaps = time_diffs[time_diffs > pd.Timedelta(minutes=10)]
            print(f"   ⏱️  Large time gaps (>10min): {len(large_gaps)}")
            if len(large_gaps) > 0:
                print(f"   ⚠️  Sample gaps: {large_gaps.head(3).tolist()}")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    check_data_quality('CLZ5', '2025-10-17T08:53:18')
    check_data_quality('MCLZ5', '2025-10-21T09:35:19')

