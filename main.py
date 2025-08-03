from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
import requests
import os

app = FastAPI()

API_URL = "https://api.groq.com/openai/v1/chat/completions"
API_KEY = os.getenv("GROQ_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Globalna promenljiva za pamćenje razgovora (privremeno u RAM-u)
istorija_poruka = [
    {"role": "system", "content": "Ti si NESAKO AI asistent. Odgovaraj jasno, korisno i na srpskom jeziku."}
]

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <html>
        <head><title>NESAKO (sa memorijom)</title></head>
        <body style="font-family:sans-serif;padding:20px;">
            <h2>NESAKO sa Groq AI (pamti pitanja!)</h2>
            <form method="post">
                <input type="text" name="pitanje" placeholder="Unesi pitanje..." style="width:100%;padding:10px;" required />
                <br><br>
                <button type="submit" style="padding:10px 20px;">Pošalji</button>
            </form>
            <p style="font-size:12px;color:gray;">Napomena: Memorija se briše kada se stranica osveži.</p>
        </body>
    </html>
    """

@app.post("/", response_class=HTMLResponse)
async def odgovori(pitanje: str = Form(...)):
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

    return f"""
    <html>
        <head><title>Odgovor</title></head>
        <body style="font-family:sans-serif;padding:20px;">
            <h2>Pitanje:</h2><p>{pitanje}</p>
            <h2>Odgovor NESAKO:</h2><p>{odgovor}</p>
            <br><a href="/">↩ Novi upit</a>
        </body>
    </html>
    """