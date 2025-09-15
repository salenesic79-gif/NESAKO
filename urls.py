from django.urls import path, include
from django.views.generic import TemplateView
from ai_assistant.views import DeepSeekAPI, LoginView, LogoutView, ProtectedTemplateView
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static

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
]

# Serve static files in development and production
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
else:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
