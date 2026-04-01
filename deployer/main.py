from fastapi import FastAPI, Request

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    event = await request.json()
    print(event)
    return {"status": 200}
