from fastapi import FastAPI, Form
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

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <html>
        <head><title>NESAKO (Groq AI)</title></head>
        <body style="font-family:sans-serif;padding:20px;">
            <h2>NESAKO sa Groq AI</h2>
            <form method="post">
                <input type="text" name="pitanje" placeholder="Unesi pitanje..." style="width:100%;padding:10px;" required />
                <br><br>
                <button type="submit" style="padding:10px 20px;">Pošalji</button>
            </form>
        </body>
    </html>
    """

@app.post("/", response_class=HTMLResponse)
async def odgovori(pitanje: str = Form(...)):
    data = {
        "model": "mixtral-8x7b-32768",
        "messages": [
            {"role": "system", "content": "Ti si pomoćnik NESAKO AI. Odgovaraj jasno, korisno i precizno."},
            {"role": "user", "content": pitanje}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        output = response.json()
        odgovor = output['choices'][0]['message']['content']
    except Exception as e:
        odgovor = f"(Greška: {e})"

    return f"""
    <html>
        <head><title>Odgovor</title></head>
        <body style="font-family:sans-serif;padding:20px;">
            <h2>Pitanje:</h2><p>{pitanje}</p>
            <h2>Odgovor:</h2><p>{odgovor}</p>
            <br><a href="/">↩ Novi upit</a>
        </body>
    </html>
    """