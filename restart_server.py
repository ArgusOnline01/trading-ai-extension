#!/usr/bin/env python
"""
Restart Server Script
Simple script to restart the Visual Trade Copilot server

Usage:
    python restart_server.py
"""

import sys
import os
import time
import subprocess
from pathlib import Path

# Change to script directory
SCRIPT_DIR = Path(__file__).parent.absolute()
os.chdir(SCRIPT_DIR)

SERVER_SCRIPT = "run_server.py"
PORT = 8765


def get_server_processes():
    """Find all Python processes running the server"""
    try:
        if sys.platform == "win32":
            # Windows: Use PowerShell
            cmd = f'powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {{$_.Path -like \\"*{SCRIPT_DIR}*\\"}} | Select-Object -ExpandProperty Id"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            pids = [int(pid.strip()) for pid in result.stdout.strip().split('\n') if pid.strip().isdigit()]
        else:
            # Linux/Mac: Use ps
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            pids = []
            for line in result.stdout.split('\n'):
                if SERVER_SCRIPT in line and 'python' in line:
                    parts = line.split()
                    if parts:
                        try:
                            pids.append(int(parts[1]))
                        except (ValueError, IndexError):
                            pass
        return pids
    except Exception as e:
        print(f"[ERROR] Failed to find processes: {e}")
        return []


def stop_server():
    """Stop all running server instances"""
    pids = get_server_processes()
    
    if not pids:
        print("[INFO] No server processes found")
        return True
    
    print(f"[INFO] Stopping {len(pids)} server process(es)...")
    
    for pid in pids:
        try:
            if sys.platform == "win32":
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                            capture_output=True, check=False)
            else:
                import signal
                os.kill(pid, signal.SIGTERM)
            print(f"[OK] Stopped process {pid}")
        except ProcessLookupError:
            print(f"[WARN] Process {pid} already stopped")
        except Exception as e:
            print(f"[ERROR] Failed to stop process {pid}: {e}")
            return False
    
    # Wait for processes to stop
    time.sleep(2)
    return True


def start_server():
    """Start the server"""
    print("[INFO] Starting server...")
    
    try:
        if sys.platform == "win32":
            # Windows: Start in new console window
            subprocess.Popen(
                [sys.executable, SERVER_SCRIPT],
                cwd=SCRIPT_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            # Linux/Mac: Start in background
            subprocess.Popen(
                [sys.executable, SERVER_SCRIPT],
                cwd=SCRIPT_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        # Wait a moment and verify
        time.sleep(3)
        
        try:
            import urllib.request
            response = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=2)
            print(f"[SUCCESS] Server restarted on http://127.0.0.1:{PORT}")
            return True
        except Exception:
            pids = get_server_processes()
            if pids:
                print(f"[SUCCESS] Server process started (PID: {pids[0]})")
                print(f"[INFO] Server may still be initializing. Check http://127.0.0.1:{PORT}")
                return True
            else:
                print("[ERROR] Server process not found. Check run_server.py for errors.")
                return False
                
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        return False


def main():
    print("[INFO] Restarting Visual Trade Copilot server...")
    
    # Stop existing server
    stop_server()
    
    # Wait a bit for cleanup
    time.sleep(1)
    
    # Start new server
    success = start_server()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

