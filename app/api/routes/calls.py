import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect

from app.core.config import settings

router = APIRouter()

twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN) if settings.TWILIO_ACCOUNT_SID else None

class CallRequest(BaseModel):
    destination_number: str

@router.post("/make-call")
async def make_call(req: CallRequest):
    """Inicia una llamada saliente utilizando Twilio."""
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio no está configurado correctamente.")
    
    if settings.PUBLIC_URL == "none" or not settings.PUBLIC_URL.startswith("http"):
        raise HTTPException(status_code=400, detail="Falta un PUBLIC_URL válido en config (p.ej. http://IP:PUERTO o https://dominio.com)")

    try:
        call = twilio_client.calls.create(
            to=req.destination_number,
            from_=settings.TWILIO_PHONE_NUMBER,
            url=f"{settings.PUBLIC_URL}/twiml",
            method="POST"
        )
        return {"status": "success", "call_sid": call.sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/twiml")
async def get_twiml(request: Request):
    """Devuelve el TwiML que conecta la llamada con nuestro WebSocket."""
    # Extraemos manualmente el CallSid de los formData que envía Twilio
    body = await request.body()
    print(f"Twilio disparó /twiml con payload: {body.decode('utf-8')}")

    # Reemplazamos http/https por ws/wss para construir el puente WebSocket
    host = settings.PUBLIC_URL.replace("https://", "").replace("http://", "")
    prot = "wss" if settings.PUBLIC_URL.startswith("https") else "ws"
    
    response = VoiceResponse()
    connect = Connect()
    
    # IMPORTANTE: Definir los tracks para evitar que se cuelgue. (bothbp significa dual bidireccional)
    # Algunos entornos de Twilio requieren `name` o que declaremos explícitamente el tipo de track.
    connect.stream(url=f"{prot}://{host}/stream", track="both_tracks")
    
    response.append(connect)
    
    twiml_str = str(response)
    print(f"Generando TwiML:\n{twiml_str}")
    
    return Response(content=twiml_str, media_type="text/xml")
