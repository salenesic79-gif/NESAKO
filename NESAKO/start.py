#!/usr/bin/env python
import os
import subprocess
import sys

def run_command(command):
    """Run a command and handle errors"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {command}")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {command}")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Run Django migrations and start gunicorn"""
    print("Starting NESAKO AI deployment...")
    
    # Collect static files so /static/manifest.json and other assets are available
    print("Collecting static files...")
    run_command("python manage.py collectstatic --noinput")

    # Run migrations
    if not run_command("python manage.py migrate --noinput"):
        print("Migration failed, but continuing...")
    
    # Start gunicorn
    port = os.environ.get('PORT', '8080')
    gunicorn_cmd = f"gunicorn NESAKO.wsgi:application --bind 0.0.0.0:{port} --workers 2 --timeout 120"
    
    print(f"Starting gunicorn on port {port}...")
    os.system(gunicorn_cmd)

if __name__ == "__main__":
    main()
