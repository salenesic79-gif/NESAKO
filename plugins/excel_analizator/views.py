from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET", "POST"])
def action_analyze(request):
    try:
        import json
        data = json.loads(request.body or '{}') if request.body else {}
        # Placeholder: analyze uploaded data in future
        return JsonResponse({
            'status': 'success',
            'module': 'excel_analizator',
            'action': 'analyze',
            'summary': 'Excel analiza skeleton spreman',
            'input': data
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

@require_http_methods(["GET", "POST"])
def action_report(request):
    return JsonResponse({
        'status': 'success',
        'module': 'excel_analizator',
        'action': 'report'
    })
