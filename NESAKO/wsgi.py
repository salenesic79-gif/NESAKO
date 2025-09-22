from django.core.wsgi import get_wsgi_application

# Remove c:\Users\PC from path to avoid conflicts with transport module
if 'C:\\Users\\PC' in sys.path:
    sys.path.remove('C:\\Users\\PC')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
>>>>>>> 024e02e54e8b229055ce5d604b8de597177ba75b

application = get_wsgi_application()
=======
from django.core.wsgi import get_wsgi_application

# Remove c:\Users\PC from path to avoid conflicts with transport module
if 'C:\\Users\\PC' in sys.path:
    sys.path.remove('C:\\Users\\PC')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
>>>>>>> 024e02e54e8b229055ce5d604b8de597177ba75b

application = get_wsgi_application()
