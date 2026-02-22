import json
import asyncio
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from getpass import getpass

from app.core.config import settings
from app.utils.audio import mulaw_to_pcm_16k_base64, pcm_24k_base64_to_mulaw_base64

router = APIRouter()

@router.websocket("/stream")
async def websocket_endpoint(twilio_ws: WebSocket):
    """Recibe la transmisión de audio de Twilio en formato mu-law de 8kHz y hace puente con Gemini."""
    await twilio_ws.accept()
    
    stream_sid = None
    
    gemini_ws_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={settings.GEMINI_API_KEY}"
    
    try:
        async with websockets.connect(gemini_ws_url) as gemini_ws:
            print("Conectado a Gemini API")
            
            # 1. Enviar el Setup inicial a Gemini
            setup_message = {
                "setup": {
                    "model": settings.GEMINI_MODEL,
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {
                                    "voiceName": "Aoede" # Opciones: Puck, Charon, Aoede, Fenrir, Kore
                                }
                            }
                        }
                    }
                }
            }
            await gemini_ws.send(json.dumps(setup_message))
            setup_response = await gemini_ws.recv()
            print("Setup Gemini response:", setup_response)
            
            # 2. Instruir a Gemini para que hable primero
            initial_prompt = {
                "clientContent": {
                    "turns": [
                        {
                            "role": "user",
                            "parts": [{"text": "Hola! Eres un asistente de voz inteligente respondiendo en una llamada telefónica en tiempo real. Por favor, sé muy breve, natural y conversacional. Saluda de manera entusiasta para iniciar la charla."}]
                        }
                    ],
                    "turnComplete": True
                }
            }
            await gemini_ws.send(json.dumps(initial_prompt))
            print("Prompt inicial enviado a Gemini para forzar la iniciativa.")

            # Funciones concurrentes para escuchar ambos WebSockets
            async def receive_from_twilio():
                nonlocal stream_sid
                try:
                    while True:
                        data = await twilio_ws.receive_text()
                        message = json.loads(data)
                        
                        event = message.get("event")
                        if event == "connected":
                            print("Llamada Twilio conectada al WebSocket")
                        elif event == "start":
                            stream_sid = message["start"]["streamSid"]
                            print(f"Twilio Media Stream Iniciado: {stream_sid}")
                        elif event == "media":
                            # mu-law -> PCM 16kHz
                            payload = message["media"]["payload"]
                            pcm_16k_b64 = mulaw_to_pcm_16k_base64(payload)
                            
                            audio_msg = {
                                "realtimeInput": {
                                    "mediaChunks": [
                                        {
                                            "mimeType": "audio/pcm;rate=16000",
                                            "data": pcm_16k_b64
                                        }
                                    ]
                                }
                            }
                            await gemini_ws.send(json.dumps(audio_msg))
                        elif event == "stop":
                            print(f"Twilio Media Stream Detenido: {stream_sid}")
                            break
                        elif event == "mark":
                            pass
                except WebSocketDisconnect:
                    print("Twilio WS Desconectado desde el cliente telefónico")
                except Exception as e:
                    print(f"Error en receive_from_twilio: {e}")

            async def receive_from_gemini():
                nonlocal stream_sid
                try:
                    async for message in gemini_ws:
                        response = json.loads(message)
                        
                        # 1. Chequear si hay errores arrojados por Gemini
                        if "error" in response:
                            print(f"ERROR DESDE GEMINI: {response['error']}")
                            continue
                            
                        # 2. Parsear el audio de Gemini
                        if "serverContent" in response:
                            model_turn = response["serverContent"].get("modelTurn")
                            if model_turn:
                                for part in model_turn.get("parts", []):
                                    if "inlineData" in part:
                                        # PCM 24kHz -> mu-law 8kHz
                                        pcm_data_b64 = part["inlineData"]["data"]
                                        mu_law_b64 = pcm_24k_base64_to_mulaw_base64(pcm_data_b64)
                                        
                                        if stream_sid:
                                            media_msg = {
                                                "event": "media",
                                                "streamSid": stream_sid,
                                                "media": {
                                                    "payload": mu_law_b64
                                                }
                                            }
                                            await twilio_ws.send_text(json.dumps(media_msg))
                                            
                        # Manejo de Interrupciones (Barge-in / Cancelación)
                        if response.get("serverContent", {}).get("interrupted"):
                            print("Gemini notificó una interrupción (barge-in)")
                            if stream_sid:
                                clear_msg = {
                                    "event": "clear",
                                    "streamSid": stream_sid
                                }
                                await twilio_ws.send_text(json.dumps(clear_msg))
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"Gemini WS Desconectado: {e}")
                except Exception as e:
                    print(f"Error en receive_from_gemini: {e}")

            print("Iniciando tareas concurrentes Twi-Gem...")
            # Correr ambas tareas
            task_twilio = asyncio.create_task(receive_from_twilio())
            task_gemini = asyncio.create_task(receive_from_gemini())
            
            done, pending = await asyncio.wait(
                [task_twilio, task_gemini],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for p in pending:
                p.cancel()

    except Exception as e:
        print(f"Error general WebSocket: {e}")
    finally:
        print("Cerrando sesión WebSocket Twilio")
