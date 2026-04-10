from fastapi import FastAPI, Request
from src.DockerImage import DockerImage

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    events = await request.json()

    for event in events["events"]:
        if event["target"]["mediaType"] != "application/vnd.oci.image.manifest.v1+json":
            break

        dockerImage = DockerImage(
            event["id"],
            event["timestamp"],
            event["actor"]["name"],
            event["request"]["host"],
            event["request"]["addr"],
            event["target"]["repository"],
            event["target"]["tag"],
        )

        print(dockerImage)

    return {"status": 200}
