from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from openai import OpenAI
import os

app = FastAPI()

# Ispravno za novu openai biblioteku (>= 1.0.0)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/", response_class=HTMLResponse)
def forma():
    return """
    <html>
        <head>
            <title>NESAKO Chat</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        </head>
        <body style="font-family:sans-serif; padding:20px;">
            <h2>🤖 Dobrodošao u NESAKO AI</h2>
            <form method="post">
                <input type="text" name="pitanje" id="pitanje" placeholder="Unesi pitanje..." 
                    style="width:100%; padding:10px; font-size:18px;" autofocus required/>
                <br><br>
                <button type="submit" style="padding:10px 20px; font-size:16px;">Pošalji</button>
            </form>
            <script>
                document.getElementById("pitanje").focus();
            </script>
        </body>
    </html>
    """

@app.post("/", response_class=HTMLResponse)
async def odgovori(pitanje: str = Form(...)):
    try:
        odgovor = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": pitanje}]
        )
        rezultat = odgovor.choices[0].message.content
    except Exception as e:
        rezultat = f"(Greška: {e})"

    return f"""
    <html>
        <head>
            <title>Odgovor iz NESAKO</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        </head>
        <body style="font-family:sans-serif; padding:20px;">
            <h2>Pitanje:</h2>
            <p>{pitanje}</p>
            <h2>Odgovor:</h2>
            <p>{rezultat}</p>
            <br>
            <a href="/" style="text-decoration:none; color:blue;">↩ Pošalji novo pitanje</a>
        </body>
    </html>
    """