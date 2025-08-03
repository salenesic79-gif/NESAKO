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
        "model": "mixtral-8x7b",
        "messages": [
            {"role": "system", "content": "Ti si NESAKO AI asistent. Odgovaraj korisno, jasno i na srpskom jeziku."},
            {"role": "user", "content": pitanje}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        output = response.json()

        # Ispiši kompletan API odgovor za debag
        print("=== GROQ ODGOVOR ===")
        print(output)

        # Izvuci odgovor
        odgovor = output['choices'][0]['message']['content']
    except Exception as e:
        try:
            error_text = response.text
            odgovor = f"(API greška: {error_text})"
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