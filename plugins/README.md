# NESAKO Plugin System

Svaki plugin je .py fajl u folderu `plugins/` i mora imati funkciju `register(app)`.

Primer:
```python
def register(app):
    # registracija hook-ova, ruta ili ekstenzija
    return {
        "name": "sample_plugin",
        "version": "1.0.0",
        "hooks": ["on_startup", "on_response"]
    }
```

Kako radi:
- `settings.py` automatski prolazi kroz `plugins/` i pokušava da `importuje` svaki `.py` fajl.
- Ako modul ima `register(app)` funkciju, dodaje je u `PLUGINS` listu.
- Greške u pluginu ne obaraju aplikaciju (bezbedan fallback).
