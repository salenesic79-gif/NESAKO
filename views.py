import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os

@csrf_exempt
def deepseek_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')

            # DeepSeek API konfiguracija
            api_url = "https://api.deepseek.com/v1/chat/completions"
            api_key = os.environ.get('DEEPSEEK_API_KEY')

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Ti si korisnički asistent."},
                    {"role": "user", "content": user_message}
                ]
            }

            response = requests.post(api_url, json=payload, headers=headers)
            response_data = response.json()

            # Provera grešaka
            if response.status_code == 200:
                ai_response = response_data['choices'][0]['message']['content']
                return JsonResponse({'response': ai_response})
            else:
                return JsonResponse({'error': 'API greška'}, status=500)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
