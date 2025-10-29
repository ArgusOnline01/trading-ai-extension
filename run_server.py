#!/usr/bin/env python3
"""
Simple launcher for Visual Trade Copilot Server
This script handles all the setup and starts the server
"""
import os
import sys
import subprocess
from pathlib import Path

def setup_api_key(server_dir):
    """Setup API key from .env file or prompt user"""
    env_file = server_dir / ".env"
    
    # Try to load from .env file
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        if key.strip() == "OPENAI_API_KEY":
                            api_key = value.strip()
                            if api_key and api_key != "your_api_key_here":
                                return api_key
    
    # Check environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key
    
    # Prompt user
    print("\n" + "=" * 60)
    print("OPENAI API KEY REQUIRED")
    print("=" * 60)
    print("No API key found. You need an OpenAI API key to use this tool.")
    print("Get one at: https://platform.openai.com/api-keys")
    print("")
    api_key = input("Enter your OpenAI API key (or press Enter to exit): ").strip()
    
    if not api_key:
        print("No API key provided. Exiting.")
        sys.exit(1)
    
    # Save to .env file
    save = input("Save this key to .env file? (y/n): ").strip().lower()
    if save == 'y':
        with open(env_file, "w") as f:
            f.write(f"OPENAI_API_KEY={api_key}\n")
        print(f"API key saved to {env_file}")
    
    return api_key

def main():
    print("Visual Trade Copilot Server Launcher")
    print("=" * 50)
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    server_dir = script_dir / "server"
    
    # Change to server directory
    os.chdir(server_dir)
    print(f"Working directory: {os.getcwd()}")
    
    # Setup API key
    api_key = setup_api_key(server_dir)
    os.environ["OPENAI_API_KEY"] = api_key
    print("API key configured")
    
    # Check if virtual environment exists
    venv_python = server_dir / "venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        print("Using virtual environment")
        python_cmd = str(venv_python)
    else:
        print("Using system Python")
        python_cmd = sys.executable
    
    # Start the server
    print("Starting server at http://127.0.0.1:8765")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        subprocess.run([python_cmd, "app.py"], check=True)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
