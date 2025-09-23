#!/usr/bin/env python
import os
import sys

def main():
    # Proveri da li je DEEPSEEK_API_KEY postavljen
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
    if not deepseek_key:
        print("⚠️  UPOZORENJE: DEEPSEEK_API_KEY nije postavljen u okruženju!")
        print("ℹ️   Aplikacija će raditi u ograničenom režimu sa fallback odgovorima")
    
    # Postavi Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NESAKO.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Django not available") from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
