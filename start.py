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
    
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NESAKO.settings')
    
    # Initialize Django to test database connection
    try:
        import django
        django.setup()
        
        # Test database connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ Database connection test successful")
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        if railway_env:
            sys.exit(1)
        else:
            print("⚠️  Continuing in development mode...")
    
    # Run migrations
    if not run_command([sys.executable, "manage.py", "migrate", "--noinput"]):
        if railway_env:
            print("❌ Migrations failed on Railway - exiting")
            sys.exit(1)
        else:
            print("⚠️  Migrations failed, but continuing in development...")
    
    # Collect static files
    if not run_command([sys.executable, "manage.py", "collectstatic", "--noinput"]):
        if railway_env:
            print("❌ Static collection failed on Railway - exiting")
            sys.exit(1)
        else:
            print("⚠️  Static collection failed, but continuing in development...")
    
    print("✅ Setup completed - Railway will start the application server")

if __name__ == "__main__":
    main()
