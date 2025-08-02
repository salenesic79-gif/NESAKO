from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
import openai
import os

app = FastAPI()
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.get("/", response_class=HTMLResponse)
def get_form():
    return """
    <html>
        <head><title>NESAKO chat</title></head>
        <body>
            <h2>Dobrodošao u NESAKO 💬</h2>
            <form method="post">
                <label>Unesi poruku:</label><br>
                <input type="text" name="pitanje" size="50"/><br><br>
                <input type="submit" value="Pošalji"/>
            </form>
        </body>
    </html>
    """

@app.post("/", response_class=HTMLResponse)
async def post_form(pitanje: str = Form(...)):
    odgovor = "Greška u vezi sa OpenAI."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": pitanje}]
        )
        odgovor = response.choices[0].message.content
    except Exception as e:
        odgovor = f"Greška: {e}"

    return f"""
    <html>
        <head><title>NESAKO odgovor</title></head>
        <body>
            <h2>Pitanje:</h2>
            <p>{pitanje}</p>
            <h2>Odgovor:</h2>
            <p>{odgovor}</p>
            <a href="/">↩ Nazad</a>
        </body>
    </html>
    """