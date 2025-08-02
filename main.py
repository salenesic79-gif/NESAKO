from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import openai
import os

app = FastAPI()
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.get("/", response_class=HTMLResponse)
def get_form():
    return """
    <!DOCTYPE html>
    <html lang="sr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NESAKO chat</title>
    </head>
    <body style="font-family:sans-serif;padding:20px;">
        <h2>💬 Dobrodošao u NESAKO</h2>
        <form method="post">
            <input type="text" name="pitanje" id="pitanje" placeholder="Unesi poruku ovde" 
                style="width:90%;padding:12px;font-size:18px;" autofocus required/>
            <br><br>
            <button type="submit" style="padding:10px 20px;font-size:16px;">Pošalji</button>
        </form>
        <script>
            document.getElementById("pitanje").focus();
        </script>
    </body>
    </html>
    """

@app.post("/", response_class=HTMLResponse)
async def chat_response(pitanje: str = Form(...)):
    try:
        odgovor = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": pitanje}]
        ).choices[0].message.content
    except Exception as e:
        odgovor = f"(Greška: {e})"

    return f"""
    <!DOCTYPE html>
    <html lang="sr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NESAKO odgovor</title>
    </head>
    <body style="font-family:sans-serif;padding:20px;">
        <h2>Pitanje:</h2>
        <p>{pitanje}</p>
        <h2>Odgovor:</h2>
        <p>{odgovor}</p>
        <br>
        <a href="/">↩ Nazad</a>
    </body>
    </html>
    """