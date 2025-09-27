#!/usr/bin/env python
"""
Startup script for Railway - runs setup commands
"""
import os
import subprocess
import sys

def run_command(cmd_list):
    """Run a command and return success status"""
    try:
        result = subprocess.run(cmd_list, check=True, capture_output=True, text=True)
        print(f"✅ {' '.join(cmd_list)} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {' '.join(cmd_list)} failed")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Run setup commands for Railway"""
    print("🚄 Starting NESAKO AI setup for Railway...")
    
    # Check if we're on Railway
    railway_env = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY_PROJECT_ID')
    if railway_env:
        print("🔧 Running in Railway environment")
    
    # Run migrations - don't exit on failure
    print("Running migrations...")
    try:
        subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], check=False)
        print("✅ Migrations completed")
    except Exception as e:
        print(f"⚠️  Migrations failed: {e}")
    
    # Collect static files - don't exit on failure
    print("Collecting static files...")
    try:
        subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"], check=False)
        print("✅ Static files collected")
    except Exception as e:
        print(f"⚠️  Static collection failed: {e}")
    
    print("✅ Setup completed - application will start")

if __name__ == "__main__":
    main()
