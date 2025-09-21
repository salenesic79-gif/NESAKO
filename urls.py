from django.urls import path, include
from django.views.generic import TemplateView
from ai_assistant.views import (
    DeepSeekAPI,
    LoginView,
    LogoutView,
    ProtectedTemplateView,
    lessons_view,
    update_feedback,
    web_check,
    health_view,
    manifest_view,
    git_sync_view,  # Dodajemo novi view
)
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static
import os

def favicon_view(request):
    return HttpResponse(status=204)  # No Content

urlpatterns = [
    # Favicon to prevent 404 errors
    path('favicon.ico', favicon_view, name='favicon'),
    # Login/Logout
    path('login/', csrf_exempt(LoginView.as_view()), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    # Glavna stranica za NESAKO AI (protected)
    path('', ProtectedTemplateView.as_view(template_name='index.html'), name='home'),
    # AI Assistant API (protected)
    path('api/chat/', csrf_exempt(DeepSeekAPI.as_view()), name='deepseek_chat'),
    # Git sync endpoint
    path('api/git-sync/', csrf_exempt(git_sync_view), name='git_sync'),
    # Lessons endpoints
    path('lessons', lessons_view, name='lessons'),
    path('lessons/<int:lesson_id>/feedback', csrf_exempt(update_feedback), name='update_feedback'),
    # Web check endpoint
    path('web_check', csrf_exempt(web_check), name='web_check'),
    # Explicit manifest route (safety net)
    path('manifest.json', manifest_view, name='manifest_json'),
    # Health endpoint
    path('health', health_view, name='health'),
]

# Serve static files in development and production
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
else:
    # Serve from STATIC_ROOT (collected static)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Additionally serve directly from STATICFILES_DIRS[0] as fallback (defensive in Render)
    try:
        if settings.STATICFILES_DIRS and os.path.isdir(settings.STATICFILES_DIRS[0]):
            urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    except Exception:
        pass
