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
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NESAKO.settings')
    
    # Run migrations
    print("Running migrations...")
    result = subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Migrations completed successfully")
    else:
        print(f"⚠️  Migrations failed with return code {result.returncode}")
        if result.stderr:
            print(f"Error: {result.stderr}")
    
    # Collect static files
    print("Collecting static files...")
    result = subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Static files collected successfully")
    else:
        print(f"⚠️  Static collection failed with return code {result.returncode}")
        if result.stderr:
            print(f"Error: {result.stderr}")
    
    print("✅ Setup completed")

if __name__ == "__main__":
    main()
