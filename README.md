# Agente de Voz con Gemini 2.5 y Twilio

Este proyecto implementa un agente de voz telefónico en tiempo real para producción utilizando Python (FastAPI), la API REST / Media Streams de Twilio, y la API Multimodal Live de Google Gemini (WebSockets).

El objetivo es lograr una conversación telefónica inteligente, natural y fluida con muy baja latencia, con soporte nativo para interrupciones (barge-in). El agente toma la iniciativa conversacional tan pronto como la llamada es contestada.

## Arquitectura y Flujo

1. El usuario envía un POST al servidor para iniciar una llamada.
2. El servidor ordena a Twilio llamar al destino.
3. Cuando el destino contesta, Twilio establece un túnel WebSocket (`/stream`) con el servidor.
4. El servidor abre simultáneamente un túnel concurrente hacia Google Gemini API.
5. El servidor traduce el audio g.711 mu-law (8kHz) de Twilio a PCM Lineal (16kHz/24kHz) para Gemini al vuelo en fragmentos ultra-pequeños, reduciendo drásticamente cualquier latencia.

---

## Requisitos de Despliegue en Producción (VPS Linux)

Para operar de forma persistente y que Twilio no rechace la conexión WebSocket bidireccional, es estricto requerir de un entorno con Proxy Inverso y certificados SSL (HTTPS/WSS).

*   **SO:** Servidor Linux (Ubuntu 20.04/22.04 recomendado).
*   **Python:** 3.8.10+.
*   **Web Server:** Nginx.
*   **Certificados:** Let's Encrypt (Certbot).
*   **Cuentas:** Twilio (con número habilitado) y Google AI Studio.

## 1. Configuración del SO y Entorno de Python

Clona tu repositorio en el VPS de Linux en `/var/www/` o tu directorio de preferencia y prepara el entorno virtual:

```bash
# Instalar python3.8-venv si no lo tienes
sudo apt update
sudo apt install python3.8-venv -y

# Crear y activar entorno
python3.8 -m venv .venv
source .venv/bin/activate

# Instalar los requerimientos de la rama modular
pip install fastapi "uvicorn[standard]" twilio websockets python-dotenv
```

## 2. Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto.
El valor de `PUBLIC_URL` debe ser tu **dominio seguro con SSL** (p.ej. `https://api.midominio.com`).

```env
TWILIO_ACCOUNT_SID=TuAccountSIDDeTwilio
TWILIO_AUTH_TOKEN=TuAuthTokenDeTwilio
TWILIO_PHONE_NUMBER=TuNumeroDeTwilio

GEMINI_API_KEY=TuClaveAPIdeGoogleGemini

PUBLIC_URL=https://api.midominio.com
```

## 3. Ejecución como Servicio Constante (PM2 / Systemd)

La aplicación FastApi nativamente está configurada para correr por defecto en el puerto `8080` de tu ambiente local.
*Ejemplo iniciando con screen o tmux en background:*

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## 4. Configuración del Proxy Reverso Nginx + SSL

Twilio requiere conexión estricta vía WebSockets seguros (`wss://`). Para lograr esto, usa Nginx para enrutar el puerto `8080` de Python hacia los puertos `80/443` estándar en la web, configurando los headers "Upgrade" necesarios.

Crea un VirtualHost simplificado en Nginx (`/etc/nginx/sites-available/api_agent`):

```nginx
server {
    server_name api.midominio.com;

    location / {
        proxy_pass http://127.0.0.0:8080;
        
        # Soportes necesarios para WSS (WebSockets)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Luego ejecuta certbot para otorgar el cifrado TSL automáticamente al bloque anterior:
```bash
sudo certbot --nginx -d api.midominio.com
sudo systemctl reload nginx
```

## 5. Iniciar la Llamada de Prueba

Con el servidor Python andando, Nginx manejando el SSL, y el `.env` apuntando a `PRIVATE_URL=https://api.midominio.com`, envía la solicitud:

```bash
curl -X POST https://api.midominio.com/make-call \
     -H "Content-Type: application/json" \
     -d '{"destination_number": "+58414XXXXXXX"}'
```

    1. El servidor enviará la petición a Twilio para que llame al `destination_number`.
    2. Cuando contestes la llamada, Twilio iniciará el TwiML `<Connect><Stream>` apuntando al WebSocket de tu servidor (`/stream`).
    3. Python conectará automáticamente con Gemini por WebSocket y enviará el audio de tu llamada, mientras simultáneamente convierte el audio de respuesta de Gemini y lo inyecta a Twilio en tiempo real.
    4. El agente te saludará inmediatamente y podrás conversar fluidamente.

## Características Técnicas

-   **Conversión de Audio Bidireccional Nativa:** El proyecto utiliza transcodificación sobre la memoria por chunks para convertir entre el formato de la red telefónica (G.711 mu-law a 8kHz) y el formato requerido por Gemini (PCM lineal a 16kHz/24kHz) simultáneamente en tiempo real.
-   **Interrupciones (Barge-In):** Si interrumpes al agente mientras él está hablando, el evento `interrupted` de Gemini Live API enviará una señal asíncrona a Twilio para limpiar su buffer de reproducción al instante, frenando el discurso en seco replicando la dinámica humana.
