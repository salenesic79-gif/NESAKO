from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import requests
import os

app = FastAPI()

# === NESAKO: DODATNI KOD POČINJE OVDE ===

dodatni_kod = ""

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
        if dodatni_kod.strip():
            istorija_poruka.append({"role": "system", "content": f"Implementiraj sledeći kod:\n{dodatni_kod}"})

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
    <head><title>NESAKO Settings</title></head>
    <body style="font-family:sans-serif;padding:20px;">
        <h2>⚙ NESAKO - Kodiranje aplikacije</h2>
        <form method="post">
            <label><b>Uputstvo ponašanja:</b></label><br>
            <textarea name="nova_uputstva" rows="5" style="width:100%;">{core_instructions}</textarea><br><br>

            <label><b>Dodatni kod (simulirano):</b></label><br>
            <textarea name="dodatni_kod" rows="8" style="width:100%;font-family:monospace;">{dodatni_kod}</textarea><br><br>

            <button type="submit">💾 Dodaj kod i sačuvaj</button>
        </form>
        <br><a href="/">↩ Nazad na chat</a>
    </body>
    </html>
    """

@app.post("/settings", response_class=HTMLResponse)
async def update_settings(nova_uputstva: str = Form(...), dodatni_kod_: str = Form(...)):
    global core_instructions, dodatni_kod, istorija_poruka
    core_instructions = nova_uputstva.strip()
    dodatni_kod = dodatni_kod_.strip()
    istorija_poruka = []
    return RedirectResponse("/", status_code=303)

def prikazi_chat():
    poruke_html = ""
    for poruka in istorija_poruka:
        if poruka["role"] == "user":
            poruke_html += f'<div class="bubble user">🧑‍💬 {poruka["content"]}</div>'
        elif poruka["role"] == "assistant":
            poruke_html += f'<div class="bubble bot">🤖 {poruka["content"]}</div>'

    return f"""
    <html>
    <head>
        <title>NESAKO Chat</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f2f2f2; margin: 0; }}
            .topbar {{
                background-color: #333; color: white; padding: 10px 20px;
                display: flex; justify-content: space-between; align-items: center;
            }}
            .chatbox {{ max-width: 700px; margin: auto; background: white; padding: 20px; border-radius: 10px; margin-top: 10px; }}
            .bubble {{ padding: 10px 15px; margin: 10px 0; border-radius: 15px; max-width: 80%; }}
            .user {{ background: #d1e7dd; text-align: left; border-top-left-radius: 0; }}
            .bot {{ background: #f8d7da; text-align: left; border-top-right-radius: 0; }}
            form {{ margin-top: 20px; }}
            input[type=text] {{ width: 100%; padding: 12px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px; }}
            button {{ padding: 10px 20px; font-size: 16px; background-color: #333; color: white; border: none; border-radius: 5px; margin-top: 10px; }}
            button:hover {{ background-color: #555; }}
        </style>
        <script>
            window.onload = function() {{
                window.scrollTo(0, document.body.scrollHeight);
            }};
        </script>
    </head>
    <body>
        <div class="topbar">
            <div><b>NESAKO Chat</b></div>
            <div><a href="/settings" style="color:white;text-decoration:none;">⚙ Podešavanja</a></div>
        </div>
        <div class="chatbox">
            {poruke_html}
            <form method="post">
                <input type="text" name="pitanje" placeholder="Unesi novo pitanje..." required />
                <button type="submit">Pošalji</button>
            </form>
        </div>
    </body>
    </html>
    """