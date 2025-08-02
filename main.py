from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Zdravo iz NESAKO aplikacije!"}
  Dodao main.py