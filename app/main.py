from fastapi import FastAPI
from app.api.routes import calls, websockets

app = FastAPI(title="Twilio Gemini Voice Agent")

# Incluir las rutas
app.include_router(calls.router)
app.include_router(websockets.router)

@app.get("/")
async def root():
    return {"message": "Twilio Gemini Voice Agent Server is running (Modular Version)"}
