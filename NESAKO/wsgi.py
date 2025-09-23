import os
import sys
from django.core.wsgi import get_wsgi_application

# Optional: remove a problematic path if present
if 'C:\\Users\\PC' in sys.path:
    try:
        sys.path.remove('C:\\Users\\PC')
    except ValueError:
        pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NESAKO.settings')

application = get_wsgi_application()
