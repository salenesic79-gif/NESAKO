from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import requests
import os

app = FastAPI()

# --- Funkcije za čuvanje i učitavanje instrukcija ---
# Koristimo fajl za trajno čuvanje instrukcija
INSTRUCTIONS_FILE = "core_instructions.txt"

def ucitaj_instrukcije():
    """Učitava instrukcije iz fajla ili vraća podrazumevane."""
    if os.path.exists(INSTRUCTIONS_FILE):
        with open(INSTRUCTIONS_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "Ti si NESAKO AI asistent. Odgovaraj jasno, korisno i na srpskom jeziku."

def sacuvaj_instrukcije(instrukcije):
    """Čuva instrukcije u fajl."""
    with open(INSTRUCTIONS_FILE, "w", encoding="utf-8") as f:
        f.write(instrukcije)

# === Globalne varijable ===
# Učitavamo instrukcije pri pokretanju aplikacije
core_instructions = ucitaj_instrukcije()
istorija_poruka = []

API_URL = "https://api.groq.com/openai/v1/chat/completions"
API_KEY = os.getenv("GROQ_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def prikazi_chat():
    """Generiše kompletan HTML za prikaz chata."""
    global istorija_poruka

    poruke_html = ""
    for poruka in istorija_poruka:
        role_class = "korisnik" if poruka["role"] == "user" else "asistent"
        poruke_html += f'<div class="{role_class}"><b>{poruka["role"]}</b>: {poruka["content"]}</div>'
        
    return f"""
    <html>
    <head>
        <title>NESAKO AI Asistent</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; max-width: 800px; margin: auto; background: #f0f2f5; }}
            .poruke {{ border: 1px solid #ddd; padding: 10px; height: 60vh; overflow-y: scroll; margin-bottom: 20px; background: white; border-radius: 8px; }}
            .korisnik {{ color: #007bff; margin-bottom: 10px; }}
            .asistent {{ color: #28a745; margin-bottom: 10px; }}
            form {{ display: flex; gap: 10px; }}
            input[type="text"] {{ flex-grow: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }}
            button {{ padding: 10px 20px; border: none; background-color: #007bff; color: white; border-radius: 4px; cursor: pointer; }}
            .navigacija {{ margin-bottom: 20px; display: flex; justify-content: flex-end; }}
            .navigacija a {{ text-decoration: none; color: #007bff; padding: 5px; }}
        </style>
    </head>
    <body>
        <div class="navigacija"><a href="/settings/instructions">Podešavanja instrukcija</a></div>
        <h2>🤖 NESAKO AI Asistent</h2>
        <div class="poruke">{poruke_html}</div>
        <form method="post" action="/">
            <input type="text" name="pitanje" placeholder="Postavi pitanje..." required>
            <button type="submit">Pošalji</button>
        </form>
    </body>
    </html>
    """

# --- Rute za chat ---
@app.get("/", response_class=HTMLResponse)
def index():
    return prikazi_chat()

@app.post("/", response_class=HTMLResponse)
async def odgovori(pitanje: str = Form(...)):
    global istorija_poruka
    global core_instructions

    if not istorija_poruka:
        istorija_poruka = [{"role": "system", "content": core_instructions}]

    istorija_poruka.append({"role": "user", "content": pitanje})

    data = {
        "model": "llama3-8b-8192",
        "messages": istorija_poruka,
        "temperature": 0.7
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        output = response.json()
        odgovor = output['choices'][0]['message']['content']
        istorija_poruka.append({"role": "assistant", "content": odgovor})
    except Exception as e:
        try:
            odgovor = f"(API greška: {response.text})"
        except:
            odgovor = f"(Greška: {e})"
        istorija_poruka.append({"role": "assistant", "content": odgovor})

    return RedirectResponse(url="/")

# --- Nove rute za podešavanja instrukcija ---
@app.get("/settings/instructions", response_class=HTMLResponse)
def get_instructions_page():
    """Prikazuje stranicu za uređivanje instrukcija."""
    trenutne_instrukcije = ucitaj_instrukcije()
    return f"""
    <html>
    <head>
        <title>Podešavanja instrukcija</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; max-width: 800px; margin: auto; background: #f0f2f5; }}
            textarea {{ width: 100%; height: 200px; padding: 10px; font-family: monospace; border: 1px solid #ddd; border-radius: 4px; }}
            form {{ margin-top: 20px; }}
            button {{ padding: 10px 20px; border: none; background-color: #28a745; color: white; border-radius: 4px; cursor: pointer; }}
            .navigacija {{ margin-bottom: 20px; }}
            .navigacija a {{ text-decoration: none; color: #007bff; padding: 5px; }}
        </style>
    </head>
    <body>
        <div class="navigacija"><a href="/">Nazad na chat</a></div>
        <h2>⚙ Uredi instrukcije za NESAKO AI</h2>
        <p>Ovde možeš da uneseš nova uputstva koja će definisati ponašanje NESAKO asistenta. Ove instrukcije se trajno čuvaju.</p>
        <form method="post" action="/update-instructions">
            <textarea name="nove_instrukcije" rows="10" required>{trenutne_instrukcije}</textarea>
            <br>
            <button type="submit">Sačuvaj instrukcije</button>
        </form>
    </body>
    </html>
    """

@app.post("/update-instructions")
async def update_instructions(nove_instrukcije: str = Form(...)):
    """Ažurira instrukcije i preusmerava na glavnu stranicu."""
    global core_instructions
    sacuvaj_instrukcije(nove_instrukcije)
    core_instructions = nove_instrukcije
    return RedirectResponse(url="/")
