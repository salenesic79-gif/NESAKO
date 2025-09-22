## NESAKO Plugin System

Svaki plugin je `.py` fajl u folderu `plugins/` i mora imati funkciju `register(app)`.

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

Settings automatski učitava pluginove i dodaje ih u `PLUGINS` listu. Greške u pluginu ne obaraju aplikaciju.
# 🤖 NESAKO AI Assistant

Napredni AI asistent sa GitHub integracijom, DeepSeek API-jem i real-time mogućnostima.

## ✨ Funkcionalnosti

- 🧠 **DeepSeek AI integracija** - Napredni chat asistent
- 🔧 **GitHub analiza** - Pristup i analiza repozitorijuma
- 🌐 **Web pretraga** - Real-time informacije
- 💻 **Kod izvršavanje** - Sandbox okruženje
- 📊 **Sportske statistike** - Predviđanja i analize
- 🛡️ **Sigurnosni sistem** - Automatska detekcija pretnji
- 📚 **Lessons Learned** - Trajno pamćenje naučenog sa feedback-om
- 🧩 **Plugin sistem** - Modularno proširenje funkcionalnosti

## Naučeno i feedback

- Sve naučene stvari i korisničke ispravke se pamte u bazi `LessonLearned`.
- Svaki korisnik može oceniti tačnost naučenog (feedback: `correct` / `incorrect` / `pending`).
- Frontend: dugme „Prikaži naučeno“ učitava listu preko `/lessons` i omogućava slanje feedback-a.

API rute:
- `GET /lessons` – poslednje naučeno
- `POST /lessons/<id>/feedback` – ažuriranje feedback-a sa JSON telom `{ "feedback": "correct|incorrect|pending" }`

## Web pouzdanost i fallback

- Sistem proverava pouzdanost AI odgovora. Ako odgovor nije dovoljno siguran ili upit sadrži reči „trenutno“, „realno stanje“, „najnovije“, automatski se radi web pretraga i dodaje izvor.
- UI ima dugme „Proveri na webu“ koje šalje zahtev ka `/web_check?q=...` i prikazuje rezultat.

## 🚀 Pokretanje

1. **Instaliraj dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Pokreni server:**
   ```bash
   python main.py
   ```

3. **Otvori u browser:**
   ```
   http://localhost:8015
   ```

## 🔑 Login podaci

- **Username:** nesako
- **Password:** nesako2024

## 🛠️ Tehnologije

- **Backend:** Django 4.2.7
- **Frontend:** HTML5, CSS3, JavaScript
- **AI:** DeepSeek API
- **Database:** SQLite
- **Deployment:** Render ready

## 📁 Struktura projekta

```
NESAKO/
├── ai_assistant/          # Main app
│   ├── views.py          # API endpoints
│   └── __init__.py
├── templates/            # HTML templates
│   ├── index.html       # Main chat interface
│   └── login.html       # Login page
├── main.py              # Django entry point
├── settings.py          # Django settings
├── plugins/             # Plugin sistem (opciono)
├── urls.py              # URL routing
└── requirements.txt     # Dependencies
```

## 🔧 Konfiguracija

Dodaj u `.env` fajl:
```
DEEPSEEK_API_KEY=your_api_key_here
WEATHER_API_KEY=your_weather_key
GITHUB_TOKEN=your_github_token
SERPAPI_API_KEY=your_serpapi_key
```

## 📝 Napomene

- Aplikacija je optimizovana za production
- Uključuje CSRF zaštitu
- Automatski error handling
- Debug mode za development

## 🌐 RENDER DEPLOYMENT - Pristup sa telefona preko interneta

### 1. Kreiranje Render servisa
1. Idite na [render.com](https://render.com) i napravite nalog
2. Kliknite "New +" → "Web Service"
3. Povežite GitHub repo ili upload-ujte kod
4. Render će automatski detektovati `render.yaml`

### 2. Environment varijable na Render
U Render dashboard-u dodajte:
```
DEEPSEEK_API_KEY = sk-8b335fd6ca5241709a173a06eea400b7
DEBUG = False
SECRET_KEY = [generiši-random-string]
SERPAPI_API_KEY = [serpapi_key]
```

### 3. Pristup aplikaciji
Nakon deployment-a dobićete URL poput:
```
https://nesako-ai-xyz123.onrender.com
```

**Ovaj URL možete koristiti sa bilo kog uređaja - telefon, tablet, računar!**

## 🚀 Lokalno pokretanje (za development)

### 1. Instaliranje zavisnosti
```bash
pip install -r requirements.txt
```

### 2. Pokretanje aplikacije (lokalno)
```bash
python manage.py runserver 8001
```
*Koristi port 8001 da ne kolizuje sa drugim aplikacijama*

### 3. Pristup aplikaciji (lokalno)
- **Računar**: http://localhost:8001
- **Telefon u istoj mreži**: http://[IP_ADRESA_RAČUNARA]:8001

## 📱 Mobilna podrška

Aplikacija je potpuno optimizovana za mobilne uređaje:
- Responzivni dizajn
- Touch-friendly interfejs
- Automatsko skaliranje
- Optimizovano za male ekrane
- **Radi preko interneta sa Render!**

## 🔧 Konfiguracija

### Environment varijable (.env fajl za lokalno)
```
DEEPSEEK_API_KEY=sk-8b335fd6ca5241709a173a06eea400b7
DEBUG=True
```

## ✅ Nezavisnost od drugih aplikacija

Ova aplikacija je potpuno nezavisna:
- ❌ Ne koristi tovar_taxi.settings
- ❌ Nema veze sa TOVAR TAXI aplikacijom  
- ✅ Koristi vlastite settings.py
- ✅ Vlastita SQLite baza (nesako_ai.sqlite3)
- ✅ Vlastiti URL patterns
- ✅ Nezavisan AI asistent
- ✅ **Različit port (8001) i Render URL**

## 🔍 Struktura aplikacije

```
NESAKO/
├── ai_assistant/          # AI funkcionalnost
│   └── views.py          # DeepSeek API integration
├── templates/
│   └── index.html        # Mobilno-optimizovan UI
├── settings.py           # NESAKO specifični settings
├── plugins/              # NESAKO Plugin System
├── urls.py              # URL konfiguracija
├── manage.py            # Django management
├── main.py              # WSGI aplikacija
├── render.yaml          # Render deployment config
└── .env                 # Environment varijable
```

## 🛠️ Troubleshooting

### Problem: Aplikacija ne radi na Render
- Proverite Environment varijable na Render
- Proverite da li je DeepSeek API ključ ispravan
- Ako SerpAPI ključ nije postavljen, sportska/web pretraga radi uz siguran fallback
- Pogledajte logs u Render dashboard-u

### Problem: Lokalno kolizuje sa drugim aplikacijama
- Koristite port 8001: `python manage.py runserver 8001`
- Ili bilo koji drugi slobodan port

### Problem: Ne mogu pristupiti sa telefona (lokalno)
- Proverite da li je firewall otvoren za port 8001
- Koristite: `python manage.py runserver 0.0.0.0:8001`

## 🎯 Funkcionalnosti

- 💬 Chat sa AI asistentom
- 📱 Mobilna podrška
- 🌐 **Internet pristup preko Render**
- 🔒 CSRF zaštita
- ⚡ Brz odgovor
- 🌍 Srpski jezik
- 🎨 Moderan UI/UX
- 🔐 Production-ready security

## 🚀 Preporučeno: Koristite Render za pristup sa telefona!

Umesto localhost-a, koristite Render deployment za:
- ✅ Pristup sa bilo kog mesta
- ✅ Nema problema sa portovima
- ✅ HTTPS sigurnost
- ✅ Uvek dostupno
