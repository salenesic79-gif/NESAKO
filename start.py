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
    
    # Check environment
    railway_env = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY_PROJECT_ID')
    if railway_env:
        print("🔧 Running in Railway environment")
    
    # Run migrations
    if not run_command([sys.executable, "manage.py", "migrate", "--noinput"]):
        print("⚠️  Migrations failed, but continuing...")
    
    # Collect static files
    if not run_command([sys.executable, "manage.py", "collectstatic", "--noinput"]):
        print("⚠️  Static collection failed, but continuing...")
    
    print("✅ Setup completed - Railway will start the application server")

if __name__ == "__main__":
    main()
