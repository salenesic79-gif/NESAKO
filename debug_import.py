import traceback
import sys

try:
    import ai_assistant.views as v
    print('OK: ai_assistant.views imported')
except Exception:
    traceback.print_exc()
    sys.exit(1)
