from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from openai import OpenAI
import os

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/", response_class=HTMLResponse)
def get_form():
    return """
    <html>
        <head>
            <title>NESAKO Chat</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family:sans-serif;padding:20px;">
            <h2>💬 Dobrodošao u NESAKO</h2>
            <form method="post">
                <input type="text" name="pitanje" id="pitanje" placeholder="Unesi poruku" 
                       style="width:100%;padding:10px;font-size:18px;" autofocus required/>
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
async def post_form(pitanje: str = Form(...)):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": pitanje}
            ]
        )
        odgovor = response.choices[0].message.content
    except Exception as e:
        odgovor = f"(Greška: {e})"

    return f"""
    <html>
        <head>
            <title>Odgovor iz NESAKO</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family:sans-serif;padding:20px;">
            <h2>Pitanje:</h2>
            <p>{pitanje}</p>
            <h2>Odgovor:</h2>
            <p>{odgovor}</p>
            <br>
            <a href="/">↩ Pošalji novo pitanje</a>
        </body>
    </html>
    """