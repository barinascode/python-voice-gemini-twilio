import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.routes import calls, websockets

app = FastAPI(title="Twilio Gemini Voice Agent")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"\n--- NUEVA PETICIÓN ENTRANTE ---")
    print(f"Método: {request.method} | Ruta: {request.url.path}")
    print(f"IP Cliente: {request.client.host if request.client else 'Desconocida'}")
    
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        print(f"Completada en {process_time:.4f}s con Código: {response.status_code}")
        print("-------------------------------\n")
        return response
    except Exception as e:
        print(f"EXCEPCIÓN INTERNA DURANTE REQUEST {request.url.path}: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

# Incluir las rutas
app.include_router(calls.router)
app.include_router(websockets.router)

@app.get("/")
async def root():
    return {"message": "Twilio Gemini Voice Agent Server is running (Modular Version)"}
