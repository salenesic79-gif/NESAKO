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
    """Run Django migrations and start development server"""
    print("Starting NESAKO AI development server...")
    
    # Collect static files
    print("Collecting static files...")
    run_command("python manage.py collectstatic --noinput")

    # Run migrations
    if not run_command("python manage.py migrate --noinput"):
        print("Migration failed, but continuing...")
    
    # Start Django development server on 127.0.0.1:8080
    print("Starting Django development server on 127.0.0.1:8080...")
    run_command("python manage.py runserver 127.0.0.1:8080")

if __name__ == "__main__":
    main()
