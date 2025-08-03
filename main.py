from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import requests
import os

app = FastAPI()

# === NESAKO: DODATNI KOD POČINJE OVDE ===

# 👇 Ovde ubacuj dodatne funkcije i pravila
# Primer: NESAKO postaje matematički asistent
# def saberi(a, b): return a + b

# === NESAKO: DODATNI KOD ZAVRŠAVA OVDE ===

API_URL = "https://api.groq.com/openai/v1/chat/completions"
API_KEY = os.getenv("GROQ_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

istorija_poruka = []
core_instructions = "Ti si NESAKO AI asistent. Odgovaraj jasno, korisno i na srpskom jeziku."

@app.get("/", response_class=HTMLResponse)
def index():
    return prikazi_chat()

@app.post("/", response_class=HTMLResponse)
async def odgovori(pitanje: str = Form(...)):
    global istorija_poruka

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

    return prikazi_chat()

@app.get("/settings", response_class=HTMLResponse)
def settings():
    return f"""
    <html>
    <head><title>NESAKO Podešavanja</title></head>
    <body style="font-family:sans-serif;padding:20px;">
        <h2>⚙ NESAKO - Kodiranje aplikacije</h2>
        <form method="post">
            <textarea name="nova_uputstva" rows="10" style="width:100%;font-family:monospace;" placeholder="Unesi instrukcije koje NESAKO koristi prilikom odgovora...">{core_instructions}</textarea