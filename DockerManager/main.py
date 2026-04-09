from fastapi import FastAPI, Request

epp = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    events = await request.json()

    for event in events["events"]:
        if event["target"]["mediaType"] != "application/vnd.oci.image.manifest.v1+json":
            break

        print("--------------------------------------------------------------------")
        print(f"ID: {event['id']}")
        print(f"Timestamp: {event['timestamp']}")
        print()
        print(f"Actor: {event['actor']['name']}")
        print()
        print(f"Host: {event['request']['host']}")
        print(f"Address: {event['request']['addr']}")
        print()
        print(f"Repository: {event['target']['repository']}")
        print(f"Tag: {event['target']['tag']}")
        print(f"Image: {event['target']['repository']}:{event['target']['tag']}")
        print("--------------------------------------------------------------------")

    return {"status": 200}
