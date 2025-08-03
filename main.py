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

# Privremeno pamćenje cele sesije
istorija_poruka = [
    {"role": "system", "content": "Ti si NESAKO AI asistent. Odgovaraj jasno, korisno i na srpskom jeziku."}
]

@app.get("/", response_class=HTMLResponse)
def index():
    return prikazi_chat("")

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
        istorija_poruka.append({"role": "assistant", "content": odgovor})

    return prikazi_chat("")

def prikazi_chat(novi_odgovor):
    poruke_html = ""
    for poruka in istorija_poruka:
        if poruka["role"] == "user":
            poruke_html += f'<div class="bubble user">🧑‍💬 {poruka["content"]}</div>'
        elif poruka["role"] == "assistant":
            poruke_html += f'<div class="bubble bot">🤖 {poruka["content"]}</div>'

    return f"""
    <html>
    <head>
        <title>NESAKO - Chat</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; background-color: #f2f2f2; }}
            .chatbox {{ max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; }}
            .bubble {{ padding: 10px 15px; margin: 10px 0; border-radius: 15px; max-width: 80%; }}
            .user {{ background: #d1e7dd; text-align: left; border-top-left-radius: 0; }}
            .bot {{ background: #f8d7da; text-align: left; border-top-right-radius: 0; }}
            form {{ margin-top: 20px; }}
            input[type=text] {{ width: 100%; padding: 12px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px; }}
            button {{ padding: 10px 20px; font-size: 16px; background-color: #333; color: white; border: none; border-radius: 5px; margin-top: 10px; }}
            button:hover {{ background-color: #555; }}
        </style>
    </head>
    <body>
        <div class="chatbox">
            <h2>💬 NESAKO AI</h2>
            {poruke_html}
            <form method="post">
                <input type="text" name="pitanje" placeholder="Unesi novo pitanje..." required />
                <button type="submit">Pošalji</button>
            </form>
        </div>
    </body>
    </html>
    """