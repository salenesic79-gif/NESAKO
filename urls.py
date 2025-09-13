from . import views

urlpatterns = [
    # ... postojeće rute
    path('api/chat/', views.deepseek_chat, name='deepseek_chat'),
]
