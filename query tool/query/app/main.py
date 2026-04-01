from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import dicom_domain, health, query, ui


app = FastAPI(
    title="UMC DICOM Query API",
    version="0.1.0",
)

frontend_dir = Path(__file__).resolve().parents[1] / "frontend"

app.include_router(health.router)
app.include_router(query.router)
app.include_router(dicom_domain.router)
app.include_router(ui.router)
app.mount("/assets", StaticFiles(directory=frontend_dir), name="frontend-assets")


@app.get("/dashboard", include_in_schema=False)
def frontend_index() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")
