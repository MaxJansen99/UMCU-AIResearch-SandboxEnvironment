from fastapi import FastAPI, Request
from src.translator import Translator

app = FastAPI()
translator = Translator()


@app.post("/webhook")
async def webhook(request: Request):
    event = await request.json()

    Translator.read_json(event)

    return {"status": 200}
