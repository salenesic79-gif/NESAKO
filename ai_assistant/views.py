import os
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

@method_decorator(csrf_exempt, name='dispatch')
class DeepSeekAPI(View):
    def post(self, request):
        try:
            # Dobijanje instrukcija od korisnika
            data = json.loads(request.body)
            user_input = data.get('instruction', '')
            
            # DeepSeek API konfiguracija
            API_URL = "https://api.deepseek.com/v1/chat/completions"
            API_KEY = os.environ.get('DEEPSEEK_API_KEY')  # Koristi environment variable
            
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system", 
                        "content": "Ti si AI asistent za Tovar Taxi aplikaciju. Pomazi korisnicima sa njihovim upitima."
                    },
                    {
                        "role": "user", 
                        "content": user_input
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            # Slanje zahteva DeepSeek API-ju
            response = requests.post(API_URL, json=payload, headers=headers)
            response_data = response.json()
            
            # Ekstrakcija odgovora
            ai_response = response_data['choices'][0]['message']['content']
            
            return JsonResponse({
                'response': ai_response,
                'status': 'success'
            })
            
        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'status': 'error'
            }, status=400)
