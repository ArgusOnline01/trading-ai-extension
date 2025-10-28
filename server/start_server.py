#!/usr/bin/env python3
"""
Simple script to start the Visual Trade Copilot server
"""
import uvicorn
import sys
import os

def main():
    print("🚀 Starting Visual Trade Copilot Server...")
    print("📍 Server will be available at: http://127.0.0.1:8765")
    print("📚 API docs will be available at: http://127.0.0.1:8765/docs")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        uvicorn.run(
            "app:app",
            host="127.0.0.1",
            port=8765,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
