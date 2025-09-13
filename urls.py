from . import views

urlpatterns = [
    # ... postojeće rute
    path('api/chat/', views.deepseek_chat, name='deepseek_chat'),
]
# tovar_taxi/urls.py
from django.urls import path
from ai_assistant.views import DeepSeekAPI

urlpatterns = [
    # ... postojeći url patterni
    path('api/chat/', DeepSeekAPI.as_view(), name='deepseek_chat'),
]
