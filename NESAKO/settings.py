ROOT_URLCONF = 'urls'
>>>>>>> 024e02e54e8b229055ce5d604b8de597177ba75b

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

<<<<<<< HEAD
WSGI_APPLICATION = 'NESAKO.wsgi.application'
=======
ROOT_URLCONF = 'urls'
>>>>>>> 024e02e54e8b229055ce5d604b8de597177ba75b

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

<<<<<<< HEAD
WSGI_APPLICATION = 'NESAKO.wsgi.application'
=======
WSGI_APPLICATION = 'NESAKO.wsgi.application'
>>>>>>> 024e02e54e8b229055ce5d604b8de597177ba75b

# Database: use DATABASE_URL if provided (Render Postgres), else fallback to SQLite
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=True)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'nesako_ai_assistant.sqlite3',
        }
    }

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

<<<<<<< HEAD
# Ensure static files are served in development
if DEBUG:
    STATICFILES_DIRS = [
        BASE_DIR / 'static',
    ]
else:
    STATIC_ROOT = BASE_DIR / 'staticfiles'

=======
>>>>>>> 024e02e54e8b229055ce5d604b8de597177ba75b
# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DeepSeek API Key
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# Private access settings
NESAKO_USERNAME = os.getenv('NESAKO_USERNAME', 'nesako')
NESAKO_PASSWORD = os.getenv('NESAKO_PASSWORD', 'nesako2024')

# Security settings za production
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
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
