import os
import sys
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent

# Jedinstveni identifikatori za NESAKO AI
APP_NAME = 'nesako-ai-assistant'
APP_VERSION = 'v1.0'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'nesako-ai-secret-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
# Detect Railway environment
RAILWAY_ENV = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY_PROJECT_ID')

# Force DEBUG=False on Railway
if RAILWAY_ENV:
    DEBUG = False
    print("🚄 Railway environment detected - forcing DEBUG=False")
else:
    DEBUG = os.getenv('DEBUG', 'True') == 'True'
    print(f"🔧 DEBUG mode: {DEBUG}")

# Safety warning
if DEBUG and RAILWAY_ENV:
    print("⚠️  WARNING: DEBUG is True in Railway production environment!")

# Railway deployment configuration
RAILWAY_ENV = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY_PROJECT_ID')
RAILWAY_PUBLIC_DOMAIN = os.getenv('RAILWAY_PUBLIC_DOMAIN')

if RAILWAY_ENV:
    if RAILWAY_PUBLIC_DOMAIN:
        ALLOWED_HOSTS = [RAILWAY_PUBLIC_DOMAIN, '.railway.app']
    else:
        ALLOWED_HOSTS = ['.railway.app', 'localhost', '127.0.0.1']
    print(f"🚄 Railway ALLOWED_HOSTS: {ALLOWED_HOSTS}")
else:
    ALLOWED_HOSTS = ['*']  # Development

# Force HTTP for local development
USE_TLS = False
SECURE_SSL_REDIRECT = False  # Do not force within container; Railway terminates TLS at edge
# Honor X-Forwarded-Proto from Railway proxy so Django knows request scheme
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ai_assistant',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Dodatna konfiguracija za development
if DEBUG:
    import mimetypes
    mimetypes.add_type("text/css", ".css", True)
    mimetypes.add_type("application/javascript", ".js", True)

ROOT_URLCONF = 'urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wsgi.application'

# Database configuration - always use DATABASE_URL if available
DATABASE_URL = os.getenv('DATABASE_URL')
RAILWAY_ENV = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY_PROJECT_ID')

if DATABASE_URL:
    # Use PostgreSQL
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=False)
    }
    print("🗄️ Using PostgreSQL database")
else:
    # Fallback to SQLite for development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    print("🗄️ Using SQLite (development)")

# Test database connection - but don't crash the app if it fails
try:
    import django
    from django.db import connection
    django.setup()
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("✅ Database connection test successful")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    # Don't crash - let Django handle database errors at runtime
    if RAILWAY_ENV and not DATABASE_URL:
        print("⚠️  WARNING: DATABASE_URL nije postavljen u Railway okruženju!")

# Authentication
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Internationalization
LANGUAGE_CODE = 'sr-rs'
TIME_ZONE = 'Europe/Belgrade'
USE_I18N = True
USE_TZ = True

# Static files configuration za Render
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DeepSeek API Configuration
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Debug API key configuration
if not DEEPSEEK_API_KEY:
    print("⚠️  WARNING: DEEPSEEK_API_KEY nije konfigurisan!")
    print("ℹ️   Sistem će koristiti fallback mode bez AI servisa")
else:
    print("✅ DEEPSEEK_API_KEY je konfigurisan")

# SerpAPI Configuration
SERPAPI_API_KEY = os.getenv('SERPAPI_API_KEY', '')
if not SERPAPI_API_KEY:
    print("⚠️  WARNING: SERPAPI_API_KEY nije konfigurisan - web pretraga onemogućena")

# Private access settings
NESAKO_USERNAME = os.getenv('NESAKO_USERNAME', 'nesako')
NESAKO_PASSWORD = os.getenv('NESAKO_PASSWORD', 'nesako2024')

# Security settings za production
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Do not force SSL redirect inside the dyno; Railway already handles HTTPS
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    # Trust Railway domains
    CSRF_TRUSTED_ORIGINS = [
        'https://*.railway.app',
        'https://*.up.railway.app'
    ]
    
    # Add specific domain if available
    RAILWAY_PUBLIC_DOMAIN = os.getenv('RAILWAY_PUBLIC_DOMAIN')
    if RAILWAY_PUBLIC_DOMAIN:
        CSRF_TRUSTED_ORIGINS.append(f'https://{RAILWAY_PUBLIC_DOMAIN}')
        print(f"🔧 Added CSRF trusted origin: https://{RAILWAY_PUBLIC_DOMAIN}")
else:
    # Development settings
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Session settings - jedinstveni naziv
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_NAME = 'nesako_ai_sessionid'
CSRF_COOKIE_NAME = 'nesako_ai_csrftoken'
SESSION_COOKIE_AGE = 86400  # 24 hours

# Plugin system loader - optional
try:
    import importlib
    plugin_folder = BASE_DIR / 'plugins'
    PLUGINS = []
    if plugin_folder.exists():
        for fname in os.listdir(plugin_folder):
            if fname.endswith('.py') and fname not in ['__init__.py']:
                mod_name = f"plugins.{fname[:-3]}"
                try:
                    mod = importlib.import_module(mod_name)
                    if hasattr(mod, 'register'):
                        PLUGINS.append(mod.register)
                except Exception:
                    # Do not break startup because of plugin error
                    pass
except Exception:
    PLUGINS = []
