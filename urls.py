from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib import admin
from ai_assistant.views import (
    DeepSeekAPI,
    LoginView,
    LogoutView,
    ProtectedTemplateView,
    fudbal_quick_odds,
    fudbal_odds_changes,
    fudbal_competition,
    sofa_quick,
    sofa_competition,
    debug_routes,
    lessons_view,
    update_feedback,
    web_check,
    health_view,
    manifest_view,
    git_sync_view,  # Dodajemo novi view
    preferences_view,
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
    # Django admin
    path('admin/', admin.site.urls),
    # Login/Logout
    path('login/', csrf_exempt(LoginView.as_view()), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    # Glavna stranica za NESAKO AI (protected)
    path('', ProtectedTemplateView.as_view(template_name='index.html'), name='home'),
    # AI Assistant API (protected)
    path('api/chat/', csrf_exempt(DeepSeekAPI.as_view()), name='deepseek_chat'),
    # Fudbal91 endpoints (read-only)
    path('api/fudbal/quick_odds', csrf_exempt(fudbal_quick_odds), name='fudbal_quick_odds'),
    path('api/fudbal/quick_odds/', csrf_exempt(fudbal_quick_odds)),
    path('api/fudbal/odds_changes', csrf_exempt(fudbal_odds_changes), name='fudbal_odds_changes'),
    path('api/fudbal/odds_changes/', csrf_exempt(fudbal_odds_changes)),
    path('api/fudbal/competition', csrf_exempt(fudbal_competition), name='fudbal_competition'),
    path('api/fudbal/competition/', csrf_exempt(fudbal_competition)),
    # SofaScore endpoints (public JSON, no odds)
    path('api/sofa/quick', csrf_exempt(sofa_quick), name='sofa_quick'),
    path('api/sofa/quick/', csrf_exempt(sofa_quick)),
    path('api/sofa/competition', csrf_exempt(sofa_competition), name='sofa_competition'),
    path('api/sofa/competition/', csrf_exempt(sofa_competition)),
    # Git sync endpoint
    path('api/git-sync/', csrf_exempt(git_sync_view), name='git_sync'),
    # Session preferences endpoint
    path('api/preferences/', csrf_exempt(preferences_view), name='preferences'),
    # Lessons endpoints
    path('lessons/', lessons_view, name='lessons'),
    path('lessons/<int:lesson_id>/feedback/', csrf_exempt(update_feedback), name='update_feedback'),
    # Web check endpoint
    path('web_check', csrf_exempt(web_check), name='web_check'),
    # Explicit manifest route (safety net)
    path('manifest.json', manifest_view, name='manifest_json'),
    # Health endpoint
    path('health', health_view, name='health'),
    # Debug: list all routes
    path('debug/routes', debug_routes, name='debug_routes'),
]

# WhiteNoise will serve static files in production
# Only serve static files via Django in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
